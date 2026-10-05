import { useQuery } from '@tanstack/react-query'
import { useAuth, useModulo } from '../../hooks/useAuth'
import { FileText, Activity, Calculator, TrendingUp } from 'lucide-react'
import { boletasApi } from '../../api/boletas'
import { liquidacionesApi } from '../../api/liquidaciones'
import { Card, CardHeader, CardTitle } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { Spinner } from '../../components/ui/Spinner'
import { clp, kwh, periodoCorto } from '../../utils/format'
import { Link } from 'react-router-dom'

function KpiCard({ title, value, sub, icon: Icon, color }: {
  title: string; value: string; sub: string
  icon: React.ComponentType<{ className?: string }>
  color: string
}) {
  return (
    <Card>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-400">{title}</p>
          <p className="mt-1 text-2xl font-bold text-slate-100">{value}</p>
          <p className="mt-1 text-xs text-slate-500">{sub}</p>
        </div>
        <div className={`rounded-xl p-3 ${color}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </Card>
  )
}

function estadoBadge(b: { lecturas_cerradas: boolean; liquidaciones_cerradas: boolean; boleta_visible_usuarios: boolean; estado: string }) {
  if (b.boleta_visible_usuarios) return <Badge color="green" dot>Publicada</Badge>
  if (b.liquidaciones_cerradas)  return <Badge color="blue" dot>Liq. cerradas</Badge>
  if (b.lecturas_cerradas)       return <Badge color="yellow" dot>Lect. cerradas</Badge>
  if (b.estado === 'validada')   return <Badge color="purple" dot>Corroborada</Badge>
  return <Badge color="slate" dot>Borrador</Badge>
}

/** Panel de un condominio sin el módulo de energía: no consulta boletas ni liquidaciones. */
function PanelSinEnergia() {
  const { user } = useAuth()
  return (
    <div className="mx-auto max-w-2xl rounded-xl border border-slate-700 bg-slate-800 p-6">
      <h1 className="text-lg font-semibold text-slate-100">{user?.condominio?.nombre ?? 'Panel'}</h1>
      <p className="mt-2 text-sm text-slate-400">
        Usa el menú para administrar las funciones habilitadas en tu condominio.
      </p>
    </div>
  )
}

export default function Dashboard() {
  return useModulo('energia') ? <PanelEnergia /> : <PanelSinEnergia />
}

function PanelEnergia() {
  const { data: boletas = [], isLoading } = useQuery({
    queryKey: ['boletas'],
    queryFn: boletasApi.list,
  })

  const ultimaBoleta = boletas[0]

  const { data: liquidaciones = [] } = useQuery({
    queryKey: ['liquidaciones', ultimaBoleta?.id],
    queryFn: () => liquidacionesApi.list(ultimaBoleta!.id),
    enabled: !!ultimaBoleta,
  })

  const totalRecaudar = liquidaciones.reduce((s, l) => s + (l.total_pagar_mes ?? 0), 0)
  const liquidacionesPagadas = liquidaciones.filter((l) => l.pagado).length

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" className="text-primary-500" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-100">Dashboard</h1>
        <p className="text-sm text-slate-500">Resumen del período activo</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard
          title="Boletas"
          value={String(boletas.length)}
          sub="períodos registrados"
          icon={FileText}
          color="bg-blue-500/10 text-blue-400"
        />
        <KpiCard
          title="Lecturas del período"
          value={ultimaBoleta ? String(liquidaciones.length) : '—'}
          sub={ultimaBoleta ? periodoCorto(ultimaBoleta.periodo_mes) : 'sin boleta activa'}
          icon={Activity}
          color="bg-yellow-500/10 text-yellow-400"
        />
        <KpiCard
          title="Liquidaciones"
          value={String(liquidaciones.length)}
          sub={`${liquidacionesPagadas} pagadas`}
          icon={Calculator}
          color="bg-primary-500/10 text-primary-400"
        />
        <KpiCard
          title="Total a recaudar"
          value={clp(totalRecaudar)}
          sub={ultimaBoleta ? periodoCorto(ultimaBoleta.periodo_mes) : '—'}
          icon={TrendingUp}
          color="bg-purple-500/10 text-purple-400"
        />
      </div>

      {/* Boletas recientes */}
      <Card padding={false}>
        <CardHeader className="px-5 pt-5">
          <CardTitle>Boletas recientes</CardTitle>
          <Link to="/boletas" className="text-sm text-primary-400 hover:underline">Ver todas</Link>
        </CardHeader>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="px-5 py-3">Período</th>
                <th className="px-5 py-3">Estado</th>
                <th className="px-5 py-3 text-right">kWh Boleta</th>
                <th className="px-5 py-3 text-right">Total Emisión</th>
              </tr>
            </thead>
            <tbody>
              {boletas.slice(0, 5).map((b) => (
                <tr key={b.id} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                  <td className="px-5 py-3">
                    <Link to={`/boletas/${b.id}`} className="font-medium text-slate-200 hover:text-primary-400">
                      {periodoCorto(b.periodo_mes)}
                    </Link>
                  </td>
                  <td className="px-5 py-3">{estadoBadge(b)}</td>
                  <td className="px-5 py-3 text-right font-mono text-slate-300">{kwh(b.total_kwh_compania)}</td>
                  <td className="px-5 py-3 text-right font-mono text-slate-300">{clp(b.monto_total_emision)}</td>
                </tr>
              ))}
              {boletas.length === 0 && (
                <tr><td colSpan={4} className="px-5 py-8 text-center text-slate-500">Sin boletas registradas</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
