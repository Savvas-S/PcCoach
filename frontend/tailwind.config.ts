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
        "aurora-1": {
          "0%, 100%": { transform: "translate(0%, 0%) scale(1)" },
          "25%": { transform: "translate(5%, -8%) scale(1.05)" },
          "50%": { transform: "translate(-3%, 6%) scale(0.98)" },
          "75%": { transform: "translate(-6%, -3%) scale(1.02)" },
        },
        "aurora-2": {
          "0%, 100%": { transform: "translate(0%, 0%) scale(1.02)" },
          "33%": { transform: "translate(-8%, 5%) scale(0.95)" },
          "66%": { transform: "translate(6%, -4%) scale(1.08)" },
        },
        "float-1": {
          "0%, 100%": { transform: "translate(0px, 0px)" },
          "25%": { transform: "translate(30px, -25px)" },
          "50%": { transform: "translate(-15px, 15px)" },
          "75%": { transform: "translate(20px, -10px)" },
        },
        "float-2": {
          "0%, 100%": { transform: "translate(0px, 0px)" },
          "33%": { transform: "translate(-25px, 30px)" },
          "66%": { transform: "translate(20px, -20px)" },
        },
        "float-3": {
          "0%, 100%": { transform: "translate(0px, 0px)" },
          "20%": { transform: "translate(15px, 25px)" },
          "40%": { transform: "translate(-20px, -10px)" },
          "60%": { transform: "translate(25px, -20px)" },
          "80%": { transform: "translate(-10px, 15px)" },
        },
        "pulse-glow": {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.6s ease both",
        "aurora-1": "aurora-1 40s ease-in-out infinite",
        "aurora-2": "aurora-2 50s ease-in-out infinite",
        "float-1": "float-1 30s ease-in-out infinite",
        "float-2": "float-2 36s ease-in-out infinite",
        "float-3": "float-3 44s ease-in-out infinite",
        "pulse-glow": "pulse-glow 5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
