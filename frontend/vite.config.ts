import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// Versión visible del portal: fecha y hora de compilación en Chile. Permite comprobar que el navegador
// tomó la última versión (src/actualizacion.ts) y sirve para soporte.
const VERSION = new Intl.DateTimeFormat('es-CL', {
  timeZone: 'America/Santiago', day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
}).format(new Date()).replace(',', '')

export default defineConfig({
  define: { __VERSION__: JSON.stringify(VERSION) },
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      // El registro lo hace src/actualizacion.ts (busca versiones nuevas y recarga sola)
      injectRegister: false,
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        cleanupOutdatedCaches: true,
        // El service worker nuevo toma el control de inmediato y la página se recarga con la versión nueva
        skipWaiting: true,
        clientsClaim: true,
        // La API y los archivos subidos nunca salen de la caché del service worker
        navigateFallbackDenylist: [/^\/api\//, /^\/uploads\//],
      },
      manifest: {
        name: 'EFFIComunidad — Portal de la comunidad',
        short_name: 'EFFIComunidad',
        description: 'Portal de la comunidad: cobros, energía y actividades del condominio',
        theme_color: '#16a34a',
        background_color: '#0f172a',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
    }),
  ],
  server: {
    proxy: {
      '/api':     { target: 'http://localhost:8000', changeOrigin: true },
      '/uploads': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
