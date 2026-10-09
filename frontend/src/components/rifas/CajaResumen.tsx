import { useQuery } from '@tanstack/react-query'
import { rifasApi } from '../../api/rifas'
import { Spinner } from '../ui/Spinner'
import { clp } from '../../utils/format'

/** Efectivo vigente recibido por día y por cuenta, para cuadrar la caja de portería. */
export function CajaResumen({ rifaId }: { rifaId: number }) {
  const { data: caja, isLoading } = useQuery({ queryKey: ['rifa-caja', rifaId], queryFn: () => rifasApi.caja(rifaId) })
  if (isLoading || !caja) return <div className="flex h-32 items-center justify-center"><Spinner size="lg" className="text-primary-500" /></div>
  return (
    <div>
      <p className="mb-1 text-sm font-semibold text-slate-300">Efectivo recibido</p>
      <p className="mb-4 text-xs text-slate-400">Solo ventas vigentes en efectivo. Las anuladas por la administración no suman.</p>
      {caja.filas.length === 0 ? (
        <p className="text-sm text-slate-500">Aún no hay ventas en efectivo.</p>
      ) : (
        <>
        {/* Celular: lista apilada, una fila por día y cuenta */}
        <ul className="divide-y divide-slate-700/50 text-sm md:hidden">
          {caja.filas.map((f) => (
            <li key={`${f.fecha}-${f.usuario_id}`} className="flex items-start justify-between gap-3 py-2">
              <div className="min-w-0">
                <p className="text-slate-200">{f.fecha.split('-').reverse().join('-')}</p>
                <p className="truncate text-xs text-slate-500">{f.usuario_nombre}</p>
                <p className="flex flex-wrap gap-x-3 text-xs text-slate-400">
                  <span>Ventas <span className="font-mono text-slate-300">{f.ventas}</span></span>
                  <span>Números <span className="font-mono text-slate-300">{f.numeros}</span></span>
                </p>
              </div>
              <p className="shrink-0 font-mono font-semibold text-slate-100">{clp(f.monto)}</p>
            </li>
          ))}
          <li className="flex flex-wrap items-baseline justify-between gap-2 pt-3">
            <span className="font-semibold text-slate-100">
              Total <span className="ml-1 text-xs font-normal text-slate-400">Números <span className="font-mono text-slate-200">{caja.total_numeros}</span></span>
            </span>
            <span className="font-mono text-lg font-bold text-primary-400">{clp(caja.total_monto)}</span>
          </li>
        </ul>
        <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-left text-xs uppercase tracking-wider text-slate-500">
              <th className="py-2">Día</th>
              <th className="py-2 text-right">Ventas</th>
              <th className="py-2 text-right">Números</th>
              <th className="py-2 text-right">Monto</th>
            </tr>
          </thead>
          <tbody>
            {caja.filas.map((f) => (
              <tr key={`${f.fecha}-${f.usuario_id}`} className="border-b border-slate-700/50">
                <td className="py-2 text-slate-200">
                  {f.fecha.split('-').reverse().join('-')}
                  <span className="block text-xs text-slate-500">{f.usuario_nombre}</span>
                </td>
                <td className="py-2 text-right font-mono text-slate-300">{f.ventas}</td>
                <td className="py-2 text-right font-mono text-slate-300">{f.numeros}</td>
                <td className="py-2 text-right font-mono font-semibold text-slate-100">{clp(f.monto)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td className="pt-3 font-semibold text-slate-100" colSpan={2}>Total</td>
              <td className="pt-3 text-right font-mono text-slate-200">{caja.total_numeros}</td>
              <td className="pt-3 text-right font-mono text-lg font-bold text-primary-400">{clp(caja.total_monto)}</td>
            </tr>
          </tfoot>
        </table>
        </div>
        </>
      )}
    </div>
  )
}
