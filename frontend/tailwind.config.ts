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
        "obsidian-bg": "#141414",
        "obsidian-surface": "#1C1C1C",
        "obsidian-raised": "#242424",
        "obsidian-border": "#2A2A2A",
        "obsidian-bright": "#3A3A3A",
        "obsidian": "#C9A84C",
        "obsidian-text": "#F5F0E8",
        "obsidian-muted": "#8A8070",
        "obsidian-muted-light": "#5A5045",
      },
      fontFamily: {
        display: ["var(--font-cormorant)", "Georgia", "serif"],
        body: ["var(--font-outfit)", "sans-serif"],
        mono: ["var(--font-jb)", "monospace"],
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(14px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.6s ease both",
      },
    },
  },
  plugins: [],
};

export default config;
