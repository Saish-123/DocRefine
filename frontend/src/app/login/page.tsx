"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "@/lib/supabaseClient";
import { Eye, EyeOff, Lock, Mail, ArrowRight, AlertCircle, Loader2, Info } from "lucide-react";

// Inline DocRefine Logo SVG from brand assets
const DocRefineLogo = () => (
  <svg viewBox="0 0 240 240" className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="lr-doc-bg" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#1E1B4B" /><stop offset="50%" stopColor="#0F172A" /><stop offset="100%" stopColor="#020617" />
      </linearGradient>
      <linearGradient id="lr-violet" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#C084FC" /><stop offset="50%" stopColor="#8B5CF6" /><stop offset="100%" stopColor="#6366F1" />
      </linearGradient>
      <linearGradient id="lr-laser" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stopColor="#38BDF8" /><stop offset="50%" stopColor="#F59E0B" /><stop offset="100%" stopColor="#10B981" />
      </linearGradient>
      <linearGradient id="lr-star" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#FDE047" /><stop offset="100%" stopColor="#EA580C" />
      </linearGradient>
      <filter id="lr-glow" x="-30%" y="-30%" width="160%" height="160%">
        <feGaussianBlur stdDeviation="8" result="blur" />
        <feComposite in="SourceGraphic" in2="blur" operator="over" />
      </filter>
    </defs>
    <rect width="240" height="240" rx="56" fill="#090D16" stroke="#1E293B" strokeWidth="2" />
    <g transform="translate(120,120)">
      <circle cx="0" cy="0" r="70" fill="url(#lr-violet)" opacity="0.15" filter="url(#lr-glow)" />
      <rect x="-42" y="-55" width="84" height="110" rx="14" fill="#0F172A" stroke="#334155" strokeWidth="2" transform="rotate(-8)" opacity="0.7" />
      <path d="M -40 -60 L 15 -60 L 45 -30 L 45 55 L -40 55 Z" fill="url(#lr-doc-bg)" stroke="url(#lr-violet)" strokeWidth="3" strokeLinejoin="round" />
      <path d="M 15 -60 L 15 -30 L 45 -30" fill="#1E293B" stroke="url(#lr-violet)" strokeWidth="2" />
      <line x1="-24" y1="-34" x2="2" y2="-34" stroke="#64748B" strokeWidth="3.5" strokeLinecap="round" opacity="0.8" />
      <line x1="-24" y1="-18" x2="18" y2="-18" stroke="#64748B" strokeWidth="3.5" strokeLinecap="round" opacity="0.8" />
      <line x1="-52" y1="2" x2="52" y2="2" stroke="url(#lr-laser)" strokeWidth="3.5" strokeLinecap="round" filter="url(#lr-glow)" />
      <line x1="-24" y1="22" x2="12" y2="22" stroke="#8B5CF6" strokeWidth="4" strokeLinecap="round" />
      <line x1="-24" y1="38" x2="24" y2="38" stroke="#10B981" strokeWidth="4" strokeLinecap="round" />
      <g transform="translate(24,18)">
        <path d="M 0 -18 Q 0 0 18 0 Q 0 0 0 18 Q 0 0 -18 0 Q 0 0 0 -18 Z" fill="url(#lr-star)" filter="url(#lr-glow)" />
        <circle cx="0" cy="0" r="3.5" fill="#FFFFFF" />
      </g>
    </g>
  </svg>
);

// Hero graphic with laser scanner + document cards (from assets)
const HeroGraphic = () => (
  <svg viewBox="0 0 420 290" className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="hg-v" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stopColor="#8B5CF6" /><stop offset="100%" stopColor="#6366F1" /></linearGradient>
      <linearGradient id="hg-beam" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stopColor="rgba(139,92,246,0)" /><stop offset="70%" stopColor="rgba(245,158,11,0.25)" /><stop offset="100%" stopColor="#F59E0B" />
      </linearGradient>
      <radialGradient id="hg-glow" cx="50%" cy="50%" r="50%"><stop offset="0%" stopColor="#8B5CF6" stopOpacity="0.18" /><stop offset="100%" stopColor="transparent" /></radialGradient>
      <filter id="hg-gf"><feGaussianBlur stdDeviation="4" result="g" /><feComposite in="SourceGraphic" in2="g" operator="over" /></filter>
      <filter id="hg-sf"><feDropShadow dx="0" dy="8" stdDeviation="10" floodColor="#090D16" floodOpacity="0.5" /></filter>
    </defs>
    <rect width="420" height="290" fill="#090D16" rx="18" />
    <circle cx="210" cy="145" r="130" fill="url(#hg-glow)" />
    <g stroke="#1E293B" strokeWidth="1" opacity="0.4">
      <line x1="80" y1="240" x2="260" y2="60" /><line x1="160" y1="265" x2="360" y2="65" /><line x1="360" y1="235" x2="210" y2="55" />
    </g>
    <g transform="translate(55,95) rotate(-12) skewX(14)" filter="url(#hg-sf)">
      <rect width="155" height="100" rx="11" fill="#0F172A" stroke="#334155" strokeWidth="1.5" />
      <rect x="11" y="11" width="58" height="6" rx="3" fill="#6366F1" />
      <rect x="11" y="24" width="115" height="5" rx="2" fill="#334155" />
      <rect x="11" y="36" width="90" height="5" rx="2" fill="#334155" />
      <text x="11" y="63" fontFamily="sans-serif" fontWeight="bold" fontSize="9.5" fill="#E2E8F0">गट क्र. २४८/१अ</text>
      <text x="11" y="78" fontFamily="sans-serif" fontSize="8.5" fill="#94A3B8">रमेश पाटील • १.४२ Ha</text>
      <circle cx="135" cy="26" r="10" fill="#8B5CF6" opacity="0.2" />
      <circle cx="135" cy="26" r="7" fill="none" stroke="#8B5CF6" strokeWidth="1.5" />
    </g>
    <g transform="translate(205,65) rotate(-12) skewX(14)" filter="url(#hg-sf)">
      <rect width="170" height="110" rx="11" fill="#1E293B" stroke="#8B5CF6" strokeWidth="1.5" />
      <rect x="13" y="13" width="62" height="6" rx="3" fill="#F59E0B" />
      <text x="13" y="38" fontFamily="sans-serif" fontWeight="800" fontSize="11" fill="#FFFFFF">₹ 84,500 / mo</text>
      <text x="13" y="53" fontFamily="monospace" fontSize="8.5" fill="#10B981">● 0 INWARD BOUNCES</text>
      <g fill="#8B5CF6" opacity="0.8">
        <rect x="13" y="68" width="8" height="19" rx="2" /><rect x="25" y="62" width="8" height="25" rx="2" fill="#10B981" />
        <rect x="37" y="56" width="8" height="31" rx="2" /><rect x="49" y="50" width="8" height="37" rx="2" fill="#10B981" />
        <rect x="61" y="44" width="8" height="43" rx="2" fill="#F59E0B" />
      </g>
      <rect x="100" y="64" width="52" height="16" rx="6" fill="#10B981" opacity="0.2" />
      <text x="126" y="75" fontFamily="sans-serif" fontWeight="bold" fontSize="7.5" fill="#10B981" textAnchor="middle">VERIFIED ✓</text>
    </g>
    <ellipse cx="210" cy="175" rx="148" ry="60" fill="none" stroke="url(#hg-v)" strokeWidth="2" strokeDasharray="10,6" opacity="0.65" />
    <g>
      <rect x="25" y="70" width="370" height="32" fill="url(#hg-beam)" opacity="0.85">
        <animate attributeName="y" values="70;215;70" dur="3.2s" repeatCount="indefinite" />
      </rect>
      <line x1="25" y1="102" x2="395" y2="102" stroke="#F59E0B" strokeWidth="2.5" filter="url(#hg-gf)">
        <animate attributeName="y1" values="102;247;102" dur="3.2s" repeatCount="indefinite" />
        <animate attributeName="y2" values="102;247;102" dur="3.2s" repeatCount="indefinite" />
      </line>
    </g>
    <circle cx="62" cy="175" r="4" fill="#8B5CF6" /><circle cx="358" cy="175" r="4" fill="#F59E0B" /><circle cx="210" cy="115" r="5" fill="#10B981" />
    <text x="12" y="280" fontFamily="monospace" fontSize="8.5" fontWeight="bold" fill="#38BDF8">SCAN_FPS: 60 // 300_DPI // EasyOCR v2.8</text>
    <text x="408" y="280" fontFamily="monospace" fontSize="8.5" fill="#8B5CF6" textAnchor="end">99.4% PRECISION</text>
  </svg>
);

// Confidence ring animated
const ConfidenceRing = () => (
  <svg viewBox="0 0 140 140" className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="cring-g" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#3B82F6" /><stop offset="50%" stopColor="#10B981" /><stop offset="100%" stopColor="#F59E0B" />
      </linearGradient>
    </defs>
    <rect width="140" height="140" rx="18" fill="#0F172A" />
    <circle cx="70" cy="66" r="45" fill="none" stroke="#1E293B" strokeWidth="10" />
    <circle cx="70" cy="66" r="45" fill="none" stroke="url(#cring-g)" strokeWidth="10" strokeLinecap="round" strokeDasharray="283" strokeDashoffset="14" transform="rotate(-90 70 66)">
      <animate attributeName="stroke-dashoffset" values="283;14" dur="2s" fill="freeze" calcMode="spline" keySplines="0.16 1 0.3 1" />
    </circle>
    <circle cx="70" cy="21" r="4.5" fill="#10B981">
      <animate attributeName="r" values="3.5;6;3.5" dur="1.5s" repeatCount="indefinite" />
    </circle>
    <text x="70" y="63" fontFamily="sans-serif" fontSize="16" fontWeight="800" fill="#F8FAFC" textAnchor="middle">99.4%</text>
    <text x="70" y="78" fontFamily="sans-serif" fontSize="7" fontWeight="700" fill="#10B981" textAnchor="middle">OCR ACCURACY</text>
    <text x="70" y="120" fontFamily="sans-serif" fontSize="7" fontWeight="bold" fill="#64748B" textAnchor="middle">FIELD PRECISION</text>
  </svg>
);

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [infoMsg, setInfoMsg] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setInfoMsg(null);

    if (!email.trim() || !password) {
      setErrorMsg("Please enter both email and password.");
      return;
    }

    setLoading(true);
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email: email.trim(),
        password
      });

      if (error) {
        const msg = error.message.toLowerCase();
        if (msg.includes("email not confirmed") || msg.includes("email_not_confirmed")) {
          setInfoMsg("Your email address is not confirmed. Please check your inbox (and spam folder) for a confirmation link from DocRefine, then sign in again.");
        } else if (msg.includes("invalid login credentials") || msg.includes("invalid credentials")) {
          setErrorMsg("Incorrect email or password. Please try again.");
        } else {
          setErrorMsg(error.message);
        }
        return;
      }

      if (data.session) {
        router.push("/dashboard");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "An unexpected error occurred. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-[#090D16] text-slate-100 selection:bg-violet-600/30 overflow-hidden">

      {/* ═══ LEFT PANEL ═══ */}
      <div className="hidden lg:flex lg:w-[52%] xl:w-[55%] flex-col relative">
        {/* Aurora ambient background */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-[-25%] right-[-15%] w-[550px] h-[550px] rounded-full bg-violet-600/18 blur-[130px]" />
          <div className="absolute bottom-[-15%] left-[-10%] w-[430px] h-[430px] rounded-full bg-amber-500/10 blur-[110px]" />
          <div className="absolute top-[40%] left-[30%] w-[320px] h-[320px] rounded-full bg-emerald-500/8 blur-[90px]" />
          {/* Dot pattern */}
          <svg className="absolute inset-0 w-full h-full opacity-[0.07]" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <pattern id="dots" x="0" y="0" width="28" height="28" patternUnits="userSpaceOnUse">
                <circle cx="1.5" cy="1.5" r="1.5" fill="#8B5CF6" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#dots)" />
          </svg>
        </div>

        <div className="relative z-10 flex flex-col h-full px-10 xl:px-14 py-10">
          {/* Brand */}
          <Link href="/" className="flex items-center gap-3 group w-fit">
            <div className="w-12 h-12 rounded-2xl bg-slate-950/60 border border-slate-700/50 p-1.5 shadow-xl shadow-violet-500/15 group-hover:border-violet-500/40 group-hover:shadow-violet-500/25 transition-all duration-300">
              <DocRefineLogo />
            </div>
            <div>
              <span className="block font-extrabold text-xl tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-violet-200 to-slate-400">
                DocRefine
              </span>
              <span className="block text-xs text-slate-500 -mt-0.5">Document Intelligence Platform</span>
            </div>
          </Link>

          {/* Hero copy */}
          <div className="flex-1 flex flex-col justify-center gap-6 mt-8">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-300 text-xs font-semibold mb-5">
                <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
                Next-Gen Multilingual OCR · AI Extraction
              </div>
              <h1 className="text-3xl xl:text-[2.6rem] font-extrabold text-white leading-[1.15] tracking-tight">
                Rescue. Refine.
                <br />
                <span className="bg-clip-text text-transparent bg-gradient-to-r from-violet-400 via-indigo-400 to-cyan-400">
                  Deliver Precision.
                </span>
              </h1>
              <p className="mt-4 text-sm text-slate-400 leading-relaxed max-w-md">
                AI-powered extraction for English, Hindi &amp; Marathi documents — 
                OCR, LLM structuring, confidence scoring and 4-format export in one workspace.
              </p>
            </div>

            {/* Hero graphic */}
            <div className="w-full max-w-[420px] rounded-2xl overflow-hidden border border-slate-800/50 shadow-2xl shadow-violet-900/20">
              <HeroGraphic />
            </div>

            {/* Stats row */}
            <div className="flex items-center gap-5">
              <div className="w-[88px] h-[88px] flex-shrink-0">
                <ConfidenceRing />
              </div>
              <div className="space-y-2.5">
                {[
                  { label: "Script Support", val: "English · Hindi · Marathi", color: "violet" },
                  { label: "Document Types", val: "7 Universal AI Schemas", color: "amber" },
                  { label: "Export Formats", val: "PDF · XLSX · CSV · JSON", color: "emerald" },
                ].map((s) => (
                  <div key={s.label} className="flex items-center gap-2.5">
                    <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${s.color === "violet" ? "bg-violet-400" : s.color === "amber" ? "bg-amber-400" : "bg-emerald-400"}`} />
                    <span className="text-xs text-slate-500">{s.label}:</span>
                    <span className={`text-xs font-semibold ${s.color === "violet" ? "text-violet-400" : s.color === "amber" ? "text-amber-400" : "text-emerald-400"}`}>{s.val}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <p className="text-xs text-slate-700 mt-6">© 2026 DocRefine · Secure Multilingual Extraction Platform</p>
        </div>
      </div>

      {/* ═══ RIGHT PANEL ═══ */}
      <div className="flex-1 flex flex-col items-center justify-center px-5 py-12 relative bg-slate-950/40 lg:border-l lg:border-slate-800/50">
        {/* Mobile brand */}
        <Link href="/" className="lg:hidden flex items-center gap-2.5 mb-8">
          <div className="w-9 h-9 rounded-xl bg-slate-900 border border-slate-700 p-1.5">
            <DocRefineLogo />
          </div>
          <span className="font-extrabold text-lg text-white">DocRefine</span>
        </Link>

        <div className="w-full max-w-[420px]">
          {/* Glow ring behind card */}
          <div className="absolute -inset-1 rounded-3xl bg-gradient-to-br from-violet-500/15 via-transparent to-indigo-500/10 blur-md pointer-events-none" />

          <div className="relative bg-slate-900/80 backdrop-blur-xl border border-slate-700/50 rounded-3xl p-8 xl:p-10 shadow-2xl space-y-6">
            <div>
              <h2 className="text-2xl font-extrabold text-white tracking-tight">Welcome Back</h2>
              <p className="text-sm text-slate-400 mt-1">Sign in to your DocRefine workspace</p>
            </div>

            {/* Info — email not confirmed */}
            {infoMsg && (
              <div className="flex items-start gap-3 p-4 rounded-xl bg-sky-500/10 border border-sky-500/30 text-sky-300 text-xs">
                <Info className="h-4 w-4 shrink-0 mt-0.5 text-sky-400" />
                <div>
                  <p className="font-semibold text-sky-200 mb-0.5">Email Not Confirmed</p>
                  <p>{infoMsg}</p>
                </div>
              </div>
            )}

            {/* Error */}
            {errorMsg && (
              <div className="flex items-start gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>{errorMsg}</span>
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-5">
              {/* Email */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Email Address</label>
                <div className="relative group">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none group-focus-within:text-violet-400 transition-colors" />
                  <input
                    type="email"
                    required
                    value={email}
                    autoComplete="email"
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@company.com"
                    className="w-full pl-10 pr-4 py-3 rounded-xl bg-slate-950/70 border border-slate-700/60 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 transition-all"
                  />
                </div>
              </div>

              {/* Password */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Password</label>
                <div className="relative group">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none group-focus-within:text-violet-400 transition-colors" />
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    value={password}
                    autoComplete="current-password"
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-12 py-3 rounded-xl bg-slate-950/70 border border-slate-700/60 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 transition-all"
                  />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition">
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 rounded-xl bg-gradient-to-r from-violet-600 via-violet-500 to-indigo-500 hover:from-violet-500 hover:via-violet-400 hover:to-indigo-400 text-white text-sm font-bold transition-all duration-200 shadow-lg shadow-violet-600/25 hover:shadow-violet-500/40 flex items-center justify-center gap-2.5 disabled:opacity-50 active:scale-[0.98]"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
                {loading ? "Signing In..." : "Sign In to Workspace"}
              </button>
            </form>

            <div className="relative flex items-center gap-3">
              <div className="flex-1 border-t border-slate-800" />
              <span className="text-xs text-slate-600">or</span>
              <div className="flex-1 border-t border-slate-800" />
            </div>

            <div className="text-center">
              <p className="text-sm text-slate-400">
                Don&apos;t have an account?{" "}
                <Link href="/register" className="text-violet-400 hover:text-violet-300 font-semibold transition">
                  Create one free →
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


