/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg:        '#0a0a0b',
        panel:     '#141417',
        'panel-2': '#1c1c20',
        border:    '#2a2a30',
        muted:     '#71717a',
        text:      '#e4e4e7',
        accent:    '#fcc419',
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
};
