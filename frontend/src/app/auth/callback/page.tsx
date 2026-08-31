"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { Loader2, CheckCircle2 } from "lucide-react";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [status, setStatus] = useState("Verifying authentication session...");

  useEffect(() => {
    const handleAuth = async () => {
      try {
        const { data: { session }, error } = await supabase.auth.getSession();
        if (session) {
          setStatus("Authentication verified! Redirecting to workspace...");
          setTimeout(() => {
            router.push("/dashboard");
          }, 500);
          return;
        }

        // If code query param is present
        const searchParams = new URLSearchParams(window.location.search);
        const code = searchParams.get("code");
        if (code) {
          const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);
          if (!exchangeError) {
            setStatus("Email confirmed! Redirecting to workspace...");
            setTimeout(() => {
              router.push("/dashboard");
            }, 500);
            return;
          }
        }

        // Fallback
        router.push("/dashboard");
      } catch (err) {
        router.push("/login");
      }
    };

    handleAuth();
  }, [router]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#090D16] text-slate-100 px-4">
      <div className="p-8 rounded-3xl bg-slate-900/80 border border-slate-700/60 shadow-2xl flex flex-col items-center space-y-4 text-center max-w-sm">
        <Loader2 className="h-8 w-8 text-violet-400 animate-spin" />
        <p className="text-sm font-semibold text-slate-200">{status}</p>
      </div>
    </div>
  );
}
