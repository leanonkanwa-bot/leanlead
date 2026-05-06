import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#fff4ee",
          100: "#ffe2cc",
          200: "#ffc59a",
          300: "#ffaa70",
          400: "#ff8c47",
          500: "#ff751f",
          600: "#e5600e",
          700: "#b84a08",
          800: "#8a3606",
          900: "#5c2404",
          950: "#3d1602",
        },
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
