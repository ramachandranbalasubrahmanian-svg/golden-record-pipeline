"""Tests for entity resolution features."""
from app.pipeline.entity_resolution import compute_features, generate_candidate_pairs


def _rec(id_, fn, ln, dob, email, phone, source="CRM"):
    return {
        "id": id_, "first_name": fn, "last_name": ln,
        "date_of_birth": dob, "email": email, "phone": phone,
        "source_system": source, "city": "New York", "country": "US",
    }


def test_exact_match_scores_high():
    a = _rec("a1", "John", "Smith", "1985-03-15", "jsmith@gmail.com", "+15551234567", "CRM")
    b = _rec("b1", "JOHN", "SMITH", "15/03/1985", "jsmith@gmail.com", "5551234567", "KYC")
    feats = compute_features(a, b)
    assert feats["last_name_soundex_match"] == 1.0
    assert feats["email_exact_match"] == 1.0
    assert feats["dob_exact_match"] == 1.0


def test_different_people_score_low():
    a = _rec("a2", "Alice", "Johnson", "1990-01-01", "alice@gmail.com", "+44201234567", "CRM")
    b = _rec("b2", "Bob", "Williams", "1975-06-15", "bob@yahoo.com", "+19871234567", "KYC")
    feats = compute_features(a, b)
    assert feats["last_name_jaro_winkler"] < 0.5
    assert feats["email_exact_match"] == 0.0


def test_blocking_reduces_pairs():
    records = [
        _rec(f"r{i}", "John", "Smith", "1985-03-15", f"j{i}@test.com", f"+1555{i:07d}")
        for i in range(100)
    ]
    pairs = generate_candidate_pairs(records)
    assert len(pairs) < 100 * 99 / 2
