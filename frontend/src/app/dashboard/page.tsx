"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { Header } from "@/components/Header";
import { CompareViewer } from "@/components/CompareViewer";
import { FieldEditor } from "@/components/FieldEditor";
import { ExportModal } from "@/components/ExportModal";
import { ConsistencyPanel } from "@/components/ConsistencyPanel";
import { QAAssistant } from "@/components/QAAssistant";
import { GuidedTour } from "@/components/GuidedTour";
import { PipelinePanel } from "@/components/PipelinePanel";
import gsap from "gsap";
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  Sparkles,
  Download,
  Filter,
  Check,
  Volume2,
  VolumeX,
  Loader2
} from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [authChecking, setAuthChecking] = useState(true);

  const [caseId, setCaseId] = useState<string | null>(null);
  const [caseData, setCaseData] = useState<any>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [extractions, setExtractions] = useState<any[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [filterAttention, setFilterAttention] = useState(false);
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [isTourOpen, setIsTourOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSeeding, setIsSeeding] = useState(false);
  const [activeTab, setActiveTab] = useState<"fields" | "consistency" | "qa" | "pipeline">("fields");
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [uploadLanguage, setUploadLanguage] = useState("Mixed");
  const [dragActive, setDragActive] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const workspaceRef = useRef<HTMLDivElement>(null);
  const hasRevealedWorkspaceRef = useRef(false);
  const prevSelectedDocIdRef = useRef<string | null>(null);

  // Auto-switch to "pipeline" tab when a processing or failed document is selected
  useEffect(() => {
    if (selectedDocId && selectedDocId !== prevSelectedDocIdRef.current) {
      const doc = documents.find((d) => d.id === selectedDocId);
      if (doc && (doc.status === "processing" || doc.status === "processing_failed")) {
        setActiveTab("pipeline");
      }
      prevSelectedDocIdRef.current = selectedDocId;
    }
  }, [selectedDocId, documents]);

  // Auto-switch back to "fields" tab when document completes processing
  useEffect(() => {
    const doc = documents.find((d) => d.id === selectedDocId);
    if (activeTab === "pipeline" && doc && doc.status !== "processing" && doc.status !== "processing_failed") {
      setActiveTab("fields");
    }
  }, [documents, selectedDocId, activeTab]);

  // Authentication check & session tracking
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        router.push("/login");
      } else {
        setSessionToken(session.access_token);
        setAuthChecking(false);
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session) {
        router.push("/login");
      } else {
        setSessionToken(session.access_token);
        setAuthChecking(false);
      }
    });

    return () => subscription.unsubscribe();
  }, [router]);

  // Auth fetch helper
  const authFetch = async (url: string, options: RequestInit = {}) => {
    const headers = new Headers(options.headers || {});
    if (sessionToken) {
      headers.set("Authorization", `Bearer ${sessionToken}`);
    }
    return fetch(url, { ...options, headers });
  };

  // Poll Case Data & Status
  const fetchCase = async (id: string) => {
    try {
      const res = await authFetch(`/api/v1/cases/${id}`);
      if (res.ok) {
        const data = await res.json();
        setCaseData(data.case);
        setDocuments(data.documents || []);
        setExtractions(data.extractions || []);
        setSelectedDocId((prev) => {
          if (prev && (data.documents || []).some((d: any) => d.id === prev)) {
            return prev; // Preserve user's manually clicked document!
          }
          return data.documents && data.documents.length > 0 ? data.documents[0].id : null;
        });
      }
    } catch (err) {
      console.error("Error polling case:", err);
    }
  };

  useEffect(() => {
    if (!caseId || authChecking) return;
    fetchCase(caseId);
    const interval = setInterval(() => {
      fetchCase(caseId);
    }, 2500);
    return () => clearInterval(interval);
  }, [caseId, authChecking, sessionToken]);

  // Seed Demo Case
  const handleSeedDemo = async () => {
    setIsSeeding(true);
    try {
      const res = await authFetch("/api/v1/cases/seed_demo", { method: "POST" });
      const data = await res.json();
      if (data.case_id) {
        setCaseId(data.case_id);
        setTimeout(() => fetchCase(data.case_id), 800);
      }
    } catch (err) {
      console.error("Demo seeding error:", err);
    } finally {
      setIsSeeding(false);
    }
  };

  // Upload Files
  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setIsUploading(true);

    let activeCaseId = caseId;
    if (!activeCaseId) {
      const caseRes = await authFetch("/api/v1/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: "Lending Review Case" })
      });
      const caseJson = await caseRes.json();
      activeCaseId = caseJson.case.id;
      setCaseId(activeCaseId);
    }

    const formData = new FormData();
    Array.from(files).forEach((f) => formData.append("files", f));
    formData.append("language_mode", uploadLanguage);

    try {
      const res = await authFetch(`/api/v1/cases/${activeCaseId}/documents`, {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (data.accepted && data.accepted.length > 0) {
        setSelectedDocId(data.accepted[0].document_id);
      }
      if (activeCaseId) fetchCase(activeCaseId);
    } catch (err) {
      console.error("Upload error:", err);
    } finally {
      setIsUploading(false);
    }
  };

  // Save Inline Field Edit
  const handleSaveField = async (fieldKey: string, newValue: string) => {
    const currentExt = extractions.find((e) => e.document_id === selectedDocId);
    if (!currentExt) return;

    await authFetch(`/api/v1/extractions/${currentExt.id}/fields/${fieldKey}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value: newValue, review_state: "reviewed" })
    });

    if (caseId) fetchCase(caseId);
  };

  // Approve Document
  const handleApproveDocument = async () => {
    const currentExt = extractions.find((e) => e.document_id === selectedDocId);
    if (!currentExt) return;

    await authFetch(`/api/v1/extractions/${currentExt.id}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ allow_unresolved: true })
    });

    if (caseId) fetchCase(caseId);
  };

  // Retry Document (Fast Mode)
  const handleRetryDocument = async (docId: string) => {
    try {
      await authFetch(`/api/v1/documents/${docId}/retry`, {
        method: "POST"
      });
      if (caseId) fetchCase(caseId);
    } catch (err) {
      console.error("Retry error:", err);
    }
  };

  // TTS Read-Aloud Summary
  const handleSpeakSummary = () => {
    if (!window.speechSynthesis) return;

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    const currentExt = extractions.find((e) => e.document_id === selectedDocId);
    if (!currentExt || !currentExt.fields) return;

    const fields = currentExt.fields;
    const summaryText = `Document type is ${currentExt.schema_name}. Extracted fields: ` +
      fields.map((f: any) => `${f.label} is ${f.normalized_value || f.raw_value || 'missing'}`).join(". ");

    const utterance = new SpeechSynthesisUtterance(summaryText);
    utterance.rate = 0.95;
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
    setIsSpeaking(true);
  };

  // --- One purposeful motion moment: when the workspace first replaces --
  // the empty dropzone (state change: no documents -> documents present),
  // it settles in rather than popping in instantly. Guarded by a ref so
  // it fires exactly once per session, not on every 2.5s poll re-render -
  // a productivity tool should never re-animate on background refresh.
  useEffect(() => {
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) return;
    if (documents.length > 0 && !hasRevealedWorkspaceRef.current && workspaceRef.current) {
      hasRevealedWorkspaceRef.current = true;
      gsap.fromTo(
        workspaceRef.current,
        { autoAlpha: 0, y: 10 },
        { autoAlpha: 1, y: 0, duration: 0.45, ease: "power2.out" }
      );
    }
  }, [documents.length]);

  if (authChecking) {
    return (
      <div className="min-h-screen bg-ink flex flex-col items-center justify-center text-paper-300 space-y-3">
        <Loader2 className="h-8 w-8 text-verify animate-spin" />
        <p className="text-xs font-semibold tracking-wide text-paper-500">Verifying secure lending workspace session...</p>
      </div>
    );
  }

  const selectedDoc = documents.find((d) => d.id === selectedDocId);
  const selectedExt = extractions.find((e) => e.document_id === selectedDocId);

  const displayedFields = (selectedExt?.fields || []).filter((f: any) => {
    if (!filterAttention) return true;
    return f.confidence_state === "Red" || f.confidence_state === "Yellow";
  });

  const unresolvedCount = (selectedExt?.fields || []).filter(
    (f: any) => (f.confidence_state === "Red" || f.confidence_state === "Yellow") && f.review_state !== "approved"
  ).length;

  return (
    <div className="min-h-screen flex flex-col bg-ink text-paper-100">
      <Header onStartTour={() => setIsTourOpen(true)} language={uploadLanguage} onLanguageChange={setUploadLanguage} />

      <main className="flex-1 p-5 max-w-[1720px] w-full mx-auto space-y-5">
        {/* Top Control & Action Bar */}
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 p-4 rounded-lg panel">
          <div className="flex flex-wrap items-center gap-3">
            {/* 1-Click Judge Demo Seeder */}
            <button
              onClick={handleSeedDemo}
              disabled={isSeeding}
              className="px-4 py-2 rounded-md verify-gradient text-ink text-xs font-bold transition hover:brightness-110 flex items-center space-x-2 disabled:opacity-50"
            >
              {isSeeding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              <span>{isSeeding ? "Loading Demo Cases..." : "Load Seeded Judge Demo Batch (EN/HI/MR)"}</span>
            </button>

            {/* Language Selector */}
            <div className="flex items-center space-x-1 bg-ink rounded-md p-1 border border-ink-rule text-xs">
              <span className="text-paper-500 px-2 font-medium">OCR Mode:</span>
              {["Mixed", "English", "Hindi", "Marathi"].map((l) => (
                <button
                  key={l}
                  onClick={() => setUploadLanguage(l)}
                  className={`px-2.5 py-1 rounded font-semibold transition ${
                    uploadLanguage === l ? "bg-verify text-ink" : "text-paper-500 hover:text-paper-100"
                  }`}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center space-x-3 w-full lg:w-auto justify-end">
            {/* Export Trigger */}
            <button
              onClick={() => setIsExportOpen(true)}
              disabled={documents.length === 0}
              className="px-4 py-2 rounded-md bg-ink hover:bg-ink-raised text-paper-100 text-xs font-bold transition flex items-center space-x-2 border border-ink-rule disabled:opacity-40"
            >
              <Download className="h-4 w-4 text-verify" />
              <span>Export Case (4 Formats)</span>
            </button>
          </div>
        </div>

        {/* If no documents uploaded yet, display Dropzone */}
        {documents.length === 0 ? (
          <div
            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={() => setDragActive(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragActive(false);
              handleFileUpload(e.dataTransfer.files);
            }}
            className={`border rounded-lg p-12 text-center transition flex flex-col items-center justify-center space-y-4 ${
              dragActive ? "border-verify bg-verify/5" : "border-ink-rule bg-ink-panel hover:border-paper-500/30"
            }`}
            style={{ borderStyle: dragActive ? "solid" : "dashed" }}
          >
            <div className="h-16 w-16 rounded-lg bg-ink border border-verify/25 flex items-center justify-center">
              <UploadCloud className="h-8 w-8 text-verify" />
            </div>
            <div className="space-y-1">
              <h3 className="font-display text-lg text-paper-100">Drag &amp; drop document images or PDFs here</h3>
              <p className="text-xs text-paper-500 max-w-md">
                Supports JPG, PNG, WEBP, and PDF up to 20MB. Multilingual Devanagari (Hindi &amp; Marathi) and English models automatically route low-quality documents through OpenCV rescue.
              </p>
            </div>

            <div className="flex items-center space-x-3 pt-2">
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="px-5 py-2.5 rounded-md verify-gradient text-ink text-xs font-bold transition hover:brightness-110"
              >
                {isUploading ? "Uploading & Validating..." : "Select Files from Computer"}
              </button>
              <span className="text-xs text-paper-500">or</span>
              <button
                onClick={handleSeedDemo}
                className="px-4 py-2.5 rounded-md bg-ink hover:bg-ink-raised text-paper-300 text-xs font-semibold border border-ink-rule transition"
              >
                Try Pre-loaded Demo Fixtures
              </button>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".png,.jpg,.jpeg,.webp,.pdf"
              className="hidden"
              onChange={(e) => handleFileUpload(e.target.files)}
            />
          </div>
        ) : (
          /* 3-Pane Review Workspace */
          <div ref={workspaceRef} className="grid grid-cols-1 lg:grid-cols-12 gap-5 min-h-[640px]">
            {/* Left Pane: Document Batch Selector (3 cols) */}
            <div className="lg:col-span-3 flex flex-col space-y-3">
              <div className="flex items-center justify-between px-1">
                <span className="text-xs font-bold uppercase tracking-wider text-paper-500">
                  Case Documents ({documents.length})
                </span>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="text-xs font-semibold text-verify hover:brightness-110 transition flex items-center space-x-1"
                >
                  <span>+ Add More</span>
                </button>
              </div>

              <div className="flex-1 space-y-2 overflow-y-auto max-h-[680px] pr-1">
                {documents.map((doc) => {
                  const ext = extractions.find((e) => e.document_id === doc.id);
                  const isSelected = doc.id === selectedDocId;
                  const isProcessing = doc.status === "processing";
                  const isFailed = doc.status === "processing_failed";
                  const isApproved = ext?.status === "approved";

                  return (
                    <div
                      key={doc.id}
                      onClick={() => !isFailed && setSelectedDocId(doc.id)}
                      className={`p-3 rounded-md border transition flex flex-col space-y-2 ${
                        isFailed
                          ? "bg-signal-red/10 border-signal-red/40 cursor-not-allowed opacity-70"
                          : isSelected
                          ? "bg-ink-raised border-verify/60 cursor-pointer"
                          : "bg-ink-panel border-ink-rule hover:bg-ink-raised hover:border-paper-500/30 cursor-pointer"
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center space-x-2 truncate">
                          <FileText className={`h-4 w-4 ${isFailed ? "text-signal-red" : isSelected ? "text-verify" : "text-paper-500"}`} />
                          <span className="text-xs font-semibold text-paper-100 truncate">{doc.filename_safe}</span>
                        </div>
                        {isFailed ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-signal-red/10 text-signal-red border border-signal-red/30 flex items-center space-x-1">
                            <span>⚠ Rejected</span>
                          </span>
                        ) : isApproved ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-verify/10 text-verify border border-verify/30 flex items-center space-x-1">
                            <Check className="h-3 w-3" />
                            <span>Approved</span>
                          </span>
                        ) : isProcessing ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-paper-500/10 text-paper-300 border border-paper-500/30 flex items-center space-x-1">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            <span>Processing</span>
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-signal-amber/10 text-signal-amber border border-signal-amber/30">
                            Needs Review
                          </span>
                        )}
                      </div>

                      <div className="flex flex-col space-y-1 text-[11px] text-paper-500">
                        {isFailed ? (
                          <div className="flex items-center justify-between gap-2 pt-0.5">
                            <span className="text-signal-red text-[10px] truncate max-w-[180px]">
                              {doc.last_error_message || "Processing failed — please retry"}
                            </span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRetryDocument(doc.id);
                              }}
                              className="px-2 py-0.5 rounded bg-verify/15 hover:bg-verify/25 text-verify text-[10px] font-bold border border-verify/30 transition shrink-0"
                            >
                              Retry
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center justify-between">
                            <span>Type: {ext?.schema_name || "Detecting..."}</span>
                            <span className="font-mono text-paper-300 tabular">
                              Quality: {doc.quality_score !== null ? `${doc.quality_score}/100` : "..."}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".png,.jpg,.jpeg,.webp,.pdf"
                className="hidden"
                onChange={(e) => handleFileUpload(e.target.files)}
              />
            </div>

            {/* Center Pane: Synchronized Original vs Enhanced Viewer (5 cols) */}
            <div className="lg:col-span-5 flex flex-col">
              {selectedDoc ? (
                <CompareViewer
                  filename={selectedDoc.filename_safe}
                  sourceUrl={`/api/v1/files/download?path=${encodeURIComponent(selectedDoc.source_path)}`}
                  enhancedUrl={`/api/v1/files/download?path=${encodeURIComponent(selectedDoc.enhanced_path || selectedDoc.source_path)}`}
                  qualityScore={selectedDoc.quality_score || 0}
                  qualityBand={selectedDoc.quality_band || "acceptable"}
                  qualityFlags={selectedDoc.quality_flags_json || []}
                />
              ) : (
                <div className="h-full panel rounded-lg flex items-center justify-center text-xs text-paper-500">
                  Select a document to inspect original and enhanced scans
                </div>
              )}
            </div>

            {/* Right Pane: Extracted Fields & Review Workflow (4 cols) */}
            <div className="lg:col-span-4 flex flex-col space-y-3">
              {/* Tab Navigation (Fields / Cross-Doc / Grounded QA) */}
              <div className="flex items-center space-x-1 bg-ink rounded-md p-1 border border-ink-rule">
                <button
                  onClick={() => setActiveTab("fields")}
                  className={`flex-1 py-1.5 rounded text-xs font-semibold transition ${
                    activeTab === "fields" ? "bg-verify text-ink" : "text-paper-500 hover:text-paper-100"
                  }`}
                >
                  Extracted Fields
                </button>
                <button
                  onClick={() => setActiveTab("consistency")}
                  className={`flex-1 py-1.5 rounded text-xs font-semibold transition ${
                    activeTab === "consistency" ? "bg-verify text-ink" : "text-paper-500 hover:text-paper-100"
                  }`}
                >
                  Cross-Doc Check
                </button>
                <button
                  onClick={() => setActiveTab("qa")}
                  className={`flex-1 py-1.5 rounded text-xs font-semibold transition ${
                    activeTab === "qa" ? "bg-verify text-ink" : "text-paper-500 hover:text-paper-100"
                  }`}
                >
                  Q&amp;A Assistant
                </button>

                {(selectedDoc?.status === "processing" || selectedDoc?.status === "processing_failed") && (
                  <button
                    onClick={() => setActiveTab("pipeline")}
                    className={`flex-1 py-1.5 rounded text-xs font-semibold transition flex items-center justify-center space-x-1 ${
                      activeTab === "pipeline" ? "bg-verify text-ink" : "text-paper-500 hover:text-paper-100"
                    }`}
                  >
                    {selectedDoc?.status === "processing" ? (
                      <Loader2 className={`h-3 w-3 animate-spin ${activeTab === "pipeline" ? "text-ink" : "text-verify"}`} />
                    ) : (
                      <span className={`h-1.5 w-1.5 rounded-full ${activeTab === "pipeline" ? "bg-ink" : "bg-signal-red"}`} />
                    )}
                    <span>Pipeline</span>
                  </button>
                )}
              </div>

              {activeTab === "pipeline" && selectedDoc && (
                <PipelinePanel
                  doc={selectedDoc}
                  sessionToken={sessionToken}
                  onRetried={() => caseId && fetchCase(caseId)}
                />
              )}

              {activeTab === "fields" && (
                <div className="flex flex-col space-y-3">
                  {/* Action row with Filter & TTS */}
                  <div className="flex items-center justify-between px-1">
                    <button
                      onClick={() => setFilterAttention((f) => !f)}
                      className={`px-2.5 py-1 rounded-md text-xs font-semibold flex items-center space-x-1.5 border transition ${
                        filterAttention
                          ? "bg-signal-amber/15 text-signal-amber border-signal-amber/40"
                          : "bg-ink text-paper-500 border-ink-rule hover:text-paper-100"
                      }`}
                    >
                      <Filter className="h-3.5 w-3.5" />
                      <span>{filterAttention ? "Showing Attention Only" : "Filter Attention (Yellow/Red)"}</span>
                    </button>

                    <button
                      onClick={handleSpeakSummary}
                      className="p-1.5 rounded-md bg-ink hover:bg-ink-raised text-paper-300 border border-ink-rule text-xs flex items-center space-x-1"
                      title="Read aloud summary in English/Hindi/Marathi"
                    >
                      {isSpeaking ? <VolumeX className="h-4 w-4 text-signal-amber" /> : <Volume2 className="h-4 w-4 text-verify" />}
                      <span>{isSpeaking ? "Stop" : "Read Aloud"}</span>
                    </button>
                  </div>

                  {/* Fields List */}
                  <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
                    {displayedFields.length === 0 ? (
                      <div className="p-8 text-center panel rounded-md text-xs text-paper-500">
                        {selectedDoc?.status === "processing" ? (
                          <div className="flex flex-col items-center justify-center space-y-2 py-4">
                            <Loader2 className="h-6 w-6 animate-spin text-verify" />
                            <span className="text-paper-100 font-semibold">Extracting &amp; Structuring Fields...</span>
                            <span className="text-[11px] text-paper-500">AI OCR pipeline in progress</span>
                          </div>
                        ) : filterAttention ? (
                          "No attention-required fields found in this document."
                        ) : (
                          "No fields extracted yet or document awaiting review."
                        )}
                      </div>
                    ) : (
                      displayedFields.map((field: any) => (
                        <FieldEditor
                          key={field.field_key}
                          extractionId={selectedExt?.id}
                          field={field}
                          onSave={handleSaveField}
                        />
                      ))
                    )}
                  </div>

                  {/* Explicit Approval Action */}
                  <div className="pt-2 border-t border-ink-rule">
                    <button
                      onClick={handleApproveDocument}
                      disabled={!selectedExt || selectedExt.status === "approved"}
                      className={`w-full py-2.5 rounded-md font-bold text-xs transition flex items-center justify-center space-x-2 ${
                        selectedExt?.status === "approved"
                          ? "bg-verify/15 text-verify border border-verify/30 cursor-default"
                          : "verify-gradient text-ink hover:brightness-110"
                      }`}
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      <span>{selectedExt?.status === "approved" ? "Document Human-Approved & Verified" : "Approve & Mark as Verified"}</span>
                    </button>
                  </div>
                </div>
              )}

              {activeTab === "consistency" && caseId && (
                <ConsistencyPanel caseId={caseId} sessionToken={sessionToken} />
              )}

              {activeTab === "qa" && caseId && (
                <QAAssistant caseId={caseId} sessionToken={sessionToken} />
              )}
            </div>
          </div>
        )}
      </main>

      {/* Modals & Guided Walkthrough */}
      {caseId && (
        <ExportModal
          isOpen={isExportOpen}
          onClose={() => setIsExportOpen(false)}
          caseId={caseId}
          unresolvedCount={unresolvedCount}
          sessionToken={sessionToken}
        />
      )}

      <GuidedTour isOpen={isTourOpen} onClose={() => setIsTourOpen(false)} />
    </div>
  );
}
