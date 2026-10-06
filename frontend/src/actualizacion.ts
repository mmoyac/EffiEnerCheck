import { registerSW } from 'virtual:pwa-register'

/**
 * Actualización automática del portal (PWA). El service worker guarda la app para cargar rápido;
 * sin esto, tras un despliegue el navegador seguía mostrando la versión anterior hasta un Ctrl+Shift+R.
 *
 * Con registerType 'autoUpdate', cuando hay un service worker nuevo este toma el control y
 * registerSW recarga la página sola. Aquí solo se decide CUÁNDO buscar versiones nuevas:
 * al abrir la app, al volver a la pestaña y cada hora (pantallas que quedan abiertas todo el día,
 * como la de portería).
 */
const CADA_HORA = 60 * 60 * 1000

export function activarActualizacionAutomatica() {
  registerSW({
    immediate: true,
    onRegisteredSW(_url, registro) {
      if (!registro) return
      const buscar = () => { if (navigator.onLine) registro.update().catch(() => {}) }
      setInterval(buscar, CADA_HORA)
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') buscar()
      })
    },
  })
}
