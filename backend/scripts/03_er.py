"""03_er.py — Entity Resolution: find duplicates, form clusters, populate stewardship queue."""
import sys
import json
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.pipeline.entity_resolution import run_entity_resolution

engine = create_engine(settings.sync_database_url)
Session = sessionmaker(engine)


def main():
    print("Loading non-quarantined source records...")
    with Session() as db:
        rows = db.execute(text(
            "SELECT * FROM source_records WHERE quarantined = false"
        )).mappings().all()
        records = [dict(r) for r in rows]

    print(f"Running entity resolution on {len(records):,} records...")
    er_result = run_entity_resolution(records)

    match_pairs = er_result["match_pairs"]
    clusters = er_result["clusters"]

    print(f"Writing {len(match_pairs)} match pairs to database...")
    with Session() as db:
        for batch in [match_pairs[i:i + 200] for i in range(0, len(match_pairs), 200)]:
            for pair in batch:
                pid = str(uuid.uuid4())
                db.execute(text("""
                    INSERT INTO match_pairs (id, record_a_id, record_b_id, match_probability, match_features, status, created_at)
                    VALUES (:id, cast(:a as uuid), cast(:b as uuid), :prob, cast(:features as jsonb), :status, NOW())
                    ON CONFLICT DO NOTHING
                """), {
                    "id": pid,
                    "a": pair["record_a_id"],
                    "b": pair["record_b_id"],
                    "prob": float(pair["match_probability"]),
                    "features": "{}",
                    "status": pair.get("status", "pending"),
                })
                if pair.get("status") == "pending":
                    priority = max(1, min(10, int((1.0 - float(pair["match_probability"])) * 10)))
                    db.execute(text("""
                        INSERT INTO stewardship_queue (id, pair_id, priority, status, created_at)
                        VALUES (gen_random_uuid(), cast(:pid as uuid), :priority, 'open', NOW())
                    """), {"pid": pid, "priority": priority})
            db.commit()

    print(f"Writing {len(clusters)} entity clusters...")
    with Session() as db:
        cluster_num = 0
        for root, member_ids in clusters.items():
            cluster_num += 1
            cluster_id = f"EC-{cluster_num:06d}"
            db.execute(text("""
                INSERT INTO entity_clusters (id, cluster_id, record_ids, confidence, match_method, created_at, updated_at)
                VALUES (gen_random_uuid(), :cid, cast(:rids as jsonb), :conf, :method, NOW(), NOW())
                ON CONFLICT (cluster_id) DO UPDATE SET record_ids = EXCLUDED.record_ids, updated_at = NOW()
            """), {
                "cid": cluster_id,
                "rids": json.dumps(list(member_ids)),
                "conf": 0.85 if len(member_ids) > 1 else 0.5,
                "method": "hybrid_er",
            })
        db.commit()

    pending_pairs = sum(1 for p in match_pairs if p.get("status") == "pending")
    print(f"\nER complete: {er_result['pairs_evaluated']} candidate pairs → "
          f"{len(match_pairs)} matches → {len(clusters)} clusters")
    print(f"  Pending human review: {pending_pairs}")
    print(f"  Singleton records: {er_result['singleton_records']}")
    print("\n✅ 03_er.py complete")


if __name__ == "__main__":
    main()
