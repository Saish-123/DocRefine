import pymupdf as fitz  # Use pymupdf to avoid deprecation warning
from typing import Tuple, Optional
from backend.config import settings

# Pull from config — overridable via .env (e.g. PDF_RENDER_DPI=300 on GPU machines)
_PDF_RENDER_DPI: int = int(getattr(settings, "PDF_RENDER_DPI", 200))

def is_pdf(data: bytes) -> bool:
    if not data:
        return False
    return data.startswith(b"%PDF") or b"%PDF-" in data[:1024]

def convert_pdf_to_image_and_text(pdf_bytes: bytes, dpi: int = _PDF_RENDER_DPI) -> Tuple[bytes, str]:
    """
    Converts PDF into a PNG image (Page 1 at specified DPI) and extracts all
    embedded digital text (which is far more accurate than OCR for typed PDFs).

    Default DPI is 200 (not 300): 300 DPI produces ~2400px images that exceed
    EasyOCR's CPU memory budget (~1.3GB OOM). 200 DPI still gives 1400-1600px
    images that are well above EasyOCR's sweet spot for accuracy while keeping
    peak memory usage under 600MB on a typical laptop.

    The enhancement pipeline (enhancement.py) can still upscale for visual
    fidelity before storing the artifact — OCR will be capped separately at
    1500px max in ocr.py.

    Returns (png_image_bytes, embedded_text)
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if len(doc) == 0:
            return b"", ""

        # Extract embedded digital text from ALL pages (much better than OCR for digital PDFs)
        full_text_list = []
        for page in doc:
            t = page.get_text()
            if t.strip():
                full_text_list.append(t.strip())
        embedded_text = "\n\n".join(full_text_list)

        # Render first page as PNG image at the requested DPI
        page0 = doc[0]
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page0.get_pixmap(matrix=mat, alpha=False)
        png_bytes = pix.tobytes(output="png")

        return png_bytes, embedded_text
    except Exception as e:
        print(f"[PDFHelper] Conversion notice: {e}")
        return b"", ""
