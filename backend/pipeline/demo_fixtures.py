import os
import io
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, List

def create_sample_document_image(doc_type: str, text_lines: List[str], tilt_deg: float = 0.0, blur: bool = False, low_contrast: bool = False) -> bytes:
    """Generates a realistic document card image for automated testing and seeded judge demos."""
    width, height = 900, 560
    img = Image.new("RGB", (width, height), color=(252, 252, 254))
    draw = ImageDraw.Draw(img)

    # Document border / header banner
    draw.rectangle([(15, 15), (885, 545)], outline=(148, 163, 184), width=3)
    draw.rectangle([(15, 15), (885, 95)], fill=(15, 23, 42))

    # Font Resolution
    title_font = None
    body_font = None
    font_candidates = [
        os.path.join(os.path.dirname(__file__), "..", "fonts", "NotoSansDevanagari-Regular.ttf"),
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/segoeui.ttf"
    ]
    for fp in font_candidates:
        if os.path.exists(fp):
            try:
                title_font = ImageFont.truetype(fp, 20)
                body_font = ImageFont.truetype(fp, 18)
                break
            except Exception:
                pass

    # Header text
    header_titles = {
        "tax_id": "INCOME TAX DEPARTMENT - GOVT OF INDIA / आयकर विभाग",
        "identity_document": "UNIQUE IDENTIFICATION AUTHORITY OF INDIA / UIDAI",
        "bank_statement": "STATE BANK OF INDIA - ACCOUNT STATEMENT",
        "address_proof": "MAHARASHTRA STATE ELECTRICITY DISTRIBUTION CO. LTD",
        "education_marksheet": "MAHARASHTRA STATE BOARD OF SECONDARY & HIGHER SECONDARY EDUCATION"
    }
    title = header_titles.get(doc_type, "OFFICIAL VERIFICATION DOCUMENT")
    draw.text((35, 38), title, fill=(255, 255, 255), font=title_font)

    # Body lines
    y = 130
    for line in text_lines:
        draw.text((40, y), line, fill=(15, 23, 42), font=body_font)
        y += 48

    # Photo / Seal placeholder box
    draw.rectangle([(710, 130), (855, 310)], fill=(226, 232, 240), outline=(148, 163, 184), width=2)
    draw.text((745, 210), "[ PHOTO ]", fill=(100, 116, 139), font=body_font)

    # Convert to OpenCV image for realistic perturbations
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    if low_contrast:
        cv_img = cv2.convertScaleAbs(cv_img, alpha=0.75, beta=35)

    if blur:
        cv_img = cv2.GaussianBlur(cv_img, (3, 3), 0.8)

    if abs(tilt_deg) > 0.1:
        center = (width // 2, height // 2)
        M = cv2.getRotationMatrix2D(center, tilt_deg, 1.0)
        cv_img = cv2.warpAffine(cv_img, M, (width, height), borderMode=cv2.BORDER_REPLICATE)

    success, buf = cv2.imencode(".png", cv_img)
    return buf.tobytes()

def get_seeded_demo_case() -> Dict[str, Any]:
    """Provides complete demo case with 4 rich multilingual documents."""
    return {
        "case_name": "Digital Lending Verification - Priority Batch #4092",
        "documents": [
            {
                "filename": "PAN_Card_Poor_Angle.png",
                "doc_type": "tax_id",
                "tilt": 4.5,
                "blur": True,
                "low_contrast": False,
                "language_mode": "English",
                "text_lines": [
                    "Permanent Account Number: ABCDE1234F",
                    "Name / नाम: RAJESH SHARMA",
                    "Father's Name: SURESH SHARMA",
                    "Date of Birth / जन्म तिथि: 1988-05-14"
                ],
                "expected_fields": {
                    "tax_id_number": "ABCDE1234F",
                    "full_name": "RAJESH SHARMA",
                    "date_of_birth": "1988-05-14"
                }
            },
            {
                "filename": "Aadhaar_Devanagari_Hindi.png",
                "doc_type": "identity_document",
                "tilt": 0.0,
                "blur": False,
                "low_contrast": False,
                "language_mode": "Hindi",
                "text_lines": [
                    "भारत सरकार / Government of India",
                    "नाव / Name: राजेश सुरेश शर्मा (Rajesh Suresh Sharma)",
                    "जन्म तारीख / DOB: 1988-05-14",
                    "लिंग / Gender: Male / पुरुष",
                    "आधार क्रमांक / Aadhaar: 5432 8765 1098",
                    "पत्ता: 402, शांति निकेतन, दादर, मुंबई 400014"
                ],
                "expected_fields": {
                    "full_name": "Rajesh Suresh Sharma",
                    "document_number": "5432 8765 1098",
                    "date_of_birth": "1988-05-14",
                    "gender": "Male",
                    "address": "402, Shanti Niketan, Dadar, Mumbai 400014"
                }
            },
            {
                "filename": "Bank_Statement_SBI.png",
                "doc_type": "bank_statement",
                "tilt": -2.0,
                "blur": False,
                "low_contrast": True,
                "language_mode": "English",
                "text_lines": [
                    "Account Holder: RAJESH S SHARMA",
                    "Account Number: 203948571029",
                    "IFSC Code: SBIN0001234",
                    "Bank Name: State Bank of India",
                    "Statement Period: 01-Jan-2026 to 31-Jan-2026",
                    "Closing Balance: INR 142500.50"
                ],
                "expected_fields": {
                    "account_holder_name": "RAJESH S SHARMA",
                    "account_number": "203948571029",
                    "ifsc": "SBIN0001234",
                    "bank_name": "State Bank of India",
                    "statement_period": "2026-01-01 to 2026-01-31",
                    "closing_balance": "142500.50"
                }
            },
            {
                "filename": "Electricity_Bill_Marathi.png",
                "doc_type": "address_proof",
                "tilt": 1.2,
                "blur": True,
                "low_contrast": True,
                "language_mode": "Marathi",
                "text_lines": [
                    "महाराष्ट्र राज्य विद्युत वितरण कंपनी मर्यादित",
                    "ग्राहकाचे नाव: राजेश शर्मा (Rajesh Sharma)",
                    "ग्राहक क्रमांक / Consumer No: 028491029384",
                    "पत्ता: 402, शांती निकेतन, दादर पश्चिम, मुंबई - 400014",
                    "देयक दिनांक / Issue Date: 2026-01-10"
                ],
                "expected_fields": {
                    "full_name": "Rajesh Sharma",
                    "document_number": "028491029384",
                    "address": "402, Shanti Niketan, Dadar West, Mumbai - 400014",
                    "issue_date": "2026-01-10"
                }
            }
        ]
    }
