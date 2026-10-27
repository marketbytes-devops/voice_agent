import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ayur: {
          50: "#ecfdf5",
          100: "#d1fae5",
          200: "#a7f3d0",
          300: "#6ee7b7",
          400: "#34d399",
          500: "#10b981",
          600: "#059669",
          700: "#047857",
          800: "#065f46",
          900: "#064e3b",
        },
        dark: {
          bg: "#090d16",
          card: "#111827",
          border: "#1f2937",
          muted: "#9ca3af",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "sans-serif"],
        malayalam: ["var(--font-noto-malayalam)", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
