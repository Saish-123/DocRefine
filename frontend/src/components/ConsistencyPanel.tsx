"use client";

import React, { useEffect, useState } from "react";
import { CheckCircle, AlertTriangle, HelpCircle, GitCompare, ArrowRight } from "lucide-react";

interface Signal {
  field: string;
  status: "consistent" | "conflict" | "insufficient_evidence";
  message: string;
  sources: Array<{ doc_id: string; doc_type: string; val: string }>;
}

interface ConsistencyPanelProps {
  caseId: string;
  sessionToken?: string | null;
}

export const ConsistencyPanel: React.FC<ConsistencyPanelProps> = ({ caseId, sessionToken }) => {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const headers: Record<string, string> = {};
    if (sessionToken) {
      headers["Authorization"] = `Bearer ${sessionToken}`;
    }

    fetch(`/api/v1/cases/${caseId}/consistency`, { headers })
      .then((res) => res.json())
      .then((data) => setSignals(data.signals || []))
      .catch((err) => console.error("Consistency fetch error:", err))
      .finally(() => setLoading(false));
  }, [caseId, sessionToken]);

  if (loading) {
    return <div className="p-4 text-xs text-slate-400">Analyzing cross-document signals...</div>;
  }

  if (signals.length === 0) {
    return (
      <div className="p-4 text-xs text-slate-400 bg-slate-900/40 rounded-xl border border-slate-800 text-center">
        No cross-document records available yet. Upload multiple documents to run consistency checking.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center space-x-2 text-xs font-semibold text-slate-300">
        <GitCompare className="h-4 w-4 text-indigo-400" />
        <span>Cross-Document Consistency Review</span>
      </div>

      <div className="space-y-2.5">
        {signals.map((sig, idx) => {
          let statusBadge = (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center space-x-1">
              <CheckCircle className="h-3 w-3" />
              <span>Consistent</span>
            </span>
          );
          if (sig.status === "conflict") {
            statusBadge = (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20 flex items-center space-x-1">
                <AlertTriangle className="h-3 w-3" />
                <span>Mismatch Alert</span>
              </span>
            );
          } else if (sig.status === "insufficient_evidence") {
            statusBadge = (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-800 text-slate-400 border border-slate-700 flex items-center space-x-1">
                <HelpCircle className="h-3 w-3" />
                <span>Single Source</span>
              </span>
            );
          }

          return (
            <div key={idx} className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-200">{sig.field}</span>
                {statusBadge}
              </div>
              <p className="text-[11px] text-slate-300">{sig.message}</p>
              {sig.sources && sig.sources.length > 0 && (
                <div className="pt-1 flex flex-wrap gap-1.5">
                  {sig.sources.map((s, i) => (
                    <span key={i} className="text-[10px] px-2 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-800 font-mono">
                      {s.doc_type}: <span className="text-indigo-300 font-semibold">{s.val}</span>
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
