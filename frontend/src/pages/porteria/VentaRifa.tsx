import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Banknote, HeartHandshake, Landmark, Search, Ticket, Trophy } from 'lucide-react'
import { rifasApi } from '../../api/rifas'
import { Header } from '../../components/layout/Header'
import { Alert } from '../../components/ui/Alert'
import { Card } from '../../components/ui/Card'
import { Spinner } from '../../components/ui/Spinner'
import { CompraPanel } from '../../components/rifas/CompraPanel'
import { ComprasLista } from '../../components/rifas/ComprasLista'
import { ComprobanteVenta } from '../../components/rifas/ComprobanteVenta'
import { CajaResumen } from '../../components/rifas/CajaResumen'
import { ParcelaBuscador } from '../../components/rifas/ParcelaBuscador'
import { clp } from '../../utils/format'
import { useRole } from '../../hooks/useAuth'
import type { CompraRifa, RifaDetalle } from '../../types'

type Tab = 'vender' | 'buscar' | 'caja'

function Cargando() {
  return <div className="flex h-48 items-center justify-center"><Spinner size="lg" className="text-primary-500" /></div>
}

function Vender({ rifa }: { rifa: RifaDetalle }) {
  const [vendida, setVendida] = useState<CompraRifa | null>(null)
  const { data: parcelas = [], isLoading } = useQuery({
    queryKey: ['rifa-parcelas', rifa.id],
    queryFn: () => rifasApi.parcelas(rifa.id),
  })

  if (vendida) {
    return (
      <Card>
        <ComprobanteVenta rifa={rifa} compra={vendida} onNuevaVenta={() => setVendida(null)} />
      </Card>
    )
  }
  if (isLoading) return <Cargando />
  return (
    <Card>
      <CompraPanel rifa={rifa} modo="porteria" parcelas={parcelas} onVendida={setVendida} barraFija />
    </Card>
  )
}

function Buscar({ rifa }: { rifa: RifaDetalle }) {
  const [parcelaId, setParcelaId] = useState<number | null>(null)
  const [folio, setFolio] = useState('')
  const { data: parcelas = [] } = useQuery({ queryKey: ['rifa-parcelas', rifa.id], queryFn: () => rifasApi.parcelas(rifa.id) })

  const filtros = parcelaId ? { parcela_id: parcelaId } : folio.trim() ? { folio: folio.trim() } : null
  const { data: compras = [], isFetching } = useQuery({
    queryKey: ['rifa-compras', rifa.id, filtros],
    queryFn: () => rifasApi.buscarCompras(rifa.id, filtros!),
    enabled: !!filtros,
  })

  return (
    <Card>
      <div className="space-y-4">
        <div className="space-y-2">
          <p className="text-sm font-semibold text-slate-300">Por parcela</p>
          <ParcelaBuscador parcelas={parcelas} value={parcelaId} onChange={(p) => { setParcelaId(p?.id ?? null); setFolio('') }} />
        </div>
        <div className="space-y-2">
          <label htmlFor="folio" className="text-sm font-semibold text-slate-300">O por folio</label>
          <input
            id="folio"
            value={folio}
            onChange={(e) => { setFolio(e.target.value); setParcelaId(null) }}
            placeholder={`Ej: R${rifa.id}-012`}
            className="w-full rounded-xl border border-slate-600 bg-slate-800 px-3 py-3 font-mono text-base uppercase text-slate-100 placeholder-slate-500 focus:border-primary-500 focus:outline-none"
          />
        </div>
        {filtros && (isFetching ? <Cargando /> : (
          <ComprasLista rifaId={rifa.id} compras={compras} mostrarParcela vacio="No hay compras con ese criterio." />
        ))}
      </div>
    </Card>
  )
}

export default function VentaRifa() {
  const role = useRole()
  const [rifaId, setRifaId] = useState<number | null>(null)
  const [tab, setTab] = useState<Tab>('vender')

  const { data: abiertas = [], isLoading } = useQuery({ queryKey: ['rifas', 'abierta'], queryFn: () => rifasApi.list('abierta') })
  // Con una sola rifa abierta, se elige sola
  useEffect(() => {
    if (rifaId == null && abiertas.length === 1) setRifaId(abiertas[0].id)
  }, [abiertas, rifaId])

  const { data: rifa } = useQuery({
    queryKey: ['rifa', rifaId],
    queryFn: () => rifasApi.get(rifaId!),
    enabled: rifaId != null,
  })

  if (role && !['porteria', 'super_admin', 'admin_condominio'].includes(role)) return <Navigate to="/" replace />

  const tabs: { key: Tab; label: string; icono: typeof Ticket }[] = [
    { key: 'vender', label: 'Vender', icono: Ticket },
    { key: 'buscar', label: 'Buscar compra', icono: Search },
    { key: 'caja', label: 'Caja', icono: Banknote },
  ]

  return (
    <div className="min-h-screen bg-slate-900">
      <Header />
      <div className="mx-auto max-w-2xl space-y-5 px-4 py-6 pb-28">
        {isLoading ? (
          <Cargando />
        ) : abiertas.length === 0 ? (
          <Alert variant="info">No hay rifas a la venta en este momento.</Alert>
        ) : (
          <>
            {abiertas.length > 1 && (
              <div className="flex flex-wrap gap-2">
                {abiertas.map((r) => (
                  <button
                    key={r.id}
                    onClick={() => setRifaId(r.id)}
                    className={`rounded-xl px-4 py-2 text-sm font-medium ${rifaId === r.id ? 'bg-primary-600 text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}`}
                  >
                    {r.nombre}
                  </button>
                ))}
              </div>
            )}

            {!rifa ? (
              rifaId == null ? <Alert variant="info">Elige la rifa que vas a vender.</Alert> : <Cargando />
            ) : (
              <>
                {/* Todo lo que la portería necesita para informar al comprador */}
                <Card>
                  <h1 className="text-xl font-bold text-slate-100">{rifa.nombre}</h1>
                  <p className="mt-1 flex items-center gap-1.5 text-sm text-slate-300">
                    <HeartHandshake className="h-4 w-4 text-primary-400" /> A beneficio de {rifa.beneficiario}
                  </p>
                  {rifa.descripcion && <p className="mt-2 whitespace-pre-line text-sm text-slate-400">{rifa.descripcion}</p>}

                  <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                    <div className="rounded-lg bg-slate-700/40 px-2 py-2">
                      <p className="text-[11px] uppercase tracking-wider text-slate-500">Valor número</p>
                      <p className="font-mono font-semibold text-slate-100">{clp(rifa.precio_numero)}</p>
                    </div>
                    <div className="rounded-lg bg-slate-700/40 px-2 py-2">
                      <p className="text-[11px] uppercase tracking-wider text-slate-500">Disponibles</p>
                      <p className="font-mono font-semibold text-slate-100">
                        {rifa.cantidad_numeros - rifa.numeros_vendidos_total} de {rifa.cantidad_numeros}
                      </p>
                    </div>
                    <div className="rounded-lg bg-slate-700/40 px-2 py-2">
                      <p className="text-[11px] uppercase tracking-wider text-slate-500">Recaudado</p>
                      <p className="font-mono font-semibold text-primary-400">{clp(rifa.recaudado)}</p>
                    </div>
                  </div>

                  <div className="mt-4">
                    <p className="mb-1.5 flex items-center gap-2 text-sm font-semibold text-slate-300">
                      <Trophy className="h-4 w-4 text-yellow-400" /> Premios
                    </p>
                    {rifa.premios.length > 0 ? (
                      <ol className="space-y-1 text-sm text-slate-200">
                        {rifa.premios.map((p, i) => (
                          <li key={i} className="flex gap-2">
                            <span className="w-5 shrink-0 text-right font-mono text-slate-500">{i + 1}.</span>{p}
                          </li>
                        ))}
                      </ol>
                    ) : (
                      <p className="text-sm text-yellow-400">La administración aún no registra los premios de esta rifa.</p>
                    )}
                  </div>

                  <div className="mt-4">
                    <p className="mb-1.5 flex items-center gap-2 text-sm font-semibold text-slate-300">
                      <Landmark className="h-4 w-4 text-primary-400" /> Datos para transferir
                    </p>
                    {rifa.datos_transferencia ? (
                      <p className="whitespace-pre-line rounded-lg bg-slate-700/40 px-3 py-2 text-sm text-slate-200">{rifa.datos_transferencia}</p>
                    ) : (
                      <p className="text-sm text-yellow-400">Sin datos de transferencia: consulta a la administración antes de aceptar transferencias.</p>
                    )}
                  </div>
                </Card>

                <div className="grid grid-cols-3 gap-1 rounded-xl bg-slate-800 p-1">
                  {tabs.map(({ key, label, icono: Icono }) => (
                    <button
                      key={key}
                      onClick={() => setTab(key)}
                      className={`flex items-center justify-center gap-1.5 rounded-lg py-2.5 text-sm font-medium transition-colors ${
                        tab === key ? 'bg-primary-600 text-white' : 'text-slate-400 hover:text-slate-100'
                      }`}
                    >
                      <Icono className="h-4 w-4" /> {label}
                    </button>
                  ))}
                </div>

                {tab === 'vender' && <Vender key={rifa.id} rifa={rifa} />}
                {tab === 'buscar' && <Buscar key={rifa.id} rifa={rifa} />}
                {tab === 'caja' && <Card><CajaResumen rifaId={rifa.id} /></Card>}
              </>
            )}
          </>
        )}
      </div>
    </div>
  )
}
