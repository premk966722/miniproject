/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          navy: '#0f172a',
          slate: '#1e293b',
          blue: '#2563eb',
          teal: '#14b8a6',
        },
      },
    },
  },
  plugins: [],
};
