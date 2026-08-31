# DocXtract: Pixels Gone Rogue — The Document Rescue

> **Enterprise Multilingual Document Rescue & Intelligent Extraction Workspace for Digital-Lending Review**

DocXtract converts poor-quality, blurry, tilted, and low-contrast photographed document images into reviewable, structured, validated, and exportable data with **100% auditability** and **fail-closed uncertainty guarantees**.

---

## Key Highlights & Architecture

1. **Multilingual Document Rescue**:
   - **Supported Languages**: English, Hindi, and Marathi (Devanagari script support).
   - **OpenCV Enhancement Pipeline**: Bilateral denoising, tilt estimation and adaptive deskewing, CLAHE contrast normalization, and unsharp masking.
   - **Original Preservation**: Source documents are byte-preserved in private storage; enhancement creates a separate verifiable artifact.

2. **Deterministic Field-Level Confidence Formula (PRD P0.7)**:
   $$\text{base} = 0.45 \cdot \text{ocr\_confidence} + 0.35 \cdot \text{structuring\_confidence} + 0.20 \cdot \text{validation\_score}$$
   $$\text{quality\_factor} = \text{clamp}(\text{quality\_score} / 100, 0.50, 1.00)$$
   $$\text{field\_score} = \text{round}(100 \cdot \text{base} \cdot \text{quality\_factor})$$
   - **Color-Coded Confidence**: Green (85–100), Yellow (60–84: Review Recommended), Red (0–59: Attention Required).
   - **Strict Hard Caps**: Missing values = `0`, format validation failure = max `59`, ambiguous OCR = max `59`.

3. **Multi-Provider LLM Extraction with Priority Fallback**:
   - **Google Gemini**: `gemini-3.7-flash` structured output.
   - **Groq**: `openai/gpt-oss-120b` / `llama-3.3-70b-versatile` low-latency JSON extraction.
   - **NVIDIA NIM**: `meta/llama-3.1-70b-instruct` enterprise reasoning.
   - **Deterministic Fallback**: Regex-based domain extractor ensures 100% uptime even if all LLMs are unreachable.

4. **Security & Supabase Row-Level Security (RLS)**:
   - Supabase Postgres DB with RLS policies enabled on all 8 tables.
   - Private storage bucket with short-lived signed URLs (300s TTL).
   - Server-side secrets protection (No API keys or database passwords exposed in client bundles).
   - Audit trail tracking without storing plaintext PII values.

5. **Multi-Format Export Engine**:
   - **Executive PDF**: Formatted case summary with confidence badges and audit history.
   - **Structured Excel (.xlsx)**: Multi-sheet workbook with summary and per-document breakdown.
   - **Canonical JSON**: Full machine-readable export with complete confidence tree.
   - **Unicode CSV**: UTF-8 BOM encoding preserving English, Hindi, and Marathi text.

6. **P1 Innovation Features**:
   - **Grounded Document Q&A Assistant**: Answers queries strictly citing verified document IDs.
   - **Cross-Document Consistency Checking**: Compares names, DOBs, IDs, and addresses across PAN, Aadhaar, and Bank Statements.
   - **Multilingual TTS Read-Aloud**: Browser Web Speech API narration in English, Hindi, and Marathi.
   - **Interactive 4-Step Guided Walkthrough**: Built-in judge tour and 1-click seeded demo fixtures.

---

## 2-Minute Judge Evaluation Walkthrough

1. Open the web interface at `http://localhost:3000`.
2. Click **"Load Seeded Judge Demo Batch (EN/HI/MR)"**.
3. Observe the asynchronous progress bar transitioning across stages (`validating` $\rightarrow$ `quality_analysis` $\rightarrow$ `enhancing` $\rightarrow$ `ocr_running` $\rightarrow$ `extracting` $\rightarrow$ `completed`).
4. Inspect the **Side-by-Side Synchronized Comparison Viewer**:
   - Notice how the tilted, blurry PAN card and Marathi electric bill are enhanced with OpenCV deskewing and CLAHE contrast normalization.
5. Click **"Filter Attention (Yellow/Red)"** to isolate fields needing review.
6. Click the edit icon on any field, update the value, and notice the instant recalculation of the confidence score and reason codes.
7. Click **"Approve & Mark as Verified"**.
8. Click **"Export Case (4 Formats)"** to generate and download the PDF, XLSX, JSON, and CSV exports.

---

## Running the Application Locally

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 2. Backend Setup
```bash
# Navigate to project root
cd c:\Users\VAISHNAVI\OneDrive\Desktop\DocXtract

# Install backend dependencies
pip install fastapi uvicorn pydantic pydantic-settings httpx numpy opencv-python pillow reportlab openpyxl python-multipart supabase pytest

# Run backend automated test suite
python -m pytest backend/tests

# Start FastAPI server on port 8000
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Frontend Setup
```bash
cd c:\Users\VAISHNAVI\OneDrive\Desktop\DocXtract\frontend

# Install dependencies
npm install

# Start Next.js development server on port 3000
npm run dev
```

---

## Health & Diagnostics Endpoints

- **`GET /health/live`**: Checks process liveness.
- **`GET /health/ready`**: Verifies Supabase DB connection and lists active LLM providers (`["gemini", "groq", "nvidia"]`).
