import { api } from './api/client'

/**
 * Marca del portal según el dominio (antes del login): título de la pestaña, nombre que iPhone propone al
 * "Agregar a inicio" y color de la barra. El manifiesto de Android lo genera la API con los mismos datos.
 */
export async function aplicarMarcaPortal() {
  try {
    const { data } = await api.get<{ nombre: string; nombre_completo: string; color: string }>('/portal/marca')
    document.title = data.nombre_completo
    document.querySelector('meta[name="apple-mobile-web-app-title"]')?.setAttribute('content', data.nombre)
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', data.color)
  } catch { /* sin red: quedan los valores por defecto de index.html */ }
}
