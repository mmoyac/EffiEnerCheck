import { Navigate, Outlet } from 'react-router-dom'
import { useModulo } from '../../hooks/useAuth'
import type { Modulo } from '../../config/modulos'

/** Rutas de un módulo: si el condominio no lo tiene habilitado, vuelve a la pantalla de inicio. */
export function ModuloRoute({ modulo }: { modulo: Modulo }) {
  return useModulo(modulo) ? <Outlet /> : <Navigate to="/" replace />
}
