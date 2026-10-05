import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { CheckCircle2, Image as ImageIcon, Paperclip } from 'lucide-react'
import { rifasApi } from '../../api/rifas'
import { Alert } from '../ui/Alert'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { Modal } from '../ui/Modal'
import { VoucherInput } from './VoucherInput'
import { clp, fechaHora } from '../../utils/format'
import { MEDIO_PAGO_TEXTO } from '../../utils/comprobante'
import type { CompraRifa } from '../../types'

interface Props {
  rifaId: number
  compras: CompraRifa[]
  /** En la consola admin y en portería se muestra la parcela de cada compra */
  mostrarParcela?: boolean
  /** Solo administración: confirmar transferencias */
  puedeConfirmar?: boolean
  vacio?: string
}

const errorMsg = (err: unknown) =>
  (err as AxiosError<{ detail: string }>)?.response?.data?.detail ?? 'Error desconocido'

function quien(c: CompraRifa): string {
  if (c.canal === 'portal') return c.usuario_nombre
  const origen = c.canal === 'porteria' ? 'Portería' : `Administración (${c.usuario_nombre})`
  return c.comprador_nombre ? `${c.comprador_nombre} · ${origen}` : origen
}

function EstadoPago({ c }: { c: CompraRifa }) {
  if (c.anulada) return <Badge color="slate">Anulada</Badge>
  if (c.medio_pago === 'gasto_comun') return <Badge color="purple">Gasto común</Badge>
  if (c.pagada) return <Badge color="green" dot>{MEDIO_PAGO_TEXTO[c.medio_pago]} · pagada</Badge>
  return <Badge color="yellow" dot>Transferencia por confirmar</Badge>
}

export function ComprasLista({ rifaId, compras, mostrarParcela = false, puedeConfirmar = false, vacio = 'Sin compras todavía.' }: Props) {
  const qc = useQueryClient()
  const [error, setError] = useState('')
  const [anulando, setAnulando] = useState<number | null>(null)
  const [voucherVisto, setVoucherVisto] = useState<{ compra: CompraRifa; url: string } | null>(null)
  const [adjuntando, setAdjuntando] = useState<CompraRifa | null>(null)
  const [nuevoVoucher, setNuevoVoucher] = useState<Blob | null>(null)

  const refrescar = () => {
    qc.invalidateQueries({ queryKey: ['rifa', rifaId] })
    qc.invalidateQueries({ queryKey: ['rifas'] })
    qc.invalidateQueries({ queryKey: ['rifa-caja', rifaId] })
    qc.invalidateQueries({ queryKey: ['rifa-compras', rifaId] })
  }

  const anularMut = useMutation({
    mutationFn: (compraId: number) => rifasApi.anularCompra(rifaId, compraId),
    onSuccess: () => { refrescar(); setAnulando(null); setError('') },
    onError: (err) => { setError(errorMsg(err)); setAnulando(null) },
  })
  const confirmarMut = useMutation({
    mutationFn: (compraId: number) => rifasApi.confirmarPago(rifaId, compraId),
    onSuccess: () => { refrescar(); setVoucherVisto(null); setError('') },
    onError: (err) => setError(errorMsg(err)),
  })
  const adjuntarMut = useMutation({
    mutationFn: ({ compraId, archivo }: { compraId: number; archivo: Blob }) => rifasApi.adjuntarVoucher(rifaId, compraId, archivo),
    onSuccess: () => { refrescar(); setAdjuntando(null); setNuevoVoucher(null); setError('') },
    onError: (err) => setError(errorMsg(err)),
  })

  const verVoucher = async (c: CompraRifa) => {
    setError('')
    try {
      const { url, tipo } = await rifasApi.verVoucher(rifaId, c.id)
      if (tipo === 'application/pdf') window.open(url, '_blank')
      else setVoucherVisto({ compra: c, url })
    } catch (err) {
      setError(errorMsg(err))
    }
  }
  const cerrarVoucher = () => {
    if (voucherVisto) URL.revokeObjectURL(voucherVisto.url)
    setVoucherVisto(null)
  }

  if (compras.length === 0) return <p className="text-sm text-slate-500">{vacio}</p>

  return (
    <div className="space-y-2">
      {error && <Alert variant="error">{error}</Alert>}
      {compras.map((c) => {
        const porConfirmar = puedeConfirmar && !c.anulada && c.medio_pago === 'transferencia' && !c.pagada
        return (
          <div
            key={c.id}
            className={`rounded-xl border p-3 ${c.anulada ? 'border-slate-700/50 bg-slate-800/40' : 'border-slate-700 bg-slate-700/30'}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs text-slate-500">{c.folio}</span>
                  <span className={`font-mono text-sm font-semibold ${c.anulada ? 'text-slate-500 line-through' : 'text-slate-100'}`}>
                    {c.numeros.join(', ')}
                  </span>
                </p>
                <p className="mt-0.5 text-xs text-slate-400">
                  {mostrarParcela && <>Parcela {c.parcela_numero} · </>}
                  {quien(c)} · {fechaHora(c.created_at)}
                </p>
                {c.anulada && (
                  <p className="mt-0.5 text-xs text-slate-500">
                    Anulada{c.anulada_por_nombre ? ` por ${c.anulada_por_nombre}` : ''} · {fechaHora(c.anulada_at)}
                  </p>
                )}
                <div className="mt-1.5"><EstadoPago c={c} /></div>
              </div>
              <span className={`shrink-0 font-mono text-sm ${c.anulada ? 'text-slate-500' : 'text-slate-200'}`}>{clp(c.monto)}</span>
            </div>
            {(c.tiene_voucher || c.puede_adjuntar_voucher || porConfirmar || c.puede_anular) && (
              <div className="mt-2 flex flex-wrap justify-end gap-1">
                {c.tiene_voucher && (
                  <Button size="sm" variant={porConfirmar ? 'secondary' : 'ghost'} onClick={() => verVoucher(c)}>
                    <ImageIcon className="h-4 w-4" /> Voucher
                  </Button>
                )}
                {c.puede_adjuntar_voucher && !c.tiene_voucher && (
                  <Button size="sm" variant="ghost" onClick={() => { setNuevoVoucher(null); setAdjuntando(c) }}>
                    <Paperclip className="h-4 w-4" /> Adjuntar voucher
                  </Button>
                )}
                {porConfirmar && (
                  <Button size="sm" loading={confirmarMut.isPending && confirmarMut.variables === c.id} onClick={() => confirmarMut.mutate(c.id)}>
                    <CheckCircle2 className="h-4 w-4" /> Confirmar pago
                  </Button>
                )}
                {c.puede_anular && (
                  anulando === c.id ? (
                    <>
                      <Button size="sm" variant="ghost" onClick={() => setAnulando(null)} disabled={anularMut.isPending}>No</Button>
                      <Button size="sm" variant="danger" loading={anularMut.isPending} onClick={() => anularMut.mutate(c.id)}>Sí, anular</Button>
                    </>
                  ) : (
                    <Button size="sm" variant="ghost" onClick={() => setAnulando(c.id)}>Anular</Button>
                  )
                )}
              </div>
            )}
          </div>
        )
      })}

      <Modal open={!!voucherVisto} onClose={cerrarVoucher} title={`Voucher ${voucherVisto?.compra.folio ?? ''}`} size="lg">
        {voucherVisto && (
          <div className="space-y-4">
            <img src={voucherVisto.url} alt="Voucher de transferencia" className="max-h-[60vh] w-full rounded-lg object-contain" />
            <p className="text-sm text-slate-300">
              Parcela {voucherVisto.compra.parcela_numero} · {clp(voucherVisto.compra.monto)} · {voucherVisto.compra.numeros.join(', ')}
            </p>
            {puedeConfirmar && !voucherVisto.compra.pagada && !voucherVisto.compra.anulada && (
              <div className="flex justify-end">
                <Button loading={confirmarMut.isPending} onClick={() => confirmarMut.mutate(voucherVisto.compra.id)}>
                  <CheckCircle2 className="h-4 w-4" /> Confirmar pago
                </Button>
              </div>
            )}
          </div>
        )}
      </Modal>

      <Modal open={!!adjuntando} onClose={() => setAdjuntando(null)} title={`Adjuntar voucher ${adjuntando?.folio ?? ''}`} size="sm">
        {adjuntando && (
          <div className="space-y-4">
            <VoucherInput value={nuevoVoucher} onChange={setNuevoVoucher} />
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setAdjuntando(null)}>Cancelar</Button>
              <Button
                disabled={!nuevoVoucher}
                loading={adjuntarMut.isPending}
                onClick={() => nuevoVoucher && adjuntarMut.mutate({ compraId: adjuntando.id, archivo: nuevoVoucher })}
              >
                Adjuntar
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
