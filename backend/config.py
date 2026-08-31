import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_ENV: str = "development"
    APP_BASE_URL: str = "http://localhost:8000"
    FRONTEND_BASE_URL: str = "http://localhost:3000"
    API_BASE_URL: str = "http://localhost:8000/api/v1"
    COOKIE_DOMAIN: str = "localhost"
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Supabase
    SUPABASE_URL: str = "https://vuoustiwrjdbqdxbaoka.supabase.co"
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "document-private"

    # Database
    DATABASE_URL: str = ""

    # LLM Providers
    # Each *_API_KEY stays as a single-key fallback for backward compatibility.
    # *_API_KEYS (plural) accepts a comma-separated list - e.g. your key plus
    # teammates' keys for the same provider - so the pipeline can rotate to
    # the next key automatically when one hits its rate limit, instead of
    # the whole extraction stopping. See backend/pipeline/key_pool.py.
    GEMINI_API_KEY: str = ""
    GEMINI_API_KEYS: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    GROQ_API_KEY: str = ""
    GROQ_API_KEYS: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    # Ordered list tried in sequence: best quality first, cheaper/faster fallback second.
    GROQ_MODELS: List[str] = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]

    # Per-provider LLM call timeout (was hardcoded at 25s, causing premature
    # timeouts on slower documents/models).
    LLM_TIMEOUT_SECONDS: float = 45.0
    LLM_TEMPERATURE: float = 0.1

    NVIDIA_API_KEY: str = ""
    NVIDIA_API_KEYS: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "meta/llama-3.2-90b-vision-instruct"

    # How long a key sits in cooldown after a 429 (rate limit) response, if
    # the provider didn't send a Retry-After header telling us the exact time.
    KEY_COOLDOWN_SECONDS: float = 60.0
    # Hard cap on how long the worker will wait in-line for a cooldown to
    # clear before giving up and marking the job for manual retry. Keeps one
    # unlucky document from blocking a worker slot indefinitely (see
    # MAX_CONCURRENT_JOBS) if every key of every provider is exhausted at once.
    MAX_RATE_LIMIT_WAIT_SECONDS: float = 90.0

    # Provider Routing
    LLM_PROVIDER_PRIORITY: str = "groq,gemini,nvidia"
    LLM_REQUEST_TIMEOUT_SECONDS: int = 30
    LLM_MAX_ATTEMPTS: int = 3

    # Processing & Limits
    MAX_FILE_SIZE_MB: int = 20
    MAX_FILES_PER_BATCH: int = 20
    JOB_LEASE_SECONDS: int = 900
    JOB_MAX_RETRIES: int = 2

    # Bounded-concurrency document processing queue (see backend/job_queue.py).
    # Prevents multiple simultaneously-uploaded documents from contending for
    # the same CPU (OCR) / network (LLM) resources, which previously caused
    # later documents in a batch to be slow and/or produce incomplete extractions.
    MAX_CONCURRENT_JOBS: int = 2

    # ── Job timeout is now SIZE-AWARE instead of one flat number ───────────
    JOB_TIMEOUT_BASE_SECONDS: float = 300.0
    JOB_TIMEOUT_SECONDS_PER_MB: float = 30.0
    JOB_TIMEOUT_MAX_SECONDS: float = 600.0
    # Backward-compat alias some code/tests may still read directly.
    JOB_TIMEOUT_SECONDS: float = 300.0

    # If a job times out (or throws) and has retries left, it is automatically
    # re-queued once in "fast mode" (skips the heavy enhancement pass, uses a
    # tighter LLM budget) instead of being shown to the user as failed.
    JOB_AUTO_RETRY_FAST_MODE: bool = True

    # Per-stage soft budgets used inside worker.py (2-3 minutes for deep processing).
    STAGE_TIMEOUT_QUALITY_SECONDS: float = 45.0
    STAGE_TIMEOUT_ENHANCEMENT_SECONDS: float = 60.0
    STAGE_TIMEOUT_OCR_SECONDS: float = 180.0

    SIGNED_URL_TTL_SECONDS: int = 300
    RETENTION_DAYS: int = 7 

    # OCR / Image processing
    # Maximum pixel dimension (longest side) passed to EasyOCR on CPU.
    # 1300px provides crisp character recognition while keeping CPU runtime fast.
    OCR_MAX_IMAGE_DIM: int = 1300
    # DPI used when rasterizing a PDF page to an image before OCR.
    # 200 DPI gives ~1700×2200px for an A4 page (safe for EasyOCR CPU).
    # Set higher (e.g. 300) if running on a GPU machine with more memory.
    PDF_RENDER_DPI: int = 200

    # n8n & Proxy
    N8N_WEBHOOK_URL: str = ""
    N8N_WEBHOOK_SECRET: str = ""
    INTERNAL_WEBHOOK_SECRET: str = ""
    RATE_LIMIT_PER_IP: int = 120
    RATE_LIMIT_PER_USER: int = 300

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.CORS_ALLOWED_ORIGINS:
            return ["*"]
        return [o.strip() for o in self.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def provider_priority_list(self) -> List[str]:
        if not self.LLM_PROVIDER_PRIORITY:
            return ["groq", "gemini", "nvidia"]
        return [p.strip().lower() for p in self.LLM_PROVIDER_PRIORITY.split(",") if p.strip()]

    def _keys_list(self, plural_val: str, singular_val: str) -> List[str]:
        """Parse a comma-separated key list; fall back to the single-key
        setting if the plural one wasn't provided. Order is preserved, so
        the first key in the list is tried first (your own key first, then
        teammates' keys, if you list them in that order)."""
        keys = [k.strip() for k in (plural_val or "").split(",") if k.strip()]
        if not keys and singular_val:
            keys = [singular_val.strip()]
        return keys

    @property
    def gemini_api_keys_list(self) -> List[str]:
        return self._keys_list(self.GEMINI_API_KEYS, self.GEMINI_API_KEY)

    @property
    def groq_api_keys_list(self) -> List[str]:
        return self._keys_list(self.GROQ_API_KEYS, self.GROQ_API_KEY)

    @property
    def nvidia_api_keys_list(self) -> List[str]:
        return self._keys_list(self.NVIDIA_API_KEYS, self.NVIDIA_API_KEY)

settings = Settings()