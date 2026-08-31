import asyncio
import uuid
import hashlib
import datetime
from backend.worker import process_document_job
from backend.pipeline.demo_fixtures import get_seeded_demo_case, create_sample_document_image
from backend.db.supabase_client import DatabaseManager, StorageManager
from backend.pipeline.qa_assistant import answer_document_query

async def test_verification():
    spec = get_seeded_demo_case()
    item = spec["documents"][1] # Aadhaar Hindi
    case = DatabaseManager.create_case(name="Aadhaar Test Case")
    case_id = case["id"]
    doc_bytes = create_sample_document_image(item["doc_type"], item["text_lines"], tilt_deg=0.0)
    doc_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    source_rel_path = f"demo_user/{case_id}/{doc_id}/source/{item['filename']}"
    StorageManager.save_file(source_rel_path, doc_bytes)
    DatabaseManager.create_document({
        "id": doc_id,
        "case_id": case_id,
        "user_id": "demo_user",
        "filename_safe": item["filename"],
        "mime_type": "image/png",
        "size_bytes": len(doc_bytes),
        "content_sha256": hashlib.sha256(doc_bytes).hexdigest(),
        "source_path": source_rel_path,
        "status": "processing",
        "language_mode": "Hindi",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })
    DatabaseManager.create_job({
        "id": job_id,
        "document_id": doc_id,
        "user_id": "demo_user",
        "status": "processing",
        "stage": "validating",
        "progress": 10,
        "attempts": 1,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })

    print("Executing document rescue & extraction pipeline...")
    await process_document_job(job_id, doc_id, case_id, "demo_user")

    exts = DatabaseManager.get_extractions_by_docs([doc_id])
    assert len(exts) > 0, "No extractions returned"
    print(f"Extracted Document Type: {exts[0].get('schema_name')}")
    print(f"Extracted Fields ({len(exts[0].get('fields', []))} fields):")
    for f in exts[0].get("fields", []):
        val = f.get("normalized_value") or f.get("raw_value")
        print(f"  • {f['label']}: {val} (Score: {f['field_score']}%, State: {f['confidence_state']})")

    print("\nTesting Grounded Q&A Chatbot...")
    qa_resp = await answer_document_query("What is the Aadhaar number and person's name?", exts)
    print(f"Chatbot Response:\n{qa_resp.get('answer')}")

if __name__ == "__main__":
    asyncio.run(test_verification())
