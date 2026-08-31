"""
Cross-document consistency checking.

Compares normalized names, dates of birth, IDs, and addresses across
multiple documents within the same case. Produces an explainable
consistency report with links to source documents.
"""

from __future__ import annotations

from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional
import re

# ---------------------------------------------------------------------------
# Config: map every possible schema field_key to a canonical signal category.
# Add new schema field names here instead of touching the matching logic.
# This is the fix for the "hardcoded field keys" problem: new document
# schemas (leaving_certificate, passport, etc.) just need an entry here.
# ---------------------------------------------------------------------------
FIELD_KEY_MAP: Dict[str, str] = {
    # Name variants
    "full_name": "name",
    "account_holder_name": "name",
    "student_name": "name",
    "candidate_name": "name",
    "holder_name": "name",
    "applicant_name": "name",
    "name": "name",

    # Date of birth variants
    "date_of_birth": "dob",
    "dob": "dob",
    "birth_date": "dob",

    # Address variants
    "address": "address",
    "residential_address": "address",
    "permanent_address": "address",
    "current_address": "address",

    # Government ID number variants (e.g. Aadhaar number, roll number, etc.)
    "id_number": "id_number",
    "aadhaar_number": "id_number",
    "tax_id_number": "id_number",
    "document_number": "id_number",
    "roll_number": "id_number",
    "seat_number": "id_number",
    "registration_number": "id_number",
}

# Below this similarity ratio (0-1), two names are considered a genuine
# conflict rather than minor OCR/formatting noise.
NAME_SIMILARITY_THRESHOLD = 0.85

# Known date formats we'll try when parsing raw date strings.
DATE_FORMATS = (
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d %B %Y",
    "%d %b %Y",
    "%B %d, %Y",
    "%b %d, %Y",
)


def _canonical_field(field_key: Optional[str]) -> Optional[str]:
    """Map a raw schema field_key to a canonical signal category, or None
    if this field isn't relevant to consistency checking."""
    if not field_key:
        return None
    return FIELD_KEY_MAP.get(field_key.strip().lower())


def _normalize_name(raw: str) -> str:
    """Lowercase, strip punctuation/titles, collapse whitespace."""
    s = raw.lower()
    s = re.sub(r"[.\-_,]", " ", s)
    s = re.sub(r"\b(mr|mrs|ms|dr|shri|smt)\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _name_similarity(a: str, b: str) -> float:
    norm_a = _normalize_name(a)
    norm_b = _normalize_name(b)
    if not norm_a or not norm_b:
        return 0.0
    if norm_a == norm_b:
        return 1.0

    tokens_a = sorted(norm_a.split())
    tokens_b = sorted(norm_b.split())
    if tokens_a == tokens_b and len(tokens_a) > 0:
        return 1.0

    set_a = set(tokens_a)
    set_b = set(tokens_b)
    if set_a and set_b:
        intersection = set_a.intersection(set_b)
        union = set_a.union(set_b)
        jaccard = len(intersection) / len(union)
        if jaccard >= 0.75:
            return max(jaccard, 0.90)

    seq_ratio = SequenceMatcher(None, norm_a, norm_b).ratio()
    seq_sorted_ratio = SequenceMatcher(None, " ".join(tokens_a), " ".join(tokens_b)).ratio()
    return max(seq_ratio, seq_sorted_ratio)


def _parse_date(raw: str) -> Optional[datetime]:
    """Try known formats; return None if the date can't be parsed
    (in which case we fall back to a cautious string comparison)."""
    s = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _normalize_address(raw: str) -> str:
    """Loose normalization for address comparison: lowercase, strip
    punctuation, collapse whitespace. Addresses are noisy (OCR line breaks,
    abbreviations), so this is intentionally forgiving."""
    s = raw.lower()
    s = re.sub(r"[.\-_,#]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _address_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize_address(a), _normalize_address(b)).ratio()


ADDRESS_SIMILARITY_THRESHOLD = 0.6  # addresses tolerate more noise than names


def _collect_signals(extractions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group every relevant field value by its canonical category."""
    buckets: Dict[str, List[Dict[str, Any]]] = {
        "name": [],
        "dob": [],
        "address": [],
        "id_number": [],
    }

    for ext in extractions:
        doc_id = ext.get("document_id")
        doc_type = ext.get("schema_name")
        for f in ext.get("fields", []):
            category = _canonical_field(f.get("field_key"))
            if category is None:
                continue
            val = f.get("normalized_value") or f.get("raw_value")
            if not val or not str(val).strip():
                continue
            buckets[category].append({
                "doc_id": doc_id,
                "doc_type": doc_type,
                "field_key": f.get("field_key"),
                "val": str(val).strip(),
            })

    return buckets


def _check_names(names: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if len(names) == 0:
        return None
    if len(names) == 1:
        return {
            "field": "Full Name",
            "status": "insufficient_evidence",
            "message": "Only 1 document has a name; add more documents for cross-verification.",
            "sources": names,
        }

    base = names[0]["val"]
    worst_ratio = 1.0
    for n in names[1:]:
        ratio = _name_similarity(base, n["val"])
        worst_ratio = min(worst_ratio, ratio)

    if worst_ratio >= NAME_SIMILARITY_THRESHOLD:
        status = "consistent"
        message = "Name matches across all provided documents."
        if worst_ratio < 1.0:
            message = "Name matches across documents (minor spelling/formatting differences)."
    else:
        status = "conflict"
        message = f"Name mismatch detected across documents (similarity {worst_ratio:.0%})."

    return {
        "field": "Full Name",
        "status": status,
        "message": message,
        "sources": names,
    }


def _check_dobs(dobs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if len(dobs) == 0:
        return None
    if len(dobs) == 1:
        return {
            "field": "Date of Birth",
            "status": "insufficient_evidence",
            "message": "Date of birth present on only 1 document.",
            "sources": dobs,
        }

    parsed = [_parse_date(d["val"]) for d in dobs]

    if all(p is not None for p in parsed):
        all_match = all(p == parsed[0] for p in parsed)
    else:
        # Fall back to exact string match if any date couldn't be parsed,
        # since we can't safely compare unparsed formats.
        raw_vals = [d["val"] for d in dobs]
        all_match = all(v == raw_vals[0] for v in raw_vals)

    return {
        "field": "Date of Birth",
        "status": "consistent" if all_match else "conflict",
        "message": (
            "Date of birth matches across all identity records."
            if all_match
            else "Date of birth mismatch detected across documents."
        ),
        "sources": dobs,
    }


def _check_addresses(addresses: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if len(addresses) == 0:
        return None
    if len(addresses) == 1:
        return {
            "field": "Address",
            "status": "insufficient_evidence",
            "message": "Address present on only 1 document.",
            "sources": addresses,
        }

    base = addresses[0]["val"]
    worst_ratio = 1.0
    for a in addresses[1:]:
        ratio = _address_similarity(base, a["val"])
        worst_ratio = min(worst_ratio, ratio)

    if worst_ratio >= ADDRESS_SIMILARITY_THRESHOLD:
        status = "consistent"
        message = "Address is consistent across documents."
    else:
        status = "conflict"
        message = f"Address differs across documents (similarity {worst_ratio:.0%}). Manual review recommended."

    return {
        "field": "Address",
        "status": status,
        "message": message,
        "sources": addresses,
    }


def _check_id_numbers(id_numbers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if len(id_numbers) == 0:
        return None
    if len(id_numbers) == 1:
        return {
            "field": "ID Number",
            "status": "insufficient_evidence",
            "message": "ID number present on only 1 document.",
            "sources": id_numbers,
        }

    # ID numbers must match exactly (after stripping whitespace) - no fuzzy
    # matching here, since a single-digit difference is a different ID.
    norm = [re.sub(r"\s+", "", i["val"]) for i in id_numbers]
    all_match = all(n == norm[0] for n in norm)

    return {
        "field": "ID Number",
        "status": "consistent" if all_match else "conflict",
        "message": (
            "ID number matches across documents."
            if all_match
            else "ID number mismatch detected across documents."
        ),
        "sources": id_numbers,
    }


def check_cross_document_consistency(extractions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Compares normalized names, dates of birth, IDs, and addresses across
    multiple documents within the same case. Produces an explainable
    consistency report with links to source documents.

    New document schemas don't require changes here - just add their
    field_key(s) to FIELD_KEY_MAP at the top of this file.
    """
    buckets = _collect_signals(extractions)

    checks = (
        _check_names(buckets["name"]),
        _check_dobs(buckets["dob"]),
        _check_addresses(buckets["address"]),
        _check_id_numbers(buckets["id_number"]),
    )

    return [c for c in checks if c is not None]
