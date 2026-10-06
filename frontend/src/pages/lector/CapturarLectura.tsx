import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, CloudOff, Zap } from 'lucide-react'
import { Button } from '../../components/ui/Button'
import { Alert } from '../../components/ui/Alert'
import { Spinner } from '../../components/ui/Spinner'
import { numero } from '../../utils/format'
import { useAuth } from '../../hooks/useAuth'
import { guardarPendiente, leerRecorrido, listarPendientes, sincronizar, type Pendiente, type Recorrido } from '../../offline/lecturas'

/**
 * Captura de una lectura. Siempre se guarda primero en el celular (IndexedDB); si hay señal se sincroniza
 * enseguida. Un solo camino con o sin conexión (cambio lecturas-sin-conexion).
 */
export default function CapturarLectura() {
  const { parcelaId } = useParams<{ parcelaId: string; boletaId: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [recorrido, setRecorrido] = useState<Recorrido | undefined>()
  const [pendiente, setPendiente] = useState<Pendiente | undefined>()
  const [cargado, setCargado] = useState(false)
  const [lecturaActual, setLecturaActual] = useState('')
  const [guardando, setGuardando] = useState(false)
  const [resultado, setResultado] = useState<'sincronizada' | 'en-celular' | null>(null)
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const parcela = recorrido?.parcelas.find((p) => p.id === Number(parcelaId))
  const lectura = recorrido?.lecturas.find((l) => l.parcela_id === Number(parcelaId))

  useEffect(() => {
    (async () => {
      const [r, ps] = await Promise.all([leerRecorrido(), listarPendientes()])
      const l = r?.lecturas.find((x) => x.parcela_id === Number(parcelaId))
      const p = ps.find((x) => x.parcela_id === Number(parcelaId))
      setRecorrido(r)
      setPendiente(p)
      // Precarga: lo que está en el celular sin sincronizar, o lo ya registrado en el servidor
      if (p) setLecturaActual(String(p.lectura_actual))
      else if (l?.fecha_toma) setLecturaActual(String(l.lectura_actual))
      setCargado(true)
      setTimeout(() => inputRef.current?.focus(), 300)
    })()
  }, [parcelaId])

  const lecturaAnterior = lectura?.lectura_anterior ?? null
  const kwh = lecturaActual !== '' && lecturaAnterior != null ? Number(lecturaActual) - lecturaAnterior : null
  const valido = lecturaActual !== '' && !isNaN(Number(lecturaActual)) && (kwh == null || kwh >= 0)
  const edicion = !!pendiente || !!lectura?.fecha_toma

  const confirmar = async () => {
    if (!lectura) return
    setGuardando(true)
    setError('')
    try {
      await guardarPendiente(lectura, Number(lecturaActual))
    } catch {
      setError('No se pudo guardar en el celular. Revisa el espacio disponible.')
      setGuardando(false)
      return
    }
    let estado: 'sincronizada' | 'en-celular' = 'en-celular'
    if (navigator.onLine) {
      try {
        await sincronizar(user?.condominio_id ?? null)
        const quedo = (await listarPendientes()).find((p) => p.lectura_id === lectura.id)
        if (!quedo) estado = 'sincronizada'
      } catch { /* queda en el celular; se reintenta al volver la señal */ }
    }
    setResultado(estado)
    setGuardando(false)
    setTimeout(() => navigate(-1), 1500)
  }

  if (!cargado) {
    return <div className="flex h-screen items-center justify-center bg-slate-900"><Spinner size="lg" className="text-primary-500" /></div>
  }

  if (resultado) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 bg-slate-900 px-6 text-center">
        {resultado === 'sincronizada'
          ? <CheckCircle2 className="h-16 w-16 text-primary-500" />
          : <CloudOff className="h-16 w-16 text-yellow-400" />}
        <p className="text-xl font-bold text-slate-100">
          {resultado === 'sincronizada' ? '¡Lectura guardada!' : 'Guardada en el celular'}
        </p>
        <p className="text-slate-500">
          {resultado === 'sincronizada' ? 'Volviendo…' : 'Se enviará cuando haya señal. Volviendo…'}
        </p>
      </div>
    )
  }

  return (
    <div className="flex h-screen flex-col bg-slate-900">
      <header className="flex items-center gap-3 border-b border-slate-700 px-4 py-3">
        <button onClick={() => navigate(-1)} className="rounded-lg p-2 text-slate-400 hover:bg-slate-700 hover:text-slate-100">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-primary-500" />
          <span className="text-sm font-medium text-slate-400">{user?.nombre}</span>
        </div>
        {!navigator.onLine && <span className="ml-auto flex items-center gap-1 text-xs text-yellow-300"><CloudOff className="h-4 w-4" /> Sin señal</span>}
      </header>

      {!parcela || !lectura ? (
        <div className="p-6">
          <Alert variant="warning">
            Esta parcela no está en el recorrido guardado en el celular. Vuelve atrás y, con señal, prepara el recorrido de nuevo.
          </Alert>
        </div>
      ) : (
        <div className="flex flex-1 flex-col justify-between px-6 py-8">
          <div className="space-y-6">
            <div className="text-center">
              <p className="text-sm font-medium uppercase tracking-widest text-slate-500">{edicion ? 'Editar lectura' : 'Registrar lectura'}</p>
              <h1 className="mt-2 text-5xl font-black text-slate-100">Parcela {parcela.numero_parcela}</h1>
              {parcela.propietario_nombre && <p className="mt-1 text-slate-400">{parcela.propietario_nombre}</p>}
              {pendiente?.estado === 'pendiente' && <p className="mt-2 text-xs text-yellow-300">Hay una lectura en el celular sin sincronizar: la reemplazarás.</p>}
              {pendiente && pendiente.estado !== 'pendiente' && (
                <p className="mt-2 text-xs text-yellow-300">Tu lectura anterior no se aplicó: {pendiente.motivo}</p>
              )}
            </div>

            {lecturaAnterior != null && (
              <div className="rounded-xl border border-slate-700 bg-slate-800 px-5 py-4 text-center">
                <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Lectura anterior</p>
                <p className="mt-1 font-mono text-3xl font-bold text-slate-300">{numero(lecturaAnterior)}</p>
              </div>
            )}

            <div className="space-y-2">
              <label className="block text-center text-sm font-medium text-slate-400">Lectura actual</label>
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

            {kwh !== null && (
              <div className={`rounded-xl border px-5 py-4 text-center ${kwh < 0 ? 'border-red-500/30 bg-red-500/10' : 'border-primary-500/30 bg-primary-500/10'}`}>
                <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Consumo del período</p>
                <p className={`mt-1 font-mono text-3xl font-bold ${kwh < 0 ? 'text-red-400' : 'text-primary-400'}`}>{numero(kwh)} kWh</p>
                {kwh < 0 && <p className="mt-1 text-xs text-red-400">La lectura actual no puede ser menor que la anterior</p>}
              </div>
            )}

            {error && <Alert variant="error">{error}</Alert>}
          </div>

          <Button size="lg" fullWidth disabled={!valido || recorrido?.boleta?.lecturas_cerradas} loading={guardando}
                  onClick={confirmar} className="mt-8 py-5 text-lg">
            Confirmar lectura
          </Button>
        </div>
      )}
    </div>
  )
}
