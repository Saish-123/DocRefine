import asyncio
import datetime
import time
import traceback
import uuid
from typing import Dict, Any, List
from backend.config import settings
from backend.db.supabase_client import DatabaseManager, StorageManager, supabase, _MEM_DOCUMENTS
from backend.pipeline.quality import analyze_document_quality
from backend.pipeline.enhancement import enhance_document_image
from backend.pipeline.ocr import run_multilingual_ocr
from backend.pipeline.llm_adapters import llm_adapter
from backend.pipeline.schemas import DOCUMENT_SCHEMAS, validate_field_value, normalize_date
from backend.pipeline.confidence import calculate_field_confidence

STAGE_TIMEOUT_QUALITY_SECONDS = float(getattr(settings, "STAGE_TIMEOUT_QUALITY_SECONDS", 20.0))
STAGE_TIMEOUT_ENHANCEMENT_SECONDS = float(getattr(settings, "STAGE_TIMEOUT_ENHANCEMENT_SECONDS", 30.0))
STAGE_TIMEOUT_OCR_SECONDS = float(getattr(settings, "STAGE_TIMEOUT_OCR_SECONDS", 60.0))


async def _run_stage_with_budget(fn, *args, budget_seconds: float, stage_name: str, job_id: str):
    """
    Runs a CPU-bound pipeline stage with its own soft time budget. If the
    stage blows its budget, we log it and let the caller fall back to a
    cheaper/degraded path instead of letting the *whole* job (and every
    later stage) get killed by the outer per-job timeout. This is what
    keeps one slow stage on a large document from surfacing to the user as
    a generic "processing failed / image too blurry" rejection.
    """
    try:
        return await asyncio.wait_for(asyncio.to_thread(fn, *args), timeout=budget_seconds)
    except asyncio.TimeoutError:
        print(f"[Worker] Job {job_id}: stage '{stage_name}' exceeded its {budget_seconds:.0f}s budget - degrading gracefully.")
        return None


async def process_document_job(job_id: str, doc_id: str, case_id: str, user_id: str, fast_mode: bool = False):
    """
    Executes the 6-stage asynchronous Document Rescue & Extraction pipeline.

    fast_mode=True is used for automatic retries after a stall (see
    job_queue.py._handle_stall): it skips the heavy OpenCV enhancement pass
    and tightens the LLM rate-limit wait, trading a little visual polish /
    provider patience for a much higher chance of finishing inside budget on
    a large document.
    """
    job_start = time.monotonic()
    try:
        # Stage 1: Initializing & Validation
        DatabaseManager.update_job(job_id, {"status": "processing", "stage": "validating", "progress": 10})
        
        doc_record = _MEM_DOCUMENTS.get(doc_id, {})
        source_path = doc_record.get("source_path")
        
        if not source_path and supabase:
            try:
                res = supabase.table("documents").select("*").eq("id", doc_id).execute()
                if res.data:
                    doc_record = res.data[0]
                    source_path = doc_record.get("source_path")
            except Exception:
                pass
        
        source_data = StorageManager.read_file(source_path) if source_path else None
        
        if not source_data:
            DatabaseManager.update_job(job_id, {"status": "failed", "stage": "failed", "error_code": "FILE_READ_ERROR", "progress": 0})
            DatabaseManager.update_document(doc_id, {"status": "processing_failed"})
            return

        # Stage 2: Quality Analysis
        DatabaseManager.update_job(job_id, {"stage": "quality_analysis", "progress": 25})
        quality_rep = await _run_stage_with_budget(
            analyze_document_quality, source_data,
            budget_seconds=STAGE_TIMEOUT_QUALITY_SECONDS, stage_name="quality_analysis", job_id=job_id
        )
        if quality_rep is None:
            # Degrade instead of aborting: assume a middling, unverified
            # score rather than failing a job just because the *scoring*
            # step itself was slow (e.g. a very large image).
            quality_rep = {
                "quality_score": 60, "quality_band": "warning",
                "quality_flags": ["QUALITY_CHECK_SKIPPED_SLOW"],
                "guidance": ["Quality scan took too long and was skipped; proceeding with extraction."],
                "algorithm_version": "1.0.0",
                "metrics": {"resolution_mp": 0.0, "blur_variance": 0.0, "brightness": 0.0, "contrast": 0.0, "estimated_tilt_deg": 0.0}
            }
        DatabaseManager.update_document(doc_id, {
            "quality_score": quality_rep["quality_score"],
            "quality_band": quality_rep["quality_band"],
            "quality_flags_json": quality_rep["quality_flags"]
        })

        # ── Quality Gate: reject only truly unreadable documents ──────────────
        # Gate triggers if BOTH conditions are true:
        #   1) quality_score < 30 (near-zero readable content)
        #   2) band is "needs_reupload" (not just "warning")
        # Previously "needs_reupload" alone would reject docs that scored well
        # on most metrics but failed one dimension (e.g. slightly low contrast
        # on a high-resolution PDF scan) — causing false rejections like
        # "SYJC RECEIPT.pdf" which scored 86/100 but was marked rejected.
        is_truly_unreadable = (
            quality_rep["quality_score"] < 30
            and quality_rep["quality_band"] == "needs_reupload"
        )
        if is_truly_unreadable:
            print(f"[Worker] Job {job_id}: Document quality too low ({quality_rep['quality_score']}/100) — rejecting.")
            DatabaseManager.update_job(job_id, {
                "status": "failed",
                "stage": "failed",
                "error_code": "QUALITY_TOO_LOW",
                "progress": 0,
                "error_message": f"Document quality score {quality_rep['quality_score']}/100 is too low to extract text reliably. Please upload a clearer, well-lit photo."
            })
            DatabaseManager.update_document(doc_id, {"status": "processing_failed"})
            return

        # Stage 3: OpenCV Rescue & Enhancement
        # fast_mode (used on auto-retry after a stall) skips this stage
        # entirely - it's the most expensive step on large images (2K
        # upscale + bilateral denoise) and OCR/LLM extraction both work fine
        # on the raw source when time is tight.
        enhanced_bytes = source_data
        manifest = {"enhancement_applied": False, "skipped_reason": None}
        if not fast_mode:
            DatabaseManager.update_job(job_id, {"stage": "enhancing", "progress": 45})
            enh_result = await _run_stage_with_budget(
                enhance_document_image, source_data, quality_rep,
                budget_seconds=STAGE_TIMEOUT_ENHANCEMENT_SECONDS, stage_name="enhancement", job_id=job_id
            )
            if enh_result is not None:
                enhanced_bytes, manifest = enh_result
            else:
                print(f"[Worker] Job {job_id}: enhancement skipped (over budget) — using source image directly.")
                manifest["skipped_reason"] = "OVER_BUDGET"
        else:
            manifest["skipped_reason"] = "FAST_MODE"

        if enhanced_bytes:
            artifact_id = str(uuid.uuid4())[:8]
            enhanced_rel_path = f"{user_id}/{case_id}/{doc_id}/enhanced/{artifact_id}.png"
            StorageManager.save_file(enhanced_rel_path, enhanced_bytes)
            DatabaseManager.update_document(doc_id, {"enhanced_path": enhanced_rel_path})

        # Stage 4: Multilingual OCR — single pass on enhanced image
        DatabaseManager.update_job(job_id, {"stage": "ocr_running", "progress": 65})
        language_mode = doc_record.get("language_mode", "Mixed")

        ocr_res = await _run_stage_with_budget(
            run_multilingual_ocr, enhanced_bytes, language_mode,
            budget_seconds=STAGE_TIMEOUT_OCR_SECONDS, stage_name="ocr", job_id=job_id
        )
        if ocr_res is None:
            print(f"[Worker] Job {job_id}: OCR stage timed out ({STAGE_TIMEOUT_OCR_SECONDS}s budget) — attempting fast source pass.")
            # Quick attempt on source data
            ocr_res = await _run_stage_with_budget(
                run_multilingual_ocr, source_data, language_mode,
                budget_seconds=30.0, stage_name="ocr_source_fast", job_id=job_id
            )
            if ocr_res is None:
                ocr_res = {
                    "text": "", "regions": [], "language": language_mode,
                    "average_confidence": 0.0, "engine": "ocr_timed_out",
                    "engine_version": "n/a", "status": "ocr_timed_out"
                }

        print(f"[Worker] Job {job_id}: OCR pass complete. Text lines: {len(ocr_res.get('text', '').splitlines())}, conf={ocr_res.get('average_confidence', 0):.3f}")

        if supabase:
            try:
                supabase.table("ocr_runs").insert({
                    "id": str(uuid.uuid4()),
                    "document_id": doc_id,
                    "artifact_type": "enhanced",
                    "engine": ocr_res.get("engine", "EasyOCR-Multilingual-Devanagari"),
                    "engine_version": ocr_res.get("engine_version", "2.8.0"),
                    "language_mode": language_mode,
                    "text_json": {"text": ocr_res.get("text", "")},
                    "regions_json": ocr_res.get("regions", [])
                }).execute()
            except Exception:
                pass

        # Stage 5: Intelligent Multimodal / LLM Extraction
        DatabaseManager.update_job(job_id, {"stage": "extracting", "progress": 85})
        ocr_text_payload = ocr_res.get("text", "")

        fname = doc_record.get("filename_safe", "")
        extracted_data = await llm_adapter.extract_structured(
            ocr_text=ocr_text_payload,
            image_bytes=enhanced_bytes or source_data,
            filename_hint=fname
        )

        # If every configured API key (across every provider) is currently
        # rate-limited, wait out the shorter of the reported cooldown or our
        # hard cap, then retry ONCE before giving up. This is what makes key
        # rotation "not stop anything" in practice: a single 429 never
        # surfaces to the user, and even a full-provider outage just adds a
        # short, visible wait instead of a failed job.
        if extracted_data.get("rate_limited"):
            # Cap the wait to whatever's actually left of THIS job's budget
            # (minus a safety buffer for the remaining stages), not just the
            # global MAX_RATE_LIMIT_WAIT_SECONDS. Without this, a rate-limit
            # wait could by itself push a large/slow document past the outer
            # job timeout and get it killed - defeating the point of waiting.
            from backend.job_queue import compute_job_timeout
            job_timeout = compute_job_timeout(doc_id)
            elapsed = time.monotonic() - job_start
            remaining_budget = max(5.0, job_timeout - elapsed - 15.0)
            wait_s = min(
                extracted_data.get("retry_after_seconds", 0.0) or 0.0,
                settings.MAX_RATE_LIMIT_WAIT_SECONDS,
                remaining_budget,
            )
            resume_at = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=wait_s)).isoformat()
            print(f"[Worker] Job {job_id}: all API keys currently rate-limited - waiting {wait_s:.0f}s then retrying once.")
            DatabaseManager.update_job(job_id, {
                "stage": "rate_limited",
                "progress": 85,
                "error_code": "PROVIDERS_RATE_LIMITED",
                "error_message": f"All configured API keys are temporarily rate-limited. Retrying automatically in {int(wait_s)}s.",
                "retry_after_seconds": wait_s,
                "resume_at": resume_at,
            })
            if wait_s > 0:
                await asyncio.sleep(wait_s)
                extracted_data = await llm_adapter.extract_structured(
                    ocr_text=ocr_text_payload,
                    image_bytes=enhanced_bytes or source_data,
                    filename_hint=fname
                )
            if extracted_data.get("rate_limited"):
                # Still exhausted (or no time left to wait). Rather than
                # failing the job outright - which used to force a manual
                # re-upload for what is really a "the AI provider is busy"
                # problem, not a bad document - fall back to the offline,
                # no-network rule-based extractor. The user still gets a
                # reviewable result; fields will just be flagged lower-
                # confidence and marked for manual review.
                print(f"[Worker] Job {job_id}: providers still rate-limited — using offline rule-based fallback extraction.")
                from backend.pipeline.llm_adapters import fallback_rule_extraction
                extracted_data = fallback_rule_extraction(ocr_text_payload, fname)
                extracted_data["provider_used"] = "rule_based_fallback_after_rate_limit"

        doc_type = extracted_data.get("document_type", "generic")
        raw_fields = extracted_data.get("fields", {})

        # Task 2.2: Merge any additional_fields from LLM into raw_fields
        additional_fields_list = extracted_data.get("additional_fields", [])
        if isinstance(additional_fields_list, list):
            for af in additional_fields_list:
                if isinstance(af, dict):
                    k_af = af.get("key") or af.get("field_key")
                    v_af = af.get("value") or af.get("raw_value")
                    if k_af and v_af is not None and k_af not in raw_fields:
                        raw_fields[k_af] = v_af
        elif isinstance(additional_fields_list, dict):
            for k_af, v_af in additional_fields_list.items():
                if k_af not in raw_fields and v_af is not None:
                    raw_fields[k_af] = v_af

        # Stage 6: Field-Level Validation & PRD Confidence Math
        DatabaseManager.update_job(job_id, {"stage": "validating_fields", "progress": 95})
        schema_def = DOCUMENT_SCHEMAS.get(doc_type, DOCUMENT_SCHEMAS["generic"])
        
        extraction_id = str(uuid.uuid4())
        total_field_score = 0
        total_fields_count = 0
        persisted_fields = []

        for f_meta in schema_def:
            k = f_meta["key"]
            lbl = f_meta["label"]
            raw_v = raw_fields.get(k)
            norm_v = normalize_date(raw_v) if "date" in k else raw_v

            val_score, val_status, val_reasons = validate_field_value(k, raw_v, norm_v)

            # Task 5.1: Per-field OCR confidence — fuzzy match field value against OCR regions
            global_ocr_conf = ocr_res.get("average_confidence", 0.90)
            ocr_regions = ocr_res.get("regions", [])
            field_ocr_conf = global_ocr_conf
            if raw_v and ocr_regions:
                raw_str = str(raw_v).lower().strip()
                best_match_conf = 0.0
                for reg in ocr_regions:
                    reg_text = reg.get("text", "").lower().strip()
                    if reg_text and raw_str and (raw_str in reg_text or reg_text in raw_str or
                       any(word in reg_text for word in raw_str.split() if len(word) > 3)):
                        conf_val = float(reg.get("confidence", global_ocr_conf))
                        if conf_val > best_match_conf:
                            best_match_conf = conf_val
                if best_match_conf > 0.0:
                    field_ocr_conf = best_match_conf

            struct_conf = extracted_data.get("confidence_estimate", 0.95)

            conf_res = calculate_field_confidence(
                ocr_confidence=field_ocr_conf,
                structuring_confidence=struct_conf,
                validation_score=val_score,
                quality_score=quality_rep["quality_score"],
                raw_value=raw_v,
                validation_status=val_status
            )

            field_score = conf_res["field_score"]
            conf_state = conf_res["confidence_state"]

            total_field_score += field_score
            total_fields_count += 1

            field_entry = {
                "id": str(uuid.uuid4()),
                "extraction_id": extraction_id,
                "field_key": k,
                "label": lbl,
                "raw_value": str(raw_v) if raw_v is not None else None,
                "normalized_value": str(norm_v) if norm_v is not None else None,
                "source_text": str(raw_v) if raw_v else "",
                "ocr_confidence": conf_res["ocr_confidence"],
                "structuring_confidence": conf_res["structuring_confidence"],
                "validation_score": conf_res["validation_score"],
                "field_score": field_score,
                "confidence_state": conf_state,
                "validation_status": val_status,
                "review_state": "needs_review",
                "reason_codes_json": conf_res["reason_codes"] + val_reasons,
                "quality_factor": round(quality_rep["quality_score"] / 100.0, 3)
            }
            persisted_fields.append(field_entry)

        # Include any dynamic additional fields extracted from the document
        handled_keys = {f["key"] for f in schema_def}
        for k, v in raw_fields.items():
            if k not in handled_keys and v is not None and str(v).strip():
                label = k.replace("_", " ").title()
                norm_v = normalize_date(str(v)) if "date" in k else str(v)
                val_score, val_status, val_reasons = validate_field_value(k, str(v), norm_v)
                
                conf_res = calculate_field_confidence(
                    ocr_confidence=ocr_res.get("average_confidence", 0.90),
                    structuring_confidence=extracted_data.get("confidence_estimate", 0.95),
                    validation_score=val_score,
                    quality_score=quality_rep["quality_score"],
                    raw_value=str(v),
                    validation_status=val_status
                )
                field_score = conf_res["field_score"]
                total_field_score += field_score
                total_fields_count += 1
                
                persisted_fields.append({
                    "id": str(uuid.uuid4()),
                    "extraction_id": extraction_id,
                    "field_key": k,
                    "label": label,
                    "raw_value": str(v),
                    "normalized_value": str(norm_v),
                    "source_text": str(v),
                    "ocr_confidence": conf_res["ocr_confidence"],
                    "structuring_confidence": conf_res["structuring_confidence"],
                    "validation_score": conf_res["validation_score"],
                    "field_score": field_score,
                    "confidence_state": conf_res["confidence_state"],
                    "validation_status": val_status,
                    "review_state": "needs_review",
                    "reason_codes_json": conf_res["reason_codes"] + val_reasons
                })

        overall_conf = int(total_field_score / total_fields_count) if total_fields_count > 0 else 0

        # Persist Extractions & Fields
        extraction_data = {
            "id": extraction_id,
            "document_id": doc_id,
            "user_id": user_id,
            "schema_name": doc_type,
            "schema_version": "1.0.0",
            "payload_json": raw_fields,
            "status": "needs_review",
            "overall_confidence": overall_conf,
            "pipeline_version": "1.0.0",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        DatabaseManager.save_extraction(extraction_data, persisted_fields)

        # Update Document & Job Status
        doc_final_status = "needs_reupload" if quality_rep["quality_band"] == "needs_reupload" else "needs_review"
        DatabaseManager.update_document(doc_id, {"status": doc_final_status})
        DatabaseManager.update_job(job_id, {
            "status": "completed",
            "stage": "completed",
            "progress": 100,
            "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })

        DatabaseManager.record_audit(
            user_id=user_id,
            case_id=case_id,
            doc_id=doc_id,
            action="PIPELINE_EXTRACTION_COMPLETED",
            entity_type="document",
            entity_id=doc_id,
            metadata={"doc_type": doc_type, "fields_extracted": len(persisted_fields), "overall_confidence": overall_conf}
        )

    except Exception as e:
        print(f"[Worker Error] Job {job_id} failed: {traceback.format_exc()}")
        DatabaseManager.update_job(job_id, {
            "status": "failed",
            "stage": "failed",
            "error_code": "PROCESSING_EXCEPTION",
            "progress": 0
        })
        DatabaseManager.update_document(doc_id, {"status": "processing_failed"})
