import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: '#1E3A5F',       // Cemento Navy (Header, bordi marcati, bottoni)
          border: '#2A5A8F',     // Acciaio Bordo (Griglie tabelle e divisori 1px)
          surface: '#F4F6F9',    // Superficie Neutra (Sfondo app e card alternate)
          accent: '#4A90D9',     // Accento Tecnico (Solo focus ring e selezioni)
          ink: '#0F172A',        // Nero Grafite (Testo primario ad altissimo contrasto)
          steel: '#0F172A',
          muted: '#5A6A7A',
        },
      },
      borderRadius: {
        DEFAULT: '0px',
        none: '0px',
        sm: '0px',
        md: '0px',
        lg: '0px',
        xl: '0px',
        '2xl': '0px',
        '3xl': '0px',
        full: '0px',
      },
      fontFamily: {
        mono: ['var(--font-space)', 'monospace'],
        sans: ['var(--font-inter)', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

export default config;
