/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        "brand-black": "#050505",
        "brand-violet": "#9d4edd",
        "brand-violet-glow": "#c77dff",
        "brand-violet-light": "#d9a2ff",
        "brand-violet-core": "#f3e8ff",
      },
      fontFamily: {
        display: ['"Cormorant Garamond"', "serif"],
        sans: ['"Hanken Grotesk"', "sans-serif"],
        mono: ["ui-monospace", "Menlo", "monospace"],
      },
      keyframes: {
        flicker: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: ".94" },
        },
        stamp: {
          "0%": { transform: "rotate(-9deg) scale(1.8)", opacity: "0" },
          "60%": { transform: "rotate(-9deg) scale(.96)", opacity: "1" },
          "100%": { transform: "rotate(-9deg) scale(1)", opacity: ".95" },
        },
        // Light running along the progress thread; the last 30% is a pause
        // so it reads as an occasional gleam rather than a constant scan.
        glint: {
          "0%": { backgroundPosition: "100% 0" },
          "70%, 100%": { backgroundPosition: "0% 0" },
        },
        glow: {
          "0%, 100%": { boxShadow: "0 0 12px #c77dff" },
          "50%": { boxShadow: "0 0 20px #c77dff" },
        },
      },
      animation: {
        flicker: "flicker 6s ease-in-out infinite",
        stamp: "stamp .5s ease-out both",
        glint: "glint 2.8s ease-in-out infinite",
        glow: "glow 3.5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
}
