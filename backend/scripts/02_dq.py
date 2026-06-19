"""02_dq.py — Data Quality validation on all source records."""
import sys
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, update
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.pipeline.data_quality import validate_record

engine = create_engine(settings.sync_database_url)
Session = sessionmaker(engine)


def main():
    print("Loading source records from database...")
    with Session() as db:
        rows = db.execute(text("SELECT * FROM source_records")).mappings().all()
        records = [dict(r) for r in rows]

    print(f"Validating {len(records):,} source records...")
    stats_by_source: dict[str, dict] = defaultdict(lambda: {"total": 0, "passed": 0, "scores": []})

    updates = []
    for rec in records:
        result = validate_record({
            **rec,
            "date_of_birth": str(rec.get("date_of_birth") or ""),
            "external_id": rec.get("external_id", ""),
            "source_system": rec.get("source_system", ""),
        })
        src = str(rec.get("source_system", "UNKNOWN"))
        stats_by_source[src]["total"] += 1
        stats_by_source[src]["scores"].append(result["overall_score"])
        if result["passed"]:
            stats_by_source[src]["passed"] += 1

        updates.append({
            "id": str(rec["id"]),
            "dq_score": result["overall_score"],
            "dq_report": json.dumps(result),
            "quarantined": not result["passed"],
        })

    print(f"Writing DQ results to database ({len(updates):,} updates)...")
    with Session() as db:
        for batch in [updates[i:i+500] for i in range(0, len(updates), 500)]:
            for upd in batch:
                db.execute(
                    text("""
                        UPDATE source_records
                        SET dq_score = :dq_score, dq_report = :dq_report::jsonb, quarantined = :quarantined
                        WHERE id = :id::uuid
                    """),
                    upd,
                )
            db.commit()

    print("\nDQ Summary:")
    print(f"{'Source':<10} {'Total':>8} {'Passed':>8} {'Failed':>8} {'Avg Score':>10}")
    print("-" * 50)
    for src, s in sorted(stats_by_source.items()):
        avg = sum(s["scores"]) / max(len(s["scores"]), 1)
        failed = s["total"] - s["passed"]
        print(f"{src:<10} {s['total']:>8} {s['passed']:>8} {failed:>8} {avg:>10.3f}")

    total_failed = sum(s["total"] - s["passed"] for s in stats_by_source.values())
    print(f"\n✅ 02_dq.py complete — {total_failed} records quarantined")


if __name__ == "__main__":
    main()
