import { Badge } from './ui/Badge'
import { clp } from '../utils/format'

/** «Pagado», «Parcial ($x de $y)» o «Pendiente» según lo abonado (cuenta corriente de luz). */
export function EstadoPagoLuz({ total, abonado }: { total: number | null; abonado: number }) {
  const monto = total ?? 0
  if (monto === 0 || abonado >= monto) return <Badge color="green" dot>Pagado</Badge>
  if (abonado > 0) return <Badge color="yellow" dot>Parcial · {clp(abonado)} de {clp(monto)}</Badge>
  return <Badge color="slate" dot>Pendiente</Badge>
}

/** «2026-10-01» → «01-10-2026», sin pasar por Date (evita el corrimiento de zona horaria). */
export const dia = (iso: string | null | undefined) => (iso ? iso.slice(0, 10).split('-').reverse().join('-') : '—')
