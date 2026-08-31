import logging
from typing import Dict, Any, List, Tuple, Optional

from backend.config import settings
from backend.pipeline.llm_adapters import llm_adapter, GROQ_MODELS, LLM_TEMPERATURE
from backend.pipeline.key_pool import get_pool, parse_retry_after

logger = logging.getLogger(__name__)

QA_SYSTEM_PROMPT = """You are DocRefine's grounded Document Verification Q&A assistant for digital lending review.
Your job is to assist lending reviewers by answering questions regarding verified documents, identity numbers, Aadhaar details, PAN, and financials.
CRITICAL RULES:
1. Answer using the document data and context provided.
2. If specific information is available in the records, state the document type and field clearly.
3. Be professional, clear, helpful, and concise.
"""


def _build_context(extractions: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    context_lines = []
    citations = []

    for ext in extractions:
        doc_id = ext.get("document_id")
        schema = ext.get("schema_name", "document")
        context_lines.append(f"--- Document Type: {schema.upper()} (ID: {doc_id}) ---")
        for f in ext.get("fields", []):
            label = f.get("label")
            val = f.get("normalized_value") or f.get("raw_value")
            score = f.get("field_score")
            state = f.get("confidence_state")
            if val:
                context_lines.append(f"  {label}: {val} (Confidence: {score}%, State: {state})")
                citations.append({"document_id": doc_id, "field": label, "value": val})

    context_str = "\n".join(context_lines) if context_lines else "No extracted fields available yet."
    return context_str, citations


def _fallback_answer(citations: List[Dict[str, Any]]) -> Dict[str, Any]:
    if citations:
        fields_summary = "\n".join([f"\u2022 {c['field']}: {c['value']}" for c in citations[:6]])
        return {
            "answer": f"Here is the data extracted from this document:\n\n{fields_summary}",
            "citations": citations,
        }
    return {
        "answer": "The document is currently being processed. Once extraction completes, you can ask about any field, ID number, name, or financial metric.",
        "citations": [],
    }


async def _call_with_rotation(provider: str, base_url: str, model: str, prompt: str) -> Optional[str]:
    """Try every key in this provider's pool (rotating past any that are
    currently rate-limited) before giving up on this provider."""
    pool = get_pool(provider)
    if not pool.has_keys():
        return None

    client = llm_adapter.client  # shared client - no per-call AsyncClient leak
    url = f"{base_url.rstrip('/')}/chat/completions"

    for _ in range(len(pool.keys)):
        acquired = await pool.acquire()
        if acquired is None:
            return None  # every key for this provider is currently cooling down
        idx, api_key = acquired
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            resp = await client.post(url, headers=headers, json={
                "model": model,
                "messages": [
                    {"role": "system", "content": QA_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": LLM_TEMPERATURE,
            })
        except Exception as e:
            logger.warning("[qa:%s:%s] key #%d request failed: %s", provider, model, idx + 1, e)
            return None

        if resp.status_code == 429:
            pool.mark_rate_limited(idx, parse_retry_after(resp.headers))
            logger.info("[qa:%s:%s] key #%d rate-limited, rotating", provider, model, idx + 1)
            continue

        if resp.status_code != 200:
            logger.warning("[qa:%s:%s] non-200: status=%s body=%s", provider, model, resp.status_code, resp.text[:300])
            return None

        try:
            return resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as e:
            logger.warning("[qa:%s:%s] malformed response: %s", provider, model, e)
            return None

    return None  # every key got rate-limited during this loop


async def answer_document_query(query: str, extractions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Answers questions strictly grounded on extracted data and document evidence.

    Uses the same rotating multi-key pools as the main extraction pipeline
    (backend/pipeline/key_pool.py) - if your Groq key is rate-limited, this
    automatically tries a teammate's key before giving up on Groq entirely.
    Reuses llm_adapter's shared httpx client rather than opening (and
    leaking) a new one per call.
    """
    context_str, citations = _build_context(extractions)
    prompt = f"Document Records:\n{context_str}\n\nUser Question: {query}\n\nAnswer concisely:"

    # Groq first (matches main extraction pipeline's provider priority)
    for model in GROQ_MODELS:
        answer = await _call_with_rotation("groq", settings.GROQ_BASE_URL, model, prompt)
        if answer is not None:
            return {"answer": answer, "citations": citations}

    # Gemini as secondary fallback
    answer = await _call_with_rotation("gemini", settings.GEMINI_BASE_URL, settings.GEMINI_MODEL, prompt)
    if answer is not None:
        return {"answer": answer, "citations": citations}

    # NVIDIA as tertiary fallback
    answer = await _call_with_rotation("nvidia", settings.NVIDIA_BASE_URL, settings.NVIDIA_MODEL, prompt)
    if answer is not None:
        return {"answer": answer, "citations": citations}

    # Every provider/key unavailable or failed - degrade gracefully with a
    # direct data dump instead of an error.
    return _fallback_answer(citations)
