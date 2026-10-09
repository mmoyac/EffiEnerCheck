import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { ProtectedRoute } from './components/layout/ProtectedRoute'
import { ModuloRoute } from './components/layout/ModuloRoute'
import { useAuth, useModulos, useRole } from './hooks/useAuth'
import { pantallaDeInicio } from './config/inicio'
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
import MiLiquidacion from './pages/comunero/MiLiquidacion'
import Cobranza from './pages/admin/Cobranza'
import EstablecerClave from './pages/EstablecerClave'
import MisRifas from './pages/comunero/Rifas'
import Rifas from './pages/admin/Rifas'
import RifaDetalle from './pages/admin/RifaDetalle'
import VentaRifa from './pages/porteria/VentaRifa'

function RoleHome() {
  const role = useRole()
  const modulos = useModulos()
  const { isLoading } = useAuth()
  if (isLoading) return <div className="flex h-screen items-center justify-center"><Spinner size="lg" className="text-primary-500" /></div>
  return <Navigate to={pantallaDeInicio(role, modulos)} replace />
}

function SinAcceso() {
  const { logout } = useAuth()
  return (
    <div className="flex h-screen flex-col items-center justify-center gap-4 bg-slate-900 px-6 text-center">
      <p className="text-slate-300">Tu cuenta no tiene funciones habilitadas en este condominio.</p>
      <button onClick={logout} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-500">
        Cerrar sesión
      </button>
    </div>
  )
}

const esAdmin = (role: string | null | undefined) => role === 'super_admin' || role === 'admin_condominio'

/** /liquidaciones es del comunero; la administración usa /cobranza (cambio cobranza-energia) */
function LiquidacionesRouter() {
  const role = useRole()
  if (esAdmin(role)) return <Navigate to="/cobranza" replace />
  return <MiLiquidacion />
}

/** /cobranza es de la administración; otro rol vuelve a su pantalla de liquidaciones */
function CobranzaRouter() {
  const role = useRole()
  if (!esAdmin(role)) return <Navigate to="/liquidaciones" replace />
  return <Cobranza />
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
      {/* Públicas: el token del enlace va en el fragmento (#), no en la ruta */}
      <Route path="/crear-clave" element={<EstablecerClave />} />
      <Route path="/restablecer-clave" element={<EstablecerClave />} />

      {/* Lector: pantalla completa sin AppLayout */}
      <Route element={<ProtectedRoute />}>
        <Route path="/sin-acceso" element={<SinAcceso />} />
        <Route element={<ModuloRoute modulo="energia" />}>
          <Route path="/lecturas" element={<LecturasRouter />} />
          <Route path="/lecturas/capturar/:parcelaId/:boletaId" element={<CapturarLectura />} />
          <Route path="/liquidaciones" element={<LiquidacionesRouter />} />
        </Route>
        <Route element={<ModuloRoute modulo="rifas" />}>
          <Route path="/mis-rifas" element={<MisRifas />} />
          <Route path="/mis-rifas/:id" element={<MisRifas />} />
          <Route path="/porteria" element={<VentaRifa />} />
        </Route>
      </Route>

      {/* Admin / Comunero con AppLayout */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<RoleHome />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/condominios" element={<Condominios />} />
          <Route path="/usuarios" element={<Usuarios />} />
          <Route path="/parcelas" element={<Parcelas />} />
          <Route element={<ModuloRoute modulo="energia" />}>
            <Route path="/boletas" element={<Boletas />} />
            <Route path="/boletas/:id" element={<BoletaDetalle />} />
            <Route path="/cobranza" element={<CobranzaRouter />} />
          </Route>
          <Route element={<ModuloRoute modulo="rifas" />}>
            <Route path="/rifas" element={<Rifas />} />
            <Route path="/rifas/:id" element={<RifaDetalle />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
