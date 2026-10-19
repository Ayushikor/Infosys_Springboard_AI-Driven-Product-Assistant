/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        navy: {
          900: '#0f1629',
          800: '#1a2340',
          700: '#2a3558',
          500: '#64708f',
          300: '#b8c0d4',
        },
        accent: {
          DEFAULT: '#6366f1',
          600: '#4f46e5',
          500: '#6366f1',
          100: '#e0e7ff',
        },
        violet: { 500: '#8b5cf6' },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(15, 22, 41, 0.04), 0 1px 3px rgba(15, 22, 41, 0.06)',
      },
    },
  },
  plugins: [],
};
