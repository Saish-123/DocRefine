"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "@/lib/supabaseClient";
import { Eye, EyeOff, Lock, Mail, User, ArrowRight, AlertCircle, CheckCircle2, Loader2, ShieldCheck, Sparkles } from "lucide-react";

// Inline DocRefine Logo SVG
const DocRefineLogo = () => (
  <svg viewBox="0 0 240 240" className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="reg-doc-bg" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#1E1B4B" /><stop offset="50%" stopColor="#0F172A" /><stop offset="100%" stopColor="#020617" />
      </linearGradient>
      <linearGradient id="reg-violet" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#C084FC" /><stop offset="50%" stopColor="#8B5CF6" /><stop offset="100%" stopColor="#6366F1" />
      </linearGradient>
      <linearGradient id="reg-laser" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stopColor="#38BDF8" /><stop offset="50%" stopColor="#F59E0B" /><stop offset="100%" stopColor="#10B981" />
      </linearGradient>
      <linearGradient id="reg-star" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#FDE047" /><stop offset="100%" stopColor="#EA580C" />
      </linearGradient>
      <filter id="reg-glow" x="-30%" y="-30%" width="160%" height="160%">
        <feGaussianBlur stdDeviation="8" result="blur" />
        <feComposite in="SourceGraphic" in2="blur" operator="over" />
      </filter>
    </defs>
    <rect width="240" height="240" rx="56" fill="#090D16" stroke="#1E293B" strokeWidth="2" />
    <g transform="translate(120,120)">
      <circle cx="0" cy="0" r="70" fill="url(#reg-violet)" opacity="0.15" filter="url(#reg-glow)" />
      <rect x="-42" y="-55" width="84" height="110" rx="14" fill="#0F172A" stroke="#334155" strokeWidth="2" transform="rotate(-8)" opacity="0.7" />
      <path d="M -40 -60 L 15 -60 L 45 -30 L 45 55 L -40 55 Z" fill="url(#reg-doc-bg)" stroke="url(#reg-violet)" strokeWidth="3" strokeLinejoin="round" />
      <path d="M 15 -60 L 15 -30 L 45 -30" fill="#1E293B" stroke="url(#reg-violet)" strokeWidth="2" />
      <line x1="-24" y1="-34" x2="2" y2="-34" stroke="#64748B" strokeWidth="3.5" strokeLinecap="round" opacity="0.8" />
      <line x1="-24" y1="-18" x2="18" y2="-18" stroke="#64748B" strokeWidth="3.5" strokeLinecap="round" opacity="0.8" />
      <line x1="-52" y1="2" x2="52" y2="2" stroke="url(#reg-laser)" strokeWidth="3.5" strokeLinecap="round" filter="url(#reg-glow)" />
      <line x1="-24" y1="22" x2="12" y2="22" stroke="#8B5CF6" strokeWidth="4" strokeLinecap="round" />
      <line x1="-24" y1="38" x2="24" y2="38" stroke="#10B981" strokeWidth="4" strokeLinecap="round" />
      <g transform="translate(24,18)">
        <path d="M 0 -18 Q 0 0 18 0 Q 0 0 0 18 Q 0 0 -18 0 Q 0 0 0 -18 Z" fill="url(#reg-star)" filter="url(#reg-glow)" />
        <circle cx="0" cy="0" r="3.5" fill="#FFFFFF" />
      </g>
    </g>
  </svg>
);

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [redirectCountdown, setRedirectCountdown] = useState<number | null>(null);

  useEffect(() => {
    if (redirectCountdown === null) return;
    if (redirectCountdown <= 0) {
      router.push("/login");
      return;
    }
    const timer = setTimeout(() => {
      setRedirectCountdown(redirectCountdown - 1);
    }, 1000);
    return () => clearTimeout(timer);
  }, [redirectCountdown, router]);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);

    // Client-side validations
    if (!email.trim() || !password) {
      setErrorMsg("Please enter both email and password.");
      return;
    }

    if (password.length < 8) {
      setErrorMsg("Password must be at least 8 characters long.");
      return;
    }

    if (password !== confirmPassword) {
      setErrorMsg("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      const { data, error } = await supabase.auth.signUp({
        email: email.trim(),
        password,
        options: {
          data: {
            full_name: fullName.trim()
          },
          emailRedirectTo: typeof window !== "undefined" ? `${window.location.origin}/auth/callback` : undefined
        }
      });

      if (error) {
        setErrorMsg(error.message);
        return;
      }

      // Clear all fields on success
      setFullName("");
      setEmail("");
      setPassword("");
      setConfirmPassword("");

      if (data.session) {
        // Direct session created -> redirect to dashboard
        setSuccessMsg("Registration successful! Redirecting to workspace...");
        setTimeout(() => {
          router.push("/dashboard");
        }, 1500);
      } else {
        // Email confirmation flow or created -> redirect to login
        setSuccessMsg(
          "Account registered successfully! If email confirmation is required, please check your inbox to verify, then sign in."
        );
        setRedirectCountdown(3);
      }
    } catch (err: any) {
      setErrorMsg(err.message || "An unexpected error occurred during registration.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-[#090D16] text-slate-100 selection:bg-violet-600/30 overflow-hidden">

      {/* ═══ LEFT PANEL ═══ */}
      <div className="hidden lg:flex lg:w-[50%] xl:w-[52%] flex-col relative overflow-hidden">
        {/* Aurora ambient glow */}
        <div className="absolute inset-0">
          <div className="absolute top-[-20%] left-[-10%] w-[500px] h-[500px] rounded-full bg-violet-600/20 blur-[130px]" />
          <div className="absolute bottom-[-10%] right-[-5%] w-[450px] h-[450px] rounded-full bg-indigo-600/15 blur-[120px]" />
          <div className="absolute top-[40%] right-[20%] w-[300px] h-[300px] rounded-full bg-amber-500/10 blur-[100px]" />
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

          {/* Main feature highlights */}
          <div className="flex-1 flex flex-col justify-center gap-6 mt-8 max-w-lg">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-300 text-xs font-semibold mb-5">
                <Sparkles className="w-3.5 h-3.5 text-violet-400" />
                Join Document Intelligence Reviewers
              </div>
              <h1 className="text-3xl xl:text-4xl font-extrabold text-white leading-tight tracking-tight">
                Enterprise Document AI,
                <br />
                <span className="bg-clip-text text-transparent bg-gradient-to-r from-violet-400 via-indigo-400 to-cyan-400">
                  Built for Indian Documents.
                </span>
              </h1>
              <p className="mt-4 text-sm text-slate-400 leading-relaxed">
                Create your reviewer workspace to process marksheets, fee receipts, Aadhaar, PAN, bank statements, 7/12 land records, and prescriptions with high precision.
              </p>
            </div>

            {/* Feature cards */}
            <div className="grid grid-cols-1 gap-3.5 pt-2">
              {[
                {
                  icon: <ShieldCheck className="h-5 w-5 text-violet-400" />,
                  title: "Multilingual OCR (EN · HI · MR)",
                  desc: "Native Devanagari & English text recognition with confidence scores."
                },
                {
                  icon: <Sparkles className="h-5 w-5 text-amber-400" />,
                  title: "Anti-Hallucination Extraction",
                  desc: "Strict schema guardrails extract ONLY factual document data."
                },
                {
                  icon: <ArrowRight className="h-5 w-5 text-emerald-400" />,
                  title: "4-Format Audit-Ready Export",
                  desc: "One-click downloads in PDF, XLSX, Unicode CSV, and JSON."
                }
              ].map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-3.5 p-4 rounded-2xl bg-slate-900/50 border border-slate-800/80 backdrop-blur-sm"
                >
                  <div className="p-2 rounded-xl bg-slate-800/60 border border-slate-700/50 shrink-0">
                    {item.icon}
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-slate-200">{item.title}</h4>
                    <p className="text-xs text-slate-400 mt-0.5">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <p className="text-xs text-slate-700 mt-6">© 2026 DocRefine · Secure Multilingual Extraction Platform</p>
        </div>
      </div>

      {/* ═══ RIGHT PANEL (FORM) ═══ */}
      <div className="flex-1 flex flex-col items-center justify-center px-5 py-10 relative bg-slate-950/40 lg:border-l lg:border-slate-800/50 overflow-y-auto">
        {/* Mobile brand */}
        <Link href="/" className="lg:hidden flex items-center gap-2.5 mb-6">
          <div className="w-9 h-9 rounded-xl bg-slate-900 border border-slate-700 p-1.5">
            <DocRefineLogo />
          </div>
          <span className="font-extrabold text-lg text-white">DocRefine</span>
        </Link>

        <div className="w-full max-w-[440px] my-auto">
          {/* Glow backdrop */}
          <div className="absolute -inset-1 rounded-3xl bg-gradient-to-br from-violet-500/15 via-transparent to-indigo-500/10 blur-md pointer-events-none" />

          <div className="relative bg-slate-900/80 backdrop-blur-xl border border-slate-700/50 rounded-3xl p-8 xl:p-10 shadow-2xl space-y-5">
            <div>
              <h2 className="text-2xl font-extrabold text-white tracking-tight">Create Account</h2>
              <p className="text-sm text-slate-400 mt-1">Get started with your DocRefine workspace</p>
            </div>

            {/* Error Message */}
            {errorMsg && (
              <div className="flex items-start gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs animate-fade-in">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Success Message & Redirect Alert */}
            {successMsg && (
              <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs space-y-2 animate-fade-in">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 shrink-0 mt-0.5 text-emerald-400" />
                  <div>
                    <p className="font-bold text-emerald-200 text-sm">Account Created!</p>
                    <p className="mt-1 leading-relaxed">{successMsg}</p>
                  </div>
                </div>
                {redirectCountdown !== null && (
                  <div className="pt-2 border-t border-emerald-500/20 flex items-center justify-between">
                    <span className="text-emerald-400/80 text-[11px]">
                      Redirecting to login in <b className="text-white">{redirectCountdown}s</b>...
                    </span>
                    <button
                      onClick={() => router.push("/login")}
                      className="px-3 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition flex items-center gap-1"
                    >
                      Go to Login <ArrowRight className="h-3 w-3" />
                    </button>
                  </div>
                )}
              </div>
            )}

            <form onSubmit={handleRegister} className="space-y-4">
              {/* Full Name */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Full Name</label>
                <div className="relative group">
                  <User className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none group-focus-within:text-violet-400 transition-colors" />
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Saish Panhalkar"
                    className="w-full pl-10 pr-4 py-3 rounded-xl bg-slate-950/70 border border-slate-700/60 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 transition-all"
                  />
                </div>
              </div>

              {/* Email Address */}
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
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Password (Min 8 Characters)</label>
                <div className="relative group">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none group-focus-within:text-violet-400 transition-colors" />
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    value={password}
                    autoComplete="new-password"
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-12 py-3 rounded-xl bg-slate-950/70 border border-slate-700/60 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 transition-all"
                  />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition">
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* Confirm Password */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Confirm Password</label>
                <div className="relative group">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none group-focus-within:text-violet-400 transition-colors" />
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    required
                    value={confirmPassword}
                    autoComplete="new-password"
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-12 py-3 rounded-xl bg-slate-950/70 border border-slate-700/60 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 transition-all"
                  />
                  <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition">
                    {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 py-3.5 rounded-xl bg-gradient-to-r from-violet-600 via-violet-500 to-indigo-500 hover:from-violet-500 hover:via-violet-400 hover:to-indigo-400 text-white text-sm font-bold transition-all duration-200 shadow-lg shadow-violet-600/25 hover:shadow-violet-500/40 flex items-center justify-center gap-2.5 disabled:opacity-50 active:scale-[0.98]"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                {loading ? "Creating Reviewer Account..." : "Create Free Account"}
              </button>
            </form>

            <div className="relative flex items-center gap-3">
              <div className="flex-1 border-t border-slate-800" />
              <span className="text-xs text-slate-600">or</span>
              <div className="flex-1 border-t border-slate-800" />
            </div>

            <div className="text-center">
              <p className="text-sm text-slate-400">
                Already have an account?{" "}
                <Link href="/login" className="text-violet-400 hover:text-violet-300 font-semibold transition">
                  Sign In →
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

