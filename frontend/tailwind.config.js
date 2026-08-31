/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",

        // --- Design system: "Verification Lab" palette ---------------
        // Replaces the generic violet/indigo SaaS palette. Named for what
        // each color does in this product, not just a hue.
        ink: {
          DEFAULT: "#0A0B0D", // canvas - true near-black, cool undertone
          panel: "#131417",   // raised surface (cards, header) - flat, no blur
          rule: "#26282D",    // hairline borders/dividers
          raised: "#1B1D21",  // hover state for panels
        },
        paper: {
          100: "#F3F4F1", // primary text - warm off-white, not pure #fff
          300: "#C9CBCC",
          500: "#9A9EA6", // muted/secondary text
          700: "#6C6F76",
        },
        // Signature accent - the ONE bold color, used sparingly (CTAs,
        // the hero scan-line, active states) rather than tinting everything.
        verify: {
          DEFAULT: "#21F0C2",
          dim: "#159A81",
          wash: "rgba(33, 240, 194, 0.10)",
        },
        // Semantic states, reused from the confidence-band system already
        // in the product (acceptable / warning / needs_reupload) rather
        // than introduced as decoration.
        signal: {
          amber: "#F5A623",
          red: "#FF5470",
        },

        brand: {
          50: "#eef2ff",
          100: "#e0e7ff",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
          900: "#312e81"
        }
      },
      fontFamily: {
        display: ["var(--font-display)", "serif"],
        sans: ["var(--font-sans)", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'scan-sweep': 'scan-sweep 3.2s cubic-bezier(0.65, 0, 0.35, 1) infinite',
      },
      keyframes: {
        'scan-sweep': {
          '0%, 100%': { transform: 'translateY(-2%)' },
          '50%': { transform: 'translateY(102%)' },
        },
      },
    },
  },
  plugins: [],
}
