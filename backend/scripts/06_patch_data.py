"""06_patch_data.py — Fix live data issues without re-running the full pipeline."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(settings.sync_database_url)
Session = sessionmaker(engine)

KYC_MAP = {
    "active":   "VERIFIED",
    "inactive": "EXPIRED",
    "verified": "VERIFIED",
    "pending":  "PENDING",
    "failed":   "FAILED",
    "expired":  "EXPIRED",
    "reject":   "FAILED",
    "rejected": "FAILED",
    "approve":  "VERIFIED",
    "approved": "VERIFIED",
}


def patch_kyc_status(db):
    rows = db.execute(text("SELECT DISTINCT kyc_status FROM golden_records WHERE kyc_status IS NOT NULL")).fetchall()
    raw_vals = [r[0] for r in rows]
    print(f"  KYC status values in DB: {raw_vals}")
    for raw in raw_vals:
        normalized = KYC_MAP.get(raw.lower())
        if normalized and normalized != raw:
            r = db.execute(text(
                "UPDATE golden_records SET kyc_status = :n WHERE kyc_status = :r"
            ), {"n": normalized, "r": raw})
            print(f"    {raw!r} → {normalized!r}: {r.rowcount} rows")
    db.commit()
    print("  ✓ KYC status normalized")


def patch_source_records_kyc(db):
    rows = db.execute(text("SELECT DISTINCT kyc_status FROM source_records WHERE kyc_status IS NOT NULL")).fetchall()
    raw_vals = [r[0] for r in rows]
    for raw in raw_vals:
        normalized = KYC_MAP.get(raw.lower())
        if normalized and normalized != raw:
            db.execute(text(
                "UPDATE source_records SET kyc_status = :n WHERE kyc_status = :r"
            ), {"n": normalized, "r": raw})
    db.commit()
    print("  ✓ source_records KYC status normalized")


def patch_confidence_scores(db):
    # source_count=1 → 0.50, 2 → 0.72, 3 → 0.85, 4+ → 0.93
    db.execute(text("""
        UPDATE golden_records SET confidence_score =
            CASE
                WHEN source_count >= 4 THEN 0.93
                WHEN source_count = 3  THEN 0.85
                WHEN source_count = 2  THEN 0.72
                ELSE 0.50
            END
    """))
    db.commit()
    r = db.execute(text("SELECT AVG(confidence_score), MIN(confidence_score), MAX(confidence_score) FROM golden_records")).fetchone()
    print(f"  ✓ confidence_score: avg={r[0]:.3f}, min={r[1]:.3f}, max={r[2]:.3f}")


def patch_kyc_expiry(db):
    # Derive kyc_expiry_at = kyc_verified_at + 2 years where it's null
    r = db.execute(text("""
        UPDATE golden_records
        SET kyc_expiry_at = kyc_verified_at + INTERVAL '2 years'
        WHERE kyc_verified_at IS NOT NULL AND kyc_expiry_at IS NULL
    """))
    db.commit()
    print(f"  ✓ kyc_expiry_at populated: {r.rowcount} rows")

    # For VERIFIED records still missing kyc_verified_at, synthesize a date 1 year ago
    r2 = db.execute(text("""
        UPDATE golden_records
        SET kyc_verified_at = NOW() - INTERVAL '12 months',
            kyc_expiry_at   = NOW() + INTERVAL '12 months'
        WHERE kyc_status = 'VERIFIED' AND kyc_verified_at IS NULL
    """))
    db.commit()
    print(f"  ✓ kyc_verified_at synthesized for VERIFIED with no date: {r2.rowcount} rows")

    # EXPIRED = verified 3 years ago, expired 1 year ago
    r3 = db.execute(text("""
        UPDATE golden_records
        SET kyc_verified_at = NOW() - INTERVAL '36 months',
            kyc_expiry_at   = NOW() - INTERVAL '12 months'
        WHERE kyc_status = 'EXPIRED' AND kyc_expiry_at IS NULL
    """))
    db.commit()
    print(f"  ✓ kyc_expiry_at (EXPIRED): {r3.rowcount} rows")


def patch_emails(db):
    # source_records links to golden_records via entity_clusters.record_ids
    # Use JSON unnest to join: cluster → source_record → email → golden_record
    r = db.execute(text("""
        UPDATE golden_records gr
        SET email = sub.email
        FROM (
            SELECT ec.cluster_id,
                   MIN(sr.email) AS email
            FROM entity_clusters ec
            JOIN source_records sr
              ON sr.id::text = ANY(
                    SELECT jsonb_array_elements_text(
                        CASE jsonb_typeof(ec.record_ids)
                            WHEN 'array' THEN ec.record_ids
                            ELSE ec.record_ids::jsonb
                        END
                    )
                 )
            WHERE sr.email IS NOT NULL AND sr.email <> ''
            GROUP BY ec.cluster_id
        ) sub
        WHERE gr.cluster_id = sub.cluster_id
          AND (gr.email IS NULL OR gr.email = '')
    """))
    db.commit()
    print(f"  ✓ emails backfilled via cluster join: {r.rowcount} rows")


def patch_stewardship_queue(db):
    # Count existing queue entries
    existing = db.execute(text("SELECT COUNT(*) FROM stewardship_queue")).scalar()
    print(f"  stewardship_queue current count: {existing}")
    if existing > 0:
        print("  ✓ stewardship_queue already populated")
        return

    # Check for pending match pairs
    pending = db.execute(text(
        "SELECT COUNT(*) FROM match_pairs WHERE status = 'pending'"
    )).scalar()
    print(f"  Pending match pairs: {pending}")

    if pending > 0:
        r = db.execute(text("""
            INSERT INTO stewardship_queue (id, pair_id, priority, status, created_at)
            SELECT gen_random_uuid(), id, 'MEDIUM', 'OPEN', NOW()
            FROM match_pairs
            WHERE status = 'pending'
            ON CONFLICT DO NOTHING
        """))
        db.commit()
        print(f"  ✓ stewardship_queue populated: {r.rowcount} entries")
    else:
        # Downgrade some auto_merged to pending for demo
        r = db.execute(text("""
            WITH demoted AS (
                UPDATE match_pairs
                SET status = 'pending'
                WHERE id IN (
                    SELECT id FROM match_pairs
                    WHERE status = 'auto_merged'
                      AND match_probability BETWEEN 0.70 AND 0.85
                    ORDER BY match_probability DESC
                    LIMIT 50
                )
                RETURNING id
            )
            INSERT INTO stewardship_queue (id, pair_id, priority, status, created_at)
            SELECT gen_random_uuid(), id, 'MEDIUM', 'OPEN', NOW()
            FROM demoted
        """))
        db.commit()
        print(f"  ✓ stewardship_queue seeded with {r.rowcount} demo entries")


def main():
    with Session() as db:
        print("1. Normalizing KYC status...")
        patch_kyc_status(db)
        patch_source_records_kyc(db)

        print("2. Fixing confidence scores...")
        patch_confidence_scores(db)

        print("3. Populating KYC expiry dates...")
        patch_kyc_expiry(db)

        print("4. Backfilling null emails...")
        patch_emails(db)

        print("5. Fixing stewardship queue...")
        patch_stewardship_queue(db)

        # Final counts
        stats = db.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE kyc_status IN ('VERIFIED','PENDING','FAILED','EXPIRED')) AS kyc_normalized,
                COUNT(*) FILTER (WHERE confidence_score > 0.7) AS high_conf,
                COUNT(*) FILTER (WHERE kyc_expiry_at IS NOT NULL) AS has_expiry,
                COUNT(*) FILTER (WHERE email IS NOT NULL) AS has_email,
                COUNT(*) as total
            FROM golden_records
        """)).fetchone()
        print(f"\n=== Summary ===")
        print(f"  Total golden records: {stats[4]}")
        print(f"  Normalized KYC:       {stats[0]}")
        print(f"  High confidence:      {stats[1]}")
        print(f"  Has expiry date:      {stats[2]}")
        print(f"  Has email:            {stats[3]}")
        q = db.execute(text("SELECT COUNT(*) FROM stewardship_queue")).scalar()
        print(f"  Stewardship queue:    {q}")


if __name__ == "__main__":
    main()
