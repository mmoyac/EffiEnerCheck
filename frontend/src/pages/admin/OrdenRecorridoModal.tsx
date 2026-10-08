import { useEffect, useState } from 'react'
import type { AxiosError } from 'axios'
import { ArrowDown, ArrowUp, GripVertical } from 'lucide-react'
import { parcelasApi } from '../../api/parcelas'
import { Modal } from '../../components/ui/Modal'
import { Button } from '../../components/ui/Button'
import { Alert } from '../../components/ui/Alert'
import { ordenarRecorrido } from '../../utils/recorrido'
import type { Parcela } from '../../types'

interface Props {
  open: boolean
  condominioId: number | null
  parcelas: Parcela[]          // las del condominio
  onClose: () => void
  onGuardado: () => void
}

/**
 * Orden del recorrido del lector (cambio orden-recorrido). Arrastrar en escritorio, flechas en el celular.
 * Guardar fija la posición de todas las parcelas activas; «Quitar recorrido» vuelve al orden numérico.
 */
export function OrdenRecorridoModal({ open, condominioId, parcelas, onClose, onGuardado }: Props) {
  const [lista, setLista] = useState<Parcela[]>([])
  const [arrastrada, setArrastrada] = useState<number | null>(null)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (open) { setLista(ordenarRecorrido(parcelas.filter((p) => p.activa))); setError('') }
  }, [open, parcelas])

  const hayRecorrido = parcelas.some((p) => p.orden_recorrido != null)

  const mover = (desde: number, hasta: number) => {
    if (hasta < 0 || hasta >= lista.length || desde === hasta) return
    setLista((l) => {
      const copia = [...l]
      const [p] = copia.splice(desde, 1)
      copia.splice(hasta, 0, p)
      return copia
    })
  }

  const guardar = async (ids: number[]) => {
    setGuardando(true)
    setError('')
    try {
      await parcelasApi.guardarOrdenRecorrido(ids, condominioId ?? undefined)
      onGuardado()
      onClose()
    } catch (err) {
      setError((err as AxiosError<{ detail: string }>)?.response?.data?.detail ?? 'No se pudo guardar el recorrido')
    } finally {
      setGuardando(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Orden del recorrido del lector" size="lg">
      <div className="space-y-4">
        <p className="text-sm text-slate-300">
          Ordena las parcelas como las camina el lector. La app de lecturas las mostrará en este orden (también sin señal),
          después de que el lector presione <strong>Preparar recorrido</strong>.
          {!hayRecorrido && ' Hoy no hay recorrido: la app usa el orden numérico.'}
        </p>
        {error && <Alert variant="error">{error}</Alert>}

        <ol className="max-h-[55vh] divide-y divide-slate-700/60 overflow-y-auto rounded-lg border border-slate-700">
          {lista.map((p, i) => (
            <li key={p.id} draggable
                onDragStart={() => setArrastrada(i)}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => { if (arrastrada != null) mover(arrastrada, i); setArrastrada(null) }}
                className={`flex items-center gap-3 px-3 py-2 text-sm ${arrastrada === i ? 'bg-slate-700/60' : 'bg-slate-800/40'}`}>
              <GripVertical className="h-4 w-4 cursor-grab text-slate-500" />
              <span className="w-7 text-right font-mono text-xs text-slate-500">{i + 1}</span>
              <span className="flex-1 font-medium text-slate-100">
                Parcela {p.numero_parcela}
                {p.propietario_nombre && <span className="ml-2 text-xs font-normal text-slate-500">{p.propietario_nombre}</span>}
                {hayRecorrido && p.orden_recorrido == null && <span className="ml-2 text-xs font-normal text-yellow-300">sin ubicar</span>}
              </span>
              <button onClick={() => mover(i, i - 1)} disabled={i === 0} title="Subir"
                      className="rounded p-1 text-slate-400 hover:bg-slate-700 disabled:opacity-30"><ArrowUp className="h-4 w-4" /></button>
              <button onClick={() => mover(i, i + 1)} disabled={i === lista.length - 1} title="Bajar"
                      className="rounded p-1 text-slate-400 hover:bg-slate-700 disabled:opacity-30"><ArrowDown className="h-4 w-4" /></button>
            </li>
          ))}
        </ol>

        <div className="flex flex-wrap justify-between gap-2 pt-2">
          <Button variant="ghost" disabled={!hayRecorrido || guardando}
                  onClick={() => { if (window.confirm('¿Quitar el recorrido? La app del lector volverá al orden numérico.')) guardar([]) }}>
            Quitar recorrido
          </Button>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={onClose}>Cancelar</Button>
            <Button loading={guardando} disabled={!lista.length} onClick={() => guardar(lista.map((p) => p.id))}>
              Guardar recorrido
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  )
}
