import { useMemo, useState } from 'react'
import { Search, X } from 'lucide-react'
import type { ParcelaVenta } from '../../types'

interface Props {
  parcelas: ParcelaVenta[]
  value: number | null
  onChange: (parcela: ParcelaVenta | null) => void
}

const normalizar = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

/** Búsqueda por número de parcela o por nombre del propietario. */
export function ParcelaBuscador({ parcelas, value, onChange }: Props) {
  const [texto, setTexto] = useState('')
  const elegida = parcelas.find((p) => p.id === value) ?? null

  const resultados = useMemo(() => {
    const q = normalizar(texto.trim())
    if (!q) return []
    // Coincidencia exacta del número primero ("2" no debe esconder a la parcela 2 entre 20–29)
    return parcelas
      .filter((p) => normalizar(p.numero_parcela).startsWith(q) || normalizar(p.propietario_nombre ?? '').includes(q))
      .sort((a, b) => Number(normalizar(b.numero_parcela) === q) - Number(normalizar(a.numero_parcela) === q))
      .slice(0, 8)
  }, [texto, parcelas])

  if (elegida) {
    return (
      <div className="flex items-center justify-between rounded-xl border border-primary-500/50 bg-primary-600/10 px-4 py-3">
        <div>
          <p className="text-lg font-bold text-slate-100">Parcela {elegida.numero_parcela}</p>
          {elegida.propietario_nombre && <p className="text-sm text-slate-300">{elegida.propietario_nombre}</p>}
        </div>
        <button
          type="button"
          onClick={() => { onChange(null); setTexto('') }}
          className="rounded-lg p-2 text-slate-400 hover:bg-slate-700 hover:text-slate-100"
          aria-label="Cambiar parcela"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-1">
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-500" />
        <input
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Número de parcela o nombre del propietario"
          aria-label="Buscar parcela"
          className="w-full rounded-xl border border-slate-600 bg-slate-800 py-3 pl-11 pr-3 text-base text-slate-100 placeholder-slate-500 focus:border-primary-500 focus:outline-none"
        />
      </div>
      {resultados.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-slate-700">
          {resultados.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => onChange(p)}
              className="flex w-full items-center justify-between border-b border-slate-700/60 bg-slate-800 px-4 py-3 text-left last:border-0 hover:bg-slate-700"
            >
              <span className="font-semibold text-slate-100">Parcela {p.numero_parcela}</span>
              <span className="ml-3 truncate text-sm text-slate-400">{p.propietario_nombre}</span>
            </button>
          ))}
        </div>
      )}
      {texto.trim() && resultados.length === 0 && <p className="px-1 text-sm text-slate-500">Sin resultados</p>}
    </div>
  )
}
