"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  Circle,
  XCircle,
  Loader2,
  RotateCw,
  AlertTriangle,
  FileSearch,
  ScanEye,
  Sparkles,
  Type,
  BrainCircuit,
  ShieldCheck,
  Timer,
  Zap,
} from "lucide-react";

// ── Stage definitions ───────────────────────────────────────────────────
// Mirrors the exact `stage` strings the backend writes via
// DatabaseManager.update_job() in worker.py, in pipeline order.
const STAGES: Array<{ key: string; label: string; hint: string; icon: React.ComponentType<any> }> = [
  { key: "validating", label: "Validating Upload", hint: "Reading the source file", icon: FileSearch },
  { key: "quality_analysis", label: "Quality Analysis", hint: "Scoring resolution, blur, brightness, tilt", icon: ScanEye },
  { key: "enhancing", label: "Image Enhancement", hint: "Deskew, denoise, contrast & sharpening", icon: Sparkles },
  { key: "ocr_running", label: "Multilingual OCR", hint: "English / Hindi / Marathi text recognition", icon: Type },
  { key: "extracting", label: "AI Field Extraction", hint: "Structuring fields with LLM providers", icon: BrainCircuit },
  { key: "validating_fields", label: "Field Validation", hint: "Confidence scoring & cross-checks", icon: ShieldCheck },
];

type StageStatus = "done" | "active" | "pending" | "failed" | "skipped" | "waiting";

interface StageHistoryEntry {
  stage: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  error_code?: string | null;
}

interface ActiveJob {
  id: string;
  status: string; // "processing" | "completed" | "failed"
  stage: string;
  progress: number;
  attempts: number;
  error_code?: string | null;
  error_message?: string | null;
  retry_after_seconds?: number | null;
  resume_at?: string | null;
  stage_history: StageHistoryEntry[];
  created_at: string;
}

interface PipelinePanelProps {
  doc: {
    id: string;
    filename_safe: string;
    status: string;
    quality_score?: number | null;
    active_job?: ActiveJob;
  };
  sessionToken?: string | null;
  onRetried?: () => void;
}

function fmtDuration(ms: number): string {
  if (ms < 1000) return "<1s";
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  const rem = Math.round(s % 60);
  return `${m}m ${rem}s`;
}

function lastEntryFor(history: StageHistoryEntry[], key: string): StageHistoryEntry | undefined {
  for (let i = history.length - 1; i >= 0; i--) {
    if (history[i].stage === key) return history[i];
  }
  return undefined;
}

const ERROR_COPY: Record<string, { title: string; detail: string }> = {
  JOB_TIMEOUT: {
    title: "Processing took longer than expected",
    detail: "This can happen on large or high-resolution files. Nothing is wrong with the document itself.",
  },
  PROCESSING_EXCEPTION: {
    title: "An unexpected error interrupted processing",
    detail: "A transient error occurred mid-pipeline. Retrying usually resolves this.",
  },
  PROVIDERS_RATE_LIMITED: {
    title: "AI extraction providers were busy",
    detail: "All configured API keys were temporarily rate-limited. Retrying now that things have cooled down usually works.",
  },
  QUALITY_TOO_LOW: {
    title: "Image quality too low to read reliably",
    detail: "The scan is too dark, blurry, or low-resolution for automated extraction. Please upload a clearer photo or scan.",
  },
  FILE_READ_ERROR: {
    title: "Couldn't read the uploaded file",
    detail: "The stored file may be corrupted or missing. Please re-upload.",
  },
};

export const PipelinePanel: React.FC<PipelinePanelProps> = ({ doc, sessionToken, onRetried }) => {
  const job = doc.active_job;
  const [nowTick, setNowTick] = useState(Date.now());
  const [retrying, setRetrying] = useState(false);

  const isLive = job?.status === "processing";
  const isFailed = doc.status === "processing_failed";
  const isCompleted = !isLive && !isFailed;

  // Live ticking clock while the job is actively processing.
  useEffect(() => {
    if (!isLive) return;
    const t = setInterval(() => setNowTick(Date.now()), 1000);
    return () => clearInterval(t);
  }, [isLive]);

  const history = job?.stage_history || [];

  const totalElapsedMs = useMemo(() => {
    if (!job?.created_at) return 0;
    const start = new Date(job.created_at).getTime();
    const end = isLive ? nowTick : (history.length ? new Date(history[history.length - 1].ended_at || job.created_at).getTime() : nowTick);
    return Math.max(0, end - start);
  }, [job?.created_at, isLive, nowTick, history]);

  const stageStatus = (key: string): { status: StageStatus; entry?: StageHistoryEntry } => {
    const entry = lastEntryFor(history, key);
    if (!entry) return { status: "pending" };
    if (entry.error_code) return { status: "failed", entry };
    if (entry.ended_at) return { status: "done", entry };
    if (job?.status === "failed") return { status: "failed", entry };
    return { status: "active", entry };
  };

  const isRateLimited = job?.stage === "rate_limited";
  const isFastRetry = job?.stage === "retrying_fast_mode" || (job?.attempts || 1) > 1;

  const resumeCountdown = useMemo(() => {
    if (!isRateLimited || !job?.resume_at) return null;
    const diff = Math.max(0, Math.round((new Date(job.resume_at).getTime() - nowTick) / 1000));
    return diff;
  }, [isRateLimited, job?.resume_at, nowTick]);

  const handleRetry = async () => {
    setRetrying(true);
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (sessionToken) headers["Authorization"] = `Bearer ${sessionToken}`;
      await fetch(`/api/v1/documents/${doc.id}/retry`, { method: "POST", headers });
      onRetried?.();
    } catch (e) {
      console.error("Retry failed:", e);
    } finally {
      setRetrying(false);
    }
  };

  const errCode = job?.error_code || "PROCESSING_EXCEPTION";
  const errCopy = ERROR_COPY[errCode] || { title: "Processing failed", detail: job?.error_message || "Please try again." };

  return (
    <div className="flex flex-col space-y-3">
      {/* Header summary */}
      <div className="panel rounded-md p-3 border border-ink-rule space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {isLive && <Loader2 className="h-4 w-4 text-verify animate-spin" />}
            {isCompleted && <CheckCircle2 className="h-4 w-4 text-verify" />}
            {isFailed && <XCircle className="h-4 w-4 text-signal-red" />}
            <span className="text-xs font-bold text-paper-100">
              {isLive ? "Processing Pipeline" : isFailed ? "Pipeline Stalled" : "Pipeline Complete"}
            </span>
          </div>
          <div className="flex items-center space-x-1 text-[10px] text-paper-500 font-mono tabular">
            <Timer className="h-3 w-3" />
            <span>{fmtDuration(totalElapsedMs)}</span>
          </div>
        </div>

        {/* Overall progress bar */}
        <div className="h-1.5 w-full rounded-full bg-ink overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              isFailed ? "bg-signal-red" : isCompleted ? "bg-verify" : "bg-verify animate-pulse-subtle"
            }`}
            style={{ width: `${isCompleted ? 100 : Math.max(4, job?.progress ?? 0)}%` }}
          />
        </div>

        {/* Fast-mode / retry banner */}
        {isFastRetry && !isFailed && (
          <div className="flex items-center space-x-1.5 text-[10px] text-signal-amber bg-signal-amber/10 border border-signal-amber/30 rounded px-2 py-1">
            <Zap className="h-3 w-3 flex-shrink-0" />
            <span>
              Auto-retrying in fast mode (attempt {job?.attempts || 2}) — a first pass took too long, so heavy
              image enhancement is being skipped this time to guarantee a result.
            </span>
          </div>
        )}

        {/* Rate-limited banner */}
        {isRateLimited && (
          <div className="flex items-center space-x-1.5 text-[10px] text-signal-amber bg-signal-amber/10 border border-signal-amber/30 rounded px-2 py-1">
            <RotateCw className="h-3 w-3 flex-shrink-0 animate-spin" />
            <span>
              AI providers are briefly rate-limited — auto-retrying{resumeCountdown !== null ? ` in ${resumeCountdown}s` : ""}.
              A local fallback extractor will run instead if this doesn't clear.
            </span>
          </div>
        )}
      </div>

      {/* Stepper */}
      <div className="panel rounded-md border border-ink-rule divide-y divide-ink-rule">
        {STAGES.map((s) => {
          const { status, entry } = stageStatus(s.key);
          const Icon = s.icon;
          const durationLabel =
            status === "done" && entry?.started_at && entry?.ended_at
              ? fmtDuration(new Date(entry.ended_at).getTime() - new Date(entry.started_at).getTime())
              : null;

          return (
            <div key={s.key} className="flex items-start space-x-3 px-3 py-2.5">
              {/* Status glyph */}
              <div className="flex-shrink-0 pt-0.5">
                {status === "done" && <CheckCircle2 className="h-4 w-4 text-verify" />}
                {status === "active" && <Loader2 className="h-4 w-4 text-verify animate-spin" />}
                {status === "failed" && <XCircle className="h-4 w-4 text-signal-red" />}
                {status === "pending" && <Circle className="h-4 w-4 text-paper-700" />}
                {status === "skipped" && <Circle className="h-4 w-4 text-paper-500" strokeDasharray="2 2" />}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-1.5">
                    <Icon className={`h-3.5 w-3.5 ${
                      status === "done" ? "text-verify" :
                      status === "active" ? "text-paper-100" :
                      status === "failed" ? "text-signal-red" : "text-paper-700"
                    }`} />
                    <span className={`text-xs font-semibold ${
                      status === "pending" ? "text-paper-500" :
                      status === "failed" ? "text-signal-red" : "text-paper-100"
                    }`}>
                      {s.label}
                    </span>
                  </div>
                  {durationLabel && (
                    <span className="text-[10px] font-mono text-paper-500 tabular">{durationLabel}</span>
                  )}
                  {status === "active" && (
                    <span className="text-[10px] font-mono text-verify tabular">running…</span>
                  )}
                </div>
                <span className="text-[10px] text-paper-500">{s.hint}</span>
                {status === "failed" && entry?.error_code && (
                  <div className="mt-1 text-[10px] text-signal-red">{ERROR_COPY[entry.error_code]?.title || entry.error_code}</div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Failure detail + retry CTA */}
      {isFailed && (
        <div className="rounded-md border border-signal-red/40 bg-signal-red/10 p-3 space-y-2.5">
          <div className="flex items-start space-x-2">
            <AlertTriangle className="h-4 w-4 text-signal-red flex-shrink-0 mt-0.5" />
            <div>
              <div className="text-xs font-bold text-signal-red">{errCopy.title}</div>
              <div className="text-[11px] text-paper-300 mt-0.5">{errCopy.detail}</div>
              {typeof doc.quality_score === "number" && doc.quality_score > 0 && errCode !== "QUALITY_TOO_LOW" && (
                <div className="text-[10px] text-paper-500 mt-1">
                  Note: this document scored {doc.quality_score}/100 on quality — the file itself looks fine.
                </div>
              )}
            </div>
          </div>
          <button
            onClick={handleRetry}
            disabled={retrying}
            className="w-full py-2 rounded-md font-bold text-xs verify-gradient text-ink hover:brightness-110 transition flex items-center justify-center space-x-2 disabled:opacity-60"
          >
            {retrying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RotateCw className="h-3.5 w-3.5" />}
            <span>{retrying ? "Retrying…" : "Retry Processing (no re-upload needed)"}</span>
          </button>
        </div>
      )}

      {isCompleted && job && (
        <div className="text-[10px] text-paper-500 text-center pt-1">
          Completed in {fmtDuration(totalElapsedMs)}
          {(job.attempts || 1) > 1 ? ` after ${job.attempts} attempts` : ""}.
        </div>
      )}
    </div>
  );
};
