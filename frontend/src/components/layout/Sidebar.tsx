import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Building2, Users, MapPin,
  FileText, Activity, Calculator, Shield, Ticket,
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { menusApi } from '../../api/menus'
import { useAuth } from '../../hooks/useAuth'
import { IconoPlataforma, PLATAFORMA } from '../../config/marca'
import { grupoDeMenu, ORDEN_GRUPOS } from '../../config/modulos'
import type { MenuItem } from '../../types'

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  'home':        LayoutDashboard,
  'building':    Building2,
  'users':       Users,
  'map-pin':     MapPin,
  'file-text':   FileText,
  'activity':    Activity,
  'calculator':  Calculator,
  'shield':      Shield,
  'ticket':      Ticket,
}

function MenuItemLink({ item }: { item: MenuItem }) {
  const Icon = ICON_MAP[item.icon] ?? LayoutDashboard
  return (
    <NavLink
      to={item.path}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
          isActive
            ? 'bg-primary-600/20 text-primary-400'
            : 'text-slate-400 hover:bg-slate-700 hover:text-slate-100'
        }`
      }
    >
      <Icon className="h-4 w-4 flex-shrink-0" />
      {item.label}
    </NavLink>
  )
}

/** Identidad del portal: logo y nombre del condominio del usuario (o la plataforma, para el super_admin). */
export function MarcaPortal() {
  const { user } = useAuth()
  const condominio = user?.condominio
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      {condominio?.logo_url ? (
        <img src={condominio.logo_url} alt="" className="h-8 w-8 flex-shrink-0 rounded-lg bg-white object-contain p-0.5" />
      ) : (
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-primary-600">
          <IconoPlataforma className="h-4 w-4 text-white" />
        </div>
      )}
      <div className="min-w-0">
        <p className="truncate text-sm font-bold text-slate-100">{condominio?.nombre ?? PLATAFORMA.nombre}</p>
        <p className="truncate text-xs text-slate-500">{condominio ? PLATAFORMA.nombre : PLATAFORMA.lema}</p>
      </div>
    </div>
  )
}

export function Sidebar() {
  const { data: menus = [] } = useQuery({
    queryKey: ['menus'],
    queryFn: menusApi.me,
    staleTime: 1000 * 60 * 5,
  })

  // El backend ya filtra por rol y por módulos habilitados; aquí solo se agrupa
  const grupos = ORDEN_GRUPOS
    .map((grupo) => ({ grupo, items: menus.filter((m) => grupoDeMenu(m.modulo) === grupo) }))
    .filter((g) => g.items.length > 0)

  return (
    <aside className="flex h-full w-60 flex-col border-r border-slate-700 bg-slate-900">
      <div className="border-b border-slate-700 px-5 py-4">
        <MarcaPortal />
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4">
        {grupos.map(({ grupo, items }) => (
          <div key={grupo}>
            <p className="mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">{grupo}</p>
            <div className="space-y-1">
              {items.map((item) => (
                <MenuItemLink key={item.id} item={item} />
              ))}
            </div>
          </div>
        ))}
      </nav>
    </aside>
  )
}
