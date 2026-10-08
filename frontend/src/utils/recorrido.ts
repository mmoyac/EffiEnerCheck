import type { Parcela } from '../types'

const natural = (a: Parcela, b: Parcela) =>
  a.numero_parcela.localeCompare(b.numero_parcela, 'es', { numeric: true, sensitivity: 'base' })

/**
 * Orden del recorrido del lector (cambio orden-recorrido): primero las parcelas con posición, en ese orden;
 * después las sin posición, en orden numérico natural. Sin recorrido definido = el orden numérico de siempre.
 * Único criterio: lo usan la app del lector y el editor del recorrido.
 */
export function ordenarRecorrido(parcelas: Parcela[]): Parcela[] {
  return [...parcelas].sort((a, b) => {
    const pa = a.orden_recorrido ?? null
    const pb = b.orden_recorrido ?? null
    if (pa != null && pb != null) return pa - pb
    if (pa != null) return -1
    if (pb != null) return 1
    return natural(a, b)
  })
}
