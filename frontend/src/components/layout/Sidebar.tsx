import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Building2, Users, MapPin,
  FileText, Activity, Calculator, Shield, Zap,
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { menusApi } from '../../api/menus'
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

export function Sidebar() {
  const { data: menus = [] } = useQuery({
    queryKey: ['menus'],
    queryFn: menusApi.me,
    staleTime: 1000 * 60 * 5,
  })

  return (
    <aside className="flex h-full w-60 flex-col border-r border-slate-700 bg-slate-900">
      {/* Logo */}
      <div className="flex items-center gap-2.5 border-b border-slate-700 px-5 py-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-600">
          <Zap className="h-4 w-4 text-white" />
        </div>
        <div>
          <p className="text-sm font-bold text-slate-100">EnerCheck</p>
          <p className="text-xs text-slate-500">Santa Laura</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <div className="space-y-1">
          {menus.map((item) => (
            <MenuItemLink key={item.id} item={item} />
          ))}
        </div>
      </nav>
    </aside>
  )
}
