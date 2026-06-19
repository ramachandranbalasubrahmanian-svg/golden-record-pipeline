"""Survivorship Engine — resolves entity clusters into authoritative Golden Records."""
from __future__ import annotations
from datetime import datetime
from typing import Optional

SOURCE_TRUST_WEIGHTS = {
    "KYC": 1.00,
    "CBS": 0.95,
    "RISK": 0.90,
    "CRM": 0.70,
}

REGULATORY_LOCK_ATTRIBUTES = {
    "is_pep", "pep_type", "pep_detected_at",
    "is_sanctioned", "sanctions_list", "sanctions_detected_at",
    "kyc_status", "kyc_tier", "kyc_verified_at", "kyc_expiry_at",
}

KEY_ATTRIBUTES = [
    "first_name", "last_name", "full_legal_name", "date_of_birth",
    "email", "phone", "address_line1", "city", "country", "nationality",
    "kyc_status", "kyc_tier", "risk_rating", "is_pep", "is_sanctioned",
]

SKIP_ATTRS = {"id", "external_id", "source_system", "_score", "ingested_at",
              "dq_score", "dq_report", "quarantined", "raw_data"}


def _recency_score(record: dict, max_days: int = 365) -> float:
    ingested = record.get("ingested_at")
    if not ingested:
        return 0.5
    if isinstance(ingested, str):
        try:
            ingested = datetime.fromisoformat(ingested)
        except Exception:
            return 0.5
    days = (datetime.utcnow() - ingested).days
    return max(0.0, 1.0 - days / max_days)


def _final_score(record: dict) -> float:
    trust = SOURCE_TRUST_WEIGHTS.get(str(record.get("source_system", "")), 0.5)
    recency = _recency_score(record)
    completeness = 1.0
    return round(trust * 0.50 + recency * 0.30 + completeness * 0.20, 4)


def build_lineage_entry(
    attribute: str,
    winner_record: dict,
    all_records: list[dict],
    rule: str,
) -> dict:
    competing = [
        {
            "source": r.get("source_system"),
            "value": str(r.get(attribute, "") or ""),
            "score": r.get("_score", 0),
        }
        for r in all_records
        if r is not winner_record and r.get(attribute) is not None
    ]
    return {
        "attribute_name": attribute,
        "winning_value": str(winner_record.get(attribute, "") or ""),
        "winning_source": winner_record.get("source_system"),
        "survivorship_rule": rule,
        "confidence": winner_record.get("_score", 0),
        "is_regulatory_lock": attribute in REGULATORY_LOCK_ATTRIBUTES,
        "competing_sources": competing,
        "resolved_at": datetime.utcnow().isoformat(),
    }


def resolve_cluster(cluster_records: list[dict], source_system_col: str = "source_system") -> dict:
    scored = []
    for rec in cluster_records:
        r = dict(rec)
        r["_score"] = _final_score(r)
        scored.append(r)

    kyc_records = [r for r in scored if r.get("source_system") == "KYC"]
    cbs_records = [r for r in scored if r.get("source_system") == "CBS"]

    all_attrs = set()
    for r in scored:
        all_attrs.update(k for k in r.keys() if k not in SKIP_ATTRS)

    golden: dict = {}
    lineage: list[dict] = []

    for attr in sorted(all_attrs):
        candidates = [r for r in scored if r.get(attr) is not None and r.get(attr) != ""]

        if not candidates:
            continue

        if attr in REGULATORY_LOCK_ATTRIBUTES:
            winner = next((r for r in kyc_records if r.get(attr) is not None), None)
            if not winner:
                winner = next((r for r in cbs_records if r.get(attr) is not None), None)
            if not winner:
                winner = max(candidates, key=lambda r: r["_score"])
            rule = "REGULATORY_LOCK"
        else:
            winner = max(candidates, key=lambda r: r["_score"])
            trust_scores = [SOURCE_TRUST_WEIGHTS.get(r.get("source_system", ""), 0.5) for r in candidates]
            recency_scores = [_recency_score(r) for r in candidates]
            if max(trust_scores) != min(trust_scores):
                rule = "HIGHEST_TRUST"
            elif max(recency_scores) != min(recency_scores):
                rule = "MOST_RECENT"
            else:
                rule = "HIGHEST_TRUST"

        golden[attr] = winner.get(attr)
        lineage.append(build_lineage_entry(attr, winner, scored, rule))

    golden["confidence_score"] = calculate_confidence(cluster_records, lineage)
    golden["source_count"] = len(cluster_records)
    golden["winning_sources"] = {
        entry["attribute_name"]: entry["winning_source"] for entry in lineage
    }

    return {"golden": golden, "lineage": lineage}


def calculate_confidence(cluster_records: list[dict], lineage: list[dict]) -> float:
    source_systems = {r.get("source_system") for r in cluster_records}
    source_coverage = len(source_systems) / 4.0

    total = len(lineage)
    if total == 0:
        return 0.5
    agreed = sum(1 for e in lineage if not e.get("competing_sources"))
    agreement_rate = agreed / total

    key_wins = sum(
        1 for e in lineage
        if e["attribute_name"] in KEY_ATTRIBUTES and e.get("winning_value")
    )
    completeness = key_wins / len(KEY_ATTRIBUTES)

    confidence = source_coverage * 0.3 + agreement_rate * 0.4 + completeness * 0.3
    return round(min(1.0, max(0.0, confidence)), 4)


def resolve_all_clusters(clusters: list[dict], source_records_map: dict) -> dict:
    golden_records = []
    lineages = []

    for cluster in clusters:
        record_ids = cluster.get("record_ids", [])
        recs = [source_records_map[rid] for rid in record_ids if rid in source_records_map]
        if not recs:
            continue
        result = resolve_cluster(recs)
        gr = result["golden"]
        gr["cluster_id"] = cluster.get("cluster_id")
        golden_records.append(gr)
        lineages.append((cluster.get("cluster_id"), result["lineage"]))

    avg_conf = sum(g.get("confidence_score", 0) for g in golden_records) / max(len(golden_records), 1)
    reg_locks = sum(
        sum(1 for e in lin if e.get("is_regulatory_lock"))
        for _, lin in lineages
    )

    print(f"Created {len(golden_records)} golden records")
    print(f"Avg confidence: {avg_conf:.3f}")
    print(f"Regulatory locks applied: {reg_locks} attributes")

    return {
        "golden_records": golden_records,
        "lineages": lineages,
        "clusters_processed": len(clusters),
        "golden_records_created": len(golden_records),
        "avg_confidence": avg_conf,
    }
