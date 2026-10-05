import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { CheckCircle2, Clock, Zap, TrendingUp, DollarSign, FileText, ImageIcon, ChevronRight, ChevronLeft, Ticket } from 'lucide-react'
import { boletasApi } from '../../api/boletas'
import { liquidacionesApi } from '../../api/liquidaciones'
import { rifasApi } from '../../api/rifas'
import { Card } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { Spinner } from '../../components/ui/Spinner'
import { Alert } from '../../components/ui/Alert'
import { Modal } from '../../components/ui/Modal'
import { clp, kwh, periodoCorto, fecha } from '../../utils/format'
import { useAuth, useModulo } from '../../hooks/useAuth'
import { Header } from '../../components/layout/Header'

export default function MiLiquidacion() {
  const { user } = useAuth()
  const misParcelas = user?.parcelas ?? []
  const [imagenOpen, setImagenOpen] = useState(false)
  const [selectedBoletaId, setSelectedBoletaId] = useState<number | null>(null)

  const { data: boletas = [], isLoading: loadingBoletas } = useQuery({
    queryKey: ['boletas'],
    queryFn: boletasApi.list,
  })

  // La API retorna las boletas ordenadas de forma descendente (más nuevas primero)
  const boletasVisibles = boletas.filter((b) => b.boleta_visible_usuarios)
  const boletaActiva = boletasVisibles.find((b) => b.id === selectedBoletaId) || null

  const { data: liquidaciones = [], isLoading: loadingLiq } = useQuery({
    queryKey: ['liquidaciones', boletaActiva?.id],
    queryFn: () => liquidacionesApi.list(boletaActiva!.id),
    enabled: !!boletaActiva,
  })

  // Sin el módulo de rifas no hay aviso (ni consulta: la API respondería 403)
  const conRifas = useModulo('rifas')
  const { data: rifasAbiertas = [] } = useQuery({
    queryKey: ['rifas', 'abierta'],
    queryFn: () => rifasApi.list('abierta'),
    enabled: conRifas,
  })

  const misLiquidaciones = liquidaciones.filter((l) =>
    misParcelas.some((p) => p.id === l.parcela_id),
  )

  return (
    <div className="min-h-screen bg-slate-900">
      <Header />
      <div className="mx-auto max-w-lg space-y-5 px-4 py-6 pb-20">
        
        {/* VISTA DE LISTA */}
        {!selectedBoletaId && (
          <>
            {rifasAbiertas.map((r) => (
              <Link
                key={r.id}
                to={`/mis-rifas/${r.id}`}
                className="flex items-center gap-3 rounded-xl border border-primary-500/40 bg-primary-600/10 p-4 transition-all hover:bg-primary-600/20 active:scale-[0.98]"
              >
                <Ticket className="h-6 w-6 shrink-0 text-primary-400" />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold text-slate-100">{r.nombre}</p>
                  <p className="truncate text-xs text-slate-300">Rifa solidaria a beneficio de {r.beneficiario} · Toca para comprar números</p>
                </div>
                <ChevronRight className="h-5 w-5 shrink-0 text-primary-400" />
              </Link>
            ))}

            <div>
              <h1 className="text-xl font-bold text-slate-100">Mis liquidaciones</h1>
              <p className="text-sm text-slate-500">Selecciona un período para ver el detalle</p>
            </div>

            {loadingBoletas ? (
              <div className="flex h-48 items-center justify-center">
                <Spinner size="lg" className="text-primary-500" />
              </div>
            ) : boletasVisibles.length === 0 ? (
              <Alert variant="info">
                Aún no hay períodos publicados. Consulta pronto con la administración.
              </Alert>
            ) : (
              <div className="space-y-3">
                {boletasVisibles.map((b) => (
                  <button
                    key={b.id}
                    onClick={() => setSelectedBoletaId(b.id)}
                    className="flex w-full items-center justify-between rounded-xl bg-slate-800 p-4 text-left transition-all hover:bg-slate-700 active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <div>
                      <p className="font-semibold capitalize text-slate-100">{periodoCorto(b.periodo_mes)}</p>
                      <p className="mt-0.5 text-xs text-slate-400">Toca para ver detalle</p>
                    </div>
                    <ChevronRight className="h-5 w-5 text-slate-500" />
                  </button>
                ))}
              </div>
            )}
          </>
        )}

        {/* VISTA DE DETALLE */}
        {selectedBoletaId && boletaActiva && (
          <>
            <div>
              <button 
                onClick={() => setSelectedBoletaId(null)}
                className="mb-4 flex items-center gap-1 text-sm font-medium text-primary-500 transition-colors hover:text-primary-400 focus:outline-none"
              >
                <ChevronLeft className="h-4 w-4" /> Volver a mis liquidaciones
              </button>
              <h1 className="text-xl font-bold capitalize text-slate-100">{periodoCorto(boletaActiva.periodo_mes)}</h1>
            </div>

            {loadingLiq ? (
              <div className="flex h-48 items-center justify-center">
                <Spinner size="lg" className="text-primary-500" />
              </div>
            ) : misLiquidaciones.length === 0 ? (
              <Alert variant="warning">No se encontraron liquidaciones para tus parcelas en este período.</Alert>
            ) : (
              misLiquidaciones.map((liq) => {
                const parcela = misParcelas.find((p) => p.id === liq.parcela_id)
                return (
                  <Card key={liq.id}>
                    {/* Header de la card */}
                    <div className="mb-4 flex items-center justify-between">
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
                          Parcela {parcela?.numero_parcela}
                        </p>
                        {parcela?.propietario_nombre && (
                          <p className="text-sm text-slate-400">{parcela.propietario_nombre}</p>
                        )}
                      </div>
                      {liq.pagado ? (
                        <Badge color="green" dot>Pagado</Badge>
                      ) : (
                        <Badge color="yellow" dot>Pendiente</Badge>
                      )}
                    </div>

                    {/* Desglose */}
                    <div className="space-y-2 rounded-xl bg-slate-700/40 p-4">
                      <div className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-2 text-slate-400"><Zap className="h-3.5 w-3.5 text-yellow-400" />Energía (kWh)</span>
                        <span className="font-mono text-slate-300">{clp(liq.monto_energia_kwh)}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-2 text-slate-400"><TrendingUp className="h-3.5 w-3.5 text-blue-400" />Prorrateo variable</span>
                        <span className="font-mono text-slate-300">{clp(liq.monto_prorrateo_variable)}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-2 text-slate-400"><DollarSign className="h-3.5 w-3.5 text-purple-400" />Cuota fija</span>
                        <span className="font-mono text-slate-300">{clp(liq.monto_cuota_fija)}</span>
                      </div>
                      <div className="mt-3 flex items-center justify-between border-t border-slate-600 pt-3">
                        <span className="font-semibold text-slate-100">Total a pagar</span>
                        <span className="font-mono text-xl font-bold text-primary-400">{clp(liq.total_pagar_mes)}</span>
                      </div>
                    </div>

                    {/* Estado pago */}
                    {liq.pagado ? (
                      <div className="mt-4 flex items-center gap-2 text-sm text-green-400">
                        <CheckCircle2 className="h-4 w-4" />
                        Pagado el {fecha(liq.fecha_pago)}
                      </div>
                    ) : (
                      <div className="mt-4 flex items-center gap-2 text-sm text-yellow-400">
                        <Clock className="h-4 w-4" />
                        Pago pendiente — contacta a la administración
                      </div>
                    )}
                  </Card>
                )
              })
            )}

            {/* Boleta de la compañía */}
            <Card>
              <p className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-300">
                <FileText className="h-4 w-4 text-primary-400" />
                Boleta de la compañía
              </p>

              {(boletaActiva.monto_total_emision != null || boletaActiva.total_kwh_compania != null) && (
                <div className="mb-4 space-y-2 rounded-xl bg-slate-700/40 p-4">
                  {boletaActiva.total_kwh_compania != null && (
                    <div className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2 text-slate-400">
                        <Zap className="h-3.5 w-3.5 text-yellow-400" />Total kWh
                      </span>
                      <span className="font-mono text-slate-300">{kwh(boletaActiva.total_kwh_compania)}</span>
                    </div>
                  )}
                  {boletaActiva.monto_neto_electricidad_consumida != null && (
                    <div className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2 text-slate-400">
                        <DollarSign className="h-3.5 w-3.5 text-green-400" />Neto electricidad
                      </span>
                      <span className="font-mono text-slate-300">{clp(boletaActiva.monto_neto_electricidad_consumida)}</span>
                    </div>
                  )}
                  {boletaActiva.monto_saldo_anterior != null && (
                    <div className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2 text-slate-400">
                        <TrendingUp className="h-3.5 w-3.5 text-orange-400" />Saldo anterior
                      </span>
                      <span className="font-mono text-slate-300">{clp(boletaActiva.monto_saldo_anterior)}</span>
                    </div>
                  )}
                  {boletaActiva.monto_total_emision != null && (
                    <div className="mt-3 flex items-center justify-between border-t border-slate-600 pt-3">
                      <span className="font-semibold text-slate-100">Total boleta</span>
                      <span className="font-mono text-xl font-bold text-primary-400">{clp(boletaActiva.monto_total_emision)}</span>
                    </div>
                  )}
                </div>
              )}

              {boletaActiva.items_detalle.length > 0 && (
                <div className="mb-4">
                  <p className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500">Desglose de cargos</p>
                  <div className="space-y-1">
                    {boletaActiva.items_detalle.map((item) => (
                      <div key={item.id} className="flex items-center justify-between rounded-lg px-2 py-2 text-sm">
                        <div className="flex min-w-0 items-center gap-2">
                          <Badge color={item.tipo_calculo === 'fijo' ? 'purple' : item.tipo_calculo === 'variable' ? 'blue' : 'slate'}>
                            {item.tipo_calculo}
                          </Badge>
                          <span className="truncate text-slate-400">{item.descripcion}</span>
                        </div>
                        <span className="ml-2 shrink-0 font-mono text-slate-300">{clp(item.monto_neto_clp)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {boletaActiva.url_imagen_boleta && (
                <button
                  onClick={() => setImagenOpen(true)}
                  className="mt-1 flex w-full items-center justify-center gap-2 rounded-xl border border-slate-600 py-3 text-sm font-medium text-slate-300 transition-colors hover:border-primary-500 hover:text-primary-400"
                >
                  <ImageIcon className="h-4 w-4" />
                  Ver imagen de la boleta
                </button>
              )}

              <Modal
                open={imagenOpen}
                onClose={() => setImagenOpen(false)}
                title={`Boleta de la compañía — ${periodoCorto(boletaActiva.periodo_mes)}`}
                size="xl"
              >
                {boletaActiva.url_imagen_boleta && (
                  <img
                    src={boletaActiva.url_imagen_boleta}
                    alt={`Boleta ${periodoCorto(boletaActiva.periodo_mes)}`}
                    className="w-full rounded-lg object-contain"
                  />
                )}
              </Modal>
            </Card>
          </>
        )}
      </div>
    </div>
  )
}
