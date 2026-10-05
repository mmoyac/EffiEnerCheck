import { useState } from 'react'

const RANGO = 100
// Sobre esta cantidad la grilla se pagina por rangos para no saturar el móvil
const UMBRAL_PAGINAR = 200

interface Props {
  cantidad: number
  vendidos: Set<number>
  mios: Set<number>
  seleccion: Set<number>
  onToggle: (n: number) => void
  disabled?: boolean
}

export function NumeroGrid({ cantidad, vendidos, mios, seleccion, onToggle, disabled = false }: Props) {
  const paginar = cantidad > UMBRAL_PAGINAR
  const rangos = paginar ? Math.ceil(cantidad / RANGO) : 1
  const [rango, setRango] = useState(0)

  const desde = paginar ? rango * RANGO + 1 : 1
  const hasta = paginar ? Math.min((rango + 1) * RANGO, cantidad) : cantidad
  const numeros = Array.from({ length: hasta - desde + 1 }, (_, i) => desde + i)

  return (
    <div className="space-y-3">
      {paginar && (
        <div className="flex flex-wrap gap-1.5">
          {Array.from({ length: rangos }, (_, i) => {
            const ini = i * RANGO + 1
            const fin = Math.min((i + 1) * RANGO, cantidad)
            return (
              <button
                key={i}
                type="button"
                onClick={() => setRango(i)}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                  rango === i ? 'bg-primary-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {ini}–{fin}
              </button>
            )
          })}
        </div>
      )}

      <div className="grid grid-cols-5 gap-2 sm:grid-cols-10">
        {numeros.map((n) => {
          const esMio = mios.has(n)
          const vendido = vendidos.has(n)
          const seleccionado = seleccion.has(n)
          const bloqueado = disabled || vendido

          let clases = 'bg-slate-700 text-slate-200 hover:bg-slate-600'
          if (seleccionado) clases = 'bg-primary-600 text-white ring-2 ring-primary-300'
          else if (esMio) clases = 'bg-green-600/25 text-green-300 ring-1 ring-green-500/50'
          else if (vendido) clases = 'bg-slate-800 text-slate-600 line-through'

          return (
            <button
              key={n}
              type="button"
              disabled={bloqueado}
              onClick={() => onToggle(n)}
              aria-pressed={seleccionado}
              aria-label={`Número ${n}${esMio ? ', de tu parcela' : vendido ? ', no disponible' : ''}`}
              className={`flex min-h-[44px] items-center justify-center rounded-lg font-mono text-sm font-semibold transition-all active:scale-95 disabled:cursor-not-allowed ${clases}`}
            >
              {n}
            </button>
          )
        })}
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-400">
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-slate-700" />Disponible</span>
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-primary-600" />Seleccionado</span>
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-green-600/40 ring-1 ring-green-500/50" />De tu parcela</span>
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-slate-800 ring-1 ring-slate-700" />No disponible</span>
      </div>
    </div>
  )
}
