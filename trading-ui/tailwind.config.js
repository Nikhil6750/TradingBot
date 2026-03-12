/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        surface: "var(--surface)",
        panel: "var(--panel)",
        card: "var(--card)",
        hoverSurface: "var(--hover-surface)",
        accent: "var(--accent)",
        border: "var(--border)",
        "card-border": "var(--card-border)",
        textPrimary: "var(--text-primary)",
        textSecondary: "var(--text-secondary)",
      },
      boxShadow: {
        'soft': '0 4px 24px rgba(0,0,0,0.18)',
        'card': '0 2px 16px rgba(0,0,0,0.12)',
        'glow': '0 0 20px rgba(59,130,246,0.18)',
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
};
