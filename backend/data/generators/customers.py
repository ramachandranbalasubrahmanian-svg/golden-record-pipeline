"""Synthetic customer generator — 5,000 banking customers."""
from __future__ import annotations
import random
import uuid
from datetime import datetime, timedelta, date
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

LOCALES = ["en_US", "en_GB", "de_DE", "fr_FR", "zh_CN", "ja_JP", "ar_SA", "pt_BR"]
PEP_TITLES = ["The Honourable", "Senator", "Dr.", "Ambassador", "Minister", "Governor"]

ISO3_SAMPLE = ["USA", "GBR", "DEU", "FRA", "CHN", "JPN", "SAU", "BRA", "IND", "CAN",
               "AUS", "SGP", "CHE", "NLD", "SWE", "NOR", "DNK", "FIN", "BEL", "AUT"]


def _random_dob(min_age: int = 18, max_age: int = 85) -> date:
    days = random.randint(min_age * 365, max_age * 365)
    return (datetime.utcnow() - timedelta(days=days)).date()


def _e164_phone(fake: Faker) -> str:
    digits = "".join(str(random.randint(0, 9)) for _ in range(10))
    country_codes = ["1", "44", "49", "33", "86", "81", "966", "55", "91", "61"]
    return f"+{random.choice(country_codes)}{digits}"


def generate(n: int = 5000, output_path: str = "data/raw/customers_master.csv") -> dict:
    random.seed(42)
    np.random.seed(42)

    fake_pool = {loc: Faker(loc) for loc in LOCALES}

    def fake() -> Faker:
        return random.choice(list(fake_pool.values()))

    now = datetime.utcnow()

    # Allocations
    n_pep = 50
    n_sanctioned = 10
    n_critical = 25
    n_high = 200
    n_medium = 1200
    n_low = n - n_pep - (n_high - n_critical - n_sanctioned) - n_medium - n_critical

    records = []
    used_emails: set[str] = set()

    def make_email(fn: str, ln: str) -> str:
        base = f"{fn.lower().replace(' ', '.')}.{ln.lower().replace(' ', '')}"
        base = "".join(c for c in base if c.isalnum() or c in "._-")
        domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "proton.me"]
        email = f"{base[:15]}@{random.choice(domains)}"
        count = 0
        while email in used_emails:
            email = f"{base[:15]}{count}@{random.choice(domains)}"
            count += 1
        used_emails.add(email)
        return email

    def make_customer(risk_rating: str, is_pep: bool = False, is_sanctioned: bool = False) -> dict:
        f = fake()
        fn = f.first_name()
        ln = f.last_name()
        full = f"{fn} {ln}"
        if is_pep:
            full = f"{random.choice(PEP_TITLES)} {full}"
        country = random.choice(ISO3_SAMPLE)
        kyc_mapping = {"LOW": "STANDARD", "MEDIUM": "STANDARD", "HIGH": "ENHANCED", "CRITICAL": "ENHANCED"}
        kyc_tier = "ENHANCED" if (is_pep or risk_rating in ("HIGH", "CRITICAL")) else kyc_mapping.get(risk_rating, "STANDARD")

        # KYC status
        if risk_rating in ("HIGH", "CRITICAL"):
            kyc_status = random.choices(["VERIFIED", "PENDING", "FAILED", "EXPIRED"], weights=[70, 15, 10, 5])[0]
        else:
            kyc_status = random.choices(["VERIFIED", "PENDING", "FAILED", "EXPIRED"], weights=[80, 10, 5, 5])[0]

        kyc_verified_at = None
        kyc_expiry_at = None
        if kyc_status == "VERIFIED":
            kyc_verified_at = now - timedelta(days=random.randint(30, 700))
            expiry_days = 365 if kyc_tier == "ENHANCED" else 730
            kyc_expiry_at = kyc_verified_at + timedelta(days=expiry_days)

        risk_bands = {"LOW": (0.0, 0.3), "MEDIUM": (0.3, 0.6), "HIGH": (0.6, 0.85), "CRITICAL": (0.85, 1.0)}
        lo, hi = risk_bands[risk_rating]
        risk_score = round(random.uniform(lo, hi), 3)

        pep_types = ["DOMESTIC_PEP", "FOREIGN_PEP", "INTERNATIONAL_ORG_PEP"]
        sanctions_lists = ["OFAC_SDN", "EU_CONSOLIDATED", "UN_SECURITY_COUNCIL"]

        onboarded_at = now - timedelta(days=random.randint(30, 5 * 365))

        dob = _random_dob()

        return {
            "customer_id": str(uuid.uuid4()),
            "first_name": fn,
            "last_name": ln,
            "full_legal_name": full,
            "date_of_birth": dob.isoformat(),
            "email": make_email(fn, ln),
            "phone": _e164_phone(f),
            "address_line1": f.street_address() if hasattr(f, 'street_address') else f.address()[:50],
            "city": f.city() if hasattr(f, 'city') else "London",
            "country": country,
            "nationality": country,
            "kyc_status": kyc_status,
            "kyc_tier": kyc_tier,
            "kyc_verified_at": kyc_verified_at.isoformat() if kyc_verified_at else None,
            "kyc_expiry_at": kyc_expiry_at.isoformat() if kyc_expiry_at else None,
            "risk_rating": risk_rating,
            "risk_score": risk_score,
            "is_pep": is_pep,
            "pep_type": random.choice(pep_types) if is_pep else None,
            "pep_detected_at": (now - timedelta(days=random.randint(1, 365))).isoformat() if is_pep else None,
            "is_sanctioned": is_sanctioned,
            "sanctions_list": random.choice(sanctions_lists) if is_sanctioned else None,
            "sanctions_detected_at": (now - timedelta(days=random.randint(1, 365))).isoformat() if is_sanctioned else None,
            "onboarded_at": onboarded_at.isoformat(),
        }

    # PEP (HIGH risk)
    for _ in range(n_pep):
        records.append(make_customer("HIGH", is_pep=True))

    # Sanctioned (CRITICAL, not PEP)
    for _ in range(n_sanctioned):
        records.append(make_customer("CRITICAL", is_sanctioned=True))

    # CRITICAL (not sanctioned)
    for _ in range(n_critical - n_sanctioned):
        records.append(make_customer("CRITICAL"))

    # HIGH (not PEP, not CRITICAL)
    for _ in range(n_high - n_critical - n_pep):
        records.append(make_customer("HIGH"))

    # MEDIUM
    for _ in range(n_medium):
        records.append(make_customer("MEDIUM"))

    # LOW
    remaining = n - len(records)
    for _ in range(remaining):
        records.append(make_customer("LOW"))

    df = pd.DataFrame(records[:n])
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} customers → {output_path}")

    pep_ids = set(df[df["is_pep"] == True]["customer_id"].tolist())
    sanctioned_ids = set(df[df["is_sanctioned"] == True]["customer_id"].tolist())
    high_risk_ids = set(df[df["risk_rating"].isin(["HIGH", "CRITICAL"])]["customer_id"].tolist())

    return {
        "customer_ids": df["customer_id"].tolist(),
        "pep_ids": pep_ids,
        "sanctioned_ids": sanctioned_ids,
        "high_risk_ids": high_risk_ids,
        "output_path": output_path,
        "count": len(df),
    }
