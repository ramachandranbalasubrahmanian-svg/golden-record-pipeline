"""Hybrid retrieval — pgvector cosine similarity + BM25 keyword search + RRF re-ranking."""
from __future__ import annotations
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text

BOOST_CONFIG = {
    "regulatory_lock_boost": 1.30,
    "recency_boost": 1.15,
    "confidence_boost": 1.10,
    "exact_name_boost": 1.20,
}

REGULATORY_CHUNK_TYPES = {"kyc_compliance", "sanctions_pep"}


def embed_query(question: str, openai_client) -> list[float]:
    response = openai_client.embeddings.create(
        input=[question], model="text-embedding-3-small"
    )
    return response.data[0].embedding


def vector_search(
    query_embedding: list[float],
    entity_id: Optional[str],
    db: Session,
    top_k: int = 20,
) -> list[dict]:
    vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
    sql = text("""
        SELECT id, customer_id, chunk_type, content, metadata,
               1 - (embedding <=> :query_vec::vector) AS similarity_score
        FROM rag_chunks
        WHERE (:entity_id IS NULL OR customer_id = :entity_id::uuid)
        ORDER BY embedding <=> :query_vec::vector
        LIMIT :top_k
    """)
    rows = db.execute(sql, {"query_vec": vec_str, "entity_id": entity_id, "top_k": top_k}).fetchall()
    return [
        {
            "id": str(row.id),
            "customer_id": str(row.customer_id),
            "chunk_type": row.chunk_type,
            "content": row.content,
            "metadata": row.metadata or {},
            "similarity_score": float(row.similarity_score),
        }
        for row in rows
    ]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def bm25_search(question: str, candidate_chunks: list[dict], top_k: int = 20) -> list[dict]:
    if not candidate_chunks:
        return []
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        return candidate_chunks[:top_k]

    corpus = [_tokenize(c["content"]) for c in candidate_chunks]
    bm25 = BM25Okapi(corpus)
    query_tokens = _tokenize(question)
    scores = bm25.get_scores(query_tokens)

    max_score = max(scores) if max(scores) > 0 else 1.0
    ranked = sorted(
        enumerate(scores), key=lambda x: x[1], reverse=True
    )[:top_k]

    results = []
    for idx, score in ranked:
        chunk = dict(candidate_chunks[idx])
        chunk["bm25_score"] = score / max_score
        results.append(chunk)
    return results


def reciprocal_rank_fusion(
    vector_results: list[dict],
    bm25_results: list[dict],
    k: int = 60,
) -> list[dict]:
    scores: dict[str, float] = {}
    all_chunks: dict[str, dict] = {}

    for rank, chunk in enumerate(vector_results, 1):
        cid = chunk["id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        all_chunks[cid] = chunk

    for rank, chunk in enumerate(bm25_results, 1):
        cid = chunk["id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        all_chunks[cid] = chunk

    merged = sorted(all_chunks.values(), key=lambda c: scores.get(c["id"], 0.0), reverse=True)
    for chunk in merged:
        chunk["rrf_score"] = scores.get(chunk["id"], 0.0)
    return merged


def apply_boosts(chunks: list[dict], question: str, customer_name: Optional[str] = None) -> list[dict]:
    now = datetime.utcnow()
    result = []
    for chunk in chunks:
        score = chunk.get("rrf_score", chunk.get("similarity_score", 0.0))
        ct = chunk.get("chunk_type", "")
        meta = chunk.get("metadata") or {}
        content = chunk.get("content", "")

        if ct in REGULATORY_CHUNK_TYPES:
            score *= BOOST_CONFIG["regulatory_lock_boost"]

        updated_str = meta.get("updated_at") or meta.get("created_at")
        if updated_str:
            try:
                updated = datetime.fromisoformat(str(updated_str))
                if (now - updated).days <= 30:
                    score *= BOOST_CONFIG["recency_boost"]
            except Exception:
                pass

        conf = meta.get("confidence_score", 0)
        if float(conf or 0) > 0.90:
            score *= BOOST_CONFIG["confidence_boost"]

        if customer_name and customer_name.lower() in content.lower():
            score *= BOOST_CONFIG["exact_name_boost"]

        chunk = dict(chunk)
        chunk["final_score"] = score
        result.append(chunk)

    return sorted(result, key=lambda c: c["final_score"], reverse=True)


def retrieve(
    question: str,
    entity_id: Optional[str],
    persona: str,
    db: Session,
    openai_client,
    top_k: int = 5,
) -> list[dict]:
    embedding = embed_query(question, openai_client)
    vector_results = vector_search(embedding, entity_id, db, top_k=20)
    bm25_results = bm25_search(question, vector_results, top_k=20)
    merged = reciprocal_rank_fusion(vector_results, bm25_results)
    boosted = apply_boosts(merged, question)
    return boosted[:top_k]
