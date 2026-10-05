import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { ChevronLeft, Download, HeartHandshake, Lock, Pencil, Trophy, Unlock } from 'lucide-react'
import { rifasApi } from '../../api/rifas'
import { Card } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Spinner } from '../../components/ui/Spinner'
import { Alert } from '../../components/ui/Alert'
import { Modal } from '../../components/ui/Modal'
import { CompraPanel } from '../../components/rifas/CompraPanel'
import { ComprasLista } from '../../components/rifas/ComprasLista'
import { ComprobanteVenta } from '../../components/rifas/ComprobanteVenta'
import { CajaResumen } from '../../components/rifas/CajaResumen'
import { RifaFormModal } from './RifaFormModal'
import { clp, fecha } from '../../utils/format'
import type { CompraRifa, RifaCreate } from '../../types'

type Tab = 'compras' | 'registrar' | 'imputaciones' | 'caja'

const errorMsg = (err: unknown) => {
  const detail = (err as AxiosError<{ detail: string }>)?.response?.data?.detail
  return typeof detail === 'string' ? detail : 'Error desconocido'
}

export default function RifaDetalle() {
  const { id } = useParams()
  const rifaId = Number(id)
  const qc = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = (searchParams.get('tab') as Tab) ?? 'compras'
  const setTab = (t: Tab) => setSearchParams({ tab: t }, { replace: true })

  const [actionError, setActionError] = useState('')
  const [editando, setEditando] = useState(false)
  const [editError, setEditError] = useState('')
  const [confirmarCierre, setConfirmarCierre] = useState(false)
  const [vendida, setVendida] = useState<CompraRifa | null>(null)

  const { data: rifa, isLoading } = useQuery({ queryKey: ['rifa', rifaId], queryFn: () => rifasApi.get(rifaId) })
  const { data: parcelas = [] } = useQuery({
    queryKey: ['rifa-parcelas', rifaId],
    queryFn: () => rifasApi.parcelas(rifaId),
    enabled: tab === 'registrar',
  })

  const alActualizar = () => {
    qc.invalidateQueries({ queryKey: ['rifa', rifaId] })
    qc.invalidateQueries({ queryKey: ['rifas'] })
  }

  const editarMut = useMutation({
    mutationFn: (body: RifaCreate) => rifasApi.update(rifaId, body),
    onSuccess: () => { alActualizar(); setEditando(false) },
    onError: (err) => setEditError(errorMsg(err)),
  })
  const cerrarMut = useMutation({
    mutationFn: () => rifasApi.cerrar(rifaId),
    onSuccess: (d) => { qc.setQueryData(['rifa', rifaId], d); qc.invalidateQueries({ queryKey: ['rifas'] }); setConfirmarCierre(false); setTab('imputaciones') },
    onError: (err) => { setActionError(errorMsg(err)); setConfirmarCierre(false) },
  })
  const reabrirMut = useMutation({
    mutationFn: () => rifasApi.reabrir(rifaId),
    onSuccess: (d) => { qc.setQueryData(['rifa', rifaId], d); qc.invalidateQueries({ queryKey: ['rifas'] }); setTab('compras') },
    onError: (err) => setActionError(errorMsg(err)),
  })
  const imputacionMut = useMutation({
    mutationFn: ({ impId, cargada }: { impId: number; cargada: boolean }) => rifasApi.marcarImputacion(rifaId, impId, cargada),
    onSuccess: alActualizar,
    onError: (err) => setActionError(errorMsg(err)),
  })
  const exportMut = useMutation({
    mutationFn: () => rifasApi.exportarCsv(rifaId),
    onError: (err) => setActionError(errorMsg(err)),
  })
  const exportImpMut = useMutation({
    mutationFn: () => rifasApi.exportarImputaciones(rifaId),
    onError: (err) => setActionError(errorMsg(err)),
  })

  if (isLoading) return <div className="flex h-64 items-center justify-center"><Spinner size="lg" className="text-primary-500" /></div>
  if (!rifa) return <Alert variant="error">Rifa no encontrada.</Alert>

  const abierta = rifa.estado === 'abierta'
  const vigentes = rifa.compras.filter((c) => !c.anulada)
  const porConfirmar = vigentes.filter((c) => c.medio_pago === 'transferencia' && !c.pagada)
  const sumar = (f: (c: CompraRifa) => boolean) => vigentes.filter(f).reduce((s, c) => s + c.monto, 0)
  const cobrado = sumar((c) => c.pagada)
  const gastoComun = sumar((c) => c.medio_pago === 'gasto_comun')
  const pendienteTransf = sumar((c) => c.medio_pago === 'transferencia' && !c.pagada)
  const hayCargadas = rifa.imputaciones.some((i) => i.cargada)
  const totalImputado = rifa.imputaciones.reduce((s, i) => s + i.monto, 0)
  const parcelasGastoComun = new Set(vigentes.filter((c) => c.medio_pago === 'gasto_comun').map((c) => c.parcela_id)).size

  const tabs: { key: Tab; label: string }[] = [
    { key: 'compras', label: `Compras (${vigentes.length})${porConfirmar.length ? ` · ${porConfirmar.length} por confirmar` : ''}` },
    ...(abierta ? [{ key: 'registrar' as Tab, label: 'Registrar venta' }] : []),
    { key: 'imputaciones', label: `Gasto común (${rifa.imputaciones.length})` },
    { key: 'caja', label: 'Caja' },
  ]
  const tabActiva = tabs.some((t) => t.key === tab) ? tab : 'compras'

  return (
    <div className="space-y-6">
      <div>
        <Link to="/rifas" className="mb-3 inline-flex items-center gap-1 text-sm text-slate-400 hover:text-slate-200">
          <ChevronLeft className="h-4 w-4" /> Rifas
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-100">{rifa.nombre}</h1>
              {abierta ? <Badge color="green" dot>Abierta</Badge> : <Badge color="slate">Cerrada</Badge>}
            </div>
            <p className="mt-1 flex items-center gap-1.5 text-sm text-slate-300">
              <HeartHandshake className="h-4 w-4 text-primary-400" /> A beneficio de {rifa.beneficiario}
            </p>
            {rifa.descripcion && <p className="mt-1 max-w-2xl text-sm text-slate-400">{rifa.descripcion}</p>}
            {rifa.premios.length > 0 ? (
              <p className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-300">
                <Trophy className="h-4 w-4 text-yellow-400" />
                {rifa.premios.map((p, i) => <span key={i}><span className="text-slate-500">{i + 1}.</span> {p}</span>)}
              </p>
            ) : (
              <p className="mt-2 text-sm text-yellow-400">Sin premios registrados: agrégalos con «Editar».</p>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {abierta && (
              <Button variant="secondary" size="sm" onClick={() => { setEditError(''); setEditando(true) }}>
                <Pencil className="h-4 w-4" /> Editar
              </Button>
            )}
            <Button variant="secondary" size="sm" loading={exportMut.isPending} onClick={() => { setActionError(''); exportMut.mutate() }}>
              <Download className="h-4 w-4" /> Lista para el sorteo
            </Button>
            {abierta && (
              <Button size="sm" onClick={() => { setActionError(''); setConfirmarCierre(true) }}>
                <Lock className="h-4 w-4" /> Cerrar rifa
              </Button>
            )}
            {!abierta && !hayCargadas && (
              <Button variant="secondary" size="sm" loading={reabrirMut.isPending} onClick={() => { setActionError(''); reabrirMut.mutate() }}>
                <Unlock className="h-4 w-4" /> Reabrir
              </Button>
            )}
          </div>
        </div>
      </div>

      {actionError && <Alert variant="error">{actionError}</Alert>}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: 'Vendidos', value: `${rifa.numeros_vendidos_total} / ${rifa.cantidad_numeros} · ${clp(rifa.recaudado)}` },
          { label: 'Cobrado (efectivo y transferencias)', value: clp(cobrado) },
          { label: 'Transferencias por confirmar', value: clp(pendienteTransf) },
          { label: 'A cargar en gasto común', value: clp(gastoComun) },
        ].map(({ label, value }) => (
          <Card key={label}>
            <p className="text-xs text-slate-500">{label}</p>
            <p className="mt-1 font-mono font-semibold text-slate-200">{value}</p>
          </Card>
        ))}
      </div>

      <div className="flex gap-1 overflow-x-auto border-b border-slate-700">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => { setTab(t.key); setVendida(null) }}
            className={`whitespace-nowrap px-4 py-2.5 text-sm font-medium transition-colors ${
              tabActiva === t.key ? 'border-b-2 border-primary-500 text-primary-400' : 'text-slate-400 hover:text-slate-100'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tabActiva === 'compras' && (
        <Card>
          <ComprasLista rifaId={rifa.id} compras={rifa.compras} mostrarParcela puedeConfirmar />
        </Card>
      )}

      {tabActiva === 'registrar' && (
        <Card>
          {vendida ? (
            <ComprobanteVenta rifa={rifa} compra={vendida} onNuevaVenta={() => setVendida(null)} />
          ) : (
            <>
              <p className="mb-4 text-xs text-slate-400">
                Venta registrada por la administración a nombre de una parcela (por ejemplo, una venta presencial).
                La portería tiene su propia pantalla en <span className="font-mono">/porteria</span>.
              </p>
              <CompraPanel rifa={rifa} modo="administracion" parcelas={parcelas} onVendida={setVendida} />
            </>
          )}
        </Card>
      )}

      {tabActiva === 'imputaciones' && (
        <Card padding={false}>
          {rifa.imputaciones.length === 0 ? (
            <p className="p-5 text-sm text-slate-500">
              {abierta
                ? 'Al cerrar la rifa se genera una imputación por parcela con lo comprado con cargo al gasto común, para cargarla en Comunidad Feliz.'
                : 'Ninguna parcela compró con cargo al gasto común.'}
            </p>
          ) : (
            <>
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-700 px-4 py-3">
                <p className="text-sm text-slate-300">
                  Total a cargar: <span className="font-mono font-semibold text-slate-100">{clp(totalImputado)}</span>
                  <span className="ml-2 text-slate-500">· marca cada fila cuando la cargues en Comunidad Feliz</span>
                </p>
                <Button size="sm" variant="secondary" loading={exportImpMut.isPending} onClick={() => { setActionError(''); exportImpMut.mutate() }}>
                  <Download className="h-4 w-4" /> CSV para Comunidad Feliz
                </Button>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700 text-left text-xs uppercase tracking-wider text-slate-500">
                    <th className="px-4 py-3">Parcela</th>
                    <th className="px-4 py-3 text-right">Números</th>
                    <th className="px-4 py-3 text-right">Monto</th>
                    <th className="px-4 py-3">Estado</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {rifa.imputaciones.map((imp) => (
                    <tr key={imp.id} className="border-b border-slate-700/50">
                      <td className="px-4 py-3 text-slate-200">{imp.parcela_numero}</td>
                      <td className="px-4 py-3 text-right font-mono text-slate-300">{imp.cantidad_numeros}</td>
                      <td className="px-4 py-3 text-right font-mono font-semibold text-slate-100">{clp(imp.monto)}</td>
                      <td className="px-4 py-3">
                        {imp.cargada ? <Badge color="green" dot>Cargada {fecha(imp.cargada_at)}</Badge> : <Badge color="yellow" dot>Por cargar</Badge>}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Button
                          size="sm"
                          variant={imp.cargada ? 'ghost' : 'secondary'}
                          loading={imputacionMut.isPending && imputacionMut.variables?.impId === imp.id}
                          onClick={() => { setActionError(''); imputacionMut.mutate({ impId: imp.id, cargada: !imp.cargada }) }}
                        >
                          {imp.cargada ? 'Desmarcar' : 'Marcar cargada'}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </Card>
      )}

      {tabActiva === 'caja' && <Card><CajaResumen rifaId={rifa.id} /></Card>}

      <RifaFormModal
        open={editando}
        onClose={() => setEditando(false)}
        onSubmit={(body) => editarMut.mutate(body)}
        loading={editarMut.isPending}
        error={editError}
        rifa={rifa}
        precioBloqueado={rifa.numeros_vendidos_total > 0}
      />

      <Modal open={confirmarCierre} onClose={() => setConfirmarCierre(false)} title="Cerrar rifa" size="sm">
        <div className="space-y-4">
          <p className="text-sm text-slate-300">
            Las compras quedan firmes y dejan de poder anularse. Se generará una imputación al gasto común para cada una de las{' '}
            <strong>{parcelasGastoComun}</strong> parcelas que compraron con ese medio, por <strong>{clp(gastoComun)}</strong> en total.
          </p>
          {porConfirmar.length > 0 && (
            <p className="text-sm text-yellow-300">
              Hay {porConfirmar.length} transferencia{porConfirmar.length > 1 ? 's' : ''} por confirmar: podrás confirmarlas después del cierre.
            </p>
          )}
          <p className="text-xs text-slate-400">Podrás reabrirla mientras ninguna imputación esté marcada como cargada.</p>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setConfirmarCierre(false)} disabled={cerrarMut.isPending}>Cancelar</Button>
            <Button loading={cerrarMut.isPending} onClick={() => cerrarMut.mutate()}>Cerrar rifa</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
