/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/templates/**/*.html',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"',
          'Roboto', '"Helvetica Neue"', 'Arial', 'sans-serif',
        ],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      colors: {
        accent: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
        },
        positive: { 500: '#22c55e', 600: '#16a34a' },
        negative: { 500: '#ef4444', 600: '#dc2626' },
      },
      borderRadius: { 'lg': '0.5rem', 'xl': '0.75rem' },
    },
  },
  plugins: [],
};
