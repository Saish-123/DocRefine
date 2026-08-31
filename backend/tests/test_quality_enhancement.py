import pytest
from backend.pipeline.quality import analyze_document_quality
from backend.pipeline.enhancement import enhance_document_image
from backend.pipeline.demo_fixtures import create_sample_document_image

def test_quality_analysis_sharp():
    img_bytes = create_sample_document_image("tax_id", ["PAN: ABCDE1234F", "Name: TEST USER"], blur=False, tilt_deg=0.0)
    rep = analyze_document_quality(img_bytes)
    assert rep["quality_score"] >= 65
    assert rep["quality_band"] in ("acceptable", "warning")
    assert "metrics" in rep

def test_quality_analysis_blurry():
    img_bytes = create_sample_document_image("tax_id", ["PAN: ABCDE1234F"], blur=True, tilt_deg=0.0)
    rep = analyze_document_quality(img_bytes)
    assert any("BLUR" in f for f in rep["quality_flags"])
    assert len(rep["guidance"]) > 0

def test_image_enhancement():
    img_bytes = create_sample_document_image("tax_id", ["PAN: ABCDE1234F"], tilt_deg=3.5)
    enhanced, manifest = enhance_document_image(img_bytes)
    assert len(enhanced) > 0
    assert manifest["status"] == "success"
    assert "operations_applied" in manifest
