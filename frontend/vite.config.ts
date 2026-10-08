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
        // La capacitación es un sitio estático aparte: el SW no debe responder con el portal
        navigateFallbackDenylist: [/^\/api\//, /^\/uploads\//, /^\/capacitacion\//],
      },
      // El manifiesto lo genera la API según el dominio (nombre y color del condominio): /manifest.webmanifest
      manifest: false,
    }),
  ],
  // Desarrollo: `npm run dev` con recarga en caliente (el backend del docker-compose recarga solo).
  // Para probar desde el celular en la misma red: `npm run dev -- --host`.
  server: {
    port: 3000,
    proxy: {
      '/api':     { target: 'http://localhost:8000', changeOrigin: true },
      '/uploads': { target: 'http://localhost:8000', changeOrigin: true },
      // El manifiesto lo arma la API según el dominio (igual que nginx en el contenedor)
      '/manifest.webmanifest': { target: 'http://localhost:8000', rewrite: () => '/api/v1/portal/manifest' },
    },
  },
})
