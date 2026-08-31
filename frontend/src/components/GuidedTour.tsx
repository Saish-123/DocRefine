"use client";

import React, { useState } from "react";
import { Sparkles, ArrowRight, Check, X, Shield, Sliders, FileText, Download } from "lucide-react";

interface GuidedTourProps {
  isOpen: boolean;
  onClose: () => void;
}

const STEPS = [
  {
    title: "1. Multi-Document Ingestion & Validation",
    icon: <FileText className="h-6 w-6 text-indigo-400" />,
    description:
      "Upload batches of mixed quality English, Hindi, and Marathi documents. The server performs MIME & magic byte inspection to reject malformed or disguised files before OCR."
  },
  {
    title: "2. Document Quality Rescue (OpenCV)",
    icon: <Sliders className="h-6 w-6 text-cyan-400" />,
    description:
      "Deterministic quality scoring analyzes blur, tilt, brightness, and contrast. OpenCV applies adaptive deskewing, CLAHE contrast equalization, and bilateral denoising."
  },
  {
    title: "3. Multilingual OCR & Field-Level Confidence",
    icon: <Shield className="h-6 w-6 text-emerald-400" />,
    description:
      "EasyOCR recognizes Devanagari (Hindi & Marathi) and English text with per-token confidence. LLM adapters (Gemini, Groq) extract structured fields with strict schemas and an anti-hallucination guardrail. Every field is scored Green (85-100), Yellow (60-84), or Red (0-59)."
  },
  {
    title: "4. Human Review & 4-Format Export",
    icon: <Download className="h-6 w-6 text-amber-400" />,
    description:
      "Inspect side-by-side zoom/pan views, filter to attention fields, edit with instant score recalculation, approve the case, and download PDF, XLSX, JSON, and CSV packages."
  }
];

export const GuidedTour: React.FC<GuidedTourProps> = ({ isOpen, onClose }) => {
  const [currentStep, setCurrentStep] = useState(0);

  if (!isOpen) return null;

  const nextStep = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      onClose();
    }
  };

  const step = STEPS[currentStep];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Step Indicator */}
        <div className="flex items-center space-x-2">
          {STEPS.map((_, idx) => (
            <div
              key={idx}
              className={`h-1.5 flex-1 rounded-full transition-all duration-300 ${
                idx === currentStep ? "bg-indigo-500" : idx < currentStep ? "bg-indigo-900" : "bg-slate-800"
              }`}
            />
          ))}
        </div>

        {/* Step Content */}
        <div className="space-y-4 pt-2">
          <div className="h-12 w-12 rounded-2xl bg-indigo-950 border border-indigo-500/30 flex items-center justify-center shadow-lg shadow-indigo-500/10">
            {step.icon}
          </div>
          <h3 className="text-xl font-bold text-white tracking-tight">{step.title}</h3>
          <p className="text-sm text-slate-300 leading-relaxed">{step.description}</p>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-800">
          <span className="text-xs font-mono text-slate-400">
            Step {currentStep + 1} of {STEPS.length}
          </span>
          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-slate-200"
            >
              Skip Tour
            </button>
            <button
              onClick={nextStep}
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition flex items-center space-x-1.5 shadow-md shadow-indigo-600/20"
            >
              <span>{currentStep === STEPS.length - 1 ? "Get Started" : "Next Step"}</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
