"""Entity Resolution — blocking + feature engineering + match scoring."""
from __future__ import annotations
import re
import pickle
from pathlib import Path
from datetime import datetime, date
from typing import Optional

import jellyfish
from fuzzywuzzy import fuzz

MODEL_PATH = Path(__file__).parent.parent.parent / "ml" / "er_model.pkl"

ISO2_TO_ISO2 = {}  # identity mapping; extended in normalize_country
ABBREV_MAP = {
    r"\bSt\b": "Street", r"\bAve\b": "Avenue", r"\bApt\b": "Apartment",
    r"\bBlvd\b": "Boulevard", r"\bDr\b": "Drive", r"\bRd\b": "Road",
}
NICKNAME_MAP = {
    "william": "bill", "bill": "william",
    "elizabeth": "liz", "liz": "elizabeth",
    "michael": "mike", "mike": "michael",
    "robert": "rob", "rob": "robert",
    "richard": "rick", "rick": "richard",
    "christopher": "chris", "chris": "christopher",
    "jennifer": "jen", "jen": "jennifer",
    "katherine": "kate", "kate": "katherine",
    "thomas": "tom", "tom": "thomas",
    "james": "jim", "jim": "james",
    "joseph": "joe", "joe": "joseph",
    "patricia": "pat", "pat": "patricia",
    "timothy": "tim", "tim": "timothy",
    "daniel": "dan", "dan": "daniel",
    "anthony": "tony", "tony": "anthony",
}


# ─── Date helpers ──────────────────────────────────────────────────────────────

def parse_dob(s) -> Optional[date]:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(s)[:10], fmt).date()
        except ValueError:
            continue
    return None


def parse_year(s) -> Optional[int]:
    d = parse_dob(s)
    return d.year if d else None


# ─── String helpers ────────────────────────────────────────────────────────────

def normalize_email(email) -> str:
    return str(email or "").lower().strip()


def email_domain(email) -> str:
    e = normalize_email(email)
    return e.split("@")[-1] if "@" in e else ""


def phone_digit_similarity(p1, p2) -> float:
    d1 = re.sub(r"\D", "", str(p1 or ""))
    d2 = re.sub(r"\D", "", str(p2 or ""))
    if not d1 or not d2:
        return 0.0
    shorter, longer = (d1, d2) if len(d1) <= len(d2) else (d2, d1)
    matches = sum(c1 == c2 for c1, c2 in zip(shorter, longer))
    return matches / max(len(d1), len(d2))


def last_n_digits(phone, n: int) -> str:
    return re.sub(r"\D", "", str(phone or ""))[-n:]


def normalize_address(addr) -> str:
    s = str(addr or "").lower()
    for pattern, replacement in ABBREV_MAP.items():
        s = re.sub(pattern, replacement, s, flags=re.IGNORECASE)
    return s


def normalize_country(code) -> str:
    mapping = {
        "USA": "US", "GBR": "GB", "DEU": "DE", "FRA": "FR", "CHN": "CN",
        "JPN": "JP", "SAU": "SA", "BRA": "BR", "IND": "IN", "CAN": "CA",
        "AUS": "AU", "SGP": "SG", "CHE": "CH", "NLD": "NL", "SWE": "SE",
    }
    c = str(code or "").upper()
    return mapping.get(c, c[:2])


def normalized_levenshtein(a: str, b: str) -> float:
    a, b = str(a or "").lower(), str(b or "").lower()
    if not a and not b:
        return 1.0
    dist = jellyfish.levenshtein_distance(a, b)
    return 1.0 - dist / max(len(a), len(b), 1)


# ─── Blocking ──────────────────────────────────────────────────────────────────

def _blocking_keys(rec: dict) -> set[str]:
    keys = set()
    ln = str(rec.get("last_name") or "").strip()
    dob = str(rec.get("date_of_birth") or "")
    year = parse_year(dob)
    month_year = dob[:7] if len(dob) >= 7 else ""

    if ln and year:
        try:
            sdx = jellyfish.soundex(ln)
            keys.add(f"sdx_{sdx}_{year}")
        except Exception:
            pass
        keys.add(f"pre3_{ln[:3].lower()}_{year}")
        try:
            meta = jellyfish.metaphone(ln)
            keys.add(f"meta_{meta}_{month_year}")
        except Exception:
            pass

    email = str(rec.get("email") or "").lower()
    if email and "@" in email:
        keys.add(f"email5_{email[:5]}")

    return keys


def generate_candidate_pairs(records: list[dict]) -> list[tuple[str, str]]:
    blocks: dict[str, list[str]] = {}
    for rec in records:
        rid = str(rec.get("id") or rec.get("external_id", ""))
        for key in _blocking_keys(rec):
            blocks.setdefault(key, []).append(rid)

    pairs: set[tuple[str, str]] = set()
    for ids in blocks.values():
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                pairs.add((min(a, b), max(a, b)))

    n = len(records)
    total_possible = n * (n - 1) / 2
    reduction = 1 - len(pairs) / total_possible if total_possible > 0 else 0
    print(f"Generated {len(pairs)} candidate pairs from {n} records (reduction ratio: {reduction:.1%})")
    return list(pairs)


# ─── Features ──────────────────────────────────────────────────────────────────

def compute_features(record_a: dict, record_b: dict) -> dict:
    a, b = record_a, record_b

    def safe_jw(x, y):
        try:
            return jellyfish.jaro_winkler_similarity(str(x or ""), str(y or ""))
        except Exception:
            return 0.0

    def safe_sdx(x, y):
        try:
            return 1.0 if jellyfish.soundex(str(x or "")) == jellyfish.soundex(str(y or "")) else 0.0
        except Exception:
            return 0.0

    def safe_meta(x, y):
        try:
            return 1.0 if jellyfish.metaphone(str(x or "")) == jellyfish.metaphone(str(y or "")) else 0.0
        except Exception:
            return 0.0

    dob_a, dob_b = parse_dob(a.get("date_of_birth")), parse_dob(b.get("date_of_birth"))
    year_a, year_b = parse_year(a.get("date_of_birth")), parse_year(b.get("date_of_birth"))

    email_a = normalize_email(a.get("email"))
    email_b = normalize_email(b.get("email"))

    return {
        "first_name_jaro_winkler": safe_jw(a.get("first_name"), b.get("first_name")),
        "last_name_jaro_winkler": safe_jw(a.get("last_name"), b.get("last_name")),
        "last_name_levenshtein_norm": normalized_levenshtein(a.get("last_name"), b.get("last_name")),
        "full_name_token_sort_ratio": fuzz.token_sort_ratio(
            str(a.get("full_name") or f"{a.get('first_name','')} {a.get('last_name','')}"),
            str(b.get("full_name") or f"{b.get('first_name','')} {b.get('last_name','')}"),
        ) / 100,
        "full_name_partial_ratio": fuzz.partial_ratio(
            str(a.get("full_name") or ""), str(b.get("full_name") or "")
        ) / 100,
        "dob_exact_match": 1.0 if dob_a and dob_b and dob_a == dob_b else 0.0,
        "birth_year_match": (
            1.0 if year_a and year_b and year_a == year_b
            else 0.5 if year_a and year_b and abs(year_a - year_b) <= 1
            else 0.0
        ),
        "email_exact_match": 1.0 if email_a and email_b and email_a == email_b else 0.0,
        "email_domain_match": 1.0 if email_domain(a.get("email")) == email_domain(b.get("email")) and email_domain(a.get("email")) else 0.0,
        "phone_digit_match": phone_digit_similarity(a.get("phone"), b.get("phone")),
        "phone_last6_match": 1.0 if last_n_digits(a.get("phone"), 6) == last_n_digits(b.get("phone"), 6) and last_n_digits(a.get("phone"), 6) else 0.0,
        "address_token_sort": fuzz.token_sort_ratio(
            normalize_address(a.get("address_line1")), normalize_address(b.get("address_line1"))
        ) / 100,
        "city_match": 1.0 if str(a.get("city") or "").lower() == str(b.get("city") or "").lower() and a.get("city") else 0.0,
        "country_match": 1.0 if normalize_country(a.get("country")) == normalize_country(b.get("country")) and a.get("country") else 0.0,
        "last_name_soundex_match": safe_sdx(a.get("last_name"), b.get("last_name")),
        "last_name_metaphone_match": safe_meta(a.get("last_name"), b.get("last_name")),
        "first_name_soundex_match": safe_sdx(a.get("first_name"), b.get("first_name")),
        "source_system_different": 1.0 if a.get("source_system") != b.get("source_system") else 0.0,
        "both_have_email": 1.0 if a.get("email") and b.get("email") else 0.0,
        "both_have_phone": 1.0 if a.get("phone") and b.get("phone") else 0.0,
    }


FEATURE_NAMES = [
    "first_name_jaro_winkler", "last_name_jaro_winkler", "last_name_levenshtein_norm",
    "full_name_token_sort_ratio", "full_name_partial_ratio", "dob_exact_match",
    "birth_year_match", "email_exact_match", "email_domain_match", "phone_digit_match",
    "phone_last6_match", "address_token_sort", "city_match", "country_match",
    "last_name_soundex_match", "last_name_metaphone_match", "first_name_soundex_match",
    "source_system_different", "both_have_email", "both_have_phone",
]


# ─── Rule-based fallback ───────────────────────────────────────────────────────

def rule_based_predict(features: dict) -> float:
    dob = features.get("dob_exact_match", 0)
    lnj = features.get("last_name_jaro_winkler", 0)
    email = features.get("email_exact_match", 0)
    p6 = features.get("phone_last6_match", 0)
    sdx = features.get("last_name_soundex_match", 0)
    city = features.get("city_match", 0)

    if dob == 1.0 and lnj >= 0.85:
        return 0.95
    if email == 1.0:
        return 0.92
    if p6 == 1.0 and sdx == 1.0 and city == 1.0:
        return 0.88
    return 0.10


# ─── Union-Find ────────────────────────────────────────────────────────────────

class UnionFind:
    def __init__(self):
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: str, y: str):
        self.parent[self.find(x)] = self.find(y)

    def clusters(self) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = {}
        for node in self.parent:
            root = self.find(node)
            groups.setdefault(root, []).append(node)
        return groups


# ─── Main entry point ──────────────────────────────────────────────────────────

def run_entity_resolution(source_records: list[dict], ground_truth_path: str = None) -> dict:
    model = None
    threshold = 0.70
    if MODEL_PATH.exists():
        with open(MODEL_PATH, "rb") as f:
            saved = pickle.load(f)
            model = saved.get("model")
            threshold = saved.get("threshold", 0.70)

    record_map = {str(r.get("id") or r.get("external_id")): r for r in source_records}
    pairs = generate_candidate_pairs(source_records)

    match_pairs_out = []
    uf = UnionFind()

    for rid_a, rid_b in pairs:
        ra = record_map.get(rid_a)
        rb = record_map.get(rid_b)
        if not ra or not rb:
            continue
        features = compute_features(ra, rb)

        if model:
            import pandas as pd
            x = pd.DataFrame([features])[FEATURE_NAMES]
            prob = float(model.predict_proba(x)[0][1])
        else:
            prob = rule_based_predict(features)

        match_pairs_out.append({
            "record_a_id": rid_a,
            "record_b_id": rid_b,
            "match_probability": round(prob, 4),
            "match_features": features,
            "status": "auto_merged" if prob >= threshold else "pending",
        })

        if prob >= threshold:
            uf.union(rid_a, rid_b)
        elif prob >= 0.30:
            uf.parent.setdefault(rid_a, rid_a)
            uf.parent.setdefault(rid_b, rid_b)

    clusters = uf.clusters()
    singletons = sum(1 for ids in clusters.values() if len(ids) == 1)

    return {
        "pairs_evaluated": len(pairs),
        "match_pairs": [p for p in match_pairs_out if float(p["match_probability"]) >= 0.30],
        "clusters": clusters,
        "clusters_formed": len(clusters),
        "singleton_records": singletons,
    }
