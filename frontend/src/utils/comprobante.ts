import { clp } from './format'
import type { CompraRifa, MedioPago, Rifa } from '../types'

export const MEDIO_PAGO_TEXTO: Record<MedioPago, string> = {
  efectivo: 'Efectivo',
  transferencia: 'Transferencia',
  gasto_comun: 'Gasto común',
}

export function estadoPagoTexto(c: Pick<CompraRifa, 'medio_pago' | 'pagada'>): string {
  if (c.medio_pago === 'gasto_comun') return 'Se cargará en el gasto común'
  if (c.pagada) return 'Pagado'
  return 'Pendiente de confirmación de la transferencia'
}

/** Texto del comprobante (WhatsApp y vista impresa comparten el contenido). */
export function mensajeComprobante(rifa: Rifa, compra: CompraRifa): string {
  const lineas = [
    `*${rifa.nombre}*`,
    `A beneficio de ${rifa.beneficiario}`,
    '',
    `Folio: *${compra.folio}*`,
    `${compra.numeros.length === 1 ? 'Número' : 'Números'}: *${compra.numeros.join(', ')}*`,
    `Parcela: ${compra.parcela_numero}`,
    ...(compra.comprador_nombre ? [`Comprador: ${compra.comprador_nombre}`] : []),
    `Monto: ${clp(compra.monto)} — ${MEDIO_PAGO_TEXTO[compra.medio_pago]}`,
    estadoPagoTexto(compra),
  ]
  if (compra.medio_pago === 'transferencia' && !compra.pagada && rifa.datos_transferencia) {
    lineas.push('', 'Datos para transferir:', rifa.datos_transferencia)
  }
  if (rifa.premios.length) {
    lineas.push('', 'Premios:', ...rifa.premios.map((p, i) => `${i + 1}. ${p}`))
  }
  lineas.push('', '¡Gracias por colaborar!')
  return lineas.join('\n')
}
