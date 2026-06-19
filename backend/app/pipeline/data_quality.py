"""Data Quality validation module — scores each source record before entering the pipeline."""
from __future__ import annotations
import re
from datetime import datetime, date
from typing import Optional

REQUIRED_FIELDS = ["first_name", "last_name", "date_of_birth", "country"]
IMPORTANT_FIELDS = ["email", "phone", "address_line1", "city"]

VALID_COUNTRIES = {
    "AF","AX","AL","DZ","AS","AD","AO","AI","AQ","AG","AR","AM","AW","AU","AT","AZ",
    "BS","BH","BD","BB","BY","BE","BZ","BJ","BM","BT","BO","BQ","BA","BW","BV","BR",
    "IO","BN","BG","BF","BI","CV","KH","CM","CA","KY","CF","TD","CL","CN","CX","CC",
    "CO","KM","CG","CD","CK","CR","CI","HR","CU","CW","CY","CZ","DK","DJ","DM","DO",
    "EC","EG","SV","GQ","ER","EE","SZ","ET","FK","FO","FJ","FI","FR","GF","PF","TF",
    "GA","GM","GE","DE","GH","GI","GR","GL","GD","GP","GU","GT","GG","GN","GW","GY",
    "HT","HM","VA","HN","HK","HU","IS","IN","ID","IR","IQ","IE","IM","IL","IT","JM",
    "JP","JE","JO","KZ","KE","KI","KP","KR","KW","KG","LA","LV","LB","LS","LR","LY",
    "LI","LT","LU","MO","MG","MW","MY","MV","ML","MT","MH","MQ","MR","MU","YT","MX",
    "FM","MD","MC","MN","ME","MS","MA","MZ","MM","NA","NR","NP","NL","NC","NZ","NI",
    "NE","NG","NU","NF","MK","MP","NO","OM","PK","PW","PS","PA","PG","PY","PE","PH",
    "PN","PL","PT","PR","QA","RE","RO","RU","RW","BL","SH","KN","LC","MF","PM","VC",
    "WS","SM","ST","SA","SN","RS","SC","SL","SG","SX","SK","SI","SB","SO","ZA","GS",
    "SS","ES","LK","SD","SR","SJ","SE","CH","SY","TW","TJ","TZ","TH","TL","TG","TK",
    "TO","TT","TN","TR","TM","TC","TV","UG","UA","AE","GB","US","UM","UY","UZ","VU",
    "VE","VN","VG","VI","WF","EH","YE","ZM","ZW",
    # ISO-3 codes commonly used
    "USA","GBR","DEU","FRA","CHN","JPN","SAU","BRA","IND","CAN","AUS","SGP","CHE",
    "NLD","SWE","NOR","DNK","FIN","BEL","AUT","ESP","ITA","PRT","GRC","POL","CZE",
    "HUN","ROU","BGR","HRV","SVK","SVN","EST","LVA","LTU","IRL","LUX","MLT","CYP",
    "ARE","KWT","QAT","OMN","BHR","JOR","ISR","EGY","MAR","TUN","DZA","ZAF","NGA",
    "KEN","ETH","GHA","TZA","UGA","MOZ","ZMB","ZWE","MYS","IDN","THA","VNM","PHL",
    "KOR","TWN","HKG","MEX","ARG","CHL","COL","PER","VEN","ECU","BOL","PRY","URY"
}

TEST_PATTERNS = re.compile(
    r"\b(test|fake|dummy|sample|xxx|john doe|jane doe)\b", re.IGNORECASE
)


def rule_completeness(record: dict) -> tuple[bool, float, str]:
    req_present = sum(1 for f in REQUIRED_FIELDS if record.get(f))
    imp_present = sum(1 for f in IMPORTANT_FIELDS if record.get(f))
    score = (req_present / len(REQUIRED_FIELDS)) * 0.7 + (imp_present / len(IMPORTANT_FIELDS)) * 0.3
    passed = score >= 0.7
    return passed, round(score, 3), f"Required: {req_present}/{len(REQUIRED_FIELDS)}, Important: {imp_present}/{len(IMPORTANT_FIELDS)}"


def rule_email_format(record: dict) -> tuple[bool, float, str]:
    email = record.get("email")
    if not email:
        return True, 1.0, "No email to validate"
    pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    if pattern.match(str(email)):
        return True, 1.0, "Valid email format"
    return False, 0.0, f"Invalid email: {email}"


def rule_phone_format(record: dict) -> tuple[bool, float, str]:
    phone = record.get("phone")
    if not phone:
        return True, 1.0, "No phone to validate"
    digits = re.sub(r"\D", "", str(phone))
    if 7 <= len(digits) <= 15:
        return True, 1.0, f"Valid phone ({len(digits)} digits)"
    if 4 <= len(digits) < 7:
        return False, 0.5, f"Partial phone ({len(digits)} digits)"
    return False, 0.0, f"Invalid phone ({len(digits)} digits)"


def rule_date_of_birth_valid(record: dict) -> tuple[bool, float, str]:
    dob = record.get("date_of_birth")
    if not dob:
        return False, 0.0, "Missing date_of_birth"
    parsed = _parse_date(str(dob))
    if not parsed:
        return False, 0.0, f"Unparseable DOB: {dob}"
    age = (date.today() - parsed).days // 365
    if 18 <= age <= 120:
        return True, 1.0, f"Valid DOB, age {age}"
    return False, 0.0, f"Impossible age: {age}"


def _parse_date(s: str) -> Optional[date]:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    return None


def rule_name_quality(record: dict) -> tuple[bool, float, str]:
    bad_pattern = re.compile(r"[^a-zA-Z\s\-\']")
    results = []
    for field in ("first_name", "last_name"):
        val = str(record.get(field, "") or "")
        ok = len(val) >= 2 and not bad_pattern.search(val)
        results.append(ok)
    score = sum(results) / 2
    passed = score >= 0.5
    return passed, score, f"first_name={'ok' if results[0] else 'fail'}, last_name={'ok' if results[1] else 'fail'}"


def rule_country_code_valid(record: dict) -> tuple[bool, float, str]:
    country = record.get("country")
    if not country:
        return True, 1.0, "No country to validate"
    if str(country).upper() in VALID_COUNTRIES:
        return True, 1.0, f"Valid country: {country}"
    return False, 0.0, f"Unknown country code: {country}"


def rule_no_test_data(record: dict) -> tuple[bool, float, str]:
    haystack = " ".join(str(record.get(f, "") or "") for f in ("first_name", "last_name", "email"))
    if TEST_PATTERNS.search(haystack):
        return False, 0.0, "Test/fake data pattern detected"
    return True, 1.0, "No test patterns found"


def rule_kyc_consistency(record: dict) -> tuple[bool, float, str]:
    if record.get("source_system") != "KYC":
        return True, 1.0, "Not a KYC record — skipped"
    checks = []
    status = record.get("kyc_status", "")
    if status == "VERIFIED":
        checks.append(bool(record.get("kyc_verified_at")))
    if status == "EXPIRED":
        checks.append(bool(record.get("kyc_expiry_at")))
        if record.get("kyc_expiry_at"):
            try:
                expiry = datetime.fromisoformat(str(record["kyc_expiry_at"]))
                checks.append(expiry < datetime.utcnow())
            except Exception:
                checks.append(False)
    if record.get("kyc_tier") == "ENHANCED":
        checks.append(record.get("is_pep") or record.get("risk_rating") in ("HIGH", "CRITICAL"))
    if not checks:
        return True, 1.0, "No KYC consistency checks applicable"
    score = sum(checks) / len(checks)
    return score >= 0.75, round(score, 3), f"Passed {sum(checks)}/{len(checks)} KYC consistency checks"


RULE_WEIGHTS = {
    "completeness": 0.25,
    "email_format": 0.10,
    "phone_format": 0.08,
    "dob_valid": 0.20,
    "name_quality": 0.15,
    "country_valid": 0.10,
    "no_test_data": 0.07,
    "kyc_consistency": 0.05,
}


def validate_record(record: dict) -> dict:
    rules_map = [
        ("completeness", rule_completeness),
        ("email_format", rule_email_format),
        ("phone_format", rule_phone_format),
        ("dob_valid", rule_date_of_birth_valid),
        ("name_quality", rule_name_quality),
        ("country_valid", rule_country_code_valid),
        ("no_test_data", rule_no_test_data),
        ("kyc_consistency", rule_kyc_consistency),
    ]
    results = []
    weighted_score = 0.0
    for name, fn in rules_map:
        passed, score, details = fn(record)
        results.append({"rule_name": name, "passed": passed, "score": score, "details": details})
        weighted_score += score * RULE_WEIGHTS[name]

    overall = round(weighted_score, 4)
    return {
        "source_id": record.get("external_id", ""),
        "source_system": record.get("source_system", ""),
        "overall_score": overall,
        "passed": overall >= 0.60,
        "rules": results,
        "checked_at": datetime.utcnow().isoformat(),
    }


def validate_batch(records: list[dict]) -> dict:
    passed, failed = [], []
    scores = []
    for r in records:
        result = validate_record(r)
        scores.append(result["overall_score"])
        if result["passed"]:
            passed.append({**r, "dq_score": result["overall_score"], "dq_report": result})
        else:
            failed.append({**r, "dq_score": result["overall_score"], "dq_report": result})

    buckets = {"0.0-0.6": 0, "0.6-0.7": 0, "0.7-0.85": 0, "0.85-1.0": 0}
    for s in scores:
        if s < 0.6:
            buckets["0.0-0.6"] += 1
        elif s < 0.7:
            buckets["0.6-0.7"] += 1
        elif s < 0.85:
            buckets["0.7-0.85"] += 1
        else:
            buckets["0.85-1.0"] += 1

    return {
        "passed": passed,
        "failed": failed,
        "stats": {
            "total": len(records),
            "passed_count": len(passed),
            "failed_count": len(failed),
            "avg_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
            "score_distribution": buckets,
        },
    }
