import asyncio
import uuid
import hashlib
import datetime
from backend.worker import process_document_job
from backend.pipeline.demo_fixtures import get_seeded_demo_case, create_sample_document_image
from backend.db.supabase_client import DatabaseManager, StorageManager

async def test_debug():
    spec = get_seeded_demo_case()
    item = spec["documents"][0]
    case = DatabaseManager.create_case(name="Debug Case")
    case_id = case["id"]
    doc_bytes = create_sample_document_image(item["doc_type"], item["text_lines"], tilt_deg=item["tilt"])
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
        "language_mode": "English",
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
    print("Starting process_document_job...")
    await process_document_job(job_id, doc_id, case_id, "demo_user")
    print("Finished process_document_job!")

if __name__ == "__main__":
    asyncio.run(test_debug())
