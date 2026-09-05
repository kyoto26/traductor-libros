/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        "brand-black": "#050505",
        "brand-violet": "#9d4edd",
        "brand-violet-glow": "#c77dff",
        "brand-violet-core": "#f3e8ff",
      },
    },
  },
  plugins: [],
}
