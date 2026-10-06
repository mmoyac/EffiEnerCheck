import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import {
  OtroCondominio, SesionVencida, leerRecorrido, listarPendientes, prepararRecorrido, sincronizar, suscribir,
  type Pendiente, type Recorrido,
} from './lecturas'

/** Estado de la app de lecturas sin conexión: recorrido, pendientes, conexión y acciones. */
export function useLecturasOffline() {
  const { user } = useAuth()
  const condominioId = user?.condominio_id ?? null
  const [recorrido, setRecorrido] = useState<Recorrido | undefined>()
  const [pendientes, setPendientes] = useState<Pendiente[]>([])
  const [cargado, setCargado] = useState(false)
  const [enLinea, setEnLinea] = useState(navigator.onLine)
  const [ocupado, setOcupado] = useState<'preparando' | 'sincronizando' | null>(null)
  const [aviso, setAviso] = useState<{ tipo: 'success' | 'error' | 'warning'; texto: string } | null>(null)
  const [ultimaSync, setUltimaSync] = useState<string | null>(null)

  const recargar = useCallback(async () => {
    const [r, p] = await Promise.all([leerRecorrido(), listarPendientes()])
    setRecorrido(r)
    setPendientes(p)
    setCargado(true)
  }, [])

  const sincronizarAhora = useCallback(async () => {
    setOcupado('sincronizando')
    try {
      const { aplicadas, conProblemas } = await sincronizar(condominioId)
      setUltimaSync(new Date().toISOString())
      if (conProblemas) setAviso({ tipo: 'warning', texto: `${conProblemas} lectura(s) necesitan revisión` })
      else if (aplicadas) setAviso({ tipo: 'success', texto: `${aplicadas} lectura(s) sincronizadas` })
    } catch (err) {
      if (err instanceof SesionVencida) setAviso({ tipo: 'error', texto: 'La sesión venció: ingresa de nuevo para sincronizar. Tus lecturas siguen guardadas.' })
      else if (err instanceof OtroCondominio) setAviso({ tipo: 'error', texto: 'Las lecturas guardadas son de otro condominio: no se enviaron.' })
      else setAviso({ tipo: 'error', texto: 'No se pudo sincronizar. Se reintentará cuando haya señal.' })
    } finally {
      setOcupado(null)
    }
  }, [condominioId])

  const preparar = useCallback(async () => {
    setOcupado('preparando')
    try {
      await prepararRecorrido(condominioId)
      setAviso({ tipo: 'success', texto: 'Recorrido listo: puedes trabajar sin señal' })
    } catch {
      setAviso({ tipo: 'error', texto: 'No se pudo descargar el recorrido. Revisa la señal.' })
    } finally {
      setOcupado(null)
    }
  }, [condominioId])

  // Al abrir: leer el celular; con señal, primero sincronizar y, si no queda nada pendiente, refrescar la base
  useEffect(() => {
    let vigente = true
    ;(async () => {
      await recargar()
      if (!navigator.onLine) return
      const quedan = (await listarPendientes()).some((p) => p.estado === 'pendiente')
      if (quedan) await sincronizarAhora()
      if (vigente && !(await listarPendientes()).some((p) => p.estado === 'pendiente')) {
        await prepararRecorrido(condominioId).catch(() => {})
      }
    })()
    return () => { vigente = false }
  }, [condominioId, recargar, sincronizarAhora])

  useEffect(() => suscribir(() => { recargar() }), [recargar])

  // Conexión: al volver la señal se sincroniza solo
  useEffect(() => {
    const online = () => { setEnLinea(true); sincronizarAhora() }
    const offline = () => setEnLinea(false)
    window.addEventListener('online', online)
    window.addEventListener('offline', offline)
    return () => { window.removeEventListener('online', online); window.removeEventListener('offline', offline) }
  }, [sincronizarAhora])

  return {
    recorrido, pendientes, cargado, enLinea, ocupado, aviso, ultimaSync,
    preparar, sincronizarAhora, cerrarAviso: () => setAviso(null),
  }
}
