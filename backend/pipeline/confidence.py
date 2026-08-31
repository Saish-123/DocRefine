from typing import Dict, Any, List, Optional

def calculate_field_confidence(
    ocr_confidence: float,
    structuring_confidence: float,
    validation_score: float,
    quality_score: int,
    raw_value: Optional[Any],
    validation_status: str,
    is_ambiguous_ocr: bool = False
) -> Dict[str, Any]:
    """
    Computes field-level confidence score and state according to PRD P0.7 formula:
      base = 0.45 * ocr_conf + 0.35 * struct_conf + 0.20 * val_score
      quality_factor = clamp(quality_score / 100, 0.50, 1.00)
      field_score = round(100 * base * quality_factor)

    Hard caps:
      - missing value: 0
      - failed format/pattern check: max 59
      - ambiguous OCR: max 59
    """
    # Check for missing value safely even if raw_value is numeric (int/float)
    raw_value_str = "" if raw_value is None else str(raw_value)
    if not raw_value_str or raw_value_str.strip() == "":
        return {
            "field_score": 0,
            "confidence_state": "Red",
            "ocr_confidence": round(ocr_confidence, 2),
            "structuring_confidence": round(structuring_confidence, 2),
            "validation_score": 0.0,
            "quality_factor": round(max(0.50, min(1.0, quality_score / 100.0)), 2),
            "reason_codes": ["MISSING_FIELD_VALUE"]
        }

    # Normalize inputs to 0.00 - 1.00
    norm_ocr = max(0.0, min(1.0, float(ocr_confidence)))
    norm_struct = max(0.0, min(1.0, float(structuring_confidence)))
    norm_val = max(0.0, min(1.0, float(validation_score)))

    base = (0.45 * norm_ocr) + (0.35 * norm_struct) + (0.20 * norm_val)
    quality_factor = max(0.50, min(1.00, quality_score / 100.0))
    raw_field_score = round(100.0 * base * quality_factor)

    reason_codes: List[str] = []

    # Apply Hard Caps
    final_score = raw_field_score
    if validation_status == "invalid":
        final_score = min(final_score, 59)
        reason_codes.append("HARD_CAP_FORMAT_VALIDATION_FAILED")

    if is_ambiguous_ocr or norm_ocr < 0.60:
        final_score = min(final_score, 59)
        reason_codes.append("HARD_CAP_AMBIGUOUS_OCR_EVIDENCE")

    if quality_score < 45:
        final_score = min(final_score, 59)
        reason_codes.append("HARD_CAP_LOW_INPUT_QUALITY")

    # Determine Color State
    if final_score >= 85 and validation_status != "invalid" and not is_ambiguous_ocr:
        confidence_state = "Green"
    elif final_score >= 60:
        confidence_state = "Yellow"
        reason_codes.append("REVIEW_RECOMMENDED")
    else:
        confidence_state = "Red"
        reason_codes.append("ATTENTION_REQUIRED")

    return {
        "field_score": int(final_score),
        "confidence_state": confidence_state,
        "ocr_confidence": round(norm_ocr, 2),
        "structuring_confidence": round(norm_struct, 2),
        "validation_score": round(norm_val, 2),
        "quality_factor": round(quality_factor, 2),
        "reason_codes": reason_codes
    }
