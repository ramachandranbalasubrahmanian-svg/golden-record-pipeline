"""Tests for data quality validation."""
from app.pipeline.data_quality import validate_record, validate_batch


def _good_record():
    return {
        "external_id": "CRM-000001",
        "source_system": "CRM",
        "first_name": "John",
        "last_name": "Smith",
        "date_of_birth": "1985-03-15",
        "country": "US",
        "email": "john.smith@gmail.com",
        "phone": "+15551234567",
        "address_line1": "123 Main St",
        "city": "New York",
    }


def test_good_record_passes():
    result = validate_record(_good_record())
    assert result["passed"] is True
    assert result["overall_score"] >= 0.60


def test_missing_required_fields_fails():
    rec = {"external_id": "X", "source_system": "CRM", "email": "bad"}
    result = validate_record(rec)
    assert result["overall_score"] < 0.60


def test_invalid_email_penalized():
    rec = {**_good_record(), "email": "not-an-email"}
    result = validate_record(rec)
    email_rule = next(r for r in result["rules"] if r["rule_name"] == "email_format")
    assert email_rule["passed"] is False


def test_test_data_flagged():
    rec = {**_good_record(), "first_name": "Test", "last_name": "User"}
    result = validate_record(rec)
    test_rule = next(r for r in result["rules"] if r["rule_name"] == "no_test_data")
    assert test_rule["passed"] is False


def test_batch_validation():
    records = [_good_record() for _ in range(5)]
    result = validate_batch(records)
    assert result["stats"]["total"] == 5
    assert result["stats"]["passed_count"] == 5
