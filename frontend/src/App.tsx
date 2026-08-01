import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { ProtectedRoute } from './components/layout/ProtectedRoute'
import { useAuth, useRole } from './hooks/useAuth'
import { Spinner } from './components/ui/Spinner'

import Login from './pages/Login'
import Dashboard from './pages/admin/Dashboard'
import Boletas from './pages/admin/Boletas'
import BoletaDetalle from './pages/admin/BoletaDetalle'
import Usuarios from './pages/admin/Usuarios'
import Parcelas from './pages/admin/Parcelas'
import Condominios from './pages/admin/Condominios'
import LectorDashboard from './pages/lector/LectorDashboard'
import CapturarLectura from './pages/lector/CapturarLectura'
import MiLiquidacion from './pages/parcelero/MiLiquidacion'

const ROLE_HOME: Record<string, string> = {
  super_admin:      '/dashboard',
  admin_condominio: '/dashboard',
  lector:           '/lecturas',
  parcelero:        '/liquidaciones',
}

function RoleHome() {
  const role = useRole()
  const { isLoading } = useAuth()
  if (isLoading) return <div className="flex h-screen items-center justify-center"><Spinner size="lg" className="text-primary-500" /></div>
  return <Navigate to={ROLE_HOME[role ?? ''] ?? '/dashboard'} replace />
}

function LecturasRouter() {
  const role = useRole()
  if (role === 'lector') return <LectorDashboard />
  return <Navigate to="/dashboard" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      {/* Lector: pantalla completa sin AppLayout */}
      <Route element={<ProtectedRoute />}>
        <Route path="/lecturas" element={<LecturasRouter />} />
        <Route path="/lecturas/capturar/:parcelaId/:boletaId" element={<CapturarLectura />} />
        <Route path="/liquidaciones" element={<MiLiquidacion />} />
      </Route>

      {/* Admin / Parcelero con AppLayout */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<RoleHome />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/condominios" element={<Condominios />} />
          <Route path="/boletas" element={<Boletas />} />
          <Route path="/boletas/:id" element={<BoletaDetalle />} />
          <Route path="/usuarios" element={<Usuarios />} />
          <Route path="/parcelas" element={<Parcelas />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
