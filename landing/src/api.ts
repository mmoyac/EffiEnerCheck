import type { SitioPublico } from './types'

/** Única llamada de la landing: mismo origen, sin sesión (el nginx solo expone esta ruta de la API). */
export async function obtenerSitio(): Promise<SitioPublico> {
  // Sin respuesta en 10 s se muestra "Sitio no disponible" en vez de un indicador de carga eterno
  const r = await fetch('/api/v1/sitio', { headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(10_000) })
  if (!r.ok) throw new Error(r.status === 404 ? 'no-encontrado' : 'error')
  return r.json()
}
