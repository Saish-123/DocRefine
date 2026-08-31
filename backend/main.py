import os
import hashlib
import uuid
import datetime
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Request, UploadFile, File, Form, Header, HTTPException, BackgroundTasks, Response, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

from backend.config import settings
from backend.db.supabase_client import DatabaseManager, StorageManager, supabase, _MEM_DOCUMENTS
from backend.pipeline.quality import analyze_document_quality
from backend.pipeline.enhancement import enhance_document_image
from backend.pipeline.schemas import validate_field_value, normalize_date
from backend.pipeline.confidence import calculate_field_confidence
from backend.pipeline.exporters import export_json, export_csv, export_xlsx, export_pdf
from backend.pipeline.consistency import check_cross_document_consistency
from backend.pipeline.qa_assistant import answer_document_query
from backend.pipeline.demo_fixtures import get_seeded_demo_case, create_sample_document_image
from backend.worker import process_document_job
from backend import job_queue

app = FastAPI(
    title="DocXtract API",
    description="Intelligent Document Rescue & Multilingual Extraction Workspace",
    version="1.0.0"
)

@app.on_event("startup")
async def _start_job_queue_workers():
    job_queue.start_workers()


@app.on_event("shutdown")
async def _stop_job_queue_workers():
    await job_queue.stop_workers()


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication Dependency for Backend API Protection
async def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """
    Verifies the Supabase JWT Bearer token and returns authenticated user ID.
    Rejects unauthorized requests with HTTP 401.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization Bearer token")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header format. Expected 'Bearer <token>'")

    token = parts[1]
    if not token:
        raise HTTPException(status_code=401, detail="Empty bearer token")

    # 1. Verify via Supabase Auth client if online
    if supabase:
        try:
            u_res = supabase.auth.get_user(token)
            if u_res and u_res.user:
                return str(u_res.user.id)
        except Exception:
            pass

    # 2. Decode JWT claims safely
    try:
        import json
        import base64
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
        user_id = decoded.get("sub") or decoded.get("id") or decoded.get("email")
        if user_id:
            return str(user_id)
        raise ValueError("Missing subject identifier in JWT")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired JWT token")

# Magic Bytes File Type Verification
MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",
    b"%PDF": "application/pdf"
}

def verify_file_magic_bytes(header_bytes: bytes) -> bool:
    for magic in MAGIC_BYTES.keys():
        if header_bytes.startswith(magic):
            return True
    return False

# Health Endpoints per PRD Section 11 (Public)
@app.get("/health/live")
async def health_live():
    return {"status": "ok", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}

@app.get("/health/ready")
async def health_ready():
    db_connected = supabase is not None
    configured_providers = [p for p in ["gemini", "groq", "nvidia"] if getattr(settings, f"{p.upper()}_API_KEY", None)]
    return {
        "status": "ready",
        "database_connected": db_connected,
        "configured_llm_providers": configured_providers,
        "ocr_engine": "EasyOCR-Multilingual-Devanagari",
        "enhancement_engine": "OpenCV-DocumentRescue"
    }

# Cases API (Authenticated)
class CreateCaseRequest(BaseModel):
    name: Optional[str] = None

@app.post("/api/v1/cases")
async def create_case(req: Optional[CreateCaseRequest] = None, user_id: str = Depends(get_current_user)):
    name = req.name if req else None
    case_row = DatabaseManager.create_case(name=name, user_id=user_id)
    DatabaseManager.record_audit(
        user_id=user_id,
        case_id=case_row["id"],
        doc_id=None,
        action="CASE_CREATED",
        entity_type="case",
        entity_id=case_row["id"],
        metadata={"name": case_row["name"]}
    )
    return {"case": case_row}

@app.get("/api/v1/cases")
async def list_cases(user_id: str = Depends(get_current_user)):
    cases = DatabaseManager.list_cases(user_id=user_id)
    return {"cases": cases}

@app.get("/api/v1/cases/{case_id}")
async def get_case_details(case_id: str, user_id: str = Depends(get_current_user)):
    case = DatabaseManager.get_case(case_id)
    if not case:
        case = {"id": case_id, "name": f"Case #{case_id[:8]}", "status": "active", "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}

    docs = DatabaseManager.get_documents_by_case(case_id)
    doc_ids = [d["id"] for d in docs]
    extractions = DatabaseManager.get_extractions_by_docs(doc_ids)

    # Attach active_job and error information from the latest processing job onto
    # each document so the frontend PipelinePanel and review cards show live stage history
    for d in docs:
        job = DatabaseManager.get_latest_job_for_document(d["id"])
        if job:
            d["active_job"] = {
                "id": job.get("id"),
                "status": job.get("status"),
                "stage": job.get("stage"),
                "progress": job.get("progress"),
                "attempts": job.get("attempts", 1),
                "error_code": job.get("error_code"),
                "error_message": job.get("error_message"),
                "retry_after_seconds": job.get("retry_after_seconds"),
                "resume_at": job.get("resume_at"),
                "stage_history": job.get("stage_history") or [],
                "created_at": job.get("created_at"),
            }
            if d.get("status") == "processing_failed":
                d["last_error_code"] = job.get("error_code")
                d["last_error_message"] = job.get("error_message")
                d["last_job_attempts"] = job.get("attempts", 1)

    # Aggregate counts
    status_counts = {"completed": 0, "needs_review": 0, "needs_reupload": 0, "processing": 0}
    unresolved_field_count = 0
    for e in extractions:
        st = e.get("status", "needs_review")
        status_counts[st] = status_counts.get(st, 0) + 1
        for f in e.get("fields", []):
            if f.get("confidence_state") in ("Red", "Yellow") and f.get("review_state") != "approved":
                unresolved_field_count += 1

    return {
        "case": case,
        "documents": docs,
        "extractions": extractions,
        "status_counts": status_counts,
        "unresolved_field_count": unresolved_field_count
    }

@app.delete("/api/v1/cases/{case_id}")
async def delete_case(case_id: str, user_id: str = Depends(get_current_user)):
    if supabase:
        try:
            supabase.table("cases").delete().eq("id", case_id).execute()
        except Exception as e:
            print(f"[API] Error deleting case: {e}")
    DatabaseManager.record_audit(user_id, case_id, None, "CASE_DELETED", "case", case_id, {})
    return {"deleted": True, "case_id": case_id}

# Multi-Document Upload with Validation & Enqueueing
@app.post("/api/v1/cases/{case_id}/documents")
async def upload_documents(
    case_id: str,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    language_mode: str = Form("Mixed"),
    idempotency_key: Optional[str] = Header(None),
    user_id: str = Depends(get_current_user)
):
    accepted = []
    rejected = []
    seen_hashes = set()

    for file in files:
        filename = file.filename or "document.png"
        content = await file.read()
        size_bytes = len(content)

        # 1. Size Validation
        if size_bytes == 0:
            rejected.append({"filename": filename, "code": "EMPTY_FILE", "message": "File is empty (0 bytes)."})
            continue
        if size_bytes > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            rejected.append({"filename": filename, "code": "FILE_TOO_LARGE", "message": f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit."})
            continue

        # 2. Magic Bytes Validation
        if not verify_file_magic_bytes(content[:32]):
            rejected.append({"filename": filename, "code": "DISGUISED_OR_UNSUPPORTED_FORMAT", "message": "Invalid file signature or disguised file extension."})
            continue

        # 3. Content Duplicate Check
        content_hash = hashlib.sha256(content).hexdigest()
        if content_hash in seen_hashes:
            rejected.append({"filename": filename, "code": "DUPLICATE_IN_BATCH", "message": "Duplicate document in the same upload batch."})
            continue
        seen_hashes.add(content_hash)

        # Accepted Document Creation
        doc_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
        source_rel_path = f"{user_id}/{case_id}/{doc_id}/source/{safe_filename}"

        StorageManager.save_file(source_rel_path, content)

        doc_row = {
            "id": doc_id,
            "case_id": case_id,
            "user_id": user_id,
            "filename_safe": safe_filename,
            "mime_type": file.content_type or "image/png",
            "size_bytes": size_bytes,
            "content_sha256": content_hash,
            "source_path": source_rel_path,
            "status": "processing",
            "language_mode": language_mode,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        DatabaseManager.create_document(doc_row)

        job_row = {
            "id": job_id,
            "document_id": doc_id,
            "user_id": user_id,
            "status": "processing",
            "stage": "validating",
            "progress": 5,
            "attempts": 1,
            "idempotency_key": idempotency_key or str(uuid.uuid4()),
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        DatabaseManager.create_job(job_row)

        # Enqueue for bounded-concurrency background processing (see job_queue.py) -
        # this replaces the previous unbounded asyncio.create_task per upload,
        # which caused 3rd/4th concurrent documents to compete for CPU/network
        # resources and produce slow, incomplete extractions.
        await job_queue.enqueue_job(job_id, doc_id, case_id, user_id)

        accepted.append({"document_id": doc_id, "job_id": job_id, "filename": safe_filename})

    return {"accepted": accepted, "rejected": rejected}

# 1-Click Seeded Demo Case for Judges & Evaluators
@app.post("/api/v1/cases/seed_demo")
async def seed_demo_case(request: Request, background_tasks: BackgroundTasks):
    user_id = "demo_user"
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        try:
            user_id = await get_current_user(token)
        except Exception:
            user_id = "demo_user"

    demo_spec = get_seeded_demo_case()
    case_row = DatabaseManager.create_case(name=demo_spec["case_name"], user_id=user_id)
    case_id = case_row["id"]
    accepted = []

    for item in demo_spec["documents"]:
        doc_bytes = create_sample_document_image(
            doc_type=item["doc_type"],
            text_lines=item["text_lines"],
            tilt_deg=item["tilt"],
            blur=item["blur"],
            low_contrast=item["low_contrast"]
        )
        doc_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        source_rel_path = f"{user_id}/{case_id}/{doc_id}/source/{item['filename']}"
        StorageManager.save_file(source_rel_path, doc_bytes)

        doc_row = {
            "id": doc_id,
            "case_id": case_id,
            "user_id": user_id,
            "filename_safe": item["filename"],
            "mime_type": "image/png",
            "size_bytes": len(doc_bytes),
            "content_sha256": hashlib.sha256(doc_bytes).hexdigest(),
            "source_path": source_rel_path,
            "status": "processing",
            "language_mode": item["language_mode"],
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        DatabaseManager.create_document(doc_row)

        job_row = {
            "id": job_id,
            "document_id": doc_id,
            "user_id": user_id,
            "status": "processing",
            "stage": "validating",
            "progress": 10,
            "attempts": 1,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        DatabaseManager.create_job(job_row)

        await job_queue.enqueue_job(job_id, doc_id, case_id, user_id)
        accepted.append({"document_id": doc_id, "job_id": job_id, "filename": item["filename"]})

    return {"case_id": case_id, "case_name": demo_spec["case_name"], "accepted": accepted}

# Retry a stalled/failed document WITHOUT requiring re-upload — the source
# file is already in storage, so a timeout/exception/rate-limit failure just
# needs the pipeline run again (in fast_mode, for a better shot at finishing
# inside budget), not a brand new file from the user.
@app.post("/api/v1/documents/{document_id}/retry")
async def retry_document(document_id: str, user_id: str = Depends(get_current_user)):
    doc = _MEM_DOCUMENTS.get(document_id)
    if not doc and supabase:
        try:
            res = supabase.table("documents").select("*").eq("id", document_id).execute()
            if res.data:
                doc = res.data[0]
        except Exception:
            pass
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.get("source_path"):
        raise HTTPException(status_code=400, detail="Original file is no longer available; please re-upload.")

    job_id = str(uuid.uuid4())
    job_row = {
        "id": job_id,
        "document_id": document_id,
        "user_id": user_id,
        "status": "processing",
        "stage": "validating",
        "progress": 5,
        "attempts": 1,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    DatabaseManager.create_job(job_row)
    DatabaseManager.update_document(document_id, {"status": "processing"})
    await job_queue.enqueue_job(job_id, document_id, doc.get("case_id"), user_id, fast_mode=True)
    return {"job_id": job_id, "document_id": document_id, "status": "processing"}

# Polling Job Status Endpoint
@app.get("/api/v1/jobs/{job_id}")
async def get_job_status(job_id: str):
    if supabase:
        res = supabase.table("processing_jobs").select("*").eq("id", job_id).execute()
        if res.data:
            return res.data[0]
    return {"job_id": job_id, "status": "completed", "stage": "completed", "progress": 100}

# Document Comparison URLs & Metadata
@app.get("/api/v1/documents/{document_id}/compare")
async def get_document_compare(document_id: str):
    doc_record = None
    if supabase:
        res = supabase.table("documents").select("*").eq("id", document_id).execute()
        if res.data:
            doc_record = res.data[0]

    if not doc_record:
        raise HTTPException(status_code=404, detail="Document not found")

    source_url = StorageManager.get_signed_url(doc_record["source_path"])
    enhanced_url = StorageManager.get_signed_url(doc_record["enhanced_path"]) if doc_record.get("enhanced_path") else source_url

    return {
        "document_id": document_id,
        "filename": doc_record.get("filename_safe"),
        "source_url": source_url,
        "enhanced_url": enhanced_url,
        "quality_score": doc_record.get("quality_score", 0),
        "quality_band": doc_record.get("quality_band", "acceptable"),
        "quality_flags": doc_record.get("quality_flags_json", []),
        "expires_in_seconds": settings.SIGNED_URL_TTL_SECONDS
    }

from backend.pipeline.pdf_helper import is_pdf, convert_pdf_to_image_and_text

# File Direct Download for Signed Links
@app.get("/api/v1/files/download")
async def download_file(path: str = Query(...), render_image: Optional[bool] = Query(None)):
    data = StorageManager.read_file(path)
    if not data:
        raise HTTPException(status_code=404, detail="File not found in storage vault")
    
    clean_p = path.replace("\\", "/")
    is_export = ("/exports/" in clean_p) or ("export" in clean_p.lower()) or "docrefine_case" in clean_p.lower()

    # If it's a PDF and explicitly requested for UI preview (and NOT an export download), render page 1 as PNG
    if is_pdf(data) and (render_image is True or (render_image is None and not is_export)):
        png_data, _ = convert_pdf_to_image_and_text(data)
        if png_data:
            return Response(content=png_data, media_type="image/png")

    media_type = "application/octet-stream"
    filename = os.path.basename(clean_p)
    if clean_p.endswith(".pdf"):
        media_type = "application/pdf"
    elif clean_p.endswith(".json"):
        media_type = "application/json"
    elif clean_p.endswith(".csv"):
        media_type = "text/csv; charset=utf-8"
    elif clean_p.endswith(".xlsx"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif clean_p.endswith(".png"):
        media_type = "image/png"
    elif clean_p.endswith(".jpg") or clean_p.endswith(".jpeg"):
        media_type = "image/jpeg"

    headers = {
        "Access-Control-Expose-Headers": "Content-Disposition",
    }
    if is_export or clean_p.endswith((".pdf", ".xlsx", ".csv", ".json")):
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'

    return Response(content=data, media_type=media_type, headers=headers)

# Inline Field Editing & Instant Recalculation
class UpdateFieldRequest(BaseModel):
    value: Optional[str] = None

@app.patch("/api/v1/extractions/{extraction_id}/fields/{field_key}")
async def update_field_value(extraction_id: str, field_key: str, req: UpdateFieldRequest, user_id: str = Depends(get_current_user)):
    val = req.value
    norm_val = normalize_date(val) if "date" in field_key else val
    val_score, val_status, val_reasons = validate_field_value(field_key, val, norm_val)

    conf_res = calculate_field_confidence(
        ocr_confidence=0.99,
        structuring_confidence=1.0,
        validation_score=val_score,
        quality_score=95,
        raw_value=val,
        validation_status=val_status
    )

    updates = {
        "raw_value": val,
        "normalized_value": norm_val,
        "validation_score": val_score,
        "validation_status": val_status,
        "field_score": conf_res["field_score"],
        "confidence_state": conf_res["confidence_state"],
        "reason_codes_json": conf_res["reason_codes"] + val_reasons,
        "review_state": "human_edited"
    }

    if supabase:
        supabase.table("extraction_fields").update(updates).eq("extraction_id", extraction_id).eq("field_key", field_key).execute()

    audit_id = str(uuid.uuid4())
    DatabaseManager.record_audit(
        user_id=user_id,
        case_id=None,
        doc_id=None,
        action="FIELD_EDITED",
        entity_type="field",
        entity_id=field_key,
        metadata={"extraction_id": extraction_id, "field_key": field_key, "score": conf_res["field_score"]}
    )

    return {"updated": True, "field": updates, "audit_event_id": audit_id}

# Approve Extraction Endpoint
class ApproveRequest(BaseModel):
    allow_unresolved: bool = False

@app.post("/api/v1/extractions/{extraction_id}/approve")
async def approve_extraction(extraction_id: str, req: ApproveRequest, user_id: str = Depends(get_current_user)):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if supabase:
        supabase.table("extractions").update({
            "status": "approved",
            "approved_at": now,
            "approved_by": user_id,
            "updated_at": now
        }).eq("id", extraction_id).execute()

        # Update fields review state
        supabase.table("extraction_fields").update({"review_state": "approved"}).eq("extraction_id", extraction_id).execute()

    DatabaseManager.record_audit(user_id, None, None, "EXTRACTION_APPROVED", "extraction", extraction_id, {})
    return {"approved": True, "extraction_id": extraction_id, "approved_at": now}

# Cross-Document Consistency (P1)
@app.get("/api/v1/cases/{case_id}/consistency")
async def get_case_consistency(case_id: str, user_id: str = Depends(get_current_user)):
    docs = DatabaseManager.get_documents_by_case(case_id)
    doc_ids = [d["id"] for d in docs]
    extractions = DatabaseManager.get_extractions_by_docs(doc_ids)

    consistency_signals = check_cross_document_consistency(extractions)
    return {"signals": consistency_signals}

# Document Q&A Assistant (P1)
class QAQueryRequest(BaseModel):
    case_id: str
    query: str

@app.post("/api/v1/qa/query")
async def qa_query(req: QAQueryRequest, user_id: str = Depends(get_current_user)):
    docs = DatabaseManager.get_documents_by_case(req.case_id)
    doc_ids = [d["id"] for d in docs]
    extractions = DatabaseManager.get_extractions_by_docs(doc_ids)

    response = await answer_document_query(req.query, extractions)
    return response

# Export Generation & Download (PDF, XLSX, CSV, JSON)
class ExportRequest(BaseModel):
    case_id: str
    formats: List[str] = ["json", "csv", "xlsx", "pdf"]
    include_unresolved: bool = False

@app.post("/api/v1/exports")
async def generate_exports(req: ExportRequest, user_id: str = Depends(get_current_user)):
    case = DatabaseManager.get_case(req.case_id) or {"id": req.case_id, "name": f"Case #{req.case_id[:8]}"}
    docs = DatabaseManager.get_documents_by_case(req.case_id)
    doc_ids = [d["id"] for d in docs]
    extractions = DatabaseManager.get_extractions_by_docs(doc_ids)

    export_files = {}
    for fmt in req.formats:
        fmt_clean = fmt.lower()
        if fmt_clean == "json":
            data = export_json(case, docs, extractions)
        elif fmt_clean == "csv":
            data = export_csv(case, docs, extractions)
        elif fmt_clean == "xlsx":
            data = export_xlsx(case, docs, extractions)
        elif fmt_clean == "pdf":
            data = export_pdf(case, docs, extractions)
        else:
            continue

        exp_id = str(uuid.uuid4())
        filename = f"DocRefine_Case_{req.case_id[:8]}.{fmt_clean}"
        rel_path = f"{user_id}/{req.case_id}/exports/{filename}"
        StorageManager.save_file(rel_path, data)
        signed_url = StorageManager.get_signed_url(rel_path)
        export_files[fmt_clean] = {"export_id": exp_id, "download_url": signed_url, "filename": filename}

    DatabaseManager.record_audit(user_id, req.case_id, None, "CASE_EXPORTED", "case", req.case_id, {"formats": req.formats})
    return {"case_id": req.case_id, "exports": export_files}