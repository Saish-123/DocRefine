"""
Bounded-concurrency job queue for document processing.

Problem this fixes:
Previously, every document upload fired an unbounded
`asyncio.create_task(process_document_job(...))`. When a user uploaded
3-4 documents in quick succession, all of them started processing
*simultaneously* - each running a CPU-heavy EasyOCR pass (torch, pinned to
1 thread) plus an LLM extraction call, all sharing the same event loop's
default thread pool. The result:
  - The 1st/2nd document had the machine mostly to itself -> fast, correct.
  - The 3rd/4th document's OCR + LLM calls were competing for the same
    CPU cores and network connections as the earlier, still-running jobs
    -> much slower, and more likely to hit the Groq timeout, falling back
    to a much weaker extraction (explains "empty" or "partial" fields).

Fix: a small in-process queue with a fixed number of worker coroutines.
Documents are processed with *bounded* concurrency (default 2, configurable),
instead of "as many as get uploaded at once". This keeps timing predictable
and avoids resource contention degrading extraction quality.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Tuple

from backend.config import settings
from backend.db.supabase_client import DatabaseManager, _MEM_DOCUMENTS
from backend.worker import process_document_job

logger = logging.getLogger(__name__)

# How many documents may have their OCR + LLM pipeline running at the same
# time. Keep this low (1-2) on typical laptop-class CPUs running EasyOCR;
# raise it only if you have more CPU cores / are not CPU-bound on OCR.
MAX_CONCURRENT_JOBS: int = int(getattr(settings, "MAX_CONCURRENT_JOBS", 2))

# Base ceiling per job (small documents). Large documents get more time -
# see compute_job_timeout() below - so a legitimately big/high-res upload
# isn't force-killed and mislabeled as a bad document.
JOB_TIMEOUT_BASE_SECONDS: float = float(getattr(settings, "JOB_TIMEOUT_BASE_SECONDS", 180.0))
JOB_TIMEOUT_SECONDS_PER_MB: float = float(getattr(settings, "JOB_TIMEOUT_SECONDS_PER_MB", 20.0))
JOB_TIMEOUT_MAX_SECONDS: float = float(getattr(settings, "JOB_TIMEOUT_MAX_SECONDS", 420.0))
JOB_AUTO_RETRY_FAST_MODE: bool = bool(getattr(settings, "JOB_AUTO_RETRY_FAST_MODE", True))
JOB_MAX_RETRIES: int = int(getattr(settings, "JOB_MAX_RETRIES", 2))

# Queue items now carry a `fast_mode` flag so an auto-retry can ask the
# worker to skip the expensive enhancement pass / use a tighter LLM budget.
_job_queue: "asyncio.Queue[Tuple[str, str, str, str, bool]]" = asyncio.Queue()
_worker_tasks: List[asyncio.Task] = []


def compute_job_timeout(doc_id: str) -> float:
    """
    Grant extra processing time proportional to the source file's size,
    instead of one flat budget for every document. A 15MB scanned PDF
    legitimately needs more wall-clock time than a 200KB photo; previously
    both got the same 180s and the big-but-fine document was killed and
    shown to the user as a quality failure.
    """
    size_bytes = 0
    doc = _MEM_DOCUMENTS.get(doc_id) or {}
    size_bytes = doc.get("size_bytes") or 0
    size_mb = size_bytes / (1024 * 1024)
    timeout = JOB_TIMEOUT_BASE_SECONDS + (size_mb * JOB_TIMEOUT_SECONDS_PER_MB)
    return float(min(JOB_TIMEOUT_MAX_SECONDS, max(JOB_TIMEOUT_BASE_SECONDS, timeout)))


async def enqueue_job(job_id: str, doc_id: str, case_id: str, user_id: str, fast_mode: bool = False) -> None:
    """
    Add a document-processing job to the queue.

    Returns immediately (this is just a queue.put) - the upload endpoint
    stays fast and responsive; the actual OCR/LLM work happens in the
    background worker pool, at most MAX_CONCURRENT_JOBS at a time.
    """
    await _job_queue.put((job_id, doc_id, case_id, user_id, fast_mode))
    logger.info(
        "[job_queue] enqueued job=%s doc=%s fast_mode=%s (queue depth now %d)",
        job_id, doc_id, fast_mode, _job_queue.qsize(),
    )


async def _worker_loop(worker_name: str) -> None:
    while True:
        job_id, doc_id, case_id, user_id, fast_mode = await _job_queue.get()
        job_timeout = compute_job_timeout(doc_id)
        try:
            logger.info(
                "[%s] starting job=%s doc=%s fast_mode=%s timeout=%.0fs",
                worker_name, job_id, doc_id, fast_mode, job_timeout,
            )
            await asyncio.wait_for(
                process_document_job(job_id, doc_id, case_id, user_id, fast_mode=fast_mode),
                timeout=job_timeout,
            )
            logger.info("[%s] finished job=%s doc=%s", worker_name, job_id, doc_id)
        except asyncio.TimeoutError:
            await _handle_stall(worker_name, job_id, doc_id, case_id, user_id, job_timeout,
                                 error_code="JOB_TIMEOUT",
                                 error_message=(
                                     f"Processing took longer than expected ({int(job_timeout)}s budget for "
                                     "this file size)."
                                 ))
        except Exception:
            # process_document_job already has its own broad try/except and
            # marks the job failed internally on error - this is only a
            # safety net in case something raises above that layer.
            logger.exception("[%s] job=%s doc=%s raised unexpectedly", worker_name, job_id, doc_id)
            await _handle_stall(worker_name, job_id, doc_id, case_id, user_id, job_timeout,
                                 error_code="PROCESSING_EXCEPTION",
                                 error_message="An unexpected error interrupted processing.")
        finally:
            _job_queue.task_done()


async def _handle_stall(worker_name, job_id, doc_id, case_id, user_id, job_timeout, error_code, error_message):
    """
    A job that timed out or raised above worker.py's own safety net is NOT
    immediately shown to the user as failed. If retries remain, it is
    automatically re-queued once in fast_mode (lighter enhancement, tighter
    LLM budget) so a slow-but-fine document gets a real second chance instead
    of forcing a manual re-upload. Only once retries are exhausted do we mark
    it failed - with the REAL reason, not a generic "blurry" message.
    """
    attempts = 1
    try:
        from backend.db.supabase_client import _MEM_JOBS
        attempts = int((_MEM_JOBS.get(job_id) or {}).get("attempts", 1))
    except Exception:
        pass

    if JOB_AUTO_RETRY_FAST_MODE and attempts < JOB_MAX_RETRIES:
        next_attempt = attempts + 1
        logger.warning(
            "[%s] job=%s doc=%s stalled (%s) - auto-retrying in fast_mode (attempt %d/%d)",
            worker_name, job_id, doc_id, error_code, next_attempt, JOB_MAX_RETRIES,
        )
        DatabaseManager.update_job(job_id, {
            "status": "processing",
            "stage": "retrying_fast_mode",
            "progress": 15,
            "attempts": next_attempt,
            "error_code": error_code,
            "error_message": f"{error_message} Retrying automatically in a faster mode...",
        })
        await enqueue_job(job_id, doc_id, case_id, user_id, fast_mode=True)
        return

    logger.error(
        "[%s] job=%s doc=%s stalled (%s) after %d attempt(s) - marking failed",
        worker_name, job_id, doc_id, error_code, attempts,
    )
    DatabaseManager.update_job(job_id, {
        "status": "failed",
        "stage": "failed",
        "error_code": error_code,
        "progress": 0,
        "error_message": f"{error_message} You can retry, or upload a smaller/clearer file.",
    })
    DatabaseManager.update_document(doc_id, {"status": "processing_failed"})


def start_workers() -> None:
    """Call once on app startup. Idempotent - safe to call more than once
    (e.g. under a dev auto-reloader) without spawning duplicate pools."""
    if _worker_tasks:
        return
    for i in range(MAX_CONCURRENT_JOBS):
        task = asyncio.create_task(_worker_loop(f"worker-{i + 1}"))
        _worker_tasks.append(task)
    logger.info("[job_queue] started %d document-processing worker(s)", MAX_CONCURRENT_JOBS)


async def stop_workers() -> None:
    """Call on app shutdown to cancel in-flight worker loops cleanly."""
    for task in _worker_tasks:
        task.cancel()
    for task in _worker_tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass
    _worker_tasks.clear()


def queue_depth() -> int:
    """Number of jobs currently waiting (not yet picked up by a worker)."""
    return _job_queue.qsize()
