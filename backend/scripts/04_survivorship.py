"""04_survivorship.py — Resolve entity clusters into Golden Records with lineage."""
import sys
import uuid
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.pipeline.survivorship import resolve_cluster

engine = create_engine(settings.sync_database_url)
Session = sessionmaker(engine)


def _safe(v):
    if v is None:
        return None
    s = str(v).strip()
    return None if s in ("", "nan", "None", "NaT") else s


def main():
    print("Loading entity clusters...")
    with Session() as db:
        clusters = [dict(c) for c in db.execute(text("SELECT * FROM entity_clusters")).mappings().all()]
        print(f"  Found {len(clusters)} clusters")
        src_rows = db.execute(text("SELECT * FROM source_records WHERE quarantined = false")).mappings().all()
        src_map = {str(r["id"]): dict(r) for r in src_rows}

    print("Resolving survivorship for each cluster...")
    golden_records = []
    all_lineage = []
    source_wins: dict[str, int] = defaultdict(int)

    for cluster in clusters:
        record_ids = cluster.get("record_ids") or []
        if isinstance(record_ids, str):
            try:
                record_ids = json.loads(record_ids)
            except Exception:
                record_ids = []

        recs = [src_map[rid] for rid in record_ids if rid in src_map]
        if not recs:
            continue

        result = resolve_cluster(recs)
        gr = result["golden"]
        lineage = result["lineage"]

        customer_id = _safe(recs[0].get("customer_id")) or str(uuid.uuid4())

        for entry in lineage:
            if entry.get("winning_source"):
                source_wins[entry["winning_source"]] += 1

        golden_records.append((customer_id, cluster["cluster_id"], gr))
        all_lineage.append((customer_id, lineage))

    # Singletons — source records not in any cluster
    with Session() as db:
        clustered_ids = set()
        for c in clusters:
            rids = c.get("record_ids") or []
            if isinstance(rids, str):
                try:
                    rids = json.loads(rids)
                except Exception:
                    rids = []
            clustered_ids.update(rids)

        singleton_rows = db.execute(text(
            "SELECT * FROM source_records WHERE quarantined = false"
        )).mappings().all()

        for row in singleton_rows:
            rid = str(row["id"])
            if rid not in clustered_ids:
                cid = _safe(row.get("customer_id")) or str(uuid.uuid4())
                gr_simple = dict(row)
                gr_simple["confidence_score"] = 0.55
                gr_simple["source_count"] = 1
                gr_simple["winning_sources"] = {
                    k: row.get("source_system") for k in ["first_name", "last_name", "email"]
                }
                golden_records.append((cid, None, gr_simple))
                all_lineage.append((cid, []))

    print(f"Writing {len(golden_records)} golden records to database...")
    with Session() as db:
        for i, (customer_id, cluster_id, gr) in enumerate(golden_records):
            fn = _safe(gr.get("first_name"))
            ln = _safe(gr.get("last_name"))
            db.execute(text("""
                INSERT INTO golden_records (
                    customer_id, cluster_id, first_name, last_name, full_legal_name,
                    date_of_birth, email, phone, address_line1, city, country, nationality,
                    kyc_status, kyc_tier, kyc_verified_at, kyc_expiry_at,
                    risk_rating, risk_score, is_pep, pep_type, pep_detected_at,
                    is_sanctioned, sanctions_list, sanctions_detected_at,
                    confidence_score, source_count, winning_sources, created_at, updated_at
                ) VALUES (
                    cast(:cid as uuid), :cluster_id, :fn, :ln, :full_name,
                    :dob, :email, :phone, :addr, :city, :country, :nationality,
                    :kyc_status, :kyc_tier, :kyc_verified_at, :kyc_expiry_at,
                    :risk_rating, :risk_score, :is_pep, :pep_type, :pep_detected_at,
                    :is_sanctioned, :sanctions_list, :sanctions_detected_at,
                    :conf, :src_count, cast(:winning as jsonb), NOW(), NOW()
                ) ON CONFLICT (customer_id) DO UPDATE SET
                    confidence_score = EXCLUDED.confidence_score,
                    source_count = EXCLUDED.source_count,
                    updated_at = NOW()
            """), {
                "cid": customer_id,
                "cluster_id": cluster_id,
                "fn": fn,
                "ln": ln,
                "full_name": _safe(gr.get("full_legal_name") or f"{fn or ''} {ln or ''}".strip()),
                "dob": _safe(gr.get("date_of_birth")),
                "email": _safe(gr.get("email")),
                "phone": _safe(gr.get("phone")),
                "addr": _safe(gr.get("address_line1")),
                "city": _safe(gr.get("city")),
                "country": _safe(gr.get("country")),
                "nationality": _safe(gr.get("nationality")),
                "kyc_status": _safe(gr.get("kyc_status")),
                "kyc_tier": _safe(gr.get("kyc_tier")),
                "kyc_verified_at": _safe(gr.get("kyc_verified_at")),
                "kyc_expiry_at": _safe(gr.get("kyc_expiry_at")),
                "risk_rating": _safe(gr.get("risk_rating")),
                "risk_score": float(gr.get("risk_score") or 0),
                "is_pep": bool(gr.get("is_pep")),
                "pep_type": _safe(gr.get("pep_type")),
                "pep_detected_at": _safe(gr.get("pep_detected_at")),
                "is_sanctioned": bool(gr.get("is_sanctioned")),
                "sanctions_list": _safe(gr.get("sanctions_list")),
                "sanctions_detected_at": _safe(gr.get("sanctions_detected_at")),
                "conf": float(gr.get("confidence_score") or 0.5),
                "src_count": int(gr.get("source_count") or 1),
                "winning": json.dumps(gr.get("winning_sources") or {}),
            })
            if (i + 1) % 500 == 0:
                db.commit()
                print(f"  {i + 1}/{len(golden_records)} golden records written...")
        db.commit()

    print("Writing lineage entries...")
    with Session() as db:
        count = 0
        for customer_id, lineage in all_lineage:
            for entry in lineage:
                db.execute(text("""
                    INSERT INTO attribute_lineage (
                        id, customer_id, attribute_name, winning_value, winning_source,
                        survivorship_rule, confidence, is_regulatory_lock, competing_sources, resolved_at
                    ) VALUES (
                        gen_random_uuid(), cast(:cid as uuid), :attr, :val, :src,
                        :rule, :conf, :lock, cast(:competing as jsonb), NOW()
                    ) ON CONFLICT (customer_id, attribute_name) DO UPDATE SET
                        winning_value = EXCLUDED.winning_value,
                        winning_source = EXCLUDED.winning_source,
                        resolved_at = NOW()
                """), {
                    "cid": customer_id,
                    "attr": entry["attribute_name"],
                    "val": _safe(entry.get("winning_value")),
                    "src": entry.get("winning_source"),
                    "rule": entry.get("survivorship_rule"),
                    "conf": float(entry.get("confidence") or 0),
                    "lock": bool(entry.get("is_regulatory_lock")),
                    "competing": "[]",
                })
                count += 1
            if count % 5000 == 0:
                db.commit()
        db.commit()
    print(f"  {count} lineage entries written")

    avg_conf = sum(float(gr.get("confidence_score") or 0.5) for _, _, gr in golden_records) / max(len(golden_records), 1)
    print(f"\nCreated {len(golden_records)} golden records")
    print(f"Avg confidence: {avg_conf:.3f}")
    print("Survivorship wins: " + " | ".join(f"{s}: {c}" for s, c in sorted(source_wins.items())))
    print("\n✅ 04_survivorship.py complete")


if __name__ == "__main__":
    main()
