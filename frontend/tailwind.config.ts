import type { Config } from "tailwindcss";
export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["'Bebas Neue'", "cursive"],
        body:    ["'DM Sans'", "sans-serif"],
        mono:    ["'DM Mono'", "monospace"],
      },
      colors: {
        ink:   "#0a0a0f",
        paper: "#f5f0e8",
        acid:  "#c8ff00",
        blood: "#ff2d55",
        gold:  "#ffd700",
        fog:   "#1a1a2e",
      },
    },
  },
  plugins: [],
} satisfies Config;
