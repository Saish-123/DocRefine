import pytest
import json
from backend.pipeline.exporters import export_json, export_csv, export_xlsx, export_pdf

def test_exporters_unicode_and_completeness():
    case = {"id": "c1", "name": "Test Case", "updated_at": "2026-08-29"}
    docs = [{"id": "d1", "filename_safe": "Aadhaar.png", "status": "approved", "quality_score": 92, "quality_band": "acceptable"}]
    extractions = [{
        "document_id": "d1",
        "schema_name": "identity_document",
        "status": "approved",
        "overall_confidence": 95,
        "fields": [
            {"field_key": "full_name", "label": "Full Name", "normalized_value": "राजेश शर्मा", "field_score": 95, "confidence_state": "Green", "validation_status": "valid"}
        ]
    }]

    # JSON
    json_bytes = export_json(case, docs, extractions)
    parsed = json.loads(json_bytes.decode("utf-8"))
    assert parsed["document_count"] == 1

    # CSV (with Unicode Marathi / Hindi characters)
    csv_bytes = export_csv(case, docs, extractions)
    assert b"\xef\xbb\xbf" in csv_bytes[:4] # UTF-8 BOM
    assert "राजेश शर्मा".encode("utf-8") in csv_bytes

    # XLSX
    xlsx_bytes = export_xlsx(case, docs, extractions)
    assert len(xlsx_bytes) > 500

    # PDF
    pdf_bytes = export_pdf(case, docs, extractions)
    assert pdf_bytes.startswith(b"%PDF")
