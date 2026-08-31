"""
Quick connectivity test for the Groq API.
Reads credentials from environment / .env file (never hardcodes keys).
"""
import httpx
from backend.config import settings

if not settings.GROQ_API_KEY:
    print("[test_groq] GROQ_API_KEY not set in environment or .env — skipping.")
    exit(0)

client = httpx.Client(timeout=15)
model = settings.GROQ_MODELS[0] if settings.GROQ_MODELS else settings.GROQ_MODEL

resp = client.post(
    f"{settings.GROQ_BASE_URL.rstrip('/')}/chat/completions",
    headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
    json={
        "model": model,
        "messages": [{"role": "user", "content": (
            'Extract Aadhaar number 7708 2761 0853 and Name Rajesh Sharma. '
            'Return JSON: {"document_type": "identity_document", '
            '"fields": {"document_number": "7708 2761 0853", "full_name": "Rajesh Sharma"}}'
        )}]
    }
)

print(f"[test_groq] Status: {resp.status_code}")
if resp.status_code == 200:
    print("[test_groq] Response:", resp.json()["choices"][0]["message"]["content"])
else:
    print("[test_groq] Error:", resp.text[:300])
