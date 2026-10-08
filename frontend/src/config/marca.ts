/**
 * Marca de la plataforma: se cambia aquí, en un solo lugar (nombre, lema e ícono).
 * "EnerCheck" sigue identificando al módulo de energía.
 */
export { UsersRound as IconoPlataforma } from 'lucide-react'

export const PLATAFORMA = {
  nombre: 'EFFIComunidad',
  lema: 'Portal de la comunidad',
  modulos: {
    energia: 'EnerCheck',
    rifas: 'Rifas solidarias',
  },
  /** Centro de capacitación: sitio estático y público en frontend/public/capacitacion/ */
  capacitacion: '/capacitacion/',
  /** Color por defecto (el verde histórico del portal): se usa sin condominio o sin color definido. */
  colorPorDefecto: '#22C55E',
} as const
