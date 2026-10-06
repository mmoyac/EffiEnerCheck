import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, Circle, ChevronRight, Zap } from 'lucide-react'
import { boletasApi } from '../../api/boletas'
import { lecturasApi } from '../../api/lecturas'
import { parcelasApi } from '../../api/parcelas'
import { Spinner } from '../../components/ui/Spinner'
import { CambiarClaveModal } from '../../components/CambiarClaveModal'
import { periodoCorto } from '../../utils/format'
import type { Parcela } from '../../types'
import { useAuth } from '../../hooks/useAuth'

type Filtro = 'pendientes' | 'todas'

export default function LectorDashboard() {
  const navigate = useNavigate()
  const { logout, user } = useAuth()
  const [cambiarClave, setCambiarClave] = useState(false)
  const [filtro, setFiltro] = useState<Filtro>('pendientes')

  const { data: boletas = [], isLoading: loadingBoletas } = useQuery({
    queryKey: ['boletas'],
    queryFn: boletasApi.list,
  })

  // Última boleta abierta (sin lecturas cerradas)
  const boletaActiva = boletas.filter((b) => !b.lecturas_cerradas).at(-1)
    ?? boletas.at(-1)

  const { data: lecturas = [], isLoading: loadingLecturas } = useQuery({
    queryKey: ['lecturas', boletaActiva?.id],
    queryFn: () => lecturasApi.list(boletaActiva!.id),
    enabled: !!boletaActiva,
  })

  const { data: parcelas = [], isLoading: loadingParcelas } = useQuery({
    queryKey: ['parcelas'],
    queryFn: parcelasApi.list,
  })

  const leidas = new Set(lecturas.filter((l: any) => l.fecha_toma).map((l: any) => l.parcela_id))
  const total = parcelas.filter((p: Parcela) => p.activa).length
  const completadas = parcelas.filter((p: Parcela) => p.activa && leidas.has(p.id)).length

  const parcelasFiltradas = parcelas.filter((p: Parcela) => {
    if (!p.activa) return false
    if (filtro === 'pendientes') return !leidas.has(p.id)
    return true
  })

  const isLoading = loadingBoletas || loadingLecturas || loadingParcelas

  return (
    <div className="flex h-screen flex-col bg-slate-900">
      {/* Header móvil */}
      <header className="sticky top-0 z-10 border-b border-slate-700 bg-slate-900 px-4 pt-safe">
        <div className="flex items-center justify-between py-3">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-600">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-100">Lecturas</p>
              <p className="text-xs text-slate-500">{user?.nombre}</p>
            </div>
          </div>
          <div className="flex items-center">
            <button onClick={() => setCambiarClave(true)} className="text-xs text-slate-500 hover:text-slate-300 px-2 py-1">
              Mi clave
            </button>
            <button onClick={logout} className="text-xs text-slate-500 hover:text-slate-300 px-2 py-1">
              Salir
            </button>
          </div>
        </div>

        {/* Período y progreso */}
        {boletaActiva && (
          <div className="pb-3">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
              {periodoCorto(boletaActiva.periodo_mes)}
            </p>
            <div className="mt-2 flex items-center gap-3">
              <div className="flex-1 overflow-hidden rounded-full bg-slate-700">
                <div
                  className="h-2 rounded-full bg-primary-500 transition-all"
                  style={{ width: total > 0 ? `${(completadas / total) * 100}%` : '0%' }}
                />
              </div>
              <span className="text-sm font-bold text-slate-200 tabular-nums">
                {completadas}/{total}
              </span>
            </div>
          </div>
        )}

        {/* Filtro tabs */}
        <div className="flex gap-1 -mb-px">
          {(['pendientes', 'todas'] as Filtro[]).map((f) => (
            <button key={f} onClick={() => setFiltro(f)}
              className={`flex-1 py-2.5 text-sm font-medium capitalize transition-colors ${
                filtro === f
                  ? 'border-b-2 border-primary-500 text-primary-400'
                  : 'text-slate-500'
              }`}>
              {f}
              {f === 'pendientes' && total - completadas > 0 && (
                <span className="ml-1.5 rounded-full bg-primary-600/20 px-1.5 py-0.5 text-xs text-primary-400">
                  {total - completadas}
                </span>
              )}
            </button>
          ))}
        </div>
      </header>

      {/* Lista */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex h-48 items-center justify-center">
            <Spinner size="lg" className="text-primary-500" />
          </div>
        ) : !boletaActiva ? (
          <div className="flex h-48 flex-col items-center justify-center gap-2 text-center px-6">
            <p className="text-slate-400">Sin período activo</p>
            <p className="text-xs text-slate-600">El administrador debe crear una boleta</p>
          </div>
        ) : parcelasFiltradas.length === 0 ? (
          <div className="flex h-48 flex-col items-center justify-center gap-2">
            <CheckCircle2 className="h-10 w-10 text-primary-500" />
            <p className="text-slate-300 font-medium">¡Todas las lecturas completadas!</p>
          </div>
        ) : (
          <ul className="divide-y divide-slate-700/50">
            {parcelasFiltradas.map((p: Parcela) => {
              const hecho = leidas.has(p.id)
              return (
                <li key={p.id}>
                  <button
                    disabled={boletaActiva.lecturas_cerradas}
                    onClick={() => navigate(`/lecturas/capturar/${p.id}/${boletaActiva.id}`)}
                    className={`flex w-full items-center gap-4 px-4 py-4 text-left transition-colors active:bg-slate-700/50 disabled:opacity-50 hover:bg-slate-800`}
                  >
                    {/* Icono estado */}
                    <div className={`flex-shrink-0 ${hecho ? 'text-primary-500' : 'text-slate-600'}`}>
                      {hecho ? <CheckCircle2 className="h-7 w-7" /> : <Circle className="h-7 w-7" />}
                    </div>

                    {/* Datos */}
                    <div className="flex-1 min-w-0">
                      <p className={`text-lg font-bold ${hecho ? 'text-slate-400' : 'text-slate-100'}`}>
                        Parcela {p.numero_parcela}
                      </p>
                      {p.propietario_nombre && (
                        <p className="text-sm text-slate-500 truncate">{p.propietario_nombre}</p>
                      )}
                    </div>

                    {/* Chevron */}
                    {!boletaActiva.lecturas_cerradas && (
                      <ChevronRight className="h-5 w-5 text-slate-600 flex-shrink-0" />
                    )}
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
      <CambiarClaveModal open={cambiarClave} onClose={() => setCambiarClave(false)} />
    </div>
  )
}
