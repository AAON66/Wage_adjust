/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#0f172a',
        sand: '#f3f7fd',
        ember: '#3370ff',
        fog: '#d8e4f4',
        mist: '#eef4ff',
        steel: '#5b6b85',
      },
      boxShadow: {
        panel: '0 18px 52px rgba(15, 23, 42, 0.06)',
        float: '0 26px 80px rgba(51, 112, 255, 0.14)',
      },
      borderRadius: {
        shell: '28px',
      },
      animation: {
        'fade-up': 'fadeUp 0.55s ease-out both',
        'fade-soft': 'fadeSoft 0.45s ease-out both',
      },
      keyframes: {
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(18px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeSoft: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
};
