"use client";

import React, { useState } from "react";
import { Check, Edit3, RotateCcw, AlertCircle, Save, CheckCircle } from "lucide-react";
import { ConfidenceBadge } from "./ConfidenceBadge";

interface FieldItem {
  id?: string;
  field_key: string;
  label: string;
  raw_value: string | null;
  normalized_value: string | null;
  field_score: number;
  confidence_state: "Green" | "Yellow" | "Red" | string;
  validation_status: string;
  review_state: string;
  ocr_confidence?: number;
  structuring_confidence?: number;
  validation_score?: number;
  reason_codes_json?: string[];
}

interface FieldEditorProps {
  extractionId: string;
  field: FieldItem;
  onSave: (fieldKey: string, newValue: string) => Promise<void>;
}

export const FieldEditor: React.FC<FieldEditorProps> = ({ extractionId, field, onSave }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [currentVal, setCurrentVal] = useState(field.normalized_value || field.raw_value || "");
  const [savedVal, setSavedVal] = useState(field.normalized_value || field.raw_value || "");
  const [isSaving, setIsSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSave(field.field_key, currentVal);
      setSavedVal(currentVal);
      setIsEditing(false);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 2500);
    } catch (err) {
      console.error("Save failed:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleUndo = () => {
    setCurrentVal(savedVal);
    setIsEditing(false);
  };

  const isChanged = currentVal !== savedVal;

  return (
    <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 transition flex flex-col space-y-2">
      {/* Top Row: Label + Confidence Badge */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">{field.label}</span>
        <div className="flex items-center space-x-2">
          <ConfidenceBadge
            score={field.field_score}
            state={field.confidence_state}
            ocrConf={field.ocr_confidence}
            structConf={field.structuring_confidence}
            valScore={field.validation_score}
            reasons={field.reason_codes_json || []}
          />
          {savedSuccess && (
            <span className="text-[11px] text-emerald-400 font-medium flex items-center space-x-1">
              <Check className="h-3 w-3" />
              <span>Saved</span>
            </span>
          )}
        </div>
      </div>

      {/* Field Value Input / Display */}
      {isEditing ? (
        <div className="flex items-center space-x-2">
          <input
            type="text"
            value={currentVal}
            onChange={(e) => setCurrentVal(e.target.value)}
            className="flex-1 bg-slate-950 border border-indigo-500/60 rounded-lg px-3 py-1.5 text-sm text-slate-100 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
            autoFocus
          />
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="p-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition disabled:opacity-50"
            title="Save changes"
          >
            <Save className="h-4 w-4" />
          </button>
          <button
            onClick={handleUndo}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
            title="Cancel / Undo"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
        </div>
      ) : (
        <div className="flex items-center justify-between group">
          <div className="font-mono text-sm text-slate-100 truncate pr-2">
            {currentVal ? (
              <span>{currentVal}</span>
            ) : (
              <span className="text-rose-400/80 italic text-xs">[MISSING / UNREADABLE]</span>
            )}
          </div>
          <button
            onClick={() => setIsEditing(true)}
            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
            title="Edit field value"
          >
            <Edit3 className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Validation status / reason note */}
      {field.validation_status === "invalid" && (
        <div className="text-[11px] text-rose-400 flex items-center space-x-1 font-mono">
          <AlertCircle className="h-3 w-3" />
          <span>Format validation failed. Please check digits/checksum.</span>
        </div>
      )}
    </div>
  );
};
