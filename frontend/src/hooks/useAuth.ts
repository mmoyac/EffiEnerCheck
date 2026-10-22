import { useAuthContext } from '../context/AuthContext'
import type { Modulo } from '../config/modulos'

export function useAuth() {
  return useAuthContext()
}

export function useRole() {
  const { user } = useAuthContext()
  return user?.rol?.nombre ?? null
}

export function useIsAdmin() {
  const role = useRole()
  return role === 'super_admin' || role === 'admin_condominio'
}

export function useIsLector() {
  const role = useRole()
  return role === 'lector'
}

/**
 * Administración, o un comunero con el permiso de administrar rifas (y el módulo contratado).
 * Mismo criterio que `administra_rifas()` del backend.
 */
export function useAdministraRifas() {
  const { user } = useAuthContext()
  const rol = user?.rol?.nombre
  if (rol === 'super_admin' || rol === 'admin_condominio') return true
  return rol === 'comunero' && !!user?.administra_rifas && (user?.modulos ?? []).includes('rifas')
}

export function useIsComunero() {
  const role = useRole()
  return role === 'comunero'
}

/** Módulos habilitados del condominio del usuario (el super_admin los tiene todos) */
export function useModulos(): Modulo[] {
  const { user } = useAuthContext()
  return user?.modulos ?? []
}

export function useModulo(modulo: Modulo): boolean {
  return useModulos().includes(modulo)
}
