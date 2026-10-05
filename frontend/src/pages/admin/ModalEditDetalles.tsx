import { useState, useEffect } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { Modal } from '../../components/ui/Modal'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Alert } from '../../components/ui/Alert'

type ModalEditDetallesProps = {
  boleta: any
  open: boolean
  onClose: () => void
  onSave: (data: any) => void
  isPending: boolean
  error: string
}

export default function ModalEditDetalles({ boleta, open, onClose, onSave, isPending, error }: ModalEditDetallesProps) {
  const [form, setForm] = useState({
    total_kwh_compania: '',
    monto_neto_electricidad_consumida: '',
    monto_total_emision: '',
    monto_saldo_anterior: '',
    items_detalle: [] as any[]
  })

  useEffect(() => {
    if (open && boleta) {
      setForm({
        total_kwh_compania: boleta.total_kwh_compania ?? '',
        monto_neto_electricidad_consumida: boleta.monto_neto_electricidad_consumida ?? '',
        monto_total_emision: boleta.monto_total_emision ?? '',
        monto_saldo_anterior: boleta.monto_saldo_anterior ?? '',
        items_detalle: (boleta.items_detalle || []).map((i: any) => ({ ...i }))
      })
    }
  }, [open, boleta])

  const handleSave = () => {
    onSave({
      total_kwh_compania: form.total_kwh_compania ? Number(form.total_kwh_compania) : undefined,
      monto_neto_electricidad_consumida: form.monto_neto_electricidad_consumida ? Number(form.monto_neto_electricidad_consumida) : undefined,
      monto_total_emision: form.monto_total_emision ? Number(form.monto_total_emision) : undefined,
      monto_saldo_anterior: form.monto_saldo_anterior ? Number(form.monto_saldo_anterior) : undefined,
      items_detalle: form.items_detalle.map(i => ({
        descripcion: i.descripcion,
        monto_neto_clp: Number(i.monto_neto_clp),
        tipo_calculo: i.tipo_calculo
      }))
    })
  }

  const addItem = () => {
    setForm(f => ({
      ...f,
      items_detalle: [...f.items_detalle, { descripcion: '', monto_neto_clp: 0, tipo_calculo: 'fijo' }]
    }))
  }

  const removeItem = (idx: number) => {
    setForm(f => ({
      ...f,
      items_detalle: f.items_detalle.filter((_, i) => i !== idx)
    }))
  }

  const updateItem = (idx: number, field: string, value: string | number) => {
    setForm(f => {
      const newItems = [...f.items_detalle]
      newItems[idx] = { ...newItems[idx], [field]: value }
      return { ...f, items_detalle: newItems }
    })
  }

  return (
    <Modal open={open} onClose={onClose} title="Editar Totales e Ítems" size="xl">
      <div className="space-y-6">
        {error && <Alert variant="error">{error}</Alert>}
        
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Input label="kWh compañía" type="number" value={form.total_kwh_compania}
            onChange={(e) => setForm((f) => ({ ...f, total_kwh_compania: e.target.value }))} />
          <Input label="Monto neto" type="number" value={form.monto_neto_electricidad_consumida}
            onChange={(e) => setForm((f) => ({ ...f, monto_neto_electricidad_consumida: e.target.value }))} />
          <Input label="Total emisión" type="number" value={form.monto_total_emision}
            onChange={(e) => setForm((f) => ({ ...f, monto_total_emision: e.target.value }))} />
          <Input label="Saldo anterior" type="number" value={form.monto_saldo_anterior}
            onChange={(e) => setForm((f) => ({ ...f, monto_saldo_anterior: e.target.value }))} />
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <label className="text-sm font-medium text-slate-300">Ítems de Detalle</label>
            <Button size="sm" variant="secondary" onClick={addItem}>
              <Plus className="h-4 w-4" /> Agregar Ítem
            </Button>
          </div>
          <p className="mb-2 text-xs text-slate-500">
            Fijo y variable entran al reparto; informativo queda fuera.
            Usa monto <span className="text-sky-400">negativo</span> para descuentos, notas de crédito y abonos.
          </p>
          
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {form.items_detalle.map((item, idx) => {
              const esPendiente = item.tipo_calculo === 'pendiente'
              const esAbono = Number(item.monto_neto_clp) < 0
              return (
                <div
                  key={idx}
                  className={`flex flex-col sm:flex-row sm:items-center gap-2 rounded p-2 ${
                    esPendiente ? 'bg-violet-500/10 ring-1 ring-violet-500/40' : 'bg-slate-800'
                  }`}
                >
                  <input
                    type="text"
                    placeholder="Descripción"
                    className="w-full rounded border border-slate-600 bg-slate-700 px-2 py-1.5 text-sm text-slate-100 focus:border-primary-500 focus:outline-none"
                    value={item.descripcion}
                    onChange={(e) => updateItem(idx, 'descripcion', e.target.value)}
                  />
                  <select
                    className={`w-full sm:w-44 rounded border bg-slate-700 px-2 py-1.5 text-sm focus:outline-none ${
                      esPendiente
                        ? 'border-violet-500 text-violet-300 focus:border-violet-400'
                        : 'border-slate-600 text-slate-100 focus:border-primary-500'
                    }`}
                    value={item.tipo_calculo}
                    onChange={(e) => updateItem(idx, 'tipo_calculo', e.target.value)}
                  >
                    <option value="fijo">Fijo — parejo</option>
                    <option value="variable">Variable — por consumo</option>
                    <option value="informativo">Informativo — no se reparte</option>
                    <option value="pendiente">Pendiente — sin clasificar</option>
                  </select>
                  <input
                    type="number"
                    placeholder="Monto ($)"
                    title="Usa monto negativo para descuentos, notas de crédito y abonos"
                    className={`w-full sm:w-32 rounded border bg-slate-700 px-2 py-1.5 text-sm tabular-nums focus:outline-none ${
                      esAbono
                        ? 'border-sky-500/60 text-sky-300 focus:border-sky-400'
                        : 'border-slate-600 text-slate-100 focus:border-primary-500'
                    }`}
                    value={item.monto_neto_clp}
                    onChange={(e) => updateItem(idx, 'monto_neto_clp', e.target.value)}
                  />
                  <button
                    type="button"
                    aria-label="Eliminar ítem"
                    className="rounded p-1.5 text-red-400 hover:bg-red-500/20"
                    onClick={() => removeItem(idx)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              )
            })}
            {form.items_detalle.length === 0 && (
              <p className="text-sm text-slate-500 text-center py-4">No hay ítems registrados.</p>
            )}
          </div>
        </div>

        <div className="flex justify-end gap-2 border-t border-slate-700 pt-4">
          <Button variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button onClick={handleSave} loading={isPending}>Guardar Cambios</Button>
        </div>
      </div>
    </Modal>
  )
}
