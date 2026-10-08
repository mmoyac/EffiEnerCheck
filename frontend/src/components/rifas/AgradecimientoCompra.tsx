import { ChevronLeft, Clock, HeartHandshake, Landmark, Plus, Printer, Receipt, Share2 } from 'lucide-react'
import { Button } from '../ui/Button'
import { clp, fechaHora } from '../../utils/format'
import { MEDIO_PAGO_TEXTO, mensajeComprobante } from '../../utils/comprobante'
import type { CompraRifa, Rifa } from '../../types'

interface Props {
  rifa: Rifa
  /** La compra tal como la registró el servidor (no la selección en pantalla) */
  compra: CompraRifa
  onComprarMas: () => void
  onVolver: () => void
}

/** Comparte el comprobante con la hoja nativa del celular; sin ella, abre WhatsApp para elegir el chat. */
async function compartir(texto: string) {
  if (navigator.share) {
    try { await navigator.share({ text: texto }) } catch { /* la persona cerró la hoja */ }
    return
  }
  window.open(`https://wa.me/?text=${encodeURIComponent(texto)}`, '_blank', 'noreferrer')
}

/**
 * Cierre de la compra del comunero desde su portal: agradece el aporte, resume lo comprado y
 * explica qué sigue según la forma de pago.
 */
export function AgradecimientoCompra({ rifa, compra, onComprarMas, onVolver }: Props) {
  const varios = compra.numeros.length > 1

  return (
    <div className="space-y-5">
      <div className="text-center">
        <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-primary-600/20">
          <HeartHandshake className="h-7 w-7 text-primary-400" />
        </div>
        <h2 className="text-2xl font-bold text-slate-100">¡Gracias por tu aporte!</h2>
        <p className="mt-1 text-sm text-slate-300">
          Tu compra ayuda a <span className="font-semibold text-slate-100">{rifa.beneficiario}</span>.
        </p>
      </div>

      {/* Lo que se imprime: ver .area-impresion en index.css */}
      <div className="area-impresion rounded-2xl border border-slate-600 bg-slate-800 p-5 text-center">
        <p className="text-sm text-slate-400 print-oscuro">{rifa.nombre}</p>
        <p className="mt-3 text-xs uppercase tracking-widest text-slate-500">Folio</p>
        <p className="font-mono text-4xl font-black tracking-wider text-slate-100 print-oscuro" data-testid="folio">{compra.folio}</p>
        <p className="mt-4 text-xs uppercase tracking-widest text-slate-500">{varios ? 'Tus números' : 'Tu número'}</p>
        <p className="font-mono text-3xl font-bold text-primary-400 print-oscuro">{compra.numeros.join(' · ')}</p>
        <div className="mx-auto mt-4 max-w-xs space-y-1 text-left text-sm">
          <p className="flex justify-between gap-3"><span className="text-slate-400">Parcela</span><span className="text-slate-200 print-oscuro">{compra.parcela_numero}</span></p>
          <p className="flex justify-between gap-3">
            <span className="text-slate-400">{compra.numeros.length} × {clp(rifa.precio_numero)}</span>
            <span className="font-mono font-semibold text-slate-100 print-oscuro">{clp(compra.monto)}</span>
          </p>
          <p className="flex justify-between gap-3"><span className="text-slate-400">Pago</span><span className="text-slate-200 print-oscuro">{MEDIO_PAGO_TEXTO[compra.medio_pago]}</span></p>
          <p className="text-center text-xs text-slate-500">{fechaHora(compra.created_at)}</p>
        </div>
      </div>

      <div className="rounded-2xl bg-slate-800 p-4">
        <p className="mb-2 text-sm font-semibold text-slate-300">Qué sigue</p>
        {compra.medio_pago === 'gasto_comun' ? (
          <p className="flex gap-2 text-sm text-slate-300">
            <Receipt className="mt-0.5 h-4 w-4 shrink-0 text-primary-400" />
            <span>No tienes que pagar nada ahora: {clp(compra.monto)} se cargarán en un próximo gasto común de tu parcela, cuando se cierre la rifa.</span>
          </p>
        ) : compra.pagada ? (
          <p className="text-sm text-slate-300">Tu pago ya está confirmado. ¡Mucha suerte en el sorteo!</p>
        ) : (
          <div className="space-y-3 text-sm text-slate-300">
            <p className="flex gap-2">
              <Landmark className="mt-0.5 h-4 w-4 shrink-0 text-primary-400" />
              <span>Transfiere {clp(compra.monto)} y guarda el comprobante de tu banco.</span>
            </p>
            {rifa.datos_transferencia ? (
              <div className="rounded-xl bg-slate-700/40 p-3">
                <p className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">Datos para transferir</p>
                <p className="whitespace-pre-line text-slate-200">{rifa.datos_transferencia}</p>
              </div>
            ) : (
              <p className="rounded-xl bg-slate-700/40 p-3">La administración te hará llegar los datos para transferir.</p>
            )}
            <p className="flex gap-2 text-yellow-300">
              <Clock className="mt-0.5 h-4 w-4 shrink-0" />
              <span>Tu compra queda pendiente hasta que la administración confirme la transferencia.</span>
            </p>
          </div>
        )}
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        <Button size="lg" variant="secondary" onClick={() => compartir(mensajeComprobante(rifa, compra))}>
          <Share2 className="h-5 w-5" /> Compartir
        </Button>
        <Button size="lg" variant="secondary" onClick={() => window.print()}>
          <Printer className="h-5 w-5" /> Guardar
        </Button>
        {rifa.estado === 'abierta' && (
          <Button size="lg" onClick={onComprarMas}>
            <Plus className="h-5 w-5" /> Comprar más números
          </Button>
        )}
        <Button size="lg" variant="ghost" onClick={onVolver}>
          <ChevronLeft className="h-5 w-5" /> Volver a rifas
        </Button>
      </div>
    </div>
  )
}
