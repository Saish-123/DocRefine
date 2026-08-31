import httpx
import time
import pytest

def test_full_pipeline_e2e():
    client = httpx.Client(timeout=30)

    # 1. Health check
    r_health = client.get("http://127.0.0.1:8000/health/ready")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ready"

    # 2. Seed demo case
    r_seed = client.post("http://127.0.0.1:8000/api/v1/cases/seed_demo")
    assert r_seed.status_code == 200
    case_id = r_seed.json()["case_id"]
    assert case_id is not None

    # 3. Wait for background worker
    completed = False
    for _ in range(30):
        time.sleep(1.0)
        r_case = client.get(f"http://127.0.0.1:8000/api/v1/cases/{case_id}")
        assert r_case.status_code == 200
        data = r_case.json()
        extractions = data.get("extractions", [])
        docs = data.get("documents", [])
        if len(extractions) >= 3:
            completed = True
            break

    assert completed, "Pipeline worker did not complete all 4 seeded documents in time"

    # 4. Check Consistency Signals
    r_cons = client.get(f"http://127.0.0.1:8000/api/v1/cases/{case_id}/consistency")
    assert r_cons.status_code == 200
    signals = r_cons.json().get("signals", [])
    assert len(signals) > 0

    # 5. Check Grounded Q&A
    r_qa = client.post("http://127.0.0.1:8000/api/v1/qa/query", json={
        "case_id": case_id,
        "query": "What is the PAN number and date of birth?"
    })
    assert r_qa.status_code == 200
    assert len(r_qa.json()["answer"]) > 0

    # 6. Generate 4-Format Exports
    r_exp = client.post("http://127.0.0.1:8000/api/v1/exports", json={
        "case_id": case_id,
        "formats": ["json", "csv", "xlsx", "pdf"]
    })
    assert r_exp.status_code == 200
    exports = r_exp.json().get("exports", {})
    assert "pdf" in exports
    assert "xlsx" in exports
    assert "json" in exports
    assert "csv" in exports

    # 7. Download PDF export
    pdf_url = exports["pdf"]["download_url"]
    r_dl = client.get(pdf_url)
    assert r_dl.status_code == 200
    assert r_dl.content.startswith(b"%PDF")
