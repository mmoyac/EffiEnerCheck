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
