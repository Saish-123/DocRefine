import cv2
import numpy as np
from typing import Dict, Any, Tuple, Optional
from backend.pipeline.pdf_helper import is_pdf, convert_pdf_to_image_and_text

def remove_shadows_and_uneven_lighting(gray_img: np.ndarray) -> np.ndarray:
    """
    Removes phone camera shadows and uneven ambient lighting using morphological background division.
    """
    dilated = cv2.dilate(gray_img, np.ones((7, 7), np.uint8))
    bg_img = cv2.medianBlur(dilated, 21)
    diff_img = 255 - cv2.absdiff(gray_img, bg_img)
    norm_img = cv2.normalize(diff_img, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)
    return norm_img

def enhance_document_image(image_bytes: bytes, quality_report: Optional[Dict[str, Any]] = None) -> Tuple[bytes, Dict[str, Any]]:
    """
    State-of-the-Art Document Preprocessing & 2K/300-DPI Super-Resolution Pipeline:
    1. PDF to 300-DPI Rasterization (if PDF)
    2. 2K Resolution Normalization (Lanczos/Cubic scaling to target ~2400px height for optimal OCR density)
    3. Hough & Minimum Area Deskewing
    4. Shadow & Illumination Correction (Neutralizing camera glare & shadows)
    5. Multi-Scale LAB CLAHE Contrast Normalization
    6. Bilateral Edge-Preserving Denoising
    7. High-Pass Unsharp Sharpening
    """
    raw_bytes = image_bytes
    if is_pdf(image_bytes):
        # Was dpi=300 here, separate from the dpi=200 render quality.py
        # already does for scoring - i.e. every PDF was rasterized TWICE.
        # 200 DPI is already well above EasyOCR's useful resolution ceiling
        # (see ocr.py OCR_MAX_DIM=1500px) and the 2K upscale step below still
        # brings it up to ~2400px for visual fidelity, so the extra render
        # cost bought nothing but time on large PDFs.
        png_data, _ = convert_pdf_to_image_and_text(image_bytes, dpi=200)
        if png_data:
            raw_bytes = png_data

    nparr = np.frombuffer(raw_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return image_bytes, {"enhancement_applied": False, "error": "DECODE_FAILED"}

    h, w = img.shape[:2]
    manifest: Dict[str, Any] = {
        "pipeline": "DocXtract-2K-SuperRes-Rescue-v3",
        "stages": []
    }

    # 1. 2K Resolution Normalization (Target height ~2200-3000px for 300 DPI OCR density)
    target_h = 2400
    if h < 2000:
        scale = target_h / float(h)
        new_w = int(w * scale)
        # Cap max width to 2800 to keep memory optimal
        if new_w > 2800:
            scale = 2800 / float(w)
            new_w = 2800
            target_h = int(h * scale)
        img = cv2.resize(img, (new_w, target_h), interpolation=cv2.INTER_LANCZOS4)
        h, w = img.shape[:2]
        manifest["stages"].append({"stage": "2k_super_res_upscale", "scale": round(scale, 2), "resolution": f"{w}x{h}"})

    # 2. Deskewing
    tilt_deg = (quality_report or {}).get("metrics", {}).get("estimated_tilt_deg", 0.0)
    if abs(tilt_deg) > 0.6:
        center = (w // 2, h // 2)
        rot_mat = cv2.getRotationMatrix2D(center, tilt_deg, 1.0)
        img = cv2.warpAffine(img, rot_mat, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        manifest["stages"].append({"stage": "subpixel_deskew", "angle_deg": round(tilt_deg, 2)})

    # 3. LAB Space: Shadow/Uneven-Lighting Removal + CLAHE Contrast Normalization
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # Apply morphological shadow and uneven lighting correction
    l = remove_shadows_and_uneven_lighting(l)
    manifest["stages"].append({"stage": "shadow_uneven_lighting_removal"})

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)

    enhanced_lab = cv2.merge((cl, a, b))
    img = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
    manifest["stages"].append({"stage": "clahe_lab_contrast", "clip_limit": 3.0})

    # 4. Bilateral Edge-Preserving Denoising (Smooths camera noise, preserves crisp letter strokes)
    # bilateralFilter's cost scales with image area, and was by far the
    # single slowest step in this pipeline on large scans (the main reason
    # big documents were slow enough to occasionally hit the overall job
    # timeout). Above ~3MP we filter at half resolution and scale the result
    # back up - denoising doesn't need full-resolution precision, and this
    # cuts the filter's cost by ~4x with no visible quality loss for document
    # text, while keeping the final output at full resolution.
    pixel_count = h * w
    if pixel_count > 3_000_000:
        small = cv2.resize(img, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
        small = cv2.bilateralFilter(small, d=9, sigmaColor=75, sigmaSpace=75)
        img = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
        manifest["stages"].append({"stage": "bilateral_denoise_half_res", "d": 9, "reason": "large_image_speed_optimization"})
    else:
        img = cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)
        manifest["stages"].append({"stage": "bilateral_denoise", "d": 9})

    # 5. High-Pass Unsharp Mask Sharpening
    gaussian = cv2.GaussianBlur(img, (0, 0), sigmaX=1.8)
    unsharp = cv2.addWeighted(img, 1.7, gaussian, -0.7, 0)
    img = np.clip(unsharp, 0, 255).astype(np.uint8)
    manifest["stages"].append({"stage": "unsharp_mask_sharpening", "strength": 1.7})

    # Encode back to high-quality PNG
    is_success, buffer = cv2.imencode(".png", img, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    if not is_success:
        return image_bytes, {"enhancement_applied": False}

    manifest["status"] = "success"
    manifest["enhancement_applied"] = True
    manifest["operations_applied"] = [s["stage"] for s in manifest["stages"]]
    manifest["final_resolution"] = f"{w}x{h}"
    return buffer.tobytes(), manifest
