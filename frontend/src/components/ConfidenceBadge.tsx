"use client";

import React, { useState } from "react";
import { CheckCircle2, AlertTriangle, XCircle, Info } from "lucide-react";

interface ConfidenceBadgeProps {
  score: number;
  state: "Green" | "Yellow" | "Red" | string;
  ocrConf?: number;
  structConf?: number;
  valScore?: number;
  qualityFactor?: number;
  reasons?: string[];
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  score,
  state,
  ocrConf = 0.9,
  structConf = 0.9,
  valScore = 1.0,
  qualityFactor = 1.0,
  reasons = []
}) => {
  const [showTooltip, setShowTooltip] = useState(false);

  let badgeStyles = "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
  let icon = <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />;
  let label = "High Confidence";

  if (state === "Yellow" || (score >= 60 && score < 85)) {
    badgeStyles = "bg-amber-500/10 text-amber-400 border-amber-500/30";
    icon = <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />;
    label = "Review Recommended";
  } else if (state === "Red" || score < 60) {
    badgeStyles = "bg-rose-500/10 text-rose-400 border-rose-500/30";
    icon = <XCircle className="h-3.5 w-3.5 text-rose-400" />;
    label = "Attention Required";
  }

  return (
    <div className="relative inline-block" onMouseEnter={() => setShowTooltip(true)} onMouseLeave={() => setShowTooltip(false)}>
      <div className={`inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${badgeStyles} cursor-help transition hover:brightness-110 shadow-sm`}>
        {icon}
        <span>{score}%</span>
      </div>

      {showTooltip && (
        <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 w-64 p-3 bg-slate-900/95 border border-slate-700 text-slate-200 text-xs rounded-xl shadow-2xl z-50 backdrop-blur-md">
          <div className="flex items-center justify-between border-b border-slate-800 pb-1.5 mb-2 font-semibold">
            <span className="text-slate-100">{label}</span>
            <span className="font-mono text-indigo-400">{score}% Score</span>
          </div>

          <div className="space-y-1 text-[11px] font-mono text-slate-300">
            <div className="flex justify-between">
              <span className="text-slate-400">OCR Evidence (45%):</span>
              <span>{(ocrConf * 100).toFixed(0)}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Structuring (35%):</span>
              <span>{(structConf * 100).toFixed(0)}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Validation (20%):</span>
              <span>{(valScore * 100).toFixed(0)}%</span>
            </div>
            <div className="flex justify-between border-t border-slate-800 pt-1">
              <span className="text-slate-400">Quality Factor:</span>
              <span>{qualityFactor.toFixed(2)}x</span>
            </div>
          </div>

          {reasons.length > 0 && (
            <div className="mt-2.5 border-t border-slate-800 pt-1.5">
              <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block mb-1">Reason Codes:</span>
              <div className="flex flex-wrap gap-1">
                {reasons.map((r, i) => (
                  <span key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    {r}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
