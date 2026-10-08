import type { Modulo } from './modulos'

/**
 * Pantalla de inicio por rol (única definición: la usan App.tsx y Login.tsx). Si la pantalla
 * principal pertenece a un módulo no habilitado, cae en una alternativa (spec modulos-plataforma).
 */
export function pantallaDeInicio(rol: string | null | undefined, modulos: readonly Modulo[]): string {
  const tiene = (m: Modulo) => modulos.includes(m)
  switch (rol) {
    case 'lector':
      return tiene('energia') ? '/lecturas' : '/dashboard'
    case 'comunero':
      if (tiene('energia')) return '/liquidaciones'
      return tiene('rifas') ? '/mis-rifas' : '/dashboard'
    case 'porteria':
      // La portería solo vende rifas: sin ese módulo no tiene pantalla (evita un ciclo de redirecciones)
      return tiene('rifas') ? '/porteria' : '/sin-acceso'
    default:
      return '/dashboard'
  }
}
