import { CheckCircle2, MessageCircle, Plus, Printer } from 'lucide-react'
import { Button } from '../ui/Button'
import { clp, fechaHora } from '../../utils/format'
import { estadoPagoTexto, MEDIO_PAGO_TEXTO, mensajeComprobante, urlWhatsApp } from '../../utils/comprobante'
import { formatearTelefono } from '../../utils/telefono'
import type { CompraRifa, Rifa } from '../../types'

interface Props {
  rifa: Rifa
  compra: CompraRifa
  onNuevaVenta?: () => void
}

/**
 * Pantalla tras una venta: el folio en grande para anotarlo en papel si el comprador no tiene
 * teléfono, el envío por WhatsApp (lo confirma la persona) y la impresión opcional.
 */
export function ComprobanteVenta({ rifa, compra, onNuevaVenta }: Props) {
  const whatsapp = compra.telefono ? urlWhatsApp(compra.telefono, mensajeComprobante(rifa, compra)) : null

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-green-400">
        <CheckCircle2 className="h-6 w-6" />
        <p className="text-lg font-semibold">Venta registrada</p>
      </div>

      {/* Lo que se imprime: ver .area-impresion en index.css */}
      <div className="area-impresion rounded-2xl border border-slate-600 bg-slate-800 p-5 text-center">
        <p className="text-sm text-slate-400 print-oscuro">{rifa.nombre}</p>
        <p className="mt-3 text-xs uppercase tracking-widest text-slate-500">Folio</p>
        <p className="font-mono text-5xl font-black tracking-wider text-slate-100 print-oscuro" data-testid="folio">{compra.folio}</p>
        <p className="mt-4 text-xs uppercase tracking-widest text-slate-500">
          {compra.numeros.length === 1 ? 'Número' : 'Números'}
        </p>
        <p className="font-mono text-3xl font-bold text-primary-400 print-oscuro">{compra.numeros.join(' · ')}</p>
        <div className="mx-auto mt-4 max-w-xs space-y-1 text-left text-sm">
          <p className="flex justify-between gap-3"><span className="text-slate-400">Parcela</span><span className="text-slate-200 print-oscuro">{compra.parcela_numero}</span></p>
          {compra.comprador_nombre && (
            <p className="flex justify-between gap-3"><span className="text-slate-400">Comprador</span><span className="text-right text-slate-200 print-oscuro">{compra.comprador_nombre}</span></p>
          )}
          <p className="flex justify-between gap-3"><span className="text-slate-400">Monto</span><span className="font-mono font-semibold text-slate-100 print-oscuro">{clp(compra.monto)}</span></p>
          <p className="flex justify-between gap-3"><span className="text-slate-400">Pago</span><span className="text-slate-200 print-oscuro">{MEDIO_PAGO_TEXTO[compra.medio_pago]}</span></p>
          <p className="text-center text-xs text-slate-400">{estadoPagoTexto(compra)}</p>
          <p className="text-center text-xs text-slate-500">{fechaHora(compra.created_at)}</p>
        </div>
        {rifa.premios.length > 0 && (
          <div className="mx-auto mt-4 max-w-xs border-t border-slate-700 pt-3 text-left text-xs text-slate-400">
            <p className="mb-1 font-semibold uppercase tracking-wider">Premios</p>
            {rifa.premios.map((p, i) => <p key={i}>{i + 1}. {p}</p>)}
          </div>
        )}
      </div>

      {!whatsapp && (
        <p className="rounded-lg bg-yellow-500/10 px-3 py-2 text-sm text-yellow-300">
          Sin teléfono: anota el folio <strong>{compra.folio}</strong> y los números en un papel para el comprador, o imprime el comprobante.
        </p>
      )}

      <div className="grid gap-2 sm:grid-cols-3">
        {whatsapp && (
          <a
            href={whatsapp}
            target="_blank"
            rel="noreferrer"
            className="flex min-h-[48px] items-center justify-center gap-2 rounded-lg bg-[#25D366] px-4 py-3 text-sm font-semibold text-slate-900 hover:brightness-110"
          >
            <MessageCircle className="h-5 w-5" /> Enviar a {formatearTelefono(compra.telefono!)}
          </a>
        )}
        <Button variant="secondary" size="lg" onClick={() => window.print()}>
          <Printer className="h-5 w-5" /> Imprimir
        </Button>
        {onNuevaVenta && (
          <Button size="lg" onClick={onNuevaVenta}>
            <Plus className="h-5 w-5" /> Nueva venta
          </Button>
        )}
      </div>
      {whatsapp && (
        <p className="text-xs text-slate-500">Se abre WhatsApp con el mensaje listo: falta tocar «Enviar» en WhatsApp.</p>
      )}
    </div>
  )
}
