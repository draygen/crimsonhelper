/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        crimson: {
          50:  '#fff1f1',
          100: '#ffe1e1',
          200: '#ffc7c7',
          300: '#ffa0a0',
          400: '#ff6b6b',
          500: '#f83b3b',
          600: '#e51d1d',
          700: '#c01313',
          800: '#9f1313',
          900: '#841717',
          950: '#490707',
        },
        surface: {
          950: '#0a0a10',
          900: '#0d0d16',
          800: '#121220',
          700: '#181828',
          600: '#1e1e32',
          500: '#252540',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-crimson': 'pulse-crimson 2s ease-in-out infinite',
        'slide-in': 'slide-in 0.2s ease-out',
      },
      keyframes: {
        'pulse-crimson': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        'slide-in': {
          from: { opacity: '0', transform: 'translateY(-6px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
