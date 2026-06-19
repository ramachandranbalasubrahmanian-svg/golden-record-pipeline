"""Tests for survivorship engine."""
from datetime import datetime, timedelta
from app.pipeline.survivorship import resolve_cluster, REGULATORY_LOCK_ATTRIBUTES


def _rec(source, is_pep=False, kyc_status="VERIFIED", risk_rating="LOW"):
    now = datetime.utcnow()
    return {
        "source_system": source,
        "first_name": "John",
        "last_name": "Smith",
        "email": f"john@{source.lower()}.com",
        "date_of_birth": "1985-03-15",
        "country": "US",
        "kyc_status": kyc_status,
        "risk_rating": risk_rating,
        "is_pep": is_pep,
        "ingested_at": (now - timedelta(days=10 if source == "KYC" else 30)).isoformat(),
    }


def test_regulatory_lock_kyc_wins():
    cluster = [_rec("CRM"), _rec("KYC", is_pep=True)]
    result = resolve_cluster(cluster)
    golden = result["golden"]
    lineage = result["lineage"]

    pep_entry = next((e for e in lineage if e["attribute_name"] == "is_pep"), None)
    assert pep_entry is not None
    assert pep_entry["winning_source"] == "KYC"
    assert pep_entry["is_regulatory_lock"] is True


def test_confidence_increases_with_sources():
    single = resolve_cluster([_rec("CRM")])
    multi = resolve_cluster([_rec("CRM"), _rec("KYC"), _rec("CBS")])
    assert multi["golden"]["confidence_score"] >= single["golden"]["confidence_score"]


def test_source_count_correct():
    cluster = [_rec("CRM"), _rec("KYC"), _rec("CBS")]
    result = resolve_cluster(cluster)
    assert result["golden"]["source_count"] == 3
