/**
 * Catálogo de módulos: espejo de backend/app/core/modulos.py (la fuente de verdad).
 * `sitio` y `portal` son los productos; `energia` y `rifas` viven dentro del portal.
 */
export type Modulo = 'sitio' | 'portal' | 'energia' | 'rifas'

export const MODULOS: Modulo[] = ['sitio', 'portal', 'energia', 'rifas']

export const ETIQUETA_MODULO: Record<Modulo, string> = {
  sitio:   'Landing',
  portal:  'Administración',
  energia: 'Energía',
  rifas:   'Rifas',
}

/** Encabezados del menú lateral. `null` = núcleo del portal. */
export type GrupoMenu = 'Energía' | 'Comunidad' | 'Administración'

export function grupoDeMenu(modulo: Modulo | null): GrupoMenu {
  if (modulo === 'energia') return 'Energía'
  if (modulo === 'rifas' || modulo === 'sitio') return 'Comunidad'
  return 'Administración'
}

export const ORDEN_GRUPOS: GrupoMenu[] = ['Energía', 'Comunidad', 'Administración']
