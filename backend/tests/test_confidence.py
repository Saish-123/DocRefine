import pytest
from backend.pipeline.confidence import calculate_field_confidence

def test_confidence_formula_green():
    res = calculate_field_confidence(
        ocr_confidence=0.95,
        structuring_confidence=0.95,
        validation_score=1.0,
        quality_score=90,
        raw_value="ABCDE1234F",
        validation_status="valid"
    )
    assert res["field_score"] >= 85
    assert res["confidence_state"] == "Green"

def test_confidence_hard_cap_missing():
    res = calculate_field_confidence(
        ocr_confidence=0.95,
        structuring_confidence=0.95,
        validation_score=0.0,
        quality_score=90,
        raw_value="",
        validation_status="missing"
    )
    assert res["field_score"] == 0
    assert res["confidence_state"] == "Red"

def test_confidence_hard_cap_invalid():
    res = calculate_field_confidence(
        ocr_confidence=0.95,
        structuring_confidence=0.95,
        validation_score=0.0,
        quality_score=90,
        raw_value="INVALID_PAN_123",
        validation_status="invalid"
    )
    # Hard cap at max 59
    assert res["field_score"] <= 59
    assert res["confidence_state"] == "Red"
    assert "HARD_CAP_FORMAT_VALIDATION_FAILED" in res["reason_codes"]
