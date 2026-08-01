import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { Spinner } from '../ui/Spinner'

export function ProtectedRoute() {
  const { token, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-900">
        <Spinner size="lg" className="text-primary-500" />
      </div>
    )
  }

  if (!token) return <Navigate to="/login" replace />
  return <Outlet />
}
