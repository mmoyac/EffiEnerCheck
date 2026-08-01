import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Zap, CheckCircle2 } from 'lucide-react'
import { parcelasApi } from '../../api/parcelas'
import { lecturasApi } from '../../api/lecturas'
import { Button } from '../../components/ui/Button'
import { Alert } from '../../components/ui/Alert'
import { Spinner } from '../../components/ui/Spinner'
import { numero } from '../../utils/format'
import { useAuth } from '../../hooks/useAuth'

export default function CapturarLectura() {
  const { parcelaId, boletaId } = useParams<{ parcelaId: string; boletaId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { user } = useAuth()
  const [lecturaActual, setLecturaActual] = useState('')
  const [inicializado, setInicializado] = useState(false)

  const [error, setError] = useState('')
  const [guardado, setGuardado] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const { data: parcela, isLoading: loadingParcela } = useQuery({
    queryKey: ['parcela', parcelaId],
    queryFn: () => parcelasApi.get(Number(parcelaId)),
  })

  // Buscar lectura anterior del último período
  const { data: lecturasExistentes = [] } = useQuery({
    queryKey: ['lecturas', Number(boletaId)],
    queryFn: () => lecturasApi.list(Number(boletaId)),
  })

  const lecturaExistente = lecturasExistentes.find((l) => l.parcela_id === Number(parcelaId))

  // Lectura anterior: si existe del período anterior, usamos su lectura_actual
  // Por ahora la traemos de la lectura existente en esta boleta si ya fue ingresada
  const lecturaAnterior = lecturaExistente?.lectura_anterior ?? null

  const kwh = lecturaActual && lecturaAnterior != null
    ? Number(lecturaActual) - lecturaAnterior
    : null

  useEffect(() => {
    if (!inicializado && lecturaExistente) {
      setLecturaActual(String(lecturaExistente.lectura_actual))
      setInicializado(true)
    }
  }, [lecturaExistente, inicializado])

  useEffect(() => {
    setTimeout(() => inputRef.current?.focus(), 300)
  }, [])

  const guardarMut = useMutation({
    mutationFn: () => {
      if (lecturaExistente) {
        return lecturasApi.update(lecturaExistente.id, { 
          lectura_actual: Number(lecturaActual),
          fecha_toma: new Date().toISOString()
        })
      }
      return lecturasApi.create({
        parcela_id: Number(parcelaId),
        boleta_id: Number(boletaId),
        lectura_anterior: lecturaAnterior ?? 0,
        lectura_actual: Number(lecturaActual),
      })
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lecturas', Number(boletaId)] })
      setGuardado(true)
      setTimeout(() => navigate(-1), 1500)
    },
    onError: (e: unknown) => setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error al guardar'),
  })

  if (loadingParcela) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-900">
        <Spinner size="lg" className="text-primary-500" />
      </div>
    )
  }

  if (guardado) {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-slate-900 gap-4">
        <CheckCircle2 className="h-16 w-16 text-primary-500" />
        <p className="text-xl font-bold text-slate-100">¡Lectura guardada!</p>
        <p className="text-slate-500">Volviendo...</p>
      </div>
    )
  }

  const valid = lecturaActual !== '' && !isNaN(Number(lecturaActual)) && (kwh == null || kwh >= 0)

  return (
    <div className="flex h-screen flex-col bg-slate-900">
      {/* Top bar */}
      <header className="flex items-center gap-3 border-b border-slate-700 px-4 py-3">
        <button onClick={() => navigate(-1)} className="rounded-lg p-2 text-slate-400 hover:bg-slate-700 hover:text-slate-100">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-primary-500" />
          <span className="text-sm font-medium text-slate-400">{user?.nombre}</span>
        </div>
      </header>

      <div className="flex flex-1 flex-col justify-between px-6 py-8">
        {/* Parcela info */}
        <div className="space-y-6">
          <div className="text-center">
            <p className="text-sm font-medium uppercase tracking-widest text-slate-500">
              {lecturaExistente ? 'Editar lectura' : 'Registrar lectura'}
            </p>
            <h1 className="mt-2 text-5xl font-black text-slate-100">
              Parcela {parcela?.numero_parcela}
            </h1>
            {parcela?.propietario_nombre && (
              <p className="mt-1 text-slate-400">{parcela.propietario_nombre}</p>
            )}
          </div>

          {/* Lectura anterior */}
          {lecturaAnterior != null && (
            <div className="rounded-xl border border-slate-700 bg-slate-800 px-5 py-4 text-center">
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Lectura anterior</p>
              <p className="mt-1 font-mono text-3xl font-bold text-slate-300">{numero(lecturaAnterior)}</p>
            </div>
          )}

          {/* Input lectura actual */}
          <div className="space-y-2">
            <label className="block text-center text-sm font-medium text-slate-400">
              Lectura actual
            </label>
            <input
              ref={inputRef}
              type="number"
              inputMode="numeric"
              value={lecturaActual}
              onChange={(e) => { setLecturaActual(e.target.value); setError('') }}
              placeholder="0"
              className="w-full rounded-xl border border-slate-600 bg-slate-800 px-4 py-5 text-center font-mono text-4xl font-bold text-slate-100 placeholder-slate-700 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            />
          </div>

          {/* kWh calculado */}
          {kwh !== null && (
            <div className={`rounded-xl border px-5 py-4 text-center ${
              kwh < 0 ? 'border-red-500/30 bg-red-500/10' : 'border-primary-500/30 bg-primary-500/10'
            }`}>
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Consumo del período</p>
              <p className={`mt-1 font-mono text-3xl font-bold ${kwh < 0 ? 'text-red-400' : 'text-primary-400'}`}>
                {numero(kwh)} kWh
              </p>
              {kwh < 0 && <p className="mt-1 text-xs text-red-400">La lectura actual no puede ser menor que la anterior</p>}
            </div>
          )}

          {error && <Alert variant="error">{error}</Alert>}
        </div>

        {/* Botón guardar */}
        <Button
          size="lg"
          fullWidth
          disabled={!valid}
          loading={guardarMut.isPending}
          onClick={() => guardarMut.mutate()}
          className="mt-8 py-5 text-lg"
        >
          Confirmar lectura
        </Button>
      </div>
    </div>
  )
}
