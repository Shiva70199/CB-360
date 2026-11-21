/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        background: "#f8fafc",
        foreground: "#0f172a",
        navy: {
          DEFAULT: "#0f172a",
          soft: "#1e293b"
        },
        accent: {
          DEFAULT: "#14532d",
          foreground: "#ffffff",
          warm: "#34d399",
          mint: "#6ee7b7"
        },
        forest: {
          DEFAULT: "#14532d",
          deep: "#10261c",
          mint: "#34d399"
        }
      },
      boxShadow: {
        soft: "0 10px 30px rgba(15, 23, 42, 0.08)"
      },
      fontFamily: {
        sans: ["var(--font-jakarta)", "Plus Jakarta Sans", "ui-sans-serif", "sans-serif"]
      }
    }
  },
  plugins: []
};
