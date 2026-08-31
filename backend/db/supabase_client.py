import os
import uuid
import datetime
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
from backend.config import settings

# Initialize Supabase client
supabase: Optional[Client] = None
try:
    if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
except Exception as e:
    print(f"[Supabase] Warning: Could not initialize remote Supabase client: {e}")

# In-memory fast write-through store & filesystem storage vault
LOCAL_STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "storage_vault")
os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)

# In-memory relational store
_MEM_CASES: Dict[str, Dict[str, Any]] = {}
_MEM_DOCUMENTS: Dict[str, Dict[str, Any]] = {}
_MEM_JOBS: Dict[str, Dict[str, Any]] = {}
_MEM_OCR_RUNS: Dict[str, Dict[str, Any]] = {}
_MEM_EXTRACTIONS: Dict[str, Dict[str, Any]] = {}
_MEM_FIELDS: Dict[str, Dict[str, Any]] = {}
_MEM_AUDIT: List[Dict[str, Any]] = []

class StorageManager:
    @staticmethod
    def save_file(rel_path: str, data: bytes) -> str:
        clean_path = rel_path.lstrip("/").replace("\\", "/")
        local_dest = os.path.join(LOCAL_STORAGE_DIR, clean_path.replace("/", os.sep))
        os.makedirs(os.path.dirname(local_dest), exist_ok=True)
        with open(local_dest, "wb") as f:
            f.write(data)

        if supabase:
            try:
                supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
                    path=clean_path,
                    file=data,
                    file_options={"upsert": "true"}
                )
            except Exception:
                pass
        return clean_path

    @staticmethod
    def read_file(rel_path: str) -> Optional[bytes]:
        clean_path = rel_path.lstrip("/").replace("\\", "/")
        local_dest = os.path.join(LOCAL_STORAGE_DIR, clean_path.replace("/", os.sep))
        if os.path.exists(local_dest):
            with open(local_dest, "rb") as f:
                return f.read()

        if supabase:
            try:
                res = supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).download(clean_path)
                return res
            except Exception:
                pass
        return None

    @staticmethod
    def get_signed_url(rel_path: str, ttl_seconds: int = 300) -> str:
        clean_path = rel_path.lstrip("/").replace("\\", "/")
        return f"{settings.API_BASE_URL}/files/download?path={clean_path}&token=sig_{uuid.uuid4().hex[:12]}"

class DatabaseManager:
    @staticmethod
    def create_case(name: Optional[str] = None, user_id: str = "demo_user") -> Dict[str, Any]:
        case_id = str(uuid.uuid4())
        case_name = name or f"Review Case #{case_id[:8]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        row = {
            "id": case_id,
            "user_id": user_id,
            "name": case_name,
            "status": "active",
            "created_at": now,
            "updated_at": now
        }
        _MEM_CASES[case_id] = row
        if supabase:
            try:
                supabase.table("cases").insert(row).execute()
            except Exception as e:
                print(f"[DB] Error inserting case to Supabase: {e}")
        return row

    @staticmethod
    def get_case(case_id: str) -> Optional[Dict[str, Any]]:
        if case_id in _MEM_CASES:
            return _MEM_CASES[case_id]
        if supabase:
            try:
                res = supabase.table("cases").select("*").eq("id", case_id).execute()
                if res.data:
                    _MEM_CASES[case_id] = res.data[0]
                    return res.data[0]
            except Exception:
                pass
        return None

    @staticmethod
    def list_cases(user_id: str = "demo_user") -> List[Dict[str, Any]]:
        if _MEM_CASES:
            return sorted(list(_MEM_CASES.values()), key=lambda x: x.get("created_at", ""), reverse=True)
        if supabase:
            try:
                res = supabase.table("cases").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
                for r in (res.data or []):
                    _MEM_CASES[r["id"]] = r
                return res.data or []
            except Exception:
                pass
        return []

    @staticmethod
    def create_document(doc_data: Dict[str, Any]) -> Dict[str, Any]:
        _MEM_DOCUMENTS[doc_data["id"]] = doc_data
        if supabase:
            try:
                supabase.table("documents").insert(doc_data).execute()
            except Exception as e:
                print(f"[DB] Error creating doc in Supabase: {e}")
        return doc_data

    @staticmethod
    def get_documents_by_case(case_id: str) -> List[Dict[str, Any]]:
        docs_map = {d["id"]: d for d in _MEM_DOCUMENTS.values() if d.get("case_id") == case_id}
        if supabase:
            try:
                res = supabase.table("documents").select("*").eq("case_id", case_id).order("created_at").execute()
                for r in (res.data or []):
                    _MEM_DOCUMENTS[r["id"]] = r
                    docs_map[r["id"]] = r
            except Exception as e:
                print(f"[DB] Error querying documents from Supabase: {e}")
        return sorted(list(docs_map.values()), key=lambda x: x.get("created_at", ""))

    @staticmethod
    def update_document(doc_id: str, updates: Dict[str, Any]):
        updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if doc_id in _MEM_DOCUMENTS:
            _MEM_DOCUMENTS[doc_id].update(updates)
        if supabase:
            try:
                supabase.table("documents").update(updates).eq("id", doc_id).execute()
            except Exception:
                pass

    @staticmethod
    def create_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
        _MEM_JOBS[job_data["id"]] = job_data
        if supabase:
            try:
                supabase.table("processing_jobs").insert(job_data).execute()
            except Exception:
                pass
        return job_data

    @staticmethod
    def get_latest_job_for_document(doc_id: str) -> Optional[Dict[str, Any]]:
        """Returns the most recently created job for a document, so the API
        can surface the REAL failure reason (timeout, exception, rate limit,
        quality) instead of the frontend guessing / hardcoding one."""
        candidates = [j for j in _MEM_JOBS.values() if j.get("document_id") == doc_id]
        if supabase:
            try:
                res = supabase.table("processing_jobs").select("*").eq("document_id", doc_id).order("created_at", desc=True).limit(1).execute()
                if res.data:
                    _MEM_JOBS[res.data[0]["id"]] = res.data[0]
                    candidates.append(res.data[0])
            except Exception:
                pass
        if not candidates:
            return None
        return sorted(candidates, key=lambda j: j.get("created_at", ""))[-1]

    @staticmethod
    def update_job(job_id: str, updates: Dict[str, Any]):
        updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if "stage" in updates:
            existing = _MEM_JOBS.get(job_id, {})
            history = list(existing.get("stage_history") or [])
            now_iso = updates["updated_at"]
            if not history or history[-1].get("stage") != updates["stage"]:
                if history:
                    history[-1]["ended_at"] = now_iso
                history.append({
                    "stage": updates["stage"],
                    "status": updates.get("status", existing.get("status", "processing")),
                    "started_at": now_iso,
                    "ended_at": None,
                    "error_code": updates.get("error_code"),
                })
                updates["stage_history"] = history
            elif updates.get("status") in ("completed", "failed"):
                history[-1]["ended_at"] = now_iso
                history[-1]["status"] = updates["status"]
                updates["stage_history"] = history
        if job_id in _MEM_JOBS:
            _MEM_JOBS[job_id].update(updates)
        if supabase:
            try:
                supabase.table("processing_jobs").update(updates).eq("id", job_id).execute()
            except Exception:
                pass

    @staticmethod
    def save_extraction(extraction_data: Dict[str, Any], fields: List[Dict[str, Any]]):
        ext_id = extraction_data["id"]
        _MEM_EXTRACTIONS[ext_id] = extraction_data
        for f in fields:
            _MEM_FIELDS[f["id"]] = f
        if supabase:
            try:
                supabase.table("extractions").insert(extraction_data).execute()
                valid_cols = {
                    "id", "extraction_id", "field_key", "label", "raw_value",
                    "normalized_value", "source_text", "ocr_confidence",
                    "structuring_confidence", "validation_score", "field_score",
                    "confidence_state", "validation_status", "review_state", "reason_codes_json"
                }
                for f in fields:
                    clean_f = {k: v for k, v in f.items() if k in valid_cols}
                    supabase.table("extraction_fields").insert(clean_f).execute()
            except Exception as e:
                print(f"[DB] Error saving extraction to Supabase: {e}")

    @staticmethod
    def get_extractions_by_docs(doc_ids: List[str]) -> List[Dict[str, Any]]:
        if not doc_ids:
            return []
        
        exts_by_doc = {e["document_id"]: dict(e) for e in _MEM_EXTRACTIONS.values() if e.get("document_id") in doc_ids}
        if supabase:
            try:
                res = supabase.table("extractions").select("*").in_("document_id", doc_ids).execute()
                for r in (res.data or []):
                    _MEM_EXTRACTIONS[r["id"]] = r
                    if r.get("document_id") not in exts_by_doc:
                        exts_by_doc[r["document_id"]] = dict(r)
                
                ext_ids = [e["id"] for e in exts_by_doc.values()]
                if ext_ids:
                    f_res = supabase.table("extraction_fields").select("*").in_("extraction_id", ext_ids).execute()
                    for f in (f_res.data or []):
                        _MEM_FIELDS[f["id"]] = f
            except Exception as e:
                print(f"[DB] Error querying extractions from Supabase: {e}")

        result = []
        for doc_id, e in exts_by_doc.items():
            e_copy = dict(e)
            fields = [f for f in _MEM_FIELDS.values() if f.get("extraction_id") == e["id"]]
            e_copy["fields"] = fields
            result.append(e_copy)
        return result

    @staticmethod
    def update_field(extraction_id: str, field_key: str, updates: Dict[str, Any]):
        for f in _MEM_FIELDS.values():
            if f.get("extraction_id") == extraction_id and f.get("field_key") == field_key:
                f.update(updates)
        if supabase:
            try:
                supabase.table("extraction_fields").update(updates).eq("extraction_id", extraction_id).eq("field_key", field_key).execute()
            except Exception:
                pass

    @staticmethod
    def approve_extraction(extraction_id: str, approved_by: str = "demo_reviewer@docxtract.ai"):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if extraction_id in _MEM_EXTRACTIONS:
            _MEM_EXTRACTIONS[extraction_id].update({
                "status": "approved",
                "approved_at": now,
                "approved_by": approved_by,
                "updated_at": now
            })
        for f in _MEM_FIELDS.values():
            if f.get("extraction_id") == extraction_id:
                f["review_state"] = "approved"
        if supabase:
            try:
                supabase.table("extractions").update({
                    "status": "approved",
                    "approved_at": now,
                    "approved_by": approved_by,
                    "updated_at": now
                }).eq("id", extraction_id).execute()
                supabase.table("extraction_fields").update({"review_state": "approved"}).eq("extraction_id", extraction_id).execute()
            except Exception:
                pass

    @staticmethod
    def record_audit(user_id: str, case_id: Optional[str], doc_id: Optional[str], action: str, entity_type: str, entity_id: str, metadata: Dict[str, Any]):
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "case_id": case_id,
            "document_id": doc_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "metadata_json": metadata,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        _MEM_AUDIT.append(row)
        if supabase:
            try:
                supabase.table("audit_events").insert(row).execute()
            except Exception:
                pass
        return row
