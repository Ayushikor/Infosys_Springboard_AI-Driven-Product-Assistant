/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        navy: {
          900: '#17110f',
          800: '#211815',
          700: '#3a2a24',
          500: '#8a756b',
          300: '#c9b8ad',
        },
        accent: {
          DEFAULT: '#8b523d',
          600: '#70402f',
          500: '#a96c52',
          100: '#f0dfd5',
        },
        indigo: {
          50: '#f8eee8',
          100: '#f0dfd5',
          200: '#e4c8b8',
          300: '#d2a58e',
          400: '#bd846b',
          500: '#a96c52',
          600: '#8b523d',
          700: '#70402f',
          800: '#52392f',
          900: '#38251f',
        },
        violet: {
          50: '#f8eee8',
          100: '#f0dfd5',
          500: '#a96c52',
          600: '#8b523d',
        },
        slate: {
          50: '#fbf8f5',
          100: '#f5eee8',
          200: '#e9dfd7',
          300: '#d7c9bf',
          400: '#ad9b90',
          500: '#88776e',
          600: '#6f5e55',
          700: '#55463f',
          800: '#342923',
          900: '#211815',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 2px 10px rgba(70, 43, 31, 0.045), 0 1px 2px rgba(70, 43, 31, 0.04)',
        soft: '0 12px 32px rgba(70, 43, 31, 0.08)',
      },
      borderRadius: {
        '2xl': '1.15rem',
      },
    },
  },
  plugins: [],
};
