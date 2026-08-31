import os
import cv2
import numpy as np
import base64
from typing import Dict, Any, List, Optional

# Multi-threaded PyTorch CPU execution for fast OCR inference
try:
    import torch
    num_threads = min(4, os.cpu_count() or 2)
    torch.set_num_threads(num_threads)
except Exception:
    pass

OCR_ENGINE_VERSION = "2.8.0-Multilingual-Devanagari+English"

_EASYOCR_READERS: Dict[str, Any] = {}

def get_easyocr_reader(language_mode: str = "Mixed"):
    global _EASYOCR_READERS
    mode = (language_mode or "Mixed").lower()
    
    # English only
    lang_key = "en" if mode == "english" else "devanagari"
    if lang_key in _EASYOCR_READERS:
        return _EASYOCR_READERS[lang_key]

    try:
        import easyocr
        # ['en', 'hi'] covers English and all Devanagari characters (Hindi, Marathi, Sanskrit)
        langs = ['en'] if lang_key == "en" else ['en', 'hi']
        reader = easyocr.Reader(langs, gpu=False)
        _EASYOCR_READERS[lang_key] = reader
        return reader
    except Exception as e:
        print(f"[OCR] EasyOCR init notice: {e}")
        return None

from backend.pipeline.pdf_helper import is_pdf, convert_pdf_to_image_and_text
from backend.config import settings

# Pull from config — default 1300px gives crisp OCR with fast CPU runtime
OCR_MAX_DIM: int = int(getattr(settings, "OCR_MAX_IMAGE_DIM", 1300))

def run_multilingual_ocr(image_bytes: bytes, language_mode: str = "Mixed") -> Dict[str, Any]:
    """
    Performs real multilingual OCR on image bytes or PDF bytes (English, Hindi, Marathi).
    Extracts text lines, bounding boxes, and per-token confidence.
    """
    raw_bytes = image_bytes
    pdf_text = ""
    if is_pdf(image_bytes):
        png_data, extracted_pdf_text = convert_pdf_to_image_and_text(image_bytes)
        if png_data:
            raw_bytes = png_data
        if extracted_pdf_text:
            pdf_text = extracted_pdf_text

    nparr = np.frombuffer(raw_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        if pdf_text:
            return {
                "text": pdf_text,
                "regions": [],
                "language": language_mode,
                "average_confidence": 0.98,
                "engine": "PyMuPDF-Digital-Engine",
                "engine_version": OCR_ENGINE_VERSION,
                "status": "success"
            }
        return {
            "text": "",
            "regions": [],
            "language": language_mode,
            "average_confidence": 0.0,
            "engine": "EasyOCR-Multilingual-Devanagari",
            "engine_version": OCR_ENGINE_VERSION,
            "status": "ocr_failed"
        }

    h, w = img.shape[:2]

    # Try EasyOCR if installed
    reader = get_easyocr_reader(language_mode)
    if reader:
        try:
            # Cap the EasyOCR input image to OCR_MAX_DIM on the longest side.
            # The enhancement stage upscales to ~2400px for visual fidelity,
            # but passing that directly to EasyOCR (CPU) tries to allocate
            # ~1.3GB of RAM and crashes with OOM on typical laptops.
            # OCR_MAX_DIM (default 1500) is more than sufficient for EasyOCR
            # text recognition accuracy while keeping memory usage safe.
            if max(h, w) > OCR_MAX_DIM:
                ocr_scale = OCR_MAX_DIM / float(max(h, w))
                ocr_img = cv2.resize(img, (int(w * ocr_scale), int(h * ocr_scale)), interpolation=cv2.INTER_AREA)
            else:
                ocr_img = img
            ocr_h, ocr_w = ocr_img.shape[:2]

            results = reader.readtext(ocr_img)
            extracted_lines = []
            regions = []
            total_conf = 0.0

            for idx, (bbox, text, conf) in enumerate(results):
                if not text.strip():
                    continue
                extracted_lines.append(text.strip())
                # Normalize bbox coords relative to the OCR-scaled image dims
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                norm_box = [
                    round(min(ys) / ocr_h, 4),
                    round(min(xs) / ocr_w, 4),
                    round(max(ys) / ocr_h, 4),
                    round(max(xs) / ocr_w, 4)
                ]
                regions.append({
                    "id": f"reg_{idx+1}",
                    "text": text,
                    "bbox": norm_box,
                    "confidence": round(float(conf), 2),
                    "language": language_mode
                })
                total_conf += float(conf)

            full_text = "\n".join(extracted_lines)
            if pdf_text:
                full_text = f"{pdf_text}\n\n{full_text}".strip()

            avg_conf = (total_conf / len(regions)) if regions else (0.95 if pdf_text else 0.85)

            if full_text:
                return {
                    "text": full_text,
                    "regions": regions,
                    "language": language_mode,
                    "average_confidence": round(avg_conf, 3),
                    "engine": "EasyOCR-Multilingual-Devanagari" if regions else "PyMuPDF-Digital-Engine",
                    "engine_version": OCR_ENGINE_VERSION,
                    "status": "success"
                }
        except Exception as e:
            print(f"[OCR] EasyOCR execution notice: {e}")

    if pdf_text:
        return {
            "text": pdf_text,
            "regions": [],
            "language": language_mode,
            "average_confidence": 0.95,
            "engine": "PyMuPDF-Digital-Engine",
            "engine_version": OCR_ENGINE_VERSION,
            "status": "success"
        }

    # Fallback to contour detection morphology (no text recognition — bbox only)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 8)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
    dilated = cv2.dilate(binary, kernel, iterations=2)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    bounding_boxes = [cv2.boundingRect(c) for c in contours]
    bounding_boxes = sorted(bounding_boxes, key=lambda b: (b[1] // 30, b[0]))

    for idx, (bx, by, bw, bh) in enumerate(bounding_boxes):
        if bw < 30 or bh < 10 or bh > h * 0.5:
            continue
        norm_box = [
            round(by / h, 4),
            round(bx / w, 4),
            round((by + bh) / h, 4),
            round((bx + bw) / w, 4)
        ]
        regions.append({
            "id": f"reg_{idx+1}",
            "bbox": norm_box,
            "confidence": 0.0,
            "language": language_mode
        })

    return {
        "text": "",
        "regions": regions,
        "language": language_mode,
        "average_confidence": 0.0,
        "engine": "fallback_bbox_only_no_recognition",
        "engine_version": OCR_ENGINE_VERSION,
        "status": "ocr_failed"
    }
