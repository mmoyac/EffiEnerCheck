import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { Download, HandCoins, Receipt, Wallet } from 'lucide-react'
import { cuentaLuzApi } from '../../api/cuentaLuz'
import { condominiosApi } from '../../api/condominios'
import { useAuth, useRole } from '../../hooks/useAuth'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Modal } from '../../components/ui/Modal'
import { Alert } from '../../components/ui/Alert'
import { Spinner } from '../../components/ui/Spinner'
import { Badge } from '../../components/ui/Badge'
import { dia } from '../../components/EstadoPagoLuz'
import { clp, periodoCorto } from '../../utils/format'
import type { CargoLuz, ResumenCobranza } from '../../types'

type Deudor = ResumenCobranza['deudores'][number]

const hoy = () => new Date().toLocaleDateString('en-CA', { timeZone: 'America/Santiago' })   // YYYY-MM-DD
const errorDe = (e: unknown, def: string) => (e as AxiosError<{ detail: string }>)?.response?.data?.detail ?? def
const etiquetaCargo = (c: Pick<CargoLuz, 'tipo' | 'fecha'>) => (c.tipo === 'saldo_inicial' ? 'Saldo inicial' : periodoCorto(c.fecha))

/**
 * Liquidaciones y cobranza (cambio cobranza-energia): cuánto deben los comuneros por luz.
 * Los abonos se registran aquí (cualquier monto) y se imputan a la deuda más antigua; nunca se borran.
 */
export default function Cobranza() {
  const qc = useQueryClient()
  const role = useRole()
  const { user } = useAuth()
  const isSuperAdmin = role === 'super_admin'
  const [condominioId, setCondominioId] = useState<number | undefined>(user?.condominio_id ?? undefined)
  const [seleccion, setSeleccion] = useState<Set<number>>(new Set())
  const [abonoDe, setAbonoDe] = useState<Deudor[] | null>(null)     // 1 = individual, varios = masivo
  const [cuentaDe, setCuentaDe] = useState<number | null>(null)

  const { data: condominios = [] } = useQuery({ queryKey: ['condominios'], queryFn: condominiosApi.list, enabled: isSuperAdmin })
  const { data, isLoading, error } = useQuery({
    queryKey: ['cobranza', condominioId],
    queryFn: () => cuentaLuzApi.resumen(condominioId),
    enabled: !isSuperAdmin || !!condominioId,
  })
  const refrescar = () => { qc.invalidateQueries({ queryKey: ['cobranza'] }); qc.invalidateQueries({ queryKey: ['cuenta-luz'] }) }

  const deudores = data?.deudores ?? []
  const seleccionados = deudores.filter((d) => seleccion.has(d.parcela_id))
  const t = data?.totales
  const porcentaje = t && t.cargos > 0 ? Math.round((t.abonado / t.cargos) * 100) : 0

  const exportar = () => {
    const filas = [['Parcela', 'Propietario', 'Meses adeudados', 'Saldo'],
      ...deudores.map((d) => [d.numero_parcela, d.propietario_nombre ?? '',
        d.pendientes.map((c) => `${etiquetaCargo(c)}${c.estado === 'parcial' ? ' (parcial)' : ''}`).join(' / '), String(d.saldo)])]
    const csv = filas.map((f) => f.map((x) => `"${x.replace(/"/g, '""')}"`).join(';')).join('\r\n')
    const url = URL.createObjectURL(new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `deudores-luz-${hoy()}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Liquidaciones y cobranza</h1>
          <p className="text-sm text-slate-500">Cuánto deben los comuneros por luz. Los abonos se imputan a la deuda más antigua.</p>
        </div>
        {isSuperAdmin && (
          <select value={condominioId ?? ''} onChange={(e) => setCondominioId(Number(e.target.value) || undefined)}
                  className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-100">
            <option value="">— Condominio —</option>
            {condominios.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
          </select>
        )}
      </div>

      {error && <Alert variant="error">{errorDe(error, 'No se pudo cargar la cobranza')}</Alert>}
      {isLoading && <div className="flex h-48 items-center justify-center"><Spinner size="lg" className="text-primary-500" /></div>}

      {data && t && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Card><p className="text-xs text-slate-500">Cargos emitidos</p><p className="mt-1 font-mono text-lg font-bold text-slate-100">{clp(t.cargos)}</p>
              {t.saldo_inicial > 0 && <p className="text-xs text-slate-500">incluye {clp(t.saldo_inicial)} de saldo inicial</p>}</Card>
            <Card><p className="text-xs text-slate-500">Abonado</p><p className="mt-1 font-mono text-lg font-bold text-green-400">{clp(t.abonado)}</p>
              <p className="text-xs text-slate-500">{porcentaje}% de lo emitido</p></Card>
            <Card><p className="text-xs text-slate-500">Por cobrar</p><p className="mt-1 font-mono text-lg font-bold text-red-400">{clp(t.por_cobrar)}</p>
              <p className="text-xs text-slate-500">{deudores.length} parcela{deudores.length === 1 ? '' : 's'} con deuda</p></Card>
            <Card><p className="text-xs text-slate-500">Saldo a favor</p><p className="mt-1 font-mono text-lg font-bold text-slate-300">{clp(t.a_favor)}</p>
              <p className="text-xs text-slate-500">se aplica al próximo período publicado</p></Card>
          </div>

          <Card padding={false}>
            <p className="border-b border-slate-700 px-5 py-3 text-sm font-semibold text-slate-300">Cobranza por período (solo publicados)</p>
            <ul className="divide-y divide-slate-700/50">
              {data.periodos.map((p) => {
                const pct = p.emitido > 0 ? Math.round((p.cubierto / p.emitido) * 100) : 100
                return (
                  <li key={`${p.tipo}-${p.boleta_id ?? p.fecha}`} className="space-y-2 px-5 py-3">
                    <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                      <span className="font-medium text-slate-200">{etiquetaCargo(p)}</span>
                      <span className="text-xs text-slate-400">{p.pagados}/{p.cargos} pagados · {pct}%</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-slate-700"><div className="h-1.5 bg-primary-500" style={{ width: `${pct}%` }} /></div>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div><p className="text-slate-500">Emitido</p><p className="font-mono text-slate-300">{clp(p.emitido)}</p></div>
                      <div><p className="text-slate-500">Cubierto</p><p className="font-mono text-green-400">{clp(p.cubierto)}</p></div>
                      <div><p className="text-slate-500">Pendiente</p><p className="font-mono text-red-400">{clp(p.pendiente)}</p></div>
                    </div>
                  </li>
                )
              })}
              {data.periodos.length === 0 && <li className="px-5 py-8 text-center text-slate-500">Aún no hay períodos publicados.</li>}
            </ul>
          </Card>

          <Card padding={false}>
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-700 px-4 py-3">
              <p className="text-sm font-semibold text-slate-300">Deudores ({deudores.length})</p>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" disabled={!seleccionados.length} onClick={() => setAbonoDe(seleccionados)}>
                  <HandCoins className="h-4 w-4" /> Pagar saldo ({seleccionados.length})
                </Button>
                <Button size="sm" variant="secondary" disabled={!deudores.length} onClick={exportar}>
                  <Download className="h-4 w-4" /> CSV
                </Button>
              </div>
            </div>
            {deudores.length > 0 && (
              <label className="flex items-center gap-2 border-b border-slate-700/50 px-4 py-2 text-xs text-slate-400">
                <input type="checkbox" checked={seleccion.size === deudores.length}
                  onChange={(e) => setSeleccion(e.target.checked ? new Set(deudores.map((d) => d.parcela_id)) : new Set())} />
                Seleccionar todos
              </label>
            )}
            <ul className="divide-y divide-slate-700/50">
              {deudores.map((d) => (
                <li key={d.parcela_id} className="flex gap-3 px-4 py-3">
                  <input type="checkbox" className="mt-1" aria-label={`Seleccionar parcela ${d.numero_parcela}`}
                    checked={seleccion.has(d.parcela_id)}
                    onChange={(e) => setSeleccion((s) => { const n = new Set(s); if (e.target.checked) n.add(d.parcela_id); else n.delete(d.parcela_id); return n })} />
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                      <div className="min-w-0">
                        <p className="font-medium text-slate-200">Parcela {d.numero_parcela}</p>
                        {d.propietario_nombre && <p className="truncate text-xs text-slate-500">{d.propietario_nombre}</p>}
                      </div>
                      <p className="font-mono font-bold text-red-400">{clp(d.saldo)}</p>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {d.pendientes.map((c) => (
                        <Badge key={`${c.tipo}-${c.fecha}`} color={c.estado === 'parcial' ? 'yellow' : 'slate'}>
                          {etiquetaCargo(c)}{c.estado === 'parcial' ? ' · parcial' : ''}
                        </Badge>
                      ))}
                    </div>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs text-slate-500">Último abono: {dia(d.ultimo_abono)}</span>
                      <div className="flex gap-1">
                        <Button size="sm" variant="secondary" onClick={() => setAbonoDe([d])}><Wallet className="h-4 w-4" /> Abonar</Button>
                        <Button size="sm" variant="ghost" onClick={() => setCuentaDe(d.parcela_id)}><Receipt className="h-4 w-4" /> Cuenta</Button>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
              {deudores.length === 0 && <li className="px-5 py-8 text-center text-slate-500">Nadie debe por luz. 🎉</li>}
            </ul>
          </Card>
        </>
      )}

      {abonoDe && <AbonoModal deudores={abonoDe} onClose={() => setAbonoDe(null)}
        onListo={() => { setAbonoDe(null); setSeleccion(new Set()); refrescar() }} />}
      {cuentaDe != null && <CuentaModal parcelaId={cuentaDe} onClose={() => setCuentaDe(null)} onCambio={refrescar} />}
    </div>
  )
}

/** Un abono (cualquier monto) o varios (el saldo de cada parcela seleccionada), con fecha y nota. */
function AbonoModal({ deudores, onClose, onListo }: { deudores: Deudor[]; onClose: () => void; onListo: () => void }) {
  const individual = deudores.length === 1
  const [monto, setMonto] = useState(individual ? String(deudores[0].saldo) : '')
  const [fecha, setFecha] = useState(hoy())
  const [nota, setNota] = useState('')
  const mut = useMutation({
    mutationFn: () => cuentaLuzApi.abonar(fecha, individual
      ? [{ parcela_id: deudores[0].parcela_id, monto: Number(monto) }]
      : deudores.map((d) => ({ parcela_id: d.parcela_id, monto: d.saldo })), nota),
    onSuccess: onListo,
  })
  const total = individual ? Number(monto) || 0 : deudores.reduce((s, d) => s + d.saldo, 0)
  const valido = individual ? Number(monto) > 0 : deudores.length > 0
  return (
    <Modal open onClose={onClose} title={individual ? `Abono · Parcela ${deudores[0].numero_parcela}` : `Pago del saldo · ${deudores.length} parcelas`}>
      <div className="space-y-4">
        {individual
          ? <p className="text-sm text-slate-300">Saldo actual: <strong className="font-mono">{clp(deudores[0].saldo)}</strong>. Puede ser un abono parcial: se aplica a la deuda más antigua.</p>
          : <p className="text-sm text-slate-300">Se registra un abono por el <strong>saldo completo</strong> de cada parcela seleccionada (total {clp(total)}).</p>}
        {individual && <Input label="Monto del abono" type="number" min={1} value={monto} onChange={(e) => setMonto(e.target.value)} />}
        <Input label="Fecha del pago" type="date" max={hoy()} value={fecha} onChange={(e) => setFecha(e.target.value)} />
        <Input label="Nota (opcional)" placeholder="Ej: gasto común octubre, comprobante 1234" value={nota} onChange={(e) => setNota(e.target.value)} />
        <p className="text-xs text-slate-500">El abono queda registrado para auditoría; si te equivocas, se anula con un motivo (no se borra).</p>
        {mut.error && <Alert variant="error">{errorDe(mut.error, 'No se pudo registrar el abono')}</Alert>}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button loading={mut.isPending} disabled={!valido || !fecha} onClick={() => mut.mutate()}>Registrar {clp(total)}</Button>
        </div>
      </div>
    </Modal>
  )
}

/** Cuenta corriente de una parcela: cargos con su estado, abonos (también los anulados) y anulación con motivo. */
export function CuentaModal({ parcelaId, onClose, onCambio, soloLectura = false }: {
  parcelaId: number; onClose: () => void; onCambio?: () => void; soloLectura?: boolean
}) {
  const qc = useQueryClient()
  const { data: cuenta, isLoading } = useQuery({ queryKey: ['cuenta-luz', parcelaId], queryFn: () => cuentaLuzApi.cuenta(parcelaId) })
  const anular = useMutation({
    mutationFn: ({ id, motivo }: { id: number; motivo: string }) => cuentaLuzApi.anular(id, motivo),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['cuenta-luz', parcelaId] }); onCambio?.() },
  })
  const movimientos = useMemo(() => {
    if (!cuenta) return []
    const cargos = cuenta.cargos.map((c) => ({ clave: `c-${c.tipo}-${c.fecha}`, fecha: c.fecha, cargo: c, abono: null }))
    const abonos = cuenta.abonos.map((a) => ({ clave: `a-${a.id}`, fecha: a.fecha, cargo: null, abono: a }))
    return [...cargos, ...abonos].sort((x, y) => x.fecha.localeCompare(y.fecha))
  }, [cuenta])
  return (
    <Modal open onClose={onClose} size="xl" title={cuenta ? `Cuenta de luz · Parcela ${cuenta.numero_parcela}` : 'Cuenta de luz'}>
      {isLoading || !cuenta ? <div className="flex h-32 items-center justify-center"><Spinner /></div> : (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-2 text-sm">
            <div className="rounded-lg bg-slate-800 p-3"><p className="text-xs text-slate-500">Cargos</p><p className="font-mono font-bold text-slate-100">{clp(cuenta.total_cargos)}</p></div>
            <div className="rounded-lg bg-slate-800 p-3"><p className="text-xs text-slate-500">Abonos</p><p className="font-mono font-bold text-green-400">{clp(cuenta.total_abonos)}</p></div>
            <div className="rounded-lg bg-slate-800 p-3"><p className="text-xs text-slate-500">{cuenta.saldo < 0 ? 'Saldo a favor' : 'Saldo'}</p>
              <p className={`font-mono font-bold ${cuenta.saldo > 0 ? 'text-red-400' : 'text-green-400'}`}>{clp(Math.abs(cuenta.saldo))}</p></div>
          </div>
          {anular.error && <Alert variant="error">{errorDe(anular.error, 'No se pudo anular')}</Alert>}
          <ul className="max-h-[50vh] divide-y divide-slate-700/50 overflow-y-auto rounded-lg border border-slate-700 text-sm">
            {movimientos.map(({ clave, cargo, abono }) => cargo ? (
              <li key={clave} className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 px-3 py-2">
                <div className="min-w-0">
                  <p className="text-slate-200">{cargo.tipo === 'saldo_inicial' ? 'Saldo inicial (deuda anterior)' : `Luz ${periodoCorto(cargo.fecha)}`}</p>
                  <p className="text-xs text-slate-500">{cargo.tipo === 'saldo_inicial' ? dia(cargo.fecha) : 'Cargo del período'}</p>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <span className="font-mono text-slate-300">{clp(cargo.monto)}</span>
                  <Badge color={cargo.estado === 'pagado' ? 'green' : cargo.estado === 'parcial' ? 'yellow' : 'slate'}>
                    {cargo.estado === 'pagado' ? 'Pagado' : cargo.estado === 'parcial' ? `Parcial · ${clp(cargo.cubierto)}` : 'Pendiente'}
                  </Badge>
                </div>
              </li>
            ) : abono && (
              <li key={clave} className={`flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 px-3 py-2 ${abono.anulado ? 'opacity-50' : ''}`}>
                <div className="min-w-0">
                  <p className={`text-slate-200 ${abono.anulado ? 'line-through' : ''}`}>Abono{abono.nota ? ` · ${abono.nota}` : ''}</p>
                  <p className="text-xs text-slate-500">{dia(abono.fecha)}</p>
                  {abono.anulado && <p className="text-xs text-yellow-300">Anulado: {abono.motivo_anulacion}</p>}
                </div>
                <div className="flex flex-col items-end gap-1">
                  <span className={`font-mono text-green-400 ${abono.anulado ? 'line-through' : ''}`}>− {clp(abono.monto)}</span>
                  {!soloLectura && !abono.anulado && (
                    <button className="text-xs text-slate-400 underline hover:text-red-300" disabled={anular.isPending}
                      onClick={() => {
                        const motivo = window.prompt('Motivo de la anulación (queda registrado):')
                        if (motivo && motivo.trim().length >= 5) anular.mutate({ id: abono.id, motivo: motivo.trim() })
                        else if (motivo !== null) window.alert('El motivo debe tener al menos 5 caracteres.')
                      }}>Anular</button>
                  )}
                </div>
              </li>
            ))}
            {movimientos.length === 0 && <li className="px-3 py-6 text-center text-slate-500">Sin movimientos.</li>}
          </ul>
        </div>
      )}
    </Modal>
  )
}
