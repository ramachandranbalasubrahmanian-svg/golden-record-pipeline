"""Source system splitter — maps customers into CRM, KYC, CBS, RISK source records."""
from __future__ import annotations
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ISO3_TO_ISO2 = {
    "USA": "US", "GBR": "GB", "DEU": "DE", "FRA": "FR", "CHN": "CN",
    "JPN": "JP", "SAU": "SA", "BRA": "BR", "IND": "IN", "CAN": "CA",
    "AUS": "AU", "SGP": "SG", "CHE": "CH", "NLD": "NL", "SWE": "SE",
    "NOR": "NO", "DNK": "DK", "FIN": "FI", "BEL": "BE", "AUT": "AT",
}

random.seed(42)
_counter = {"CRM": 0, "KYC": 0, "CBS": 0, "RISK": 0}


def _next_id(source: str) -> str:
    _counter[source] += 1
    return f"{source}-{_counter[source]:06d}"


def _iso2(country: str) -> str:
    return ISO3_TO_ISO2.get(str(country or "").upper(), str(country or "")[:2])


def _crm_phone(phone: str) -> str:
    digits = "".join(c for c in str(phone or "") if c.isdigit())[-10:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return phone


def _cbs_phone(phone: str) -> str:
    digits = "".join(c for c in str(phone or "") if c.isdigit())
    if len(digits) >= 10:
        return f"+1-{digits[-10:-7]}-{digits[-7:-4]}-{digits[-4:]}"
    return phone


def _dob_slash(dob: str) -> str:
    try:
        d = datetime.strptime(str(dob)[:10], "%Y-%m-%d")
        return d.strftime("%d/%m/%Y")
    except Exception:
        return str(dob or "")


def _crm_kyc_status(kyc_status: str) -> str:
    mapping = {"VERIFIED": "Active", "EXPIRED": "Inactive", "PENDING": "Pending", "FAILED": "Inactive"}
    return mapping.get(str(kyc_status or "").upper(), "Active")


def _crm_risk_rating(risk: str) -> str:
    mapping = {"LOW": "Standard", "MEDIUM": "Watch", "HIGH": "High", "CRITICAL": "Priority"}
    return mapping.get(str(risk or "").upper(), "Standard")


def split_to_sources(
    customers_path: str,
    output_dir: str,
    crm_ratio: float = 0.90,
    kyc_ratio: float = 0.64,
    cbs_ratio: float = 0.46,
    risk_ratio: float = 0.60,
) -> dict:
    df = pd.read_csv(customers_path)
    n = len(df)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    pep_ids = set(df[df["is_pep"] == True]["customer_id"].tolist())
    sanctioned_ids = set(df[df["is_sanctioned"] == True]["customer_id"].tolist())
    critical_ids = set(df[df["risk_rating"] == "CRITICAL"]["customer_id"].tolist())

    def select_ids(ratio: float, must_include: set) -> set:
        pool = set(df["customer_id"].tolist())
        n_select = int(n * ratio)
        optional = list(pool - must_include)
        random.shuffle(optional)
        selected = must_include | set(optional[: max(0, n_select - len(must_include))])
        return selected

    crm_ids = select_ids(crm_ratio, set())
    kyc_ids = select_ids(kyc_ratio, pep_ids | sanctioned_ids)
    cbs_ids = select_ids(cbs_ratio, sanctioned_ids)
    risk_ids = select_ids(risk_ratio, pep_ids | sanctioned_ids | critical_ids)

    now = datetime.utcnow()

    crm_rows = []
    for _, row in df[df["customer_id"].isin(crm_ids)].iterrows():
        crm_rows.append({
            "external_id": _next_id("CRM"),
            "source_system": "CRM",
            "customer_id": row["customer_id"],
            "first_name": str(row.get("first_name", "") or "").title(),
            "last_name": str(row.get("last_name", "") or "").title(),
            "email": str(row.get("email", "") or "").lower(),
            "phone": _crm_phone(row.get("phone", "")),
            "address_line1": row.get("address_line1"),
            "city": row.get("city"),
            "country": _iso2(row.get("country", "")),
            "kyc_status": _crm_kyc_status(row.get("kyc_status", "")),
            "risk_rating": _crm_risk_rating(row.get("risk_rating", "")),
            "ingested_at": (now - timedelta(days=random.randint(0, 30))).isoformat(),
        })

    kyc_rows = []
    for _, row in df[df["customer_id"].isin(kyc_ids)].iterrows():
        kyc_rows.append({
            "external_id": _next_id("KYC"),
            "source_system": "KYC",
            "customer_id": row["customer_id"],
            "full_legal_name": str(row.get("full_legal_name", "") or "").upper(),
            "date_of_birth": row.get("date_of_birth"),
            "nationality": row.get("nationality"),
            "country": row.get("country"),
            "kyc_status": row.get("kyc_status"),
            "kyc_tier": row.get("kyc_tier"),
            "kyc_verified_at": row.get("kyc_verified_at"),
            "kyc_expiry_at": row.get("kyc_expiry_at"),
            "is_pep": row.get("is_pep"),
            "pep_type": row.get("pep_type"),
            "is_sanctioned": row.get("is_sanctioned"),
            "sanctions_list": row.get("sanctions_list"),
            "first_name": row.get("first_name"),
            "last_name": row.get("last_name"),
            "ingested_at": (now - timedelta(days=random.randint(0, 30))).isoformat(),
        })

    cbs_rows = []
    for _, row in df[df["customer_id"].isin(cbs_ids)].iterrows():
        account_types = ["checking", "savings", "business"]
        cbs_rows.append({
            "external_id": _next_id("CBS"),
            "source_system": "CBS",
            "customer_id": row["customer_id"],
            "first_name": str(row.get("first_name", "") or "").upper(),
            "last_name": str(row.get("last_name", "") or "").upper(),
            "date_of_birth": _dob_slash(row.get("date_of_birth", "")),
            "phone": _cbs_phone(row.get("phone", "")),
            "address_line1": row.get("address_line1"),
            "city": row.get("city"),
            "country": _iso2(row.get("country", "")),
            "account_type": random.choice(account_types),
            "account_status": random.choices(["active", "dormant", "closed"], weights=[90, 7, 3])[0],
            "ingested_at": (now - timedelta(days=random.randint(0, 30))).isoformat(),
        })

    risk_rows = []
    for _, row in df[df["customer_id"].isin(risk_ids)].iterrows():
        risk_rows.append({
            "external_id": _next_id("RISK"),
            "source_system": "RISK",
            "customer_id": row["customer_id"],
            "full_name": f"{row.get('first_name', '')} {row.get('last_name', '')}".title(),
            "date_of_birth": row.get("date_of_birth"),
            "risk_rating": row.get("risk_rating"),
            "risk_score": row.get("risk_score"),
            "is_pep": row.get("is_pep"),
            "is_sanctioned": row.get("is_sanctioned"),
            "last_review_date": (now - timedelta(days=random.randint(1, 365))).isoformat(),
            "next_review_date": (now + timedelta(days=random.randint(1, 365))).isoformat(),
            "first_name": row.get("first_name"),
            "last_name": row.get("last_name"),
            "ingested_at": (now - timedelta(days=random.randint(0, 30))).isoformat(),
        })

    pd.DataFrame(crm_rows).to_csv(out / "crm_records.csv", index=False)
    pd.DataFrame(kyc_rows).to_csv(out / "kyc_records.csv", index=False)
    pd.DataFrame(cbs_rows).to_csv(out / "cbs_records.csv", index=False)
    pd.DataFrame(risk_rows).to_csv(out / "risk_records.csv", index=False)

    coverage = []
    for _, row in df.iterrows():
        cid = row["customer_id"]
        coverage.append({
            "customer_id": cid,
            "in_crm": cid in crm_ids,
            "in_kyc": cid in kyc_ids,
            "in_cbs": cid in cbs_ids,
            "in_risk": cid in risk_ids,
        })
    pd.DataFrame(coverage).to_csv(out / "source_coverage.csv", index=False)

    print(f"CRM: {len(crm_rows)}, KYC: {len(kyc_rows)}, CBS: {len(cbs_rows)}, RISK: {len(risk_rows)}")
    return {"crm": len(crm_rows), "kyc": len(kyc_rows), "cbs": len(cbs_rows), "risk": len(risk_rows)}
