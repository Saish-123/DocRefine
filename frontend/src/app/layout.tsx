import "./globals.css";
import type { Metadata } from "next";
import { Fraunces, Manrope } from "next/font/google";
import React from "react";

// Display serif with ink-trap detailing - carries the "official document"
// gravitas for headlines. Variable font, used only for display/headline
// roles (see .font-display / h1-h3 in globals.css).
const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
  axes: ["opsz", "SOFT", "WONK"],
});

// Geometric grotesk for UI, body copy, and data-dense dashboard surfaces -
// distinct from the display face, clean at small sizes.
const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "DocRefine - Next-Gen Multilingual Document Intelligence & Verification",
  description: "Enterprise workspace for document rescue, OpenCV 2K enhancement, multilingual OCR (English/Hindi/Marathi), and 100% precise structured extraction.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`dark ${fraunces.variable} ${manrope.variable}`}>
      <body className="min-h-screen bg-ink text-paper-100 antialiased selection:bg-verify/25 selection:text-verify">
        {children}
      </body>
    </html>
  );
}
