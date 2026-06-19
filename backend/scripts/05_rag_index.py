"""05_rag_index.py — Embed golden record chunks and store in pgvector."""
import sys
import json
import time
import uuid
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import openai as openai_lib
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(settings.sync_database_url)
Session = sessionmaker(engine)

CHUNK_GROUPS = {
    "identity": ["first_name", "last_name", "full_legal_name", "date_of_birth", "nationality"],
    "contact": ["email", "phone", "address_line1", "city", "country"],
    "kyc_compliance": ["kyc_status", "kyc_tier", "kyc_verified_at", "kyc_expiry_at"],
    "risk_profile": ["risk_rating", "risk_score"],
    "sanctions_pep": ["is_pep", "pep_type", "pep_detected_at", "is_sanctioned", "sanctions_list", "sanctions_detected_at"],
    "customer_lifecycle": ["onboarded_at", "source_count", "confidence_score"],
    "confidence_metadata": ["confidence_score", "winning_sources", "source_count"],
}

BOOL_LABELS = {"is_pep": "PEP Status", "is_sanctioned": "Sanctions Status"}


def build_chunk_text(customer: dict, chunk_type: str, fields: list[str]) -> str:
    cid = str(customer.get("customer_id", ""))[:8]
    full_name = customer.get("full_legal_name") or f"{customer.get('first_name','')} {customer.get('last_name','')}".strip()
    lines = [
        f"Customer {full_name} (ID: {cid}...)",
        f"[CHUNK_TYPE: {chunk_type.upper()}]",
    ]
    for field in fields:
        val = customer.get(field)
        if val is None or str(val).strip() in ("", "None", "nan", "NaT"):
            continue
        label = BOOL_LABELS.get(field) or field.replace("_", " ").title()
        if field in BOOL_LABELS:
            val = "Yes" if val in (True, "True", "true", "1", 1) else "No"
        elif "score" in field and isinstance(val, (int, float)):
            val = f"{float(val) * 100:.1f}%"
        elif "at" in field and val:
            try:
                dt = datetime.fromisoformat(str(val)[:19])
                val = dt.strftime("%b %d, %Y")
            except Exception:
                pass
        lines.append(f"{label}: {val}")

    meta = (
        f"[Confidence: {float(customer.get('confidence_score') or 0) * 100:.1f}%] "
        f"[Sources: {customer.get('source_count', 1)}] "
        f"[Updated: {datetime.utcnow().strftime('%Y-%m-%d')}]"
    )
    lines.append(meta)
    return "\n".join(lines)


def embed_batch(texts: list[str], client) -> list[list[float]]:
    batch_size = 100
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(input=batch, model="text-embedding-3-small")
        all_embeddings.extend([d.embedding for d in response.data])
        if i + batch_size < len(texts):
            time.sleep(0.5)
    return all_embeddings


def index_all_customers(db_engine, openai_client) -> dict:
    with Session() as db:
        rows = db.execute(text("SELECT * FROM golden_records LIMIT 5000")).mappings().all()
        customers = [dict(r) for r in rows]

    print(f"Indexing {len(customers)} customers...")
    total_chunks = 0
    estimated_tokens = 0
    batch_size = 50

    for batch_start in range(0, len(customers), batch_size):
        batch = customers[batch_start:batch_start + batch_size]
        sys.stdout.write(f"\rIndexing: {batch_start + len(batch)}/{len(customers)} customers...")
        sys.stdout.flush()

        chunk_texts = []
        chunk_meta = []

        for cust in batch:
            cid = str(cust["customer_id"])
            for chunk_type, fields in CHUNK_GROUPS.items():
                text_content = build_chunk_text(cust, chunk_type, fields)
                if len(text_content) < 20:
                    continue
                chunk_texts.append(text_content)
                chunk_meta.append({"customer_id": cid, "chunk_type": chunk_type, "content": text_content})
                estimated_tokens += len(text_content.split()) * 1.3

        if not chunk_texts:
            continue

        embeddings = embed_batch(chunk_texts, openai_client)

        with Session() as db:
            # Delete existing chunks for this batch
            cids = [m["customer_id"] for m in chunk_meta]
            for cid in set(cids):
                db.execute(text("DELETE FROM rag_chunks WHERE customer_id = cast(:cid as uuid)"), {"cid": cid})

            for meta, embedding in zip(chunk_meta, embeddings):
                vec_str = "[" + ",".join(str(v) for v in embedding) + "]"
                db.execute(text("""
                    INSERT INTO rag_chunks (id, customer_id, chunk_type, content, metadata, embedding, created_at, updated_at)
                    VALUES (gen_random_uuid(), cast(:cid as uuid), :ctype, :content, cast(:meta as jsonb), cast(:emb as vector), NOW(), NOW())
                """), {
                    "cid": meta["customer_id"],
                    "ctype": meta["chunk_type"],
                    "content": meta["content"],
                    "meta": json.dumps({"chunk_type": meta["chunk_type"], "updated_at": datetime.utcnow().isoformat()}),
                    "emb": vec_str,
                })
            db.commit()
        total_chunks += len(chunk_texts)

    cost_estimate = (estimated_tokens / 1_000_000) * 0.02
    avg_chunks = total_chunks / max(len(customers), 1)
    print(f"\n✅ Indexed {len(customers)} customers × {avg_chunks:.1f} chunks = {total_chunks} total chunks")
    print(f"   Embedding cost estimate: ${cost_estimate:.2f} (text-embedding-3-small @ $0.02/1M tokens)")

    return {"customers_indexed": len(customers), "chunks_created": total_chunks, "cost_estimate": cost_estimate}


if __name__ == "__main__":
    client = openai_lib.OpenAI(api_key=settings.openai_api_key)
    result = index_all_customers(engine, client)
    print(f"\nDone: {result}")
