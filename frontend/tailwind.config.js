/** @type {import('tailwindcss').Config} */
// Палитра и токены — из brand-assets/colors/tailwind.config.js
// Правила бренда: только 4 цвета, pill-кнопки, карточки 24–32px, без теней/градиентов.
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Бренд
        fitsiz: {
          black: '#121212',
          white: '#FFFFFF',
          green: '#42BA1A',
          'green-hover': '#3AA817',
          lime: '#C2D918',
          'lime-hover': '#B3C713',
          'surface-1': '#1A1A1A',
          'surface-2': '#232323',
          'surface-3': '#2C2C2C',
          muted: '#8A8A8A',
          'muted-light': '#B5B5B5',
          border: '#2A2A2A',
        },
        // Семантические алиасы — чтобы существующий UI-код тоже работал
        background: '#121212',
        foreground: '#FFFFFF',
        border: '#2A2A2A',
        muted: '#1A1A1A',
        'muted-foreground': '#8A8A8A',
        primary: '#42BA1A',
        'primary-foreground': '#121212',
      },
      fontFamily: {
        heading: ['"Russo One"', 'system-ui', 'sans-serif'],
        body: ['"Inter"', 'system-ui', 'sans-serif'],
        sans: ['"Inter"', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        pill: '9999px',
        card: '24px',
        'card-lg': '32px',
        chip: '16px',
      },
      letterSpacing: {
        heading: '0.02em',
        cta: '0.04em',
        badge: '0.06em',
      },
    },
  },
  plugins: [],
}
