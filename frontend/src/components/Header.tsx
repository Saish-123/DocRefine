"use client";

import React, { useEffect, useState } from "react";
import { ShieldCheck, Moon, Sun, HelpCircle, LogOut, User } from "lucide-react";
import { supabase } from "@/lib/supabaseClient";
import { useRouter } from "next/navigation";

interface HeaderProps {
  onStartTour?: () => void;
  language?: string;
  onLanguageChange?: (lang: string) => void;
  showNavLinks?: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onStartTour, showNavLinks = false }) => {
  const router = useRouter();
  const [isDark, setIsDark] = useState(true);
  const [backendReady, setBackendReady] = useState<boolean | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);

  useEffect(() => {
    fetch("/health/ready")
      .then((res) => res.json())
      .then((data) => setBackendReady(data.status === "ready"))
      .catch(() => setBackendReady(false));

    supabase.auth.getSession().then(({ data: { session } }) => {
      setUserEmail(session?.user?.email ?? null);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUserEmail(session?.user?.email ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  };

  const toggleTheme = () => {
    const next = !isDark;
    setIsDark(next);
    if (next) {
      document.documentElement.classList.add("dark");
      document.documentElement.classList.remove("light");
    } else {
      document.documentElement.classList.remove("dark");
      document.documentElement.classList.add("light");
    }
  };

  return (
    <header className="sticky top-0 z-40 w-full panel border-b px-6 py-3.5 flex items-center justify-between">
      <div className="flex items-center space-x-4">
        <a href="/" className="flex items-center space-x-3 group">
          {/* Signature mark: a document corner with a single scan-line -
              flat ink surface, one accent color, no gradient blob. */}
          <div className="h-10 w-10 rounded-md bg-ink border border-ink-rule flex items-center justify-center overflow-hidden group-hover:border-verify/50 transition-colors">
            <svg viewBox="0 0 40 40" className="w-6 h-6" xmlns="http://www.w3.org/2000/svg">
              <path
                d="M10 6h14l6 6v22a2 2 0 0 1-2 2H10a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2Z"
                fill="none"
                stroke="#6C6F76"
                strokeWidth="1.6"
              />
              <path d="M24 6v6h6" fill="none" stroke="#6C6F76" strokeWidth="1.6" />
              <line x1="12" y1="20" x2="28" y2="20" stroke="#21F0C2" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-display text-xl tracking-tight text-paper-100">
                DocRefine
              </span>
              <span className="text-[10px] font-semibold tracking-wide px-2 py-0.5 rounded bg-verify/10 text-verify border border-verify/25">
                AI Intelligence
              </span>
            </div>
            <p className="text-xs text-paper-500">Multilingual Document Rescue &amp; Verification</p>
          </div>
        </a>
      </div>

      <div className="flex items-center space-x-3">
        {/* Security / Verification Badge */}
        <div className="hidden md:flex items-center space-x-1.5 px-3 py-1 rounded-md bg-verify/10 border border-verify/25 text-verify text-xs font-medium">
          <ShieldCheck className="h-4 w-4" />
          <span>Secure Private Storage (RLS)</span>
        </div>

        {/* Backend Status Indicator */}
        <div className="flex items-center space-x-2 px-2.5 py-1 rounded-md bg-ink border border-ink-rule text-xs text-paper-300">
          <div className={`h-2 w-2 rounded-full ${backendReady ? "bg-verify animate-pulse" : "bg-signal-amber"}`} />
          <span className="font-mono text-[11px] tabular">{backendReady ? "Pipeline Online" : "Connecting..."}</span>
        </div>

        {/* Guided Tour Trigger (if provided) */}
        {onStartTour && (
          <button
            onClick={onStartTour}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-ink hover:bg-ink-raised text-paper-300 text-xs font-medium transition border border-ink-rule"
            title="Start Guided Walkthrough"
          >
            <HelpCircle className="h-4 w-4 text-verify" />
            <span>Walkthrough</span>
          </button>
        )}

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-md bg-ink hover:bg-ink-raised text-paper-300 transition border border-ink-rule"
          title="Toggle Dark/Light Mode"
        >
          {isDark ? <Sun className="h-4 w-4 text-signal-amber" /> : <Moon className="h-4 w-4 text-verify" />}
        </button>

        {/* Auth status or Links */}
        {userEmail ? (
          <div className="flex items-center space-x-2 pl-2 border-l border-ink-rule">
            <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-ink border border-ink-rule text-paper-300 text-xs font-medium">
              <User className="h-3.5 w-3.5 text-verify" />
              <span className="max-w-[140px] truncate">{userEmail}</span>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center space-x-1 px-3 py-1.5 rounded-md bg-signal-red/10 hover:bg-signal-red/20 text-signal-red border border-signal-red/30 text-xs font-semibold transition"
              title="Sign Out"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span>Logout</span>
            </button>
          </div>
        ) : showNavLinks ? (
          <div className="flex items-center space-x-2 pl-2 border-l border-ink-rule">
            <a
              href="/login"
              className="px-3 py-1.5 rounded-md bg-ink hover:bg-ink-raised text-paper-100 text-xs font-semibold border border-ink-rule transition"
            >
              Login
            </a>
            <a
              href="/register"
              className="px-3 py-1.5 rounded-md verify-gradient text-ink text-xs font-bold transition hover:brightness-110"
            >
              Register
            </a>
          </div>
        ) : null}
      </div>
    </header>
  );
};
