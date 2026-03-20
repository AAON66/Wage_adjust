/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#14213d',
        sand: '#f5efe6',
        ember: '#d97706',
        fog: '#e5e7eb',
      },
      boxShadow: {
        panel: '0 20px 45px rgba(20, 33, 61, 0.12)',
      },
    },
  },
  plugins: [],
};
