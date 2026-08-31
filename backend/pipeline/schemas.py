import re
import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field

DOCUMENT_SCHEMAS: Dict[str, List[Dict[str, Any]]] = {
    "education_marksheet": [
        {"key": "candidate_name", "label": "Candidate / Student Name", "type": "string", "required": True},
        {"key": "mother_name", "label": "Mother's Name", "type": "string", "required": False},
        {"key": "seat_number", "label": "Seat / Roll Number", "type": "string", "required": True},
        {"key": "center_number", "label": "Center / School Index No", "type": "string", "required": False},
        {"key": "board_university", "label": "Board / University", "type": "string", "required": True},
        {"key": "examination_name", "label": "Examination Session / Year", "type": "string", "required": True},
        {"key": "date_of_birth", "label": "Date of Birth (YYYY-MM-DD)", "type": "date", "required": False},
        {"key": "total_marks", "label": "Total Marks Obtained / Out of", "type": "string", "required": True},
        {"key": "percentage", "label": "Percentage / GPA", "type": "string", "required": False},
        {"key": "result_status", "label": "Result Status (Pass/Distinction)", "type": "string", "required": True},
        {"key": "subject_scores", "label": "Subjects & Marks Breakdown", "type": "string", "required": False}
    ],
    "leaving_certificate": [
        {"key": "candidate_name", "label": "Student Name", "type": "string", "required": True},
        {"key": "date_of_birth", "label": "Date of Birth (YYYY-MM-DD)", "type": "date", "required": True},
        {"key": "institution_name", "label": "Institution / School Name", "type": "string", "required": True},
        {"key": "class_last_studied", "label": "Class / Standard Last Studied", "type": "string", "required": True},
        {"key": "year_of_leaving", "label": "Year of Leaving", "type": "string", "required": True},
        {"key": "conduct", "label": "Conduct / Character", "type": "string", "required": False},
        {"key": "reason_for_leaving", "label": "Reason for Leaving", "type": "string", "required": False},
        {"key": "principal_name", "label": "Principal / Authority Name", "type": "string", "required": False},
        {"key": "date_of_issue", "label": "Date of Issue (YYYY-MM-DD)", "type": "date", "required": False}
    ],
    "identity_document": [
        {"key": "full_name", "label": "Full Name", "type": "string", "required": True},
        {"key": "document_number", "label": "Aadhaar / Document Number", "type": "string", "required": True},
        {"key": "date_of_birth", "label": "Date of Birth (YYYY-MM-DD)", "type": "date", "required": True},
        {"key": "gender", "label": "Gender", "type": "string", "required": False},
        {"key": "address", "label": "Address", "type": "string", "required": False}
    ],
    "tax_id": [
        {"key": "full_name", "label": "Full Name", "type": "string", "required": True},
        {"key": "tax_id_number", "label": "Tax ID / PAN Number", "type": "string", "required": True},
        {"key": "date_of_birth", "label": "Date of Birth (YYYY-MM-DD)", "type": "date", "required": True}
    ],
    "address_proof": [
        {"key": "full_name", "label": "Full Name", "type": "string", "required": True},
        {"key": "address", "label": "Address", "type": "string", "required": True},
        {"key": "document_number", "label": "Document / Consumer Number", "type": "string", "required": False},
        {"key": "issue_date", "label": "Issue Date (YYYY-MM-DD)", "type": "date", "required": False}
    ],
    "fee_receipt": [
        {"key": "student_name", "label": "Student / Payer Name", "type": "string", "required": True},
        {"key": "receipt_number", "label": "Receipt / Transaction No", "type": "string", "required": True},
        {"key": "institution_name", "label": "College / Institution Name", "type": "string", "required": True},
        {"key": "course_class", "label": "Class / Course (e.g. SYJC)", "type": "string", "required": False},
        {"key": "roll_number", "label": "Roll / Admission / PRN No", "type": "string", "required": False},
        {"key": "date", "label": "Receipt Date (YYYY-MM-DD)", "type": "date", "required": True},
        {"key": "total_amount_paid", "label": "Total Amount Paid (INR)", "type": "currency", "required": True},
        {"key": "payment_mode", "label": "Payment Mode / Ref No", "type": "string", "required": False},
        {"key": "fee_breakdown", "label": "Fee Head Breakdown", "type": "string", "required": False}
    ],
    "bank_statement": [
        {"key": "account_holder_name", "label": "Account Holder Name", "type": "string", "required": True},
        {"key": "account_number", "label": "Account Number", "type": "string", "required": True},
        {"key": "ifsc", "label": "IFSC Code", "type": "string", "required": True},
        {"key": "bank_name", "label": "Bank Name", "type": "string", "required": True},
        {"key": "closing_balance", "label": "Closing Balance (INR)", "type": "currency", "required": False}
    ],
    "medical_prescription": [
        {"key": "patient_name", "label": "Patient Name", "type": "string", "required": True},
        {"key": "doctor_name", "label": "Doctor / Clinic Name", "type": "string", "required": True},
        {"key": "date", "label": "Prescription Date (YYYY-MM-DD)", "type": "date", "required": True},
        {"key": "diagnosis", "label": "Diagnosis / Symptoms", "type": "string", "required": False},
        {"key": "medications", "label": "Prescribed Medications & Dosage", "type": "string", "required": True}
    ],
    "generic": [
        {"key": "document_title", "label": "Document Title / Heading", "type": "string", "required": False},
        {"key": "primary_party", "label": "Primary Person / Organization", "type": "string", "required": False},
        {"key": "identifier_number", "label": "Reference / ID Number", "type": "string", "required": False},
        {"key": "issue_date", "label": "Date (YYYY-MM-DD)", "type": "date", "required": False},
        {"key": "summary_details", "label": "Key Extracted Content", "type": "string", "required": False}
    ]
}

PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")
IFSC_REGEX = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$", re.IGNORECASE)
AADHAAR_REGEX = re.compile(r"^\d{4}\s?\d{4}\s?\d{4}$")
DATE_ISO_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Formats attempted, in order, when the value contains a textual month
# name (e.g. "12 April 2006", "March 31, 2024") - very common on Indian
# certificates/marksheets/receipts.
_TEXTUAL_DATE_FORMATS = (
    "%d %B %Y", "%d %b %Y",       # 12 April 2006 / 12 Apr 2006
    "%B %d, %Y", "%b %d, %Y",     # April 12, 2006 / Apr 12, 2006
    "%B %d %Y", "%b %d %Y",       # April 12 2006
    "%d-%B-%Y", "%d-%b-%Y",       # 12-April-2006
)


def _is_valid_calendar_date(y: int, m: int, d: int) -> bool:
    """Real calendar validity check."""
    try:
        datetime.date(y, m, d)
        return True
    except ValueError:
        return False


def normalize_date(val: Optional[Any]) -> Optional[str]:
    if val is None or val == "":
        return None
    # Coerce to str safely in case raw LLM response provided int/float
    val = str(val).strip()

    # Try textual-month formats first
    for fmt in _TEXTUAL_DATE_FORMATS:
        try:
            parsed = datetime.datetime.strptime(val, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Replace space separators with dashes if 2006 03 31
    val_dashed = re.sub(r"[/\.\s]", "-", val)
    if DATE_ISO_REGEX.match(val_dashed):
        y, m, d = (int(x) for x in val_dashed.split("-"))
        if _is_valid_calendar_date(y, m, d):
            return val_dashed
        return val

    # Match DD-MM-YYYY
    match_dmy = re.match(r"^(\d{1,2})-(\d{1,2})-(\d{4})$", val_dashed)
    if match_dmy:
        d, m, y = (int(g) for g in match_dmy.groups())
        if _is_valid_calendar_date(y, m, d):
            return f"{y:04d}-{m:02d}-{d:02d}"
        return val

    # Match YYYY-MM-DD
    match_ymd = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", val_dashed)
    if match_ymd:
        y, m, d = (int(g) for g in match_ymd.groups())
        if _is_valid_calendar_date(y, m, d):
            return f"{y:04d}-{m:02d}-{d:02d}"
        return val

    return val

def validate_field_value(field_key: str, raw_val: Optional[Any], normalized_val: Optional[Any]) -> tuple[float, str, List[str]]:
    if raw_val is None and normalized_val is None:
        return 0.0, "missing", ["FIELD_VALUE_MISSING"]
    if raw_val == "" and normalized_val in (None, ""):
        return 0.0, "missing", ["FIELD_VALUE_MISSING"]

    chosen = normalized_val if normalized_val not in (None, "") else raw_val
    val = str(chosen).strip() if chosen is not None else ""
    if val.upper() in ("NONE", "NULL", "[MISSING / UNREADABLE]"):
        return 0.0, "missing", ["FIELD_VALUE_MISSING"]

    if field_key in ("tax_id_number", "pan"):
        clean_pan = val.replace(" ", "").upper()
        if PAN_REGEX.match(clean_pan):
            return 1.0, "valid", ["PAN_FORMAT_VERIFIED"]
        else:
            return 0.0, "invalid", ["INVALID_PAN_FORMAT"]

    if field_key == "ifsc":
        clean_ifsc = val.replace(" ", "").upper()
        if IFSC_REGEX.match(clean_ifsc):
            return 1.0, "valid", ["IFSC_FORMAT_VERIFIED"]
        else:
            return 0.0, "invalid", ["INVALID_IFSC_FORMAT"]

    if "date" in field_key or field_key == "date_of_birth":
        norm_d = normalize_date(val)
        if norm_d and DATE_ISO_REGEX.match(norm_d):
            try:
                y, m, d = (int(x) for x in norm_d.split("-"))
                datetime.date(y, m, d)
                return 1.0, "valid", ["DATE_ISO_VERIFIED"]
            except ValueError:
                return 0.0, "invalid", ["INVALID_CALENDAR_DATE"]
        return 0.5, "weak", ["NON_STANDARD_DATE_FORMAT"]

    if field_key in ("candidate_name", "full_name", "mother_name", "account_holder_name", "patient_name", "doctor_name"):
        if len(val) >= 2 and not val.isdigit():
            return 1.0, "valid", ["NAME_PLAUSIBLE"]
        return 0.5, "weak", ["NAME_SUSPICIOUS"]

    if field_key in ("seat_number", "document_number", "center_number"):
        if len(val) >= 3:
            return 1.0, "valid", ["IDENTIFIER_VALID"]
        return 0.5, "weak", ["IDENTIFIER_SHORT"]

    if field_key in ("total_marks", "percentage", "result_status", "subject_scores", "board_university", "examination_name", "address"):
        if len(val) >= 2:
            return 1.0, "valid", ["FIELD_VERIFIED"]
        return 0.5, "weak", ["FIELD_SHORT"]

    return 1.0, "valid", ["FIELD_POPULATED"]
