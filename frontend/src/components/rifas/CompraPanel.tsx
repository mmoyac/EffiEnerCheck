import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { Banknote, Landmark, Receipt, Ticket } from 'lucide-react'
import { rifasApi } from '../../api/rifas'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { Modal } from '../ui/Modal'
import { NumeroGrid } from './NumeroGrid'
import { ParcelaBuscador } from './ParcelaBuscador'
import { VoucherInput } from './VoucherInput'
import { clp } from '../../utils/format'
import { MEDIO_PAGO_TEXTO } from '../../utils/comprobante'
import { formatearTelefono, normalizarTelefono } from '../../utils/telefono'
import type { CompraRifa, MedioPago, ParcelaVenta, RifaDetalle } from '../../types'

interface Props {
  rifa: RifaDetalle
  /**
   * portal: el vecino compra a nombre de sus parcelas (transferencia o gasto común).
   * porteria / administracion: venta a nombre de cualquier parcela, con efectivo y comprador libre.
   */
  modo: 'portal' | 'porteria' | 'administracion'
  /** Parcelas a nombre de las cuales se puede comprar */
  parcelas: ParcelaVenta[]
  onVendida?: (compra: CompraRifa) => void
  /** Barra de confirmación fija al pie (móvil) o en línea (consola admin) */
  barraFija?: boolean
}

const MEDIOS: { valor: MedioPago; icono: typeof Banknote; ayuda: string }[] = [
  { valor: 'efectivo', icono: Banknote, ayuda: 'Pagado ahora' },
  { valor: 'transferencia', icono: Landmark, ayuda: 'A la cuenta de la comunidad' },
  { valor: 'gasto_comun', icono: Receipt, ayuda: 'Se carga en el gasto común' },
]

const errorMsg = (err: unknown) => {
  const detail = (err as AxiosError<{ detail: unknown }>)?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d: { msg?: string }) => d.msg).join('. ')
  return 'Error desconocido'
}

export function CompraPanel({ rifa, modo, parcelas, onVendida, barraFija = false }: Props) {
  const qc = useQueryClient()
  const esStaff = modo !== 'portal'
  // Las que acepta la rifa; el efectivo, además, solo en portería o administración
  const medios = MEDIOS.filter((m) => rifa.medios_pago.includes(m.valor) && (esStaff || m.valor !== 'efectivo'))
  const medioInicial: MedioPago = medios[0]?.valor ?? 'transferencia'

  const [parcelaId, setParcelaId] = useState<number | null>(parcelas.length === 1 ? parcelas[0].id : null)
  const [seleccion, setSeleccion] = useState<Set<number>>(new Set())
  const [medioPago, setMedioPago] = useState<MedioPago>(medioInicial)
  const [comprador, setComprador] = useState('')
  const [telefono, setTelefono] = useState('')
  const [voucher, setVoucher] = useState<Blob | null>(null)
  const [confirmando, setConfirmando] = useState(false)
  const [error, setError] = useState('')

  const parcela = parcelas.find((p) => p.id === parcelaId) ?? null
  const vendidos = useMemo(() => new Set(rifa.numeros_vendidos), [rifa.numeros_vendidos])
  const mios = useMemo(() => new Set(rifa.mis_numeros), [rifa.mis_numeros])

  // Teléfonos registrados de los residentes de la parcela, para proponerlos
  const { data: sugeridos = [] } = useQuery({
    queryKey: ['rifa-telefonos', rifa.id, parcelaId],
    queryFn: () => rifasApi.telefonos(rifa.id, parcelaId!),
    enabled: esStaff && parcelaId != null,
  })

  // Al elegir parcela en el mesón: se propone el propietario como comprador y el primer teléfono
  useEffect(() => {
    if (!esStaff) return
    setComprador(parcela?.propietario_nombre ?? '')
    setTelefono('')
  }, [parcelaId]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (esStaff && sugeridos.length > 0) setTelefono((t) => t || sugeridos[0].telefono)
  }, [sugeridos, esStaff])

  // Si la grilla se refresca y alguien tomó un número elegido, se quita de la selección
  useEffect(() => {
    setSeleccion((prev) => {
      const libres = [...prev].filter((n) => !vendidos.has(n))
      return libres.length === prev.size ? prev : new Set(libres)
    })
  }, [vendidos])

  const toggle = (n: number) => {
    setSeleccion((prev) => {
      const next = new Set(prev)
      if (next.has(n)) next.delete(n)
      else next.add(n)
      return next
    })
  }

  const elegidos = [...seleccion].sort((a, b) => a - b)
  const total = elegidos.length * rifa.precio_numero
  const telefonoNormalizado = normalizarTelefono(telefono)
  const voucherObligatorio = modo === 'porteria' && medioPago === 'transferencia'

  const faltante = !parcelaId
    ? 'Elige la parcela'
    : telefonoNormalizado === undefined
      ? 'Revisa el teléfono'
      : voucherObligatorio && !voucher
        ? 'Falta la foto del voucher'
        : null

  const reiniciar = () => {
    setSeleccion(new Set())
    setVoucher(null)
    setConfirmando(false)
    if (esStaff) {
      setParcelaId(null)
      setComprador('')
      setTelefono('')
      setMedioPago(medioInicial)
    }
  }

  const comprarMut = useMutation({
    mutationFn: () =>
      rifasApi.comprar(
        rifa.id,
        {
          parcela_id: parcelaId!,
          numeros: elegidos,
          medio_pago: medioPago,
          comprador_nombre: esStaff ? comprador.trim() || null : null,
          telefono: telefonoNormalizado ?? null,
        },
        medioPago === 'transferencia' ? voucher : null,
      ),
    onSuccess: ({ rifa: detalle, compra }) => {
      qc.setQueryData(['rifa', rifa.id], detalle)
      qc.invalidateQueries({ queryKey: ['rifas'] })
      qc.invalidateQueries({ queryKey: ['rifa-caja', rifa.id] })
      setError('')
      reiniciar()
      onVendida?.(compra)
    },
    onError: (err: unknown) => {
      setError(errorMsg(err))
      setConfirmando(false)
      // Un 409 significa que alguien tomó un número: se refresca la grilla
      if ((err as AxiosError)?.response?.status === 409) qc.invalidateQueries({ queryKey: ['rifa', rifa.id] })
    },
  })

  return (
    <div className="space-y-5">
      {/* 1. Parcela */}
      {esStaff ? (
        <section className="space-y-2">
          <p className="text-sm font-semibold text-slate-300">1. Parcela</p>
          <ParcelaBuscador parcelas={parcelas} value={parcelaId} onChange={(p) => setParcelaId(p?.id ?? null)} />
        </section>
      ) : parcelas.length > 1 ? (
        <div className="flex flex-col gap-1">
          <label htmlFor="parcela-compra" className="text-sm font-medium text-slate-300">¿A nombre de qué parcela?</label>
          <select
            id="parcela-compra"
            value={parcelaId ?? ''}
            onChange={(e) => setParcelaId(e.target.value ? Number(e.target.value) : null)}
            className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-sm text-slate-100 focus:border-primary-500 focus:outline-none"
          >
            <option value="">— Elige una parcela —</option>
            {parcelas.map((p) => (
              <option key={p.id} value={p.id}>
                Parcela {p.numero_parcela}{p.propietario_nombre ? ` — ${p.propietario_nombre}` : ''}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      {error && <Alert variant="error">{error}</Alert>}

      {/* 2. Números */}
      <section className="space-y-2">
        {esStaff && <p className="text-sm font-semibold text-slate-300">2. Números</p>}
        <NumeroGrid
          cantidad={rifa.cantidad_numeros}
          vendidos={vendidos}
          mios={mios}
          seleccion={seleccion}
          onToggle={toggle}
          disabled={rifa.estado !== 'abierta'}
        />
      </section>

      {/* 3. Comprador, pago y comprobante */}
      <section className="space-y-4">
        {esStaff && <p className="text-sm font-semibold text-slate-300">3. Comprador y pago</p>}

        {esStaff && (
          <div className="flex flex-col gap-1">
            <label htmlFor="comprador" className="text-sm font-medium text-slate-300">Nombre del comprador</label>
            <input
              id="comprador"
              value={comprador}
              onChange={(e) => setComprador(e.target.value)}
              placeholder="Puede ser alguien de fuera de la comunidad"
              className="rounded-xl border border-slate-600 bg-slate-800 px-3 py-3 text-base text-slate-100 placeholder-slate-500 focus:border-primary-500 focus:outline-none"
            />
          </div>
        )}

        <div className="space-y-1">
          <p className="text-sm font-medium text-slate-300">Forma de pago</p>
          <div className={`grid gap-2 ${medios.length === 3 ? 'grid-cols-3' : medios.length === 2 ? 'grid-cols-2' : 'grid-cols-1'}`} role="radiogroup">
            {medios.map(({ valor, icono: Icono, ayuda }) => (
              <button
                key={valor}
                type="button"
                role="radio"
                aria-checked={medioPago === valor}
                onClick={() => setMedioPago(valor)}
                className={`flex min-h-[64px] flex-col items-center justify-center gap-0.5 rounded-xl border-2 px-2 py-2 text-center transition-colors ${
                  medioPago === valor
                    ? 'border-primary-500 bg-primary-600/15 text-slate-100'
                    : 'border-slate-700 bg-slate-800 text-slate-300 hover:border-slate-500'
                }`}
              >
                <Icono className="h-5 w-5" />
                <span className="text-sm font-semibold">{MEDIO_PAGO_TEXTO[valor]}</span>
                <span className="text-[11px] leading-tight text-slate-400">{ayuda}</span>
              </button>
            ))}
          </div>
        </div>

        {medioPago === 'transferencia' && (
          <div className="space-y-2">
            {rifa.datos_transferencia && (
              <div className="rounded-xl bg-slate-700/40 p-3 text-sm">
                <p className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">Datos para transferir</p>
                <p className="whitespace-pre-line text-slate-200">{rifa.datos_transferencia}</p>
              </div>
            )}
            <VoucherInput value={voucher} onChange={setVoucher} obligatorio={voucherObligatorio} />
            {!esStaff && (
              <p className="text-xs text-slate-400">La compra queda pendiente hasta que la administración confirme la transferencia.</p>
            )}
          </div>
        )}

        {esStaff && (
          <div className="space-y-2">
            <label htmlFor="telefono" className="text-sm font-medium text-slate-300">Teléfono para el comprobante (WhatsApp)</label>
            {sugeridos.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {sugeridos.map((s) => (
                  <button
                    key={s.telefono}
                    type="button"
                    onClick={() => setTelefono(s.telefono)}
                    className={`rounded-full px-3 py-1.5 text-sm transition-colors ${
                      telefonoNormalizado === s.telefono ? 'bg-primary-600 text-white' : 'bg-slate-700 text-slate-200 hover:bg-slate-600'
                    }`}
                  >
                    {s.nombre.split(' ')[0]} · {formatearTelefono(s.telefono)}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => setTelefono('')}
                  className={`rounded-full px-3 py-1.5 text-sm ${!telefono ? 'bg-slate-500 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
                >
                  Sin teléfono
                </button>
              </div>
            )}
            <input
              id="telefono"
              type="tel"
              inputMode="tel"
              value={telefono}
              onChange={(e) => setTelefono(e.target.value)}
              placeholder="Ej: 9 1234 5678 (opcional)"
              className={`w-full rounded-xl border bg-slate-800 px-3 py-3 text-base text-slate-100 placeholder-slate-500 focus:outline-none ${
                telefonoNormalizado === undefined ? 'border-red-500' : 'border-slate-600 focus:border-primary-500'
              }`}
            />
            {telefonoNormalizado === undefined && <p className="text-xs text-red-400">Teléfono inválido: debe tener 8 o 9 dígitos, o empezar con 56.</p>}
          </div>
        )}
      </section>

      {elegidos.length > 0 && (
        <div
          className={
            barraFija
              ? 'fixed inset-x-0 bottom-0 z-40 border-t border-slate-700 bg-slate-900/95 px-4 py-3 backdrop-blur'
              : 'rounded-xl border border-slate-700 bg-slate-900 px-4 py-3'
          }
        >
          <div className="mx-auto flex max-w-2xl items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-100">
                {elegidos.length} {elegidos.length === 1 ? 'número' : 'números'} · {clp(total)}
              </p>
              <p className="truncate text-xs text-slate-400">{faltante ?? elegidos.join(', ')}</p>
            </div>
            <Button onClick={() => { setError(''); setConfirmando(true) }} disabled={!!faltante}>
              <Ticket className="h-4 w-4" /> Confirmar
            </Button>
          </div>
        </div>
      )}

      <Modal open={confirmando} onClose={() => setConfirmando(false)} title="Confirmar compra" size="sm">
        <div className="space-y-4">
          <div className="space-y-2 rounded-xl bg-slate-700/40 p-4 text-sm">
            <div className="flex justify-between gap-3">
              <span className="text-slate-400">Parcela</span>
              <span className="text-slate-200">{parcela?.numero_parcela}</span>
            </div>
            {esStaff && comprador.trim() && (
              <div className="flex justify-between gap-3">
                <span className="text-slate-400">Comprador</span>
                <span className="text-right text-slate-200">{comprador.trim()}</span>
              </div>
            )}
            <div className="flex justify-between gap-3">
              <span className="text-slate-400">Números</span>
              <span className="text-right font-mono text-slate-200">{elegidos.join(', ')}</span>
            </div>
            <div className="flex justify-between gap-3">
              <span className="text-slate-400">Pago</span>
              <span className="text-slate-200">{MEDIO_PAGO_TEXTO[medioPago]}</span>
            </div>
            <div className="flex justify-between gap-3">
              <span className="text-slate-400">{elegidos.length} × {clp(rifa.precio_numero)}</span>
              <span className="font-mono text-lg font-bold text-primary-400">{clp(total)}</span>
            </div>
          </div>
          <p className="text-xs text-slate-400">
            {medioPago === 'efectivo' && 'Recibe el dinero antes de confirmar.'}
            {medioPago === 'transferencia' && 'Queda pendiente hasta que la administración confirme la transferencia.'}
            {medioPago === 'gasto_comun' && 'El monto se cargará en el gasto común de la parcela cuando se cierre la rifa.'}
            {!esStaff && ' Puedes anular la compra mientras la rifa siga abierta y no esté pagada.'}
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setConfirmando(false)} disabled={comprarMut.isPending}>
              Cancelar
            </Button>
            <Button loading={comprarMut.isPending} onClick={() => comprarMut.mutate()}>
              Comprar
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
