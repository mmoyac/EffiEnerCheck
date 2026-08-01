import { useAuthContext } from '../context/AuthContext'

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

export function useIsParcelero() {
  const role = useRole()
  return role === 'parcelero'
}
