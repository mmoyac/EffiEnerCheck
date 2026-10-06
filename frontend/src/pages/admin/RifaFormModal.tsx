import { useEffect, useState } from 'react'
import { ArrowDown, ArrowUp, Plus, X } from 'lucide-react'
import { Modal } from '../../components/ui/Modal'
import { Input } from '../../components/ui/Input'
import { Button } from '../../components/ui/Button'
import { Alert } from '../../components/ui/Alert'
import type { MedioPago, Rifa, RifaCreate } from '../../types'
import { MEDIO_PAGO_TEXTO } from '../../utils/comprobante'

const TODOS_LOS_MEDIOS: MedioPago[] = ['efectivo', 'transferencia', 'gasto_comun']

interface Props {
  open: boolean
  onClose: () => void
  onSubmit: (body: RifaCreate) => void
  loading: boolean
  error: string
  /** Rifa a editar; si no viene, el formulario crea una nueva */
  rifa?: Rifa
  /** Solo super_admin: elige el condominio al crear */
  condominios?: { id: number; nombre: string }[]
  /** Con números vendidos el precio queda bloqueado */
  precioBloqueado?: boolean
}

const textareaClase =
  'rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500'

export function RifaFormModal({ open, onClose, onSubmit, loading, error, rifa, condominios, precioBloqueado = false }: Props) {
  const [nombre, setNombre] = useState('')
  const [beneficiario, setBeneficiario] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [premios, setPremios] = useState<string[]>([''])
  const [datosTransferencia, setDatosTransferencia] = useState('')
  const [precio, setPrecio] = useState('')
  const [cantidad, setCantidad] = useState('')
  const [condominioId, setCondominioId] = useState('')
  const [medios, setMedios] = useState<MedioPago[]>(TODOS_LOS_MEDIOS)

  useEffect(() => {
    if (!open) return
    setNombre(rifa?.nombre ?? '')
    setBeneficiario(rifa?.beneficiario ?? '')
    setDescripcion(rifa?.descripcion ?? '')
    setPremios(rifa?.premios.length ? rifa.premios : [''])
    setDatosTransferencia(rifa?.datos_transferencia ?? '')
    setPrecio(rifa ? String(rifa.precio_numero) : '')
    setCantidad(rifa ? String(rifa.cantidad_numeros) : '')
    setCondominioId('')
    setMedios(rifa?.medios_pago ?? TODOS_LOS_MEDIOS)
  }, [open, rifa])

  const precioNum = Number(precio)
  const cantidadNum = Number(cantidad)
  const premiosLimpios = premios.map((p) => p.trim()).filter(Boolean)
  const valido =
    nombre.trim() && beneficiario.trim() && premiosLimpios.length > 0 &&
    Number.isInteger(precioNum) && precioNum > 0 &&
    Number.isInteger(cantidadNum) && cantidadNum > 0 &&
    (!condominios || condominioId) && medios.length > 0

  const setPremio = (i: number, v: string) => setPremios((ps) => ps.map((p, j) => (j === i ? v : p)))
  const moverPremio = (i: number, d: -1 | 1) =>
    setPremios((ps) => {
      const next = [...ps]
      ;[next[i], next[i + d]] = [next[i + d], next[i]]
      return next
    })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!valido) return
    onSubmit({
      ...(condominios ? { condominio_id: Number(condominioId) } : {}),
      nombre: nombre.trim(),
      beneficiario: beneficiario.trim(),
      descripcion: descripcion.trim() || null,
      premios: premiosLimpios,
      datos_transferencia: datosTransferencia.trim() || null,
      ...(precioBloqueado ? {} : { precio_numero: precioNum }),
      cantidad_numeros: cantidadNum,
      medios_pago: TODOS_LOS_MEDIOS.filter((m) => medios.includes(m)),
    } as RifaCreate)
  }

  return (
    <Modal open={open} onClose={onClose} title={rifa ? 'Editar rifa' : 'Nueva rifa'} size="lg">
      <form onSubmit={submit} className="max-h-[75vh] space-y-4 overflow-y-auto pr-1">
        {condominios && (
          <div className="flex flex-col gap-1">
            <label htmlFor="rifa-condominio" className="text-sm font-medium text-slate-300">Condominio</label>
            <select
              id="rifa-condominio"
              value={condominioId}
              onChange={(e) => setCondominioId(e.target.value)}
              className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:border-primary-500 focus:outline-none"
            >
              <option value="">— Elige un condominio —</option>
              {condominios.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
            </select>
          </div>
        )}
        <Input label="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Ej: Rifa solidaria para Juan" required />
        <Input label="Beneficiario" value={beneficiario} onChange={(e) => setBeneficiario(e.target.value)} placeholder="Ej: Juan Pérez, parcela 14" required />
        <div className="flex flex-col gap-1">
          <label htmlFor="rifa-descripcion" className="text-sm font-medium text-slate-300">Descripción (opcional)</label>
          <textarea id="rifa-descripcion" value={descripcion} onChange={(e) => setDescripcion(e.target.value)} rows={2}
            placeholder="Para qué se reúne el dinero, fecha y lugar del sorteo…" className={textareaClase} />
        </div>

        <div className="space-y-2">
          <p className="text-sm font-medium text-slate-300">Premios <span className="text-slate-500">(en orden: el primero es el 1.º premio)</span></p>
          {premios.map((p, i) => (
            <div key={i} className="flex items-center gap-1.5">
              <span className="w-6 shrink-0 text-right font-mono text-sm text-slate-500">{i + 1}.</span>
              <input
                value={p}
                onChange={(e) => setPremio(i, e.target.value)}
                placeholder={i === 0 ? 'Ej: Notebook e impresora reacondicionadas' : 'Otro premio'}
                aria-label={`Premio ${i + 1}`}
                className="min-w-0 flex-1 rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-primary-500 focus:outline-none"
              />
              <button type="button" disabled={i === 0} onClick={() => moverPremio(i, -1)} className="rounded p-1.5 text-slate-400 hover:bg-slate-700 disabled:opacity-30" aria-label="Subir"><ArrowUp className="h-4 w-4" /></button>
              <button type="button" disabled={i === premios.length - 1} onClick={() => moverPremio(i, 1)} className="rounded p-1.5 text-slate-400 hover:bg-slate-700 disabled:opacity-30" aria-label="Bajar"><ArrowDown className="h-4 w-4" /></button>
              <button type="button" disabled={premios.length === 1} onClick={() => setPremios((ps) => ps.filter((_, j) => j !== i))} className="rounded p-1.5 text-slate-400 hover:bg-slate-700 disabled:opacity-30" aria-label="Quitar"><X className="h-4 w-4" /></button>
            </div>
          ))}
          <Button type="button" variant="ghost" size="sm" onClick={() => setPremios((ps) => [...ps, ''])}>
            <Plus className="h-4 w-4" /> Agregar premio
          </Button>
        </div>

        <fieldset className="space-y-1">
          <legend className="text-sm font-medium text-slate-300">Formas de pago aceptadas</legend>
          <div className="flex flex-wrap gap-2">
            {TODOS_LOS_MEDIOS.map((m) => (
              <label key={m} className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm ${medios.includes(m) ? 'border-primary-500 bg-primary-600/10 text-slate-100' : 'border-slate-600 text-slate-400'}`}>
                <input
                  type="checkbox"
                  className="accent-primary-500"
                  checked={medios.includes(m)}
                  onChange={(e) => setMedios((ms) => (e.target.checked ? [...ms, m] : ms.filter((x) => x !== m)))}
                />
                {MEDIO_PAGO_TEXTO[m]}
              </label>
            ))}
          </div>
          {medios.length === 0
            ? <p className="text-xs text-red-400">Elige al menos una forma de pago.</p>
            : <p className="text-xs text-slate-500">Las compras ya hechas conservan su forma de pago; solo las nuevas usan esta lista.</p>}
        </fieldset>

        <div className="flex flex-col gap-1">
          <label htmlFor="rifa-transferencia" className="text-sm font-medium text-slate-300">Datos para transferir (opcional)</label>
          <textarea id="rifa-transferencia" value={datosTransferencia} onChange={(e) => setDatosTransferencia(e.target.value)} rows={3}
            placeholder={'Banco, tipo y número de cuenta\nTitular y RUT\nCorreo para el comprobante'} className={textareaClase} />
          <p className="text-xs text-slate-500">Se muestran al elegir transferencia y van en el comprobante.</p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Precio por número (CLP)"
            type="number" min={1} step={1}
            value={precio}
            onChange={(e) => setPrecio(e.target.value)}
            disabled={precioBloqueado}
            hint={precioBloqueado ? 'No se puede cambiar: ya hay números vendidos' : undefined}
            required
          />
          <Input
            label="Cantidad de números"
            type="number" min={1} step={1}
            value={cantidad}
            onChange={(e) => setCantidad(e.target.value)}
            hint="Del 1 al número indicado"
            required
          />
        </div>
        {error && <Alert variant="error">{error}</Alert>}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose} disabled={loading}>Cancelar</Button>
          <Button type="submit" loading={loading} disabled={!valido}>{rifa ? 'Guardar' : 'Crear rifa'}</Button>
        </div>
      </form>
    </Modal>
  )
}
