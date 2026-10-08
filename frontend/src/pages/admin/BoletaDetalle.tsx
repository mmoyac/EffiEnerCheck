import { useEffect, useState } from 'react'
import { useParams, Link, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Lock, Calculator, Globe, Check, X, Pencil, Upload, ImageIcon, ScanLine, ClipboardCheck, Camera, CameraOff, Download, FileSpreadsheet } from 'lucide-react'
import { boletasApi } from '../../api/boletas'
import { lecturasApi } from '../../api/lecturas'
import { liquidacionesApi } from '../../api/liquidaciones'
import { parcelasApi } from '../../api/parcelas'
import { usuariosApi } from '../../api/usuarios'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'
import { Alert } from '../../components/ui/Alert'
import { Spinner } from '../../components/ui/Spinner'
import { clp, kwh, numero, periodoCorto, fecha, fechaHora } from '../../utils/format'
import type { LecturaParcela, Parcela } from '../../types'
import ModalEditDetalles, { CONCEPTOS_SUGERIDOS } from './ModalEditDetalles'
import { FotoMedidorModal } from '../../components/FotoMedidorModal'
import { ImportarLecturasIniciales } from './ImportarLecturasIniciales'

type Tab = 'resumen' | 'lecturas' | 'liquidaciones' | 'boleta'

const TIPO_COLOR: Record<string, string> = {
  fijo:       'text-blue-400',
  variable:   'text-yellow-400',
  informativo:'text-slate-500',
  pendiente:  'text-violet-400',
}

export default function BoletaDetalle() {
  const { id } = useParams<{ id: string }>()
  const boletaId = Number(id)
  const qc = useQueryClient()
  const [searchParams] = useSearchParams()
  const [tab, setTab] = useState<Tab>((searchParams.get('tab') as Tab) ?? 'resumen')
  const [actionError, setActionError] = useState('')
  const [editingLectura, setEditingLectura] = useState<number | null>(null)
  const [editValue, setEditValue] = useState('')
  const [editingDetalles, setEditingDetalles] = useState(false)
  const [conSugeridos, setConSugeridos] = useState(false)
  const [fotoDe, setFotoDe] = useState<LecturaParcela | null>(null)
  // Lectura anterior de una parcela sin historial (cambio lectura-inicial)
  const [editingAnterior, setEditingAnterior] = useState<number | null>(null)
  const [anteriorValue, setAnteriorValue] = useState('')
  const [importarOpen, setImportarOpen] = useState(false)

  const { data: boleta, isLoading } = useQuery({
    queryKey: ['boleta', boletaId],
    queryFn: () => boletasApi.get(boletaId),
  })

  // La lectura inicial solo tiene la pestaña Lecturas
  const inicial = boleta?.tipo === 'lectura_inicial'
  useEffect(() => { if (inicial && tab !== 'lecturas') setTab('lecturas') }, [inicial, tab])

  const { data: lecturas = [] } = useQuery({
    queryKey: ['lecturas', boletaId],
    queryFn: () => lecturasApi.list(boletaId),
    enabled: tab === 'lecturas',
  })

  const { data: liquidaciones = [] } = useQuery({
    queryKey: ['liquidaciones', boletaId],
    queryFn: () => liquidacionesApi.list(boletaId),
  })

  const { data: parcelas = [] } = useQuery({
    queryKey: ['parcelas'],
    queryFn: parcelasApi.list,
  })
  const parcelaMap = Object.fromEntries(parcelas.map((p: Parcela) => [p.id, p]))

  const { data: usuarios = [] } = useQuery({
    queryKey: ['usuarios'],
    queryFn: usuariosApi.list,
  })
  const usuarioMap = Object.fromEntries(usuarios.map((u: any) => [u.id, u]))

  const lecturasSorted = [...lecturas].sort((a, b) => {
    const pa = parcelaMap[a.parcela_id]?.numero_parcela ?? ''
    const pb = parcelaMap[b.parcela_id]?.numero_parcela ?? ''
    return pa.localeCompare(pb, 'es', { numeric: true, sensitivity: 'base' })
  })

  const liquidacionesSorted = [...liquidaciones].sort((a, b) => {
    const pa = parcelaMap[a.parcela_id]?.numero_parcela ?? ''
    const pb = parcelaMap[b.parcela_id]?.numero_parcela ?? ''
    return pa.localeCompare(pb, 'es', { numeric: true, sensitivity: 'base' })
  })

  const cerrarLectMut = useMutation({
    mutationFn: () => boletasApi.cerrarLecturas(boletaId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['boleta', boletaId] }); qc.invalidateQueries({ queryKey: ['boletas'] }) },
    onError: (e: unknown) => setActionError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error'),
  })

  const reabrirLectMut = useMutation({
    mutationFn: () => boletasApi.reabrirLecturas(boletaId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['boleta', boletaId] }); qc.invalidateQueries({ queryKey: ['boletas'] }); setTab('lecturas') },
    onError: (e: unknown) => setActionError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error'),
  })

  const updateLecturaMut = useMutation({
    mutationFn: ({ lecturaId, lecturaActual }: { lecturaId: number; lecturaActual: number }) =>
      lecturasApi.update(lecturaId, { 
        lectura_actual: lecturaActual,
        fecha_toma: new Date().toISOString()
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lecturas', boletaId] })
      setEditingLectura(null)
      // La lectura inicial no se liquida; un período regular sin corroborar tampoco se puede calcular
      if (!inicial && boleta?.estado === 'validada') calcularMut.mutate()
    },
    onError: (e: unknown) => setActionError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error al guardar lectura'),
  })

  const updateAnteriorMut = useMutation({
    mutationFn: ({ lecturaId, valor }: { lecturaId: number; valor: number }) =>
      lecturasApi.update(lecturaId, { lectura_anterior: valor }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lecturas', boletaId] })
      setEditingAnterior(null)
    },
    onError: (e: unknown) => setActionError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error al guardar la lectura anterior'),
  })

  const guardarAnterior = (l: LecturaParcela) => {
    const v = Number(anteriorValue)
    if (anteriorValue === '' || isNaN(v) || v < 0) { setActionError('Ingresa una lectura anterior válida'); return }
    if (l.fecha_toma && v > l.lectura_actual) { setActionError(`La lectura anterior (${v}) no puede ser mayor que la actual (${l.lectura_actual})`); return }
    setActionError('')
    updateAnteriorMut.mutate({ lecturaId: l.id, valor: v })
  }

  const calcularMut = useMutation({
    mutationFn: () => liquidacionesApi.calcular(boletaId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['liquidaciones', boletaId] }); qc.invalidateQueries({ queryKey: ['boleta', boletaId] }); setTab('liquidaciones') },
    onError: (e: unknown) => setActionError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error'),
  })

  const cerrarLiqMut = useMutation({
    mutationFn: () => boletasApi.cerrarLiquidaciones(boletaId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['boleta', boletaId] }); qc.invalidateQueries({ queryKey: ['boletas'] }) },
    onError: (e: unknown) => setActionError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error'),
  })

  const reabrirLiqMut = useMutation({
    mutationFn: () => boletasApi.reabrirLiquidaciones(boletaId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['boleta', boletaId] }); qc.invalidateQueries({ queryKey: ['boletas'] }) },
    onError: (e: unknown) => setActionError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error'),
  })

  const publicarMut = useMutation({
    mutationFn: () => boletasApi.update(boletaId, { boleta_visible_usuarios: true }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['boleta', boletaId] }); qc.invalidateQueries({ queryKey: ['boletas'] }) },
    onError: (e: unknown) => setActionError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error'),
  })

  const marcarPagoMut = useMutation({
    mutationFn: ({ liqId, pagado }: { liqId: number; pagado: boolean }) =>
      liquidacionesApi.marcarPago(liqId, pagado, pagado ? new Date().toISOString() : undefined),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['liquidaciones', boletaId] }),
  })

  const uploadImagenMut = useMutation({
    mutationFn: (file: File) => boletasApi.uploadImagen(boletaId, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['boleta', boletaId] })
      qc.invalidateQueries({ queryKey: ['boletas'] })
    },
    onError: (e: unknown) => setActionError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error al subir imagen'),
  })

  const procesarOcrMut = useMutation({
    mutationFn: () => boletasApi.procesarOcr(boletaId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['boleta', boletaId] })
      setTab('resumen')
    },
    onError: (e: unknown) => setActionError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error al procesar la imagen con IA'),
  })

  const updateDetallesMut = useMutation({
    mutationFn: (data: any) => boletasApi.updateDetalles(boletaId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['boleta', boletaId] })
      qc.invalidateQueries({ queryKey: ['boletas'] })
      setEditingDetalles(false)
    },
    onError: (e: unknown) => setActionError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error al actualizar detalles'),
  })

  const validarItemsMut = useMutation({
    mutationFn: () => boletasApi.validarItems(boletaId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['boleta', boletaId] })
      qc.invalidateQueries({ queryKey: ['boletas'] })
    },
    onError: (e: unknown) => setActionError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error al corroborar el desglose'),
  })

  if (isLoading || !boleta) {
    return <div className="flex h-64 items-center justify-center"><Spinner size="lg" className="text-primary-500" /></div>
  }

  const totalLiq = liquidaciones.reduce((s, l) => s + (l.total_pagar_mes ?? 0), 0)
  const pagadas = liquidaciones.filter((l) => l.pagado).length
  // Ítems que el OCR creó y nadie ha clasificado: bloquean la corroboración.
  const itemsPendientes = boleta.items_detalle.filter((i) => i.tipo_calculo === 'pendiente').length

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-start gap-4">
        <Link to="/boletas" className="mt-1 text-slate-400 hover:text-slate-100">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-slate-100">
            {inicial ? 'Lectura inicial' : 'Boleta'} {periodoCorto(boleta.periodo_mes)}
          </h1>
          <div className="mt-1 flex flex-wrap gap-2">
            {boleta.estado === 'validada' && <Badge color="purple">Desglose corroborado</Badge>}
            {boleta.lecturas_cerradas && <Badge color="yellow">Lecturas cerradas</Badge>}
            {boleta.liquidaciones_cerradas && <Badge color="blue">Período cerrado</Badge>}
            {boleta.boleta_visible_usuarios && <Badge color="green">Publicada</Badge>}
          </div>
        </div>
        {/* Actions */}
        <div className="flex flex-wrap gap-2">
          {!boleta.lecturas_cerradas && (
            <Button variant="secondary" size="sm" loading={cerrarLectMut.isPending}
              onClick={() => { setActionError(''); cerrarLectMut.mutate() }}>
              <Lock className="h-4 w-4" /> Cerrar lecturas
            </Button>
          )}
          {boleta.lecturas_cerradas && !boleta.liquidaciones_cerradas && (
            <Button variant="secondary" size="sm" loading={reabrirLectMut.isPending}
              onClick={() => { setActionError(''); reabrirLectMut.mutate() }}>
              <Lock className="h-4 w-4 text-orange-400" /> Reabrir lecturas
            </Button>
          )}
          {!inicial && boleta.estado === 'borrador' && !boleta.liquidaciones_cerradas && (
            <Button size="sm" loading={validarItemsMut.isPending}
              disabled={itemsPendientes > 0}
              title={itemsPendientes > 0 ? 'Clasifica primero los ítems pendientes' : undefined}
              onClick={() => { setActionError(''); validarItemsMut.mutate() }}>
              <ClipboardCheck className="h-4 w-4" /> Corroborar desglose
            </Button>
          )}
          {!inicial && boleta.estado === 'validada' && !boleta.liquidaciones_cerradas && (
            <Button size="sm" loading={calcularMut.isPending}
              onClick={() => { setActionError(''); calcularMut.mutate() }}>
              <Calculator className="h-4 w-4" /> Calcular liquidaciones
            </Button>
          )}
          {liquidaciones.length > 0 && boleta.lecturas_cerradas && !boleta.liquidaciones_cerradas && (
            <Button variant="secondary" size="sm" loading={cerrarLiqMut.isPending}
              onClick={() => { setActionError(''); cerrarLiqMut.mutate() }}>
              <Lock className="h-4 w-4" /> Cerrar período
            </Button>
          )}
          {boleta.liquidaciones_cerradas && !boleta.boleta_visible_usuarios && (
            <Button variant="secondary" size="sm" loading={reabrirLiqMut.isPending}
              onClick={() => { setActionError(''); reabrirLiqMut.mutate() }}>
              <Lock className="h-4 w-4 text-orange-400" /> Reabrir período
            </Button>
          )}
          {boleta.liquidaciones_cerradas && !boleta.boleta_visible_usuarios && (
            <Button variant="secondary" size="sm" loading={publicarMut.isPending}
              onClick={() => { setActionError(''); publicarMut.mutate() }}>
              <Globe className="h-4 w-4" /> Publicar
            </Button>
          )}
        </div>
      </div>

      {actionError && <Alert variant="error">{actionError}</Alert>}

      {inicial && (
        <Alert variant="info">
          Período de <strong>lectura inicial</strong>: registra la lectura de partida de cada medidor. No tiene boleta
          ni liquidaciones y no se publica. El lector la toma con la app; aquí puedes ingresarla o corregirla.
          Al cerrar las lecturas, la primera boleta parte de estos valores.
        </Alert>
      )}

      {!inicial && itemsPendientes > 0 && (
        <Alert variant="warning">
          <span className="font-semibold">
            {itemsPendientes} ítem{itemsPendientes > 1 ? 's' : ''} sin clasificar.
          </span>{' '}
          El OCR encontró {itemsPendientes > 1 ? 'líneas nuevas' : 'una línea nueva'} que no
          {itemsPendientes > 1 ? ' existían' : ' existía'} en el período anterior. Decide si
          {itemsPendientes > 1 ? ' entran' : ' entra'} al reparto antes de corroborar el desglose.{' '}
          <button
            type="button"
            className="font-medium text-primary-400 underline underline-offset-2 hover:text-primary-300"
            onClick={() => setEditingDetalles(true)}
          >
            Clasificar ahora
          </button>
        </Alert>
      )}

      {!inicial && boleta.estado === 'borrador' && itemsPendientes === 0 && !boleta.liquidaciones_cerradas && (
        <Alert variant="info">
          Revisa el desglose y corrobóralo para habilitar el cálculo. Cada período requiere que
          confirmes qué ítems entran al reparto, aunque vengan igual que el mes anterior.
        </Alert>
      )}

      {/* KPI strip */}
      {!inicial && <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: 'kWh compañía', value: kwh(boleta.total_kwh_compania) },
          { label: 'Monto neto', value: clp(boleta.monto_neto_electricidad_consumida) },
          { label: 'Total emisión', value: clp(boleta.monto_total_emision) },
          { label: 'Saldo anterior', value: clp(boleta.monto_saldo_anterior) },
        ].map(({ label, value }) => (
          <Card key={label}>
            <p className="text-xs text-slate-500">{label}</p>
            <p className="mt-1 font-mono font-semibold text-slate-200">{value}</p>
          </Card>
        ))}
      </div>}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-700">
        {((inicial ? ['lecturas'] : ['resumen', 'lecturas', 'liquidaciones', 'boleta']) as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-sm font-medium capitalize transition-colors ${
              tab === t ? 'border-b-2 border-primary-500 text-primary-400' : 'text-slate-400 hover:text-slate-100'
            }`}>
            {t === 'liquidaciones' && liquidaciones.length > 0 ? `${t} (${liquidaciones.length})` : t}
          </button>
        ))}
      </div>

      {/* Resumen */}
      {tab === 'resumen' && (
        <Card padding={false}>
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
            <h3 className="text-sm font-semibold text-slate-300">Ítems de Detalle</h3>
            {!boleta.liquidaciones_cerradas && (
              <Button size="sm" variant="secondary" onClick={() => setEditingDetalles(true)}>
                <Pencil className="h-4 w-4" /> Editar Valores
              </Button>
            )}
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="px-5 py-3">Descripción</th>
                <th className="px-5 py-3">Tipo</th>
                <th className="px-5 py-3 text-right">Monto neto CLP</th>
              </tr>
            </thead>
            <tbody>
              {boleta.items_detalle.map((item) => (
                <tr key={item.id} className="border-b border-slate-700/50">
                  <td className="px-5 py-3 text-slate-200">{item.descripcion}</td>
                  <td className="px-5 py-3">
                    <span className={`text-xs font-medium capitalize ${TIPO_COLOR[item.tipo_calculo]}`}>
                      {item.tipo_calculo}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right font-mono text-slate-300">{clp(item.monto_neto_clp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {boleta.items_detalle.length === 0 && !boleta.liquidaciones_cerradas && (
            <div className="space-y-3 px-5 py-8 text-center">
              <p className="text-sm text-slate-300">
                {boleta.total_kwh_compania == null
                  ? 'Este período aún no tiene los datos de la boleta.'
                  : 'Este período no tiene conceptos de detalle.'}
              </p>
              <p className="mx-auto max-w-xl text-xs text-slate-500">
                Sube la boleta en la pestaña <strong>Boleta</strong> y procésala con IA, o ingrésala a mano. Lo mínimo para
                liquidar son 3 totales: <strong>kWh compañía</strong>, <strong>monto neto</strong> y <strong>total emisión</strong>.
                Los conceptos son opcionales y pueden cambiar mes a mes.
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                <Button size="sm" variant="secondary" onClick={() => { setConSugeridos(false); setEditingDetalles(true) }}>
                  <Pencil className="h-4 w-4" /> Ingresar a mano
                </Button>
                <Button size="sm" onClick={() => { setConSugeridos(true); setEditingDetalles(true) }}>
                  <ClipboardCheck className="h-4 w-4" /> Usar conceptos sugeridos
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Lecturas */}
      {tab === 'lecturas' && (
        <Card padding={false}>
          {inicial && !boleta.lecturas_cerradas && (
            <div className="flex flex-wrap items-center justify-end gap-2 border-b border-slate-700 px-5 py-3">
              <Button size="sm" variant="secondary"
                onClick={() => boletasApi.descargarPlantillaLecturasIniciales(boletaId, `lecturas-iniciales-${boleta.periodo_mes.slice(0, 7)}.xlsx`)
                  .catch(() => setActionError('No se pudo descargar la plantilla'))}>
                <Download className="h-4 w-4" /> Descargar plantilla
              </Button>
              <Button size="sm" onClick={() => setImportarOpen(true)}>
                <FileSpreadsheet className="h-4 w-4" /> Cargar desde Excel
              </Button>
              <ImportarLecturasIniciales open={importarOpen} boletaId={boletaId} onClose={() => setImportarOpen(false)}
                onAplicada={() => { qc.invalidateQueries({ queryKey: ['lecturas', boletaId] }); qc.invalidateQueries({ queryKey: ['boleta', boletaId] }) }} />
            </div>
          )}
          {(() => {
            const sinFoto = lecturas.filter((l) => l.fecha_toma && !l.tiene_foto).length
            return sinFoto > 0 && (
              <p className="flex items-center gap-2 border-b border-slate-700 px-5 py-3 text-xs text-slate-400">
                <CameraOff className="h-4 w-4" /> {sinFoto} lectura{sinFoto === 1 ? '' : 's'} tomada{sinFoto === 1 ? '' : 's'} sin foto del medidor
              </p>
            )
          })()}
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="px-5 py-3">Parcela</th>
                {!inicial && <th className="px-5 py-3 text-right">L. Anterior</th>}
                <th className="px-5 py-3 text-right">{inicial ? 'Lectura inicial' : 'L. Actual'}</th>
                {!inicial && <th className="px-5 py-3 text-right">kWh consumidos</th>}
                <th className="px-5 py-3">Fecha y Hora</th>
                <th className="px-5 py-3">Lector</th>
                <th className="px-3 py-3">Foto</th>
                {!boleta.lecturas_cerradas && !boleta.liquidaciones_cerradas && <th className="px-5 py-3" />}
              </tr>
            </thead>
            <tbody>
              {lecturasSorted.map((l) => (
                <tr key={l.id} className="border-b border-slate-700/50">
                  <td className="px-5 py-3 font-medium text-slate-200">
                    {parcelaMap[l.parcela_id]?.numero_parcela ?? `#${l.parcela_id}`}
                  </td>
                  {!inicial && (
                    <td className="px-5 py-3 text-right font-mono text-slate-400">
                      {editingAnterior === l.id ? (
                        <span className="inline-flex items-center gap-1">
                          <input type="number" value={anteriorValue} autoFocus
                            onChange={(e) => setAnteriorValue(e.target.value)}
                            onKeyDown={(e) => { if (e.key === 'Enter') guardarAnterior(l); if (e.key === 'Escape') setEditingAnterior(null) }}
                            className="w-28 rounded border border-primary-500 bg-slate-800 px-2 py-1 text-right font-mono text-slate-100 focus:outline-none" />
                          <button onClick={() => guardarAnterior(l)} className="rounded p-1 text-green-400 hover:bg-green-500/20" title="Guardar"><Check className="h-3.5 w-3.5" /></button>
                          <button onClick={() => setEditingAnterior(null)} className="rounded p-1 text-slate-400 hover:bg-slate-700" title="Cancelar"><X className="h-3.5 w-3.5" /></button>
                        </span>
                      ) : l.lectura_anterior_editable && !boleta.lecturas_cerradas ? (
                        <button onClick={() => { setEditingAnterior(l.id); setAnteriorValue(l.lectura_anterior ? String(l.lectura_anterior) : '') }}
                                title="Parcela sin período anterior: ingresa su lectura anterior"
                                className="inline-flex items-center gap-1 rounded px-1 text-yellow-300 hover:bg-slate-700">
                          {numero(l.lectura_anterior)} <Pencil className="h-3 w-3" />
                        </button>
                      ) : numero(l.lectura_anterior)}
                    </td>
                  )}
                  <td className="px-5 py-3 text-right font-mono text-slate-300">
                    {editingLectura === l.id ? (
                      <input
                        type="number"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            const v = Number(editValue)
                            if (v < l.lectura_anterior) { setActionError(`Lectura actual (${v}) no puede ser menor que la anterior (${l.lectura_anterior})`); return }
                            setActionError(''); updateLecturaMut.mutate({ lecturaId: l.id, lecturaActual: v })
                          }
                          if (e.key === 'Escape') setEditingLectura(null)
                        }}
                        className="w-28 rounded border border-primary-500 bg-slate-800 px-2 py-1 text-right font-mono text-slate-100 focus:outline-none"
                        autoFocus
                      />
                    ) : (
                      numero(l.lectura_actual)
                    )}
                  </td>
                  {!inicial && <td className="px-5 py-3 text-right font-mono font-medium text-primary-400">{numero(l.kwh_consumidos)}</td>}
                  <td className="px-5 py-3 text-slate-400">{fechaHora(l.fecha_toma)}</td>
                  <td className="px-5 py-3 text-slate-400">{l.fecha_toma ? (usuarioMap[l.lector_id]?.nombre ?? 'Desconocido') : '—'}</td>
                  <td className="px-3 py-3">
                    {l.tiene_foto ? (
                      <button onClick={() => setFotoDe(l)} title="Ver foto del medidor"
                              className="rounded p-1 text-primary-400 hover:bg-slate-700 hover:text-primary-300">
                        <Camera className="h-4 w-4" />
                      </button>
                    ) : <span className="text-slate-600">—</span>}
                  </td>
                  {!boleta.lecturas_cerradas && !boleta.liquidaciones_cerradas && (
                    <td className="px-3 py-3">
                      {editingLectura === l.id ? (
                        <div className="flex gap-1">
                          <button
                            onClick={() => {
                              const v = Number(editValue)
                              if (v < l.lectura_anterior) { setActionError(`Lectura actual (${v}) no puede ser menor que la anterior (${l.lectura_anterior})`); return }
                              setActionError(''); updateLecturaMut.mutate({ lecturaId: l.id, lecturaActual: v })
                            }}
                            className="rounded p-1 text-green-400 hover:bg-green-500/20"
                            title="Guardar"
                          ><Check className="h-3.5 w-3.5" /></button>
                          <button
                            onClick={() => setEditingLectura(null)}
                            className="rounded p-1 text-slate-400 hover:bg-slate-700"
                            title="Cancelar"
                          ><X className="h-3.5 w-3.5" /></button>
                        </div>
                      ) : (
                        <button
                          onClick={() => { setEditingLectura(l.id); setEditValue(String(l.lectura_actual)) }}
                          className="rounded p-1 text-slate-500 hover:text-slate-200 hover:bg-slate-700"
                          title="Editar lectura"
                        ><Pencil className="h-3.5 w-3.5" /></button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
              {lecturas.length === 0 && (
                <tr><td colSpan={8} className="px-5 py-8 text-center text-slate-500">Sin lecturas registradas para este período</td></tr>
              )}
            </tbody>
          </table>
          <FotoMedidorModal lectura={fotoDe} onClose={() => setFotoDe(null)}
            titulo={`Medidor parcela ${fotoDe ? (parcelaMap[fotoDe.parcela_id]?.numero_parcela ?? fotoDe.parcela_id) : ''}`} />
        </Card>
      )}

      {/* Imagen boleta */}
      {tab === 'boleta' && (
        <div className="space-y-4">
          {boleta.url_imagen_boleta ? (
            <Card>
              <div className="flex flex-wrap items-center justify-between gap-4 mb-3">
                <p className="text-sm font-medium text-slate-400">Imagen de la boleta</p>
                {!boleta.liquidaciones_cerradas && (
                  <Button size="sm" onClick={() => { setActionError(''); procesarOcrMut.mutate() }} loading={procesarOcrMut.isPending}>
                    <ScanLine className="h-4 w-4" /> Procesar con IA
                  </Button>
                )}
              </div>
              <img
                src={boleta.url_imagen_boleta}
                alt={`Boleta ${periodoCorto(boleta.periodo_mes)}`}
                className="w-full rounded-lg border border-slate-700 object-contain max-h-[75vh]"
              />
            </Card>
          ) : (
            <Alert variant="info">No hay imagen cargada para esta boleta.</Alert>
          )}

          <Card>
            <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-300">
              <ImageIcon className="h-4 w-4 text-primary-400" />
              {boleta.url_imagen_boleta ? 'Reemplazar imagen' : 'Subir imagen'}
            </p>
            <label className="flex cursor-pointer flex-col items-center gap-3 rounded-xl border-2 border-dashed border-slate-600 px-6 py-8 transition-colors hover:border-primary-500">
              {uploadImagenMut.isPending ? (
                <Spinner size="lg" className="text-primary-500" />
              ) : (
                <>
                  <Upload className="h-8 w-8 text-slate-500" />
                  <span className="text-sm text-slate-400">
                    Haz clic para seleccionar un archivo
                  </span>
                  <span className="text-xs text-slate-600">JPG, PNG, WEBP, HEIC o PDF</span>
                </>
              )}
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,image/heic,application/pdf"
                className="hidden"
                disabled={uploadImagenMut.isPending}
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) { setActionError(''); uploadImagenMut.mutate(file) }
                  e.target.value = ''
                }}
              />
            </label>
          </Card>
        </div>
      )}

      {/* Liquidaciones */}
      {tab === 'liquidaciones' && (
        <>
          {liquidaciones.length > 0 && (
            <div className="flex items-center justify-between rounded-lg bg-primary-600/10 px-4 py-3">
              <p className="text-sm text-primary-300">
                {pagadas}/{liquidaciones.length} pagadas
              </p>
              <p className="font-mono font-bold text-primary-400">{clp(totalLiq)}</p>
            </div>
          )}
          <Card padding={false}>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700 text-left text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-5 py-3">Parcela</th>
                    <th className="px-5 py-3 text-right">Energía</th>
                    <th className="px-5 py-3 text-right">Variable</th>
                    <th className="px-5 py-3 text-right">Fijo</th>
                    <th className="px-5 py-3 text-right font-bold">Total</th>
                    <th className="px-5 py-3 text-center">Pago</th>
                  </tr>
                </thead>
                <tbody>
                  {liquidacionesSorted.map((liq) => (
                    <tr key={liq.id} className={`border-b border-slate-700/50 ${liq.pagado ? 'opacity-60' : ''}`}>
                      <td className="px-5 py-3 font-medium text-slate-200">
                        {parcelaMap[liq.parcela_id]?.numero_parcela ?? `#${liq.parcela_id}`}
                      </td>
                      <td className="px-5 py-3 text-right font-mono text-slate-400">{clp(liq.monto_energia_kwh)}</td>
                      <td className="px-5 py-3 text-right font-mono text-slate-400">{clp(liq.monto_prorrateo_variable)}</td>
                      <td className="px-5 py-3 text-right font-mono text-slate-400">{clp(liq.monto_cuota_fija)}</td>
                      <td className="px-5 py-3 text-right font-mono font-bold text-slate-100">{clp(liq.total_pagar_mes)}</td>
                      <td className="px-5 py-3 text-center">
                        <button
                          disabled={boleta.liquidaciones_cerradas}
                          onClick={() => marcarPagoMut.mutate({ liqId: liq.id, pagado: !liq.pagado })}
                          className={`rounded-full p-1.5 transition-colors ${
                            liq.pagado
                              ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
                              : 'bg-slate-700 text-slate-500 hover:bg-slate-600'
                          } disabled:opacity-40 disabled:cursor-not-allowed`}
                        >
                          {liq.pagado ? <Check className="h-3.5 w-3.5" /> : <X className="h-3.5 w-3.5" />}
                        </button>
                      </td>
                    </tr>
                  ))}
                  {liquidaciones.length === 0 && (
                    <tr><td colSpan={6} className="px-5 py-8 text-center text-slate-500">Sin liquidaciones. Usa "Calcular" para generarlas.</td></tr>
                  )}
                </tbody>
                {liquidaciones.length > 0 && (
                  <tfoot>
                    <tr className="border-t border-slate-600 bg-slate-700/30">
                      <td className="px-5 py-3 font-semibold text-slate-300" colSpan={4}>TOTAL</td>
                      <td className="px-5 py-3 text-right font-mono font-bold text-primary-400">{clp(totalLiq)}</td>
                      <td />
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          </Card>
        </>
      )}

      <ModalEditDetalles
        boleta={boleta}
        open={editingDetalles}
        onClose={() => { setEditingDetalles(false); setConSugeridos(false) }}
        onSave={(data) => updateDetallesMut.mutate(data)}
        itemsIniciales={conSugeridos ? CONCEPTOS_SUGERIDOS : undefined}
        isPending={updateDetallesMut.isPending}
        error={(updateDetallesMut.error as any)?.response?.data?.detail ?? ''}
      />
    </div>
  )
}
