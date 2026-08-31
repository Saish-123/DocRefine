"use client";

import React, { useState } from "react";
import { Download, FileText, FileSpreadsheet, Code, AlertTriangle, X, Check, Loader2, AlertCircle } from "lucide-react";

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  unresolvedCount: number;
  sessionToken?: string | null;
}

export const ExportModal: React.FC<ExportModalProps> = ({
  isOpen,
  onClose,
  caseId,
  unresolvedCount,
  sessionToken
}) => {
  const [formats, setFormats] = useState<{ [key: string]: boolean }>({
    pdf: true,
    xlsx: true,
    json: true,
    csv: true
  });
  const [includeUnresolved, setIncludeUnresolved] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [downloadLinks, setDownloadLinks] = useState<{ [key: string]: string } | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const toggleFormat = (fmt: string) => {
    setFormats((prev) => ({ ...prev, [fmt]: !prev[fmt] }));
  };

  const handleExport = async () => {
    setIsExporting(true);
    setErrorMsg(null);
    try {
      const selectedFormats = Object.keys(formats).filter((k) => formats[k]);
      if (selectedFormats.length === 0) {
        setErrorMsg("Please select at least one export format.");
        setIsExporting(false);
        return;
      }
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (sessionToken) {
        headers["Authorization"] = `Bearer ${sessionToken}`;
      }
      const res = await fetch("/api/v1/exports", {
        method: "POST",
        headers,
        body: JSON.stringify({
          case_id: caseId,
          formats: selectedFormats,
          include_unresolved: includeUnresolved
        })
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData?.detail || `Export failed with status ${res.status}`);
      }
      const data = await res.json();
      if (data.exports) {
        const links: { [key: string]: string } = {};
        for (const [k, v] of Object.entries(data.exports as any)) {
          links[k] = (v as any).download_url;
        }
        setDownloadLinks(links);
      } else {
        throw new Error("No export links returned from server.");
      }
    } catch (err: any) {
      console.error("Export error:", err);
      setErrorMsg(err?.message || "An unexpected error occurred during export.");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2">
            <Download className="h-5 w-5 text-indigo-400" />
            <h2 className="text-lg font-bold text-white">Export Case Data</h2>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Warning if unresolved fields exist */}
        {unresolvedCount > 0 && (
          <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start space-x-2.5">
            <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Unresolved Attention Fields</p>
              <p className="text-amber-300/80 mt-0.5">
                This case contains <b>{unresolvedCount}</b> field(s) with Yellow/Red confidence states that have not been human-approved.
              </p>
            </div>
          </div>
        )}

        {/* Error banner */}
        {errorMsg && (
          <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs flex items-start space-x-2.5">
            <AlertCircle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Export Failed</p>
              <p className="text-red-300/80 mt-0.5">{errorMsg}</p>
            </div>
          </div>
        )}

        {/* Format Selector */}
        <div>
          <label className="text-xs font-semibold text-slate-300 block mb-2 uppercase tracking-wider">Select Export Formats</label>
          <div className="grid grid-cols-2 gap-3">
            {[
              { id: "pdf", label: "Executive PDF", desc: "Formatted report & audit badges", icon: <FileText className="h-4 w-4 text-rose-400" /> },
              { id: "xlsx", label: "Excel (.xlsx)", desc: "Multi-sheet structured workbook", icon: <FileSpreadsheet className="h-4 w-4 text-emerald-400" /> },
              { id: "json", label: "Canonical JSON", desc: "Standard schema & confidence tree", icon: <Code className="h-4 w-4 text-indigo-400" /> },
              { id: "csv", label: "Unicode CSV", desc: "UTF-8 BOM English/Hindi/Marathi", icon: <FileSpreadsheet className="h-4 w-4 text-cyan-400" /> }
            ].map((item) => (
              <div
                key={item.id}
                onClick={() => toggleFormat(item.id)}
                className={`p-3 rounded-xl border cursor-pointer transition flex items-start space-x-2.5 ${
                  formats[item.id] ? "bg-indigo-950/40 border-indigo-500/60 ring-1 ring-indigo-500/20" : "bg-slate-950 border-slate-800 opacity-60"
                }`}
              >
                <div className="mt-0.5">{item.icon}</div>
                <div>
                  <div className="text-xs font-semibold text-slate-200">{item.label}</div>
                  <div className="text-[10px] text-slate-400">{item.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Download links if generated */}
        {downloadLinks ? (
          <div className="space-y-2 border-t border-slate-800 pt-3">
            <p className="text-xs font-semibold text-emerald-400 flex items-center space-x-1.5">
              <Check className="h-4 w-4" />
              <span>Exports Generated Successfully (Signed 300s TTL)</span>
            </p>
            <div className="grid grid-cols-2 gap-2.5 pt-1">
              {Object.entries(downloadLinks).map(([fmt, url]) => (
                <a
                  key={fmt}
                  href={url}
                  download={`DocRefine_Case_${caseId.slice(0, 8)}.${fmt}`}
                  className="px-3.5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center justify-between border border-slate-700 transition shadow-sm hover:border-indigo-500/50 hover:text-white"
                >
                  <span className="uppercase font-bold tracking-wider">{fmt} File</span>
                  <Download className="h-3.5 w-3.5 text-indigo-400" />
                </a>
              ))}
            </div>
          </div>
        ) : (
          <button
            onClick={handleExport}
            disabled={isExporting}
            className="w-full py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-semibold text-sm transition flex items-center justify-center space-x-2 shadow-lg shadow-indigo-600/20 disabled:opacity-50"
          >
            {isExporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            <span>{isExporting ? "Generating Verified Packages..." : "Generate & Download Exports"}</span>
          </button>
        )}
      </div>
    </div>
  );
};
