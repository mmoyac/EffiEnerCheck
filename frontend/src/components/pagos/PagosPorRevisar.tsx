import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { AlertTriangle } from 'lucide-react'
import { pagosApi } from '../../api/pagos'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Modal } from '../ui/Modal'
import { Spinner } from '../ui/Spinner'
import { clp, fechaHora } from '../../utils/format'
import type { IntencionRevision } from '../../types'

function errorMsg(err: unknown): string {
  const detail = (err as AxiosError<{ detail: unknown }>)?.response?.data?.detail
  return typeof detail === 'string' ? detail : 'Error desconocido'
}

/**
 * Pagos en línea aprobados que no se pudieron aplicar solos. Lo usan /pasarelas (administración) y
 * /rifas: al comunero que administra rifas la API le entrega solo los de rifas (cambio admin-rifas).
 */
export function PagosPorRevisar() {
  const qc = useQueryClient()
  const { data: pagos = [], isLoading } = useQuery({ queryKey: ['pagos-revision'], queryFn: pagosApi.revision })
  const [resolviendo, setResolviendo] = useState<IntencionRevision | null>(null)
  const [nota, setNota] = useState('')
  const [error, setError] = useState('')
  const mut = useMutation({
    mutationFn: () => pagosApi.resolver(resolviendo!.id, nota.trim()),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['pagos-revision'] }); setResolviendo(null) },
    onError: (err) => setError(errorMsg(err)),
  })

  return (
    <section className="space-y-3">
      <div>
        <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-100"><AlertTriangle className="h-5 w-5 text-yellow-400" /> Pagos por revisar</h2>
        <p className="text-sm text-slate-500">Pagos aprobados por la pasarela que no se pudieron aplicar solos (por ejemplo, números que ya se vendieron).</p>
      </div>
      {isLoading ? (
        <div className="flex h-20 items-center justify-center"><Spinner className="text-primary-500" /></div>
      ) : pagos.length === 0 ? (
        <Alert variant="info">No hay pagos por revisar.</Alert>
      ) : (
        pagos.map((p) => (
          <Card key={p.id}>
            <div className="space-y-2">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate font-semibold text-slate-100">{p.usuario_nombre}</p>
                  <p className="truncate text-xs text-slate-400">{p.descripcion}</p>
                </div>
                <span className="shrink-0 font-mono font-bold text-slate-100">{clp(p.monto_confirmado ?? p.total)}</span>
              </div>
              <p className="text-sm text-yellow-300">{p.motivo}</p>
              <p className="text-xs text-slate-500">
                {p.pasarela_nombre}{p.numero_operacion ? ` · operación ${p.numero_operacion}` : ''} · {fechaHora(p.confirmado_at ?? p.created_at)}
              </p>
              <div className="flex justify-end">
                <Button size="sm" variant="secondary" onClick={() => { setResolviendo(p); setNota(''); setError('') }}>Marcar resuelto</Button>
              </div>
            </div>
          </Card>
        ))
      )}
      <Modal open={!!resolviendo} onClose={() => setResolviendo(null)} title="Marcar resuelto" size="md">
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); setError(''); mut.mutate() }}>
          <p className="text-sm text-slate-300">
            Anota qué se hizo con este pago (por ejemplo, la devolución en el panel de la pasarela o la venta de otros números).
          </p>
          <textarea value={nota} onChange={(e) => setNota(e.target.value)} rows={3} required minLength={3}
            className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:border-primary-500 focus:outline-none" />
          {error && <Alert variant="error">{error}</Alert>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setResolviendo(null)}>Cancelar</Button>
            <Button type="submit" loading={mut.isPending} disabled={nota.trim().length < 3}>Guardar</Button>
          </div>
        </form>
      </Modal>
    </section>
  )
}
