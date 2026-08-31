import re
from typing import Dict, Any, List

# Dictionary of common OCR character & word substitutions in Indian documents & handwritten notes
COMMON_OCR_REPLACEMENTS = {
    # Administrative & Address terms
    r"\bDisiricl\b": "District",
    r"\bDislricl\b": "District",
    r"\bDislrict\b": "District",
    r"\bDistric\b": "District",
    r"\bSlale\b": "State",
    r"\bSlatc\b": "State",
    r"\bStale\b": "State",
    r"\bVIC\b": "VTC",
    r"\bV1C\b": "VTC",
    r"\bVTC\s*:\s*": "VTC: ",
    r"\bJrd\b": "3rd",
    r"\b1sl\b": "1st",
    r"\b2nd\b": "2nd",
    r"\b4lh\b": "4th",
    r"\bNras\b": "Nivas",
    r"\bNiwas\b": "Nivas",
    r"\bSalrasla\b": "Saat Rasta",
    r"\bSaatrasla\b": "Saat Rasta",
    r"\bSat Rasta\b": "Saat Rasta",
    r"\bIgnalius\b": "Ignatius",
    r"\bMumbal\b": "Mumbai",
    r"\bMumbay\b": "Mumbai",
    r"\bMaharashta\b": "Maharashtra",
    r"\bMaharastra\b": "Maharashtra",
    r"\bMaharashira\b": "Maharashtra",
    r"\bGoverment\b": "Government",
    r"\bGovt\b": "Government",
    r"\bGovcrnmcnt\b": "Government",
    r"\bAuthorily\b": "Authority",
    r"\bEnrolment\b": "Enrollment",
    r"\bldentification\b": "Identification",
    r"\bFathcr\b": "Father",
    r"\bMolher\b": "Mother",
    r"\bDatc\b": "Date",
    r"\bBirlh\b": "Birth",
    r"\bFcmdlc\b": "Female",
    r"\bMalc\b": "Male",
}

def clean_ocr_typos(text: str) -> str:
    """
    Cleans up systematic OCR recognition errors from blurred or degraded text.
    """
    if not text:
        return ""
    
    cleaned = text
    for pattern, replacement in COMMON_OCR_REPLACEMENTS.items():
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    
    # Fix common punctuation / spacing bugs
    cleaned = re.sub(r"[\|\\_~`]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    cleaned = re.sub(r"\s*:\s*", ": ", cleaned)
    
    return cleaned.strip()

def repair_address_string(addr: str) -> str:
    """
    Standardizes and repairs Indian address formatting.
    """
    if not addr:
        return ""
    
    addr = clean_ocr_typos(addr)
    # Ensure PIN code has standard spacing
    addr = re.sub(r"\bPIN\s*:?\s*(\d{6})\b", r"PIN: \1", addr, flags=re.IGNORECASE)
    return addr
