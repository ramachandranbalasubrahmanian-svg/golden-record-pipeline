"""01_seed.py — Load CSV source records and transactions into PostgreSQL."""
import sys
import csv
import uuid
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from app.config import settings

SYNC_URL = settings.sync_database_url
_url = SYNC_URL.replace("postgresql://", "")
_user_pass, _rest = _url.split("@", 1)
_user, _pass = _user_pass.split(":", 1)
_host_port, _db = _rest.rsplit("/", 1)
_host, _port = (_host_port.split(":", 1) if ":" in _host_port else (_host_port, "5432"))

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"


def _safe(v):
    if v is None:
        return None
    s = str(v).strip()
    return None if s in ("", "nan", "None", "NaT") else s


def _parse_date(v):
    if not v:
        return None
    s = str(v).strip()
    if not s or s in ("nan", "None", "NaT"):
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def get_conn():
    conn = psycopg2.connect(
        host=_host, port=int(_port), dbname=_db, user=_user, password=_pass
    )
    with conn.cursor() as cur:
        cur.execute("SET datestyle = 'ISO, DMY'")
    conn.commit()
    return conn


def create_extensions_and_tables(conn):
    from sqlalchemy import create_engine, text
    from app.database import Base
    from app.models import db_models  # noqa
    engine = create_engine(SYNC_URL)
    with engine.begin() as c:
        c.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        c.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(c)
    print("✓ Extensions and tables created")


def seed_source_records(conn):
    sources = {
        "crm_records.csv": "CRM",
        "kyc_records.csv": "KYC",
        "cbs_records.csv": "CBS",
        "risk_records.csv": "RISK",
    }
    totals = {}
    for fname, system in sources.items():
        path = RAW_DIR / fname
        if not path.exists():
            print(f"  ⚠ {fname} not found — skipping")
            continue
        with open(path) as f:
            rows = list(csv.DictReader(f))

        with conn.cursor() as cur:
            inserted = 0
            for row in rows:
                ext_id = _safe(row.get("external_id")) or str(uuid.uuid4())[:12]
                cur.execute(
                    """
                    INSERT INTO source_records (
                        id, external_id, source_system, first_name, last_name, full_name,
                        date_of_birth, email, phone, address_line1, city, country, nationality,
                        kyc_status, kyc_tier, risk_rating, is_pep, is_sanctioned,
                        ingested_at, quarantined
                    ) VALUES (
                        gen_random_uuid(), %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, false
                    ) ON CONFLICT DO NOTHING
                    """,
                    (
                        ext_id, system,
                        _safe(row.get("first_name")),
                        _safe(row.get("last_name")),
                        _safe(row.get("full_legal_name") or row.get("full_name")),
                        _parse_date(row.get("date_of_birth")),
                        _safe(row.get("email")),
                        _safe(row.get("phone")),
                        _safe(row.get("address_line1")),
                        _safe(row.get("city")),
                        _safe(row.get("country")),
                        _safe(row.get("nationality")),
                        _safe(row.get("kyc_status")),
                        _safe(row.get("kyc_tier")),
                        _safe(row.get("risk_rating")),
                        row.get("is_pep") in (True, "True", "true", "1"),
                        row.get("is_sanctioned") in (True, "True", "true", "1"),
                        datetime.utcnow(),
                    ),
                )
                inserted += 1
            conn.commit()
        totals[system] = inserted
        print(f"  ✓ {system}: {inserted} records seeded")

    total = sum(totals.values())
    print(f"Seeded {total} source records ({' + '.join(f'{v} {k}' for k, v in totals.items())})")
    return total


def seed_transactions(conn):
    path = RAW_DIR / "transactions.csv"
    if not path.exists():
        print("  ⚠ transactions.csv not found — skipping")
        return 0

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM golden_records")
        gr_count = cur.fetchone()[0]

    if gr_count == 0:
        print("  ⚠ No golden records yet — transactions will be seeded after survivorship")
        return 0

    with open(path) as f:
        rows = list(csv.DictReader(f))

    with conn.cursor() as cur:
        n = 0
        for row in rows:
            cur.execute(
                """
                INSERT INTO transactions (
                    id, customer_id, transaction_date, amount, currency,
                    transaction_type, channel, counterparty_name, counterparty_country,
                    is_suspicious, suspicious_reason, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) ON CONFLICT DO NOTHING
                """,
                (
                    _safe(row.get("transaction_id")) or str(uuid.uuid4()),
                    _safe(row.get("customer_id")),
                    _parse_date(row.get("transaction_date")) or row.get("transaction_date"),
                    float(row.get("amount") or 0),
                    _safe(row.get("currency")) or "USD",
                    _safe(row.get("transaction_type")),
                    _safe(row.get("channel")),
                    _safe(row.get("counterparty_name")),
                    _safe(row.get("counterparty_country")),
                    row.get("is_suspicious") in (True, "True", "true", "1"),
                    _safe(row.get("suspicious_reason")),
                    datetime.utcnow(),
                ),
            )
            n += 1
        conn.commit()
    print(f"  ✓ {n} transactions seeded")
    return n


if __name__ == "__main__":
    print("Connecting to database...")
    conn = get_conn()
    create_extensions_and_tables(conn)
    seed_source_records(conn)
    seed_transactions(conn)
    conn.close()
    print("\n✅ 01_seed.py complete")
