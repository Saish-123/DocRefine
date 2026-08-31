"use client";

import React, { useState, useRef } from "react";
import { ZoomIn, ZoomOut, RotateCcw, SplitSquareVertical, Eye, Layers, Sparkles, ShieldAlert } from "lucide-react";

interface CompareViewerProps {
  filename: string;
  sourceUrl: string;
  enhancedUrl: string;
  qualityScore: number;
  qualityBand: string;
  qualityFlags: string[];
}

export const CompareViewer: React.FC<CompareViewerProps> = ({
  filename,
  sourceUrl,
  enhancedUrl,
  qualityScore,
  qualityBand,
  qualityFlags
}) => {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [viewMode, setViewMode] = useState<"side-by-side" | "toggle" | "enhanced-only">("side-by-side");
  const [activeToggle, setActiveToggle] = useState<"original" | "enhanced">("enhanced");

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    });
  };

  const handleMouseUp = () => setIsDragging(false);

  const resetTransform = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const bandColor =
    qualityBand === "acceptable"
      ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/30"
      : qualityBand === "warning"
      ? "text-amber-400 bg-amber-500/10 border-amber-500/30"
      : "text-rose-400 bg-rose-500/10 border-rose-500/30";

  return (
    <div className="flex flex-col h-full bg-slate-900/60 rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
      {/* Top Action Bar */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-900/90 border-b border-slate-800">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-200">
            <Layers className="h-4 w-4 text-indigo-400" />
            <span className="truncate max-w-[200px]">{filename}</span>
          </div>

          <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium border ${bandColor}`}>
            Quality: {qualityScore}/100 ({qualityBand})
          </span>
        </div>

        {/* Controls */}
        <div className="flex items-center space-x-2">
          {/* View Mode Selector */}
          <div className="flex items-center rounded-lg bg-slate-800 p-0.5 border border-slate-700">
            <button
              onClick={() => setViewMode("side-by-side")}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition ${viewMode === "side-by-side" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-slate-200"}`}
            >
              Side-by-Side
            </button>
            <button
              onClick={() => setViewMode("toggle")}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition ${viewMode === "toggle" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-slate-200"}`}
            >
              Toggle
            </button>
          </div>

          {/* Zoom Controls */}
          <div className="flex items-center space-x-1 bg-slate-800 rounded-lg p-0.5 border border-slate-700">
            <button
              onClick={() => setZoom((z) => Math.max(0.6, z - 0.2))}
              className="p-1.5 rounded hover:bg-slate-700 text-slate-300 transition"
              title="Zoom Out"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </button>
            <span className="text-[11px] font-mono px-1.5 text-slate-300">{(zoom * 100).toFixed(0)}%</span>
            <button
              onClick={() => setZoom((z) => Math.min(3.0, z + 0.2))}
              className="p-1.5 rounded hover:bg-slate-700 text-slate-300 transition"
              title="Zoom In"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={resetTransform}
              className="p-1.5 rounded hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition"
              title="Reset Zoom & Pan"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Quality Flags Bar */}
      {qualityFlags && qualityFlags.length > 0 && (
        <div className="px-4 py-1.5 bg-slate-950/60 border-b border-slate-800/80 flex items-center space-x-2 text-[11px] overflow-x-auto">
          <span className="text-slate-400 font-semibold uppercase tracking-wider text-[10px]">Diagnostics:</span>
          {qualityFlags.map((flag, idx) => (
            <span key={idx} className="px-2 py-0.5 rounded bg-slate-800/90 text-slate-300 border border-slate-700/60 font-mono text-[10px]">
              {flag}
            </span>
          ))}
        </div>
      )}

      {/* Canvas Area */}
      <div
        className="flex-1 relative overflow-hidden bg-slate-950/90 flex items-center justify-center cursor-grab active:cursor-grabbing select-none p-4"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {viewMode === "side-by-side" ? (
          <div
            className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full h-full"
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: "center center",
              transition: isDragging ? "none" : "transform 0.1s ease-out"
            }}
          >
            {/* Original Box */}
            <div className="relative rounded-xl border border-slate-800 bg-slate-900/50 flex flex-col overflow-hidden min-h-[380px]">
              <div className="absolute top-3 left-3 z-10 px-2.5 py-1 rounded-md bg-slate-900/90 border border-slate-700 text-[11px] font-semibold text-slate-300 flex items-center space-x-1.5 shadow-lg">
                <span className="h-2 w-2 rounded-full bg-slate-400" />
                <span>Original Source (Raw)</span>
              </div>
              <div className="flex-1 flex items-center justify-center p-4">
                <img
                  src={sourceUrl}
                  alt="Original Document"
                  className="max-h-[420px] max-w-full object-contain rounded-lg shadow-md pointer-events-none transition duration-200"
                />
              </div>
            </div>

            {/* Enhanced Box */}
            <div className="relative rounded-xl border border-indigo-500/30 bg-slate-900/50 flex flex-col overflow-hidden ring-1 ring-indigo-500/20 min-h-[380px]">
              <div className="absolute top-3 left-3 z-10 px-2.5 py-1 rounded-md bg-indigo-950/90 border border-indigo-500/40 text-[11px] font-semibold text-indigo-200 flex items-center space-x-1.5 shadow-lg">
                <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
                <span>Rescued & Enhanced (OpenCV)</span>
              </div>
              <div className="flex-1 flex items-center justify-center p-4">
                <img
                  src={enhancedUrl}
                  alt="Enhanced Document"
                  className="max-h-[420px] max-w-full object-contain rounded-lg shadow-md pointer-events-none transition duration-200"
                />
              </div>
            </div>
          </div>
        ) : (
          /* Toggle Mode */
          <div
            className="relative w-full h-full flex flex-col items-center justify-center min-h-[380px]"
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: "center center",
              transition: isDragging ? "none" : "transform 0.1s ease-out"
            }}
          >
            <div className="absolute top-3 z-20 flex items-center space-x-1 bg-slate-900/90 rounded-lg p-1 border border-slate-700 shadow-xl">
              <button
                onClick={() => setActiveToggle("original")}
                className={`px-3 py-1 rounded text-xs font-semibold transition ${activeToggle === "original" ? "bg-slate-700 text-white" : "text-slate-400"}`}
              >
                Original
              </button>
              <button
                onClick={() => setActiveToggle("enhanced")}
                className={`px-3 py-1 rounded text-xs font-semibold transition ${activeToggle === "enhanced" ? "bg-indigo-600 text-white" : "text-slate-400"}`}
              >
                Enhanced
              </button>
            </div>
            <img
              src={activeToggle === "original" ? sourceUrl : enhancedUrl}
              alt="Document"
              className="max-h-[440px] max-w-full object-contain rounded-xl shadow-2xl pointer-events-none"
            />
          </div>
        )}
      </div>
    </div>
  );
};
