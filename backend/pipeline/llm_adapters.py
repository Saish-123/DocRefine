import re
import json
import logging
import httpx
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

from backend.config import settings
from backend.pipeline.schemas import DOCUMENT_SCHEMAS, normalize_date
from backend.pipeline.ocr_corrector import clean_ocr_typos, repair_address_string
from backend.pipeline.key_pool import ApiKeyPool, get_pool, parse_retry_after

logger = logging.getLogger(__name__)

UNIVERSAL_EXTRACTION_SYSTEM_PROMPT = """You are a World-Class Document AI Extraction Engine (equivalent to Google Cloud Document AI and AWS Textract).
Your task is to analyze document OCR text and extract ALL structured data with 100% precision.

SUPPORTED SCHEMAS & FIELD GUIDELINES:

1. "education_marksheet" (10th/12th/Degree Board Marksheets & Statement of Marks):
   - candidate_name: Full name of candidate/student (e.g., "Panhalkar Saish Sanjay")
   - mother_name: Candidate's mother's name if present
   - seat_number: Seat / Roll / Enrollment number (e.g., "A239327", "2722/05798/00099")
   - center_number: Center number / School index number (e.g., "6213", "31.08.077")
   - board_university: Board or University name (e.g., "Maharashtra State Board of Secondary and Higher Secondary Education")
   - examination_name: Exam session (e.g., "SSC Examination MARCH-2022")
   - date_of_birth: Date of birth in YYYY-MM-DD format (e.g., "2006-03-31")
   - total_marks: Total marks obtained out of maximum (e.g., "438 / 500" or "438")
   - percentage: Percentage / GPA if calculated (e.g., "87.60%")
   - result_status: "PASSED", "PASSED WITH DISTINCTION", or "FAILED"
   - subject_scores: Comprehensive list of all subjects with marks/grades (e.g., "English: 87, Marathi: 86, Hindi: 89, Mathematics: 83, Science & Tech: 88, Social Sciences: 95")

2. "leaving_certificate" (School / College Leaving Certificate, Transfer Certificate, LC):
   - candidate_name: Full name of student (e.g., "Panhalkar Saish Sanjay")
   - date_of_birth: Date of birth in YYYY-MM-DD format
   - institution_name: Name of the school or college issuing the certificate (e.g., "Jai Hind College")
   - class_last_studied: Last class studied / standard (e.g., "XII", "10th", "FY B.Com")
   - year_of_leaving: Year or date of leaving (e.g., "2024", "June 2024")
   - conduct: Student's conduct (e.g., "Good", "Excellent")
   - reason_for_leaving: Reason stated (e.g., "Passed", "Transferred")
   - principal_name: Name or signature of Principal / Head of Institution
   - date_of_issue: Date the certificate was issued (YYYY-MM-DD)

3. "fee_receipt" / "invoice_receipt" (College Fee Receipts, Admission Receipts, Invoices):
   - student_name, receipt_number, institution_name, course_class, roll_number, date (YYYY-MM-DD), total_amount_paid, payment_mode, fee_breakdown

4. "identity_document" (Aadhaar Card, Voter ID, Passport, Driving License):
   - full_name, document_number (12-digit Aadhaar as "XXXX XXXX XXXX"), date_of_birth (YYYY-MM-DD), gender, address

5. "tax_id" (Income Tax PAN Card):
   - full_name, tax_id_number (10-char PAN), date_of_birth (YYYY-MM-DD)

6. "bank_statement" (Bank Account Statement, Passbook):
   - account_holder_name, account_number, ifsc, bank_name, closing_balance

7. "medical_prescription" (Doctor Prescription, Medical Record):
   - patient_name, doctor_name, date, diagnosis, medications

8. "generic" (Any other official document):
   - document_title, primary_party, identifier_number, issue_date, summary_details

CRITICAL EXTRACTION RULES:
- Identify the most accurate "document_type" from the 8 types above.
- Extract ALL available values into the "fields" dictionary using the schema keys above.
- Any labeled fields in the document that do NOT match a schema key must go into "additional_fields" as a list of {"key": "...", "value": "..."} objects.
- Output strict valid JSON only — no markdown fences, no commentary, no extra prose.

ANTI-HALLUCINATION GUARDRAIL (MOST IMPORTANT RULE):
- ONLY extract values that are EXPLICITLY and CLEARLY present in the OCR text.
- If a value is not found, omit the key entirely — do NOT guess, infer, or invent values.
- If the OCR text is partial or unclear, extract only what you can read with confidence.
- NEVER fabricate names, numbers, dates, amounts, or addresses.
- Confidence should reflect whether each field was clearly visible (high) or partially visible (low).

OUTPUT FORMAT (strict JSON, no markdown):
{
  "document_type": "<one of the 8 types>",
  "fields": {"<key>": "<value>", ...},
  "additional_fields": [{"key": "<label>", "value": "<extracted_value>"}, ...],
  "confidence_estimate": <0.0 to 1.0>
}
"""

# ---------------------------------------------------------------------------
# Config-driven values (previously hardcoded inline).
# ---------------------------------------------------------------------------
GROQ_MODELS: List[str] = list(getattr(
    settings, "GROQ_MODELS",
    ["openai/gpt-oss-120b", "openai/gpt-oss-20b"],
))
LLM_TIMEOUT_SECONDS: float = float(getattr(settings, "LLM_TIMEOUT_SECONDS", 45.0))
LLM_TEMPERATURE: float = float(getattr(settings, "LLM_TEMPERATURE", 0.1))
MAX_RATE_LIMIT_WAIT_SECONDS: float = float(getattr(settings, "MAX_RATE_LIMIT_WAIT_SECONDS", 90.0))

MIN_ACCEPTABLE_FIELDS = 1


@dataclass
class CallResult:
    """Outcome of a single provider call attempt."""
    data: Optional[Dict[str, Any]] = None
    # True if EVERY key configured for this provider is currently in
    # cooldown (rate-limited) - as opposed to a genuine failure (timeout,
    # bad response, no keys configured at all).
    keys_exhausted: bool = False
    retry_after_seconds: float = 0.0


def fallback_rule_extraction(ocr_text: str, filename_hint: str = "") -> Dict[str, Any]:
    text = clean_ocr_typos(ocr_text or "")
    combined = (text + " " + filename_hint).upper()

    doc_type = "generic"
    if any(k in combined for k in ["LEAVING CERTIFICATE", "TRANSFER CERTIFICATE", "LC", "SCHOOL LEAVING", "COLLEGE LEAVING"]):
        doc_type = "leaving_certificate"
    elif any(k in combined for k in ["MARKSHEET", "STATEMENT OF MARKS", "SECONDARY AND HIGHER SECONDARY", "EXAMINATION", "SSC", "HSC", "MAHARASHTRA STATE BOARD"]):
        doc_type = "education_marksheet"
    elif "PAN" in combined or "INCOME TAX" in combined or re.search(r"[A-Z]{5}[0-9]{4}[A-Z]", text):
        doc_type = "tax_id"
    elif any(k in combined for k in ["AADHAAR", "AADHAR", "GOVERNMENT OF INDIA", "भारत सरकार"]) or re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", text):
        doc_type = "identity_document"
    elif any(k in combined for k in ["STATEMENT", "ACCOUNT", "IFSC", "BANK"]):
        doc_type = "bank_statement"
    elif any(k in combined for k in ["PRESCRIPTION", "DR.", "DOCTOR", "RX", "HOSPITAL", "CLINIC"]):
        doc_type = "medical_prescription"

    fields: Dict[str, Any] = {}
    additional_fields: List[Dict[str, Any]] = []

    date_match = re.search(r"\b(\d{4}[/\-\s\.]\d{1,2}[/\-\s\.]\d{1,2}|\d{1,2}[/\-\s\.]\d{1,2}[/\-\s\.]\d{4})\b", text)
    if date_match:
        norm_d = normalize_date(date_match.group(1))
        fields["date_of_birth"] = norm_d
        fields["issue_date"] = norm_d
        fields["date"] = norm_d

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines:
        if any(k in line.upper() for k in ["NAME", "CANDIDATE", "STUDENT", "NAME OF STUDENT"]):
            parts = re.split(r"[:/]", line)
            val = parts[-1].strip() if len(parts) > 1 else line
            val = re.sub(r"(?i)(name|candidate|student)\s*[:/-]?\s*", "", val).strip()
            if len(val) > 3 and not val.isdigit():
                fields["candidate_name"] = clean_ocr_typos(val)
                fields["full_name"] = clean_ocr_typos(val)
                break

    if doc_type == "education_marksheet":
        board_match = re.search(
            r"([A-Z][A-Za-z\.\s]{5,80}?\b(?:BOARD|UNIVERSITY)\b[A-Za-z\.\s]*)",
            text,
        )
        if board_match:
            fields["board_university"] = re.sub(r"\s+", " ", board_match.group(1)).strip()
        seat_match = re.search(r"\b([A-Z]\d{6,7})\b", text)
        if seat_match:
            fields["seat_number"] = seat_match.group(1)
        fields["result_status"] = "PASSED" if "PASS" in combined else "COMPLETED"

    elif doc_type == "leaving_certificate":
        for line in lines:
            if any(k in line.upper() for k in ["COLLEGE", "SCHOOL", "VIDYALAYA", "INSTITUTE"]):
                fields["institution_name"] = line.strip()
                break
        year_match = re.search(r"\b(20\d{2})\b", text)
        if year_match:
            fields["year_of_leaving"] = year_match.group(1)
        class_match = re.search(r"\b(XII|XI|X|IX|12th|11th|10th|FY|SY|TY)\b", text, re.IGNORECASE)
        if class_match:
            fields["class_last_studied"] = class_match.group(1).upper()

    field_count = len(fields)
    confidence = min(0.55 + 0.05 * field_count, 0.80)

    return {
        "document_type": doc_type,
        "fields": fields,
        "additional_fields": additional_fields,
        "provider_used": "rule_based_fallback",
        "confidence_estimate": round(confidence, 2),
    }


def _extract_json_object(content: str) -> Optional[dict]:
    """Brace-depth-counting JSON extractor - robust to markdown fences and
    trailing commentary around the JSON object."""
    content = content.strip()
    content = re.sub(r"^```(json)?", "", content).strip()
    content = re.sub(r"```$", "", content).strip()

    start = content.find("{")
    if start == -1:
        return None

    depth = 0
    for i in range(start, len(content)):
        if content[i] == "{":
            depth += 1
        elif content[i] == "}":
            depth -= 1
            if depth == 0:
                candidate = content[start:i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    return None
    return None


def _postprocess_fields(parsed: Dict[str, Any]) -> None:
    fields = parsed.get("fields")
    if not isinstance(fields, dict):
        return
    if "date_of_birth" in fields and fields["date_of_birth"]:
        fields["date_of_birth"] = normalize_date(fields["date_of_birth"])
    if "address" in fields and fields["address"]:
        fields["address"] = repair_address_string(fields["address"])


def _is_usable_result(parsed: Optional[dict]) -> bool:
    return bool(
        parsed
        and isinstance(parsed, dict)
        and "document_type" in parsed
        and isinstance(parsed.get("fields"), dict)
        and len(parsed["fields"]) >= MIN_ACCEPTABLE_FIELDS
    )


class LLMAdapter:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS)

    async def _call_openai_compatible(
        self,
        base_url: str,
        key_pool: ApiKeyPool,
        model: str,
        ocr_text: str,
        filename_hint: str,
        provider_label: str,
    ) -> CallResult:
        """
        Shared call path for any OpenAI-compatible chat/completions API
        (Groq, Gemini, NVIDIA NIM), with automatic key rotation: if the key
        currently in use gets rate-limited (429), it's put in cooldown and
        the next key in the pool is tried immediately - the caller/user
        never sees a gap unless every key for this provider is cooling
        down at once.
        """
        if not key_pool.has_keys():
            return CallResult(data=None, keys_exhausted=False)

        url = f"{base_url.rstrip('/')}/chat/completions"
        cleaned_input = clean_ocr_typos(ocr_text)
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": UNIVERSAL_EXTRACTION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Filename hint: {filename_hint}\nOCR Text:\n\n{cleaned_input}\n\n"
                        "Extract all structured data and classify the exact document_type. "
                        "Return strict JSON."
                    ),
                },
            ],
            "temperature": LLM_TEMPERATURE,
        }

        attempts = len(key_pool.keys)
        for _ in range(attempts):
            acquired = await key_pool.acquire()
            if acquired is None:
                # every key for this provider is currently cooling down
                return CallResult(
                    data=None,
                    keys_exhausted=True,
                    retry_after_seconds=key_pool.seconds_until_next_available(),
                )
            idx, api_key = acquired
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

            try:
                resp = await self.client.post(url, headers=headers, json=payload)
            except httpx.TimeoutException:
                logger.warning("[%s:%s] key #%d request timed out after %.1fs", provider_label, model, idx + 1, LLM_TIMEOUT_SECONDS)
                return CallResult(data=None)
            except httpx.HTTPError as e:
                logger.warning("[%s:%s] key #%d request failed: %s", provider_label, model, idx + 1, e)
                return CallResult(data=None)

            if resp.status_code == 429:
                retry_after = parse_retry_after(resp.headers)
                key_pool.mark_rate_limited(idx, retry_after)
                logger.warning(
                    "[%s:%s] key #%d hit rate limit - rotating to next key (retry_after=%s)",
                    provider_label, model, idx + 1, retry_after,
                )
                continue  # try the next key in the pool immediately

            if resp.status_code != 200:
                logger.warning(
                    "[%s:%s] key #%d non-200 response: status=%s body=%s",
                    provider_label, model, idx + 1, resp.status_code, resp.text[:500],
                )
                return CallResult(data=None)

            try:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, ValueError) as e:
                logger.warning("[%s:%s] key #%d malformed response shape: %s", provider_label, model, idx + 1, e)
                return CallResult(data=None)

            parsed = _extract_json_object(content)
            if not _is_usable_result(parsed):
                logger.info("[%s:%s] key #%d response had no usable structured fields", provider_label, model, idx + 1)
                return CallResult(data=None)

            _postprocess_fields(parsed)
            parsed["provider_used"] = f"{provider_label}:{model}"
            model_conf = parsed.get("confidence_estimate")
            if not isinstance(model_conf, (int, float)) or not (0.0 <= model_conf <= 1.0):
                parsed["confidence_estimate"] = 0.9
            return CallResult(data=parsed)

        # Every key in the pool got rate-limited during this loop.
        return CallResult(
            data=None,
            keys_exhausted=True,
            retry_after_seconds=key_pool.seconds_until_next_available(),
        )

    async def call_groq(self, ocr_text: str, filename_hint: str = "") -> CallResult:
        pool = get_pool("groq")
        last_exhaustion = CallResult(data=None)
        for model in GROQ_MODELS:
            result = await self._call_openai_compatible(
                base_url=settings.GROQ_BASE_URL, key_pool=pool, model=model,
                ocr_text=ocr_text, filename_hint=filename_hint, provider_label="groq",
            )
            if result.data is not None:
                return result
            if result.keys_exhausted:
                # No point trying the next model with the same exhausted pool.
                return result
            last_exhaustion = result
        return last_exhaustion

    async def call_gemini(self, ocr_text: str, filename_hint: str = "") -> CallResult:
        pool = get_pool("gemini")
        return await self._call_openai_compatible(
            base_url=settings.GEMINI_BASE_URL, key_pool=pool, model=settings.GEMINI_MODEL,
            ocr_text=ocr_text, filename_hint=filename_hint, provider_label="gemini",
        )

    async def call_nvidia(self, ocr_text: str, filename_hint: str = "") -> CallResult:
        pool = get_pool("nvidia")
        return await self._call_openai_compatible(
            base_url=settings.NVIDIA_BASE_URL, key_pool=pool, model=settings.NVIDIA_MODEL,
            ocr_text=ocr_text, filename_hint=filename_hint, provider_label="nvidia",
        )

    async def extract_structured(
        self,
        ocr_text: str,
        image_bytes: Optional[bytes] = None,
        filename_hint: str = "",
    ) -> Dict[str, Any]:
        """
        Executes multi-provider document extraction in the order given by
        settings.provider_priority_list (default: groq -> gemini -> nvidia),
        each with automatic multi-key rotation on rate limits.

        Only if EVERY provider tried has EVERY one of its keys currently
        rate-limited do we return a `rate_limited` result instead of the
        rule-based fallback - a genuine "come back in a bit" situation
        rather than "this document is hard to read". The caller (worker.py)
        can wait out the cooldown and retry once before giving up.
        """
        callers = {
            "groq": self.call_groq,
            "gemini": self.call_gemini,
            "nvidia": self.call_nvidia,
        }

        if ocr_text:
            any_provider_attempted = False
            all_exhausted = True
            max_retry_after = 0.0

            for provider in settings.provider_priority_list:
                caller = callers.get(provider)
                if caller is None:
                    continue
                pool = get_pool(provider)
                if not pool.has_keys():
                    continue  # provider not configured - skip silently, don't count as "exhausted"

                any_provider_attempted = True
                result: CallResult = await caller(ocr_text, filename_hint)
                if result.data is not None:
                    return result.data
                if result.keys_exhausted:
                    max_retry_after = max(max_retry_after, result.retry_after_seconds)
                else:
                    # a genuine failure (timeout/bad response), not a rate
                    # limit - so this isn't a "wait it out" situation.
                    all_exhausted = False

            if any_provider_attempted and all_exhausted:
                return {
                    "document_type": None,
                    "fields": {},
                    "additional_fields": [],
                    "provider_used": "rate_limited",
                    "confidence_estimate": 0.0,
                    "rate_limited": True,
                    "retry_after_seconds": round(max_retry_after, 1),
                }

        return fallback_rule_extraction(ocr_text, filename_hint)


llm_adapter = LLMAdapter()
