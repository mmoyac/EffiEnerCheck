import { useState } from 'react'
import { Link } from 'react-router-dom'
import { KeyRound, LogOut, Ticket, User } from 'lucide-react'
import { useAuth, useModulo } from '../../hooks/useAuth'
import { CambiarClaveModal } from '../CambiarClaveModal'

const ROLE_LABELS: Record<string, string> = {
  super_admin:      'Super Admin',
  admin_condominio: 'Administrador',
  lector:           'Lector',
  parcelero:        'Parcelero',
  porteria:         'Portería',
}

export function Header() {
  const { user, logout } = useAuth()
  const conRifas = useModulo('rifas')
  const [cambiarClave, setCambiarClave] = useState(false)

  return (
    <header className="flex h-14 items-center justify-between border-b border-slate-700 bg-slate-900 px-5">
      <div />
      <div className="flex items-center gap-4">
        {/* El parcelero no tiene sidebar: su acceso a las rifas vive en la cabecera */}
        {user?.rol?.nombre === 'parcelero' && conRifas && (
          <Link
            to="/mis-rifas"
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-slate-400 transition-colors hover:bg-slate-700 hover:text-slate-100"
          >
            <Ticket className="h-4 w-4" />
            Rifas
          </Link>
        )}
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-600/20 text-primary-400">
            <User className="h-4 w-4" />
          </div>
          <div className="hidden sm:block">
            <p className="text-sm font-medium text-slate-200">{user?.nombre}</p>
            <p className="text-xs text-slate-500">{ROLE_LABELS[user?.rol?.nombre ?? ''] ?? user?.rol?.nombre}</p>
          </div>
        </div>
        <button
          onClick={() => setCambiarClave(true)}
          className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-slate-400 hover:bg-slate-700 hover:text-slate-100 transition-colors"
          title="Cambiar mi clave"
        >
          <KeyRound className="h-4 w-4" />
          <span className="hidden md:inline">Mi clave</span>
        </button>
        <button
          onClick={logout}
          className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-slate-400 hover:bg-slate-700 hover:text-slate-100 transition-colors"
          title="Cerrar sesión"
        >
          <LogOut className="h-4 w-4" />
          <span className="hidden sm:inline">Salir</span>
        </button>
      </div>
      <CambiarClaveModal open={cambiarClave} onClose={() => setCambiarClave(false)} />
    </header>
  )
}
