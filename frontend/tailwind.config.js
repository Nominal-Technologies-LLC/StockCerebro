/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'brand': {
          50: '#f0f7ff',
          100: '#e0effe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          900: '#1e3a5f',
        },
        'score': {
          strong_buy: '#16a34a',
          buy: '#22c55e',
          hold: '#eab308',
          sell: '#f97316',
          strong_sell: '#ef4444',
        },
      },
    },
  },
  plugins: [],
}
