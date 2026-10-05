/**
 * Marca de la plataforma. "EnerCheck" identifica al módulo de energía; el nombre comercial de la
 * plataforma completa todavía no está definido y se cambia aquí, en un solo lugar.
 */
export const PLATAFORMA = {
  nombre: 'EnerCheck',
  lema: 'Portal de la comunidad',
  modulos: {
    energia: 'EnerCheck',
    rifas: 'Rifas solidarias',
  },
  /** Color por defecto (el verde histórico del portal): se usa sin condominio o sin color definido. */
  colorPorDefecto: '#22C55E',
} as const
