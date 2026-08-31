"use client";

import React, { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { Header } from "@/components/Header";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import {
  ArrowRight,
  Zap,
  Layers,
  FileCheck2,
  Languages,
  Activity,
  Sliders,
  Scale,
  Check,
} from "lucide-react";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

const PIPELINE_STAGES = [
  {
    label: "Capture",
    detail: "Phone-camera photo or scan, however imperfect — tilted, shadowed, low-light.",
  },
  {
    label: "Rescue",
    detail: "Hough deskew, LAB CLAHE contrast recovery, shadow correction, Lanczos 2K upscale.",
  },
  {
    label: "Extract",
    detail: "Trilingual EasyOCR (English, Hindi, Marathi) into strict per-document-type schemas.",
  },
  {
    label: "Verify",
    detail: "Per-field confidence scoring and cross-document consistency, ready for review.",
  },
];

const FEATURES = [
  {
    icon: Zap,
    title: "Adaptive rescue pipeline",
    body: "Raw camera uploads with blur, extreme tilt, or low contrast get automated denoise, sub-pixel deskew, and CLAHE enhancement before OCR ever runs.",
  },
  {
    icon: FileCheck2,
    title: "Multilingual OCR, strict schemas",
    body: "Devanagari (Hindi & Marathi) and English recognized natively. Validators enforce exact field formats for Aadhaar, PAN, IFSC, ISO dates, marksheets, and receipts.",
  },
  {
    icon: Scale,
    title: "Deterministic field confidence",
    body: "Every field scores 0–100 from per-token OCR confidence, structuring confidence, format validation, and document quality — not a black-box guess.",
  },
  {
    icon: Layers,
    title: "Cross-document consistency",
    body: "Names, dates of birth, and ID numbers get checked against each other across every document in a case, with a grounded Q&A assistant for fast review.",
  },
];

export default function LandingPage() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  const heroDocRef = useRef<HTMLDivElement>(null);
  const scanLineRef = useRef<HTMLDivElement>(null);
  const fieldRefs = useRef<Array<HTMLDivElement | null>>([]);
  const pipelineRailRef = useRef<HTMLDivElement>(null);
  const pipelineDotRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const hash = window.location.hash;
      const search = window.location.search;
      if (hash.includes("access_token") || search.includes("code=")) {
        setTimeout(() => {
          router.push("/dashboard");
        }, 600);
      }
    }

    supabase.auth.getSession().then(({ data: { session } }) => {
      setIsAuthenticated(!!session);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      setIsAuthenticated(!!session);
      if ((event === "SIGNED_IN" || event === "USER_UPDATED") && session) {
        router.push("/dashboard");
      }
    });

    return () => subscription.unsubscribe();
  }, [router]);

  // --- Signature motion: one orchestrated scan-reveal on the hero -------
  // The document scan-line sweeps down through the mock card once as it
  // enters view, revealing extracted field chips as it passes — this
  // mirrors the actual product mechanic (OCR scanning a page) rather than
  // being decorative motion. A second, scroll-scrubbed animation moves a
  // dot along the pipeline rail as the reader scrolls past the four
  // pipeline stages. Both respect prefers-reduced-motion.
  useEffect(() => {
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) return;

    const ctx = gsap.context(() => {
      if (heroDocRef.current && scanLineRef.current) {
        const fields = fieldRefs.current.filter(Boolean) as HTMLDivElement[];
        gsap.set(fields, { autoAlpha: 0, y: 6 });

        const tl = gsap.timeline({
          scrollTrigger: {
            trigger: heroDocRef.current,
            start: "top 75%",
            once: true,
          },
        });

        tl.fromTo(
          scanLineRef.current,
          { yPercent: -10, autoAlpha: 0 },
          { yPercent: 10, autoAlpha: 1, duration: 0.4, ease: "power1.out" }
        )
          .to(scanLineRef.current, {
            yPercent: 100,
            duration: 1.4,
            ease: "power1.inOut",
            onUpdate: function () {
              const progress = this.progress();
              fields.forEach((el, i) => {
                const threshold = (i + 1) / (fields.length + 1);
                if (progress >= threshold) {
                  gsap.to(el, { autoAlpha: 1, y: 0, duration: 0.35, ease: "power2.out", overwrite: true });
                }
              });
            },
          })
          .to(scanLineRef.current, { autoAlpha: 0, duration: 0.3 }, "-=0.1");
      }

      if (pipelineRailRef.current && pipelineDotRef.current) {
        gsap.fromTo(
          pipelineDotRef.current,
          { left: "0%" },
          {
            left: "100%",
            ease: "none",
            scrollTrigger: {
              trigger: pipelineRailRef.current,
              start: "top 70%",
              end: "bottom 40%",
              scrub: 0.6,
            },
          }
        );
      }
    });

    return () => ctx.revert();
  }, []);

  const handleStartNow = () => {
    if (isAuthenticated) {
      router.push("/dashboard");
    } else {
      router.push("/login");
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-ink text-paper-100 selection:bg-verify/25 selection:text-verify overflow-x-hidden">
      <Header showNavLinks={true} />

      <main className="flex-1 flex flex-col items-center relative">
        {/* Hero */}
        <section className="w-full max-w-6xl mx-auto px-6 pt-20 pb-16 grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-7 space-y-7 text-left">
            <div className="inline-flex items-center space-x-2 text-verify text-xs font-semibold tracking-wide">
              <span className="w-1.5 h-1.5 rounded-full bg-verify" />
              <span>Document rescue &amp; verification engine</span>
            </div>

            <h1 className="font-display text-5xl sm:text-6xl xl:text-[5.2rem] leading-[1.02] text-paper-100">
              Every document
              <br />
              tells the truth
              <br />
              <span className="verify-text-gradient">once you can read it.</span>
            </h1>

            <p className="text-base sm:text-lg text-paper-500 max-w-lg leading-relaxed">
              DocRefine rescues tilted, blurry, low-contrast identity cards, marksheets, receipts,
              and bank records in English, Hindi &amp; Marathi — then scores every extracted field
              so reviewers know exactly what to trust.
            </p>

            <div className="flex flex-col sm:flex-row items-start gap-4 pt-2">
              <button
                onClick={handleStartNow}
                className="px-7 py-3.5 rounded-md verify-gradient text-ink font-bold text-sm transition hover:brightness-110 flex items-center justify-center gap-2.5 group active:scale-[0.98]"
              >
                <span>{isAuthenticated ? "Enter review workspace" : "Open the workspace — free"}</span>
                <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </button>
              <a
                href="/login"
                className="px-6 py-3.5 rounded-md bg-ink border border-ink-rule hover:border-paper-500/40 text-paper-300 font-semibold text-sm transition"
              >
                Sign in to account
              </a>
            </div>
          </div>

          {/* Signature moment: document scan-reveal */}
          <div className="lg:col-span-5">
            <div
              ref={heroDocRef}
              className="relative w-full aspect-[4/5] rounded-lg panel overflow-hidden"
            >
              <div className="absolute inset-0 p-6 flex flex-col gap-3">
                <div ref={(el) => { fieldRefs.current[0] = el; }} className="h-8 w-2/3 rounded bg-verify/10 border border-verify/25 flex items-center px-3">
                  <span className="text-[11px] text-verify font-mono">full_name — 96%</span>
                </div>
                <div ref={(el) => { fieldRefs.current[1] = el; }} className="h-8 w-1/2 rounded bg-ink-raised border border-ink-rule flex items-center px-3">
                  <span className="text-[11px] text-paper-300 font-mono">date_of_birth — 91%</span>
                </div>
                <div ref={(el) => { fieldRefs.current[2] = el; }} className="h-8 w-3/4 rounded bg-ink-raised border border-ink-rule flex items-center px-3">
                  <span className="text-[11px] text-paper-300 font-mono">document_number — 98%</span>
                </div>
                <div ref={(el) => { fieldRefs.current[3] = el; }} className="h-14 w-full rounded bg-signal-amber/10 border border-signal-amber/25 flex items-center px-3">
                  <span className="text-[11px] text-signal-amber font-mono">address — 68% · needs review</span>
                </div>
                <div className="flex-1" />
                <div ref={(el) => { fieldRefs.current[4] = el; }} className="text-[11px] text-paper-500 font-mono">
                  quality_score: 84/100 · acceptable
                </div>
              </div>
              {/* Scan-line beam */}
              <div
                ref={scanLineRef}
                className="absolute left-0 right-0 h-16 pointer-events-none opacity-0"
                style={{
                  background: "linear-gradient(180deg, transparent, rgba(33,240,194,0.22) 45%, rgba(33,240,194,0.5) 50%, rgba(33,240,194,0.22) 55%, transparent)",
                }}
              />
            </div>
          </div>
        </section>

        {/* Quick metrics */}
        <section className="w-full max-w-6xl mx-auto px-6 pb-16">
          <div className="rule-line mb-10" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-ink-rule rounded-lg overflow-hidden">
            {[
              { icon: Languages, label: "Multilingual native", value: "EN / HI / MR", sub: "Devanagari Unicode & English" },
              { icon: Sliders, label: "Super-res rescue", value: "2K / 300 DPI", sub: "Lanczos & OpenCV deskew" },
              { icon: Activity, label: "Deterministic score", value: "4-part formula", sub: "OCR + LLM + format + quality" },
              { icon: FileCheck2, label: "Structured export", value: "CSV / XLSX / PDF", sub: "Plus canonical JSON payload" },
            ].map((m, i) => (
              <div key={i} className="panel border-0 p-5 text-left">
                <div className="flex items-center gap-2 text-verify text-xs font-semibold mb-2">
                  <m.icon className="h-4 w-4" />
                  <span>{m.label}</span>
                </div>
                <p className="text-lg font-bold text-paper-100 tabular">{m.value}</p>
                <p className="text-[11px] text-paper-500">{m.sub}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Pipeline — a real sequence, shown as one */}
        <section className="w-full max-w-6xl mx-auto px-6 py-16">
          <div className="max-w-xl mb-12">
            <h2 className="font-display text-3xl sm:text-4xl text-paper-100 mb-3">The rescue pipeline</h2>
            <p className="text-sm text-paper-500 leading-relaxed">
              Four stages, always in this order, from a flawed photo to a verified structured record.
            </p>
          </div>

          <div ref={pipelineRailRef} className="relative">
            <div className="absolute top-5 left-0 right-0 h-px bg-ink-rule" />
            <div ref={pipelineDotRef} className="absolute top-5 -translate-x-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full bg-verify shadow-[0_0_12px_rgba(33,240,194,0.7)]" />

            <div className="grid grid-cols-1 sm:grid-cols-4 gap-8 relative">
              {PIPELINE_STAGES.map((stage, i) => (
                <div key={stage.label} className="pt-12 text-left">
                  <div className="absolute top-3.5 w-3 h-3 rounded-full border-2 border-ink bg-ink-rule" style={{ left: `calc(${(i / (PIPELINE_STAGES.length - 1)) * 100}% - 6px)` }} />
                  <span className="text-xs font-mono text-paper-500">0{i + 1}</span>
                  <h3 className="font-display text-xl text-paper-100 mt-1 mb-2">{stage.label}</h3>
                  <p className="text-xs text-paper-500 leading-relaxed">{stage.detail}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Feature grid */}
        <section className="w-full max-w-6xl mx-auto px-6 py-16 border-t border-ink-rule">
          <div className="max-w-xl mb-12">
            <h2 className="font-display text-3xl sm:text-4xl text-paper-100 mb-3">
              Built for underwriting speed
            </h2>
            <p className="text-sm text-paper-500 leading-relaxed">
              Engineered to remove reviewer bottlenecks on KYC identity proofs, tax cards, marksheets,
              receipts, and financial statements.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-ink-rule rounded-lg overflow-hidden">
            {FEATURES.map((f) => (
              <div key={f.title} className="panel border-0 p-7 flex flex-col space-y-3.5">
                <div className="h-10 w-10 rounded-md bg-verify/10 border border-verify/25 flex items-center justify-center text-verify">
                  <f.icon className="h-5 w-5" />
                </div>
                <h3 className="text-base font-bold text-paper-100">{f.title}</h3>
                <p className="text-xs text-paper-500 leading-relaxed">{f.body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="w-full max-w-6xl mx-auto px-6 py-16">
          <div className="rounded-lg panel p-8 sm:p-12 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
            <div className="max-w-lg">
              <h2 className="font-display text-2xl sm:text-3xl text-paper-100 mb-2">
                Ready to verify with precision?
              </h2>
              <p className="text-sm text-paper-500">
                Start extracting Hindi, Marathi, and English documents with zero setup.
              </p>
            </div>
            <button
              onClick={handleStartNow}
              className="px-7 py-3.5 rounded-md verify-gradient text-ink font-bold text-sm transition hover:brightness-110 flex items-center gap-2.5 shrink-0"
            >
              <span>Open workspace</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </section>
      </main>

      <footer className="border-t border-ink-rule py-8 px-6 text-center text-xs text-paper-500">
        <p>DocRefine &copy; {new Date().getFullYear()} — Multilingual Document Intelligence &amp; Verification Platform</p>
      </footer>
    </div>
  );
}
