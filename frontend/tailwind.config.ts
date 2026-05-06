import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { 400: "#38bdf8", 500: "#0ea5e9", 600: "#0284c7" },
      },
      animation: {
        "fade-in": "fadeIn .15s ease-out",
      },
      keyframes: {
        fadeIn: { from: { opacity: "0", transform: "translateY(4px)" }, to: { opacity: "1", transform: "none" } },
      },
    },
  },
  plugins: [],
} satisfies Config;
