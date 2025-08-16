/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'pokemon-blue': '#3B82F6',
        'pokemon-yellow': '#FCD34D',
        'pokemon-red': '#EF4444',
      }
    },
  },
  plugins: [],
}