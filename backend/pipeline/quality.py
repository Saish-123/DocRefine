import cv2
import numpy as np
from typing import Dict, Any, List

from backend.pipeline.pdf_helper import is_pdf, convert_pdf_to_image_and_text

ALGORITHM_VERSION = "1.0.0"

def analyze_document_quality(image_bytes: bytes) -> Dict[str, Any]:
    """
    Computes a deterministic quality report before enhancement.
    Assesses resolution, blur/sharpness, brightness, contrast, and tilt.
    Handles both Image (JPG, PNG, WEBP) and PDF files.
    """
    raw_bytes = image_bytes
    if is_pdf(image_bytes):
        png_data, _ = convert_pdf_to_image_and_text(image_bytes)
        if png_data:
            raw_bytes = png_data

    nparr = np.frombuffer(raw_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return {
            "quality_score": 0,
            "quality_band": "needs_reupload",
            "quality_flags": ["UNREADABLE_FILE", "CORRUPT_IMAGE"],
            "guidance": ["The uploaded file cannot be decoded. Please upload a valid document."],
            "algorithm_version": ALGORITHM_VERSION,
            "metrics": {"resolution_mp": 0.0, "blur_variance": 0.0, "brightness": 0.0, "contrast": 0.0, "estimated_tilt_deg": 0.0}
        }

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1. Resolution
    megapixels = (h * w) / 1_000_000.0
    res_score = min(100.0, max(50.0, (megapixels / 0.5) * 100.0))

    # 2. Blur / Sharpness via Laplacian Variance
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    # Calibrated: >60 is readable for documents, >150 is crisp
    blur_score = float(np.clip(50.0 + (lap_var / 4.0), 30.0, 100.0))

    # 3. Brightness & Contrast
    mean_brightness = float(np.mean(gray)) # 0 to 255
    contrast_std = float(np.std(gray)) # 0 to 128

    if mean_brightness < 40:
        bright_score = 35.0
    elif mean_brightness > 245:
        bright_score = 45.0
    else:
        bright_score = 95.0 - abs(mean_brightness - 150.0) * 0.25
    bright_score = float(np.clip(bright_score, 30.0, 100.0))

    contrast_score = float(np.clip(50.0 + (contrast_std * 0.8), 35.0, 100.0))

    # 4. Estimated Tilt
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)
    estimated_tilt = 0.0
    if lines is not None and len(lines) > 0:
        angles = []
        for line in lines[:20]:
            rho, theta = line[0]
            angle_deg = (theta * 180.0 / np.pi) - 90.0
            if abs(angle_deg) <= 45.0:
                angles.append(angle_deg)
        if angles:
            estimated_tilt = float(np.median(angles))

    tilt_score = max(50.0, 100.0 - (abs(estimated_tilt) * 4.0))

    # Composite Score
    weights = [0.20, 0.30, 0.20, 0.15, 0.15]
    scores = [res_score, blur_score, bright_score, contrast_score, tilt_score]
    final_score = int(np.clip(np.dot(weights, scores), 10, 100))

    flags: List[str] = []
    guidance: List[str] = []

    if megapixels < 0.15:
        flags.append("EXTREMELY_LOW_RESOLUTION")
        guidance.append("Document resolution is very low. Consider uploading higher resolution photo.")
    elif lap_var < 30:
        flags.append("MODERATE_BLUR")
        guidance.append("Minor blur detected. Image enhancement applied.")
    
    if abs(estimated_tilt) > 4.0:
        flags.append("DETECTED_TILT")
        guidance.append(f"Document tilt of {estimated_tilt:.1f}° corrected via OpenCV deskewing.")

    if not flags:
        flags.append("CLEAN_DOCUMENT")
        guidance.append("Image quality is optimal for automated extraction.")

    # Quality Band per PRD
    if final_score >= 70:
        band = "acceptable"
    elif final_score >= 45:
        band = "warning"
    else:
        band = "needs_reupload"

    return {
        "quality_score": final_score,
        "quality_band": band,
        "quality_flags": flags,
        "guidance": guidance,
        "algorithm_version": ALGORITHM_VERSION,
        "metrics": {
            "resolution_mp": round(megapixels, 2),
            "blur_variance": round(lap_var, 1),
            "brightness": round(mean_brightness, 1),
            "contrast": round(contrast_std, 1),
            "estimated_tilt_deg": round(estimated_tilt, 2)
        }
    }
