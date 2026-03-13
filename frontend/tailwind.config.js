/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["DM Sans", "system-ui", "sans-serif"],
      },
      colors: {
        primary: {
          DEFAULT: "#0d9488",
          hover: "#0f766e",
          muted: "rgba(13, 148, 136, 0.12)",
        },
        surface: {
          DEFAULT: "#ffffff",
          elevated: "#f8fafc",
          muted: "#f1f5f9",
        },
        border: {
          DEFAULT: "#e2e8f0",
          strong: "#cbd5e1",
        },
        muted: {
          text: "#64748b",
          subtle: "#94a3b8",
        },
        danger: {
          DEFAULT: "#dc2626",
          muted: "rgba(220, 38, 38, 0.1)",
        },
        success: {
          DEFAULT: "#059669",
          muted: "rgba(5, 150, 105, 0.12)",
        },
        partial: {
          DEFAULT: "#d97706",
          muted: "rgba(217, 119, 6, 0.12)",
        },
      },
      borderRadius: {
        card: "12px",
        input: "8px",
        pill: "9999px",
      },
      boxShadow: {
        card: "0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.06)",
        cardHover: "0 4px 6px -1px rgb(0 0 0 / 0.07), 0 2px 4px -2px rgb(0 0 0 / 0.07)",
      },
    },
  },
  plugins: [],
};
