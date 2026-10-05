import type { Config } from 'tailwindcss'

const tonos = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950] as const

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Color institucional del condominio: variables CSS que fija src/tema.ts (defecto en index.css)
        marca: Object.fromEntries(tonos.map((t) => [t, `rgb(var(--marca-${t}) / <alpha-value>)`])),
        // Texto legible sobre el color de marca (blanco o casi negro)
        'sobre-marca': 'rgb(var(--sobre-marca) / <alpha-value>)',
      },
      // Fuentes del sistema: sin peticiones a terceros desde un sitio público
      fontFamily: {
        titulo: ['Georgia', 'Cambria', '"Times New Roman"', 'serif'],
        sans: ['system-ui', '-apple-system', '"Segoe UI"', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
} satisfies Config
