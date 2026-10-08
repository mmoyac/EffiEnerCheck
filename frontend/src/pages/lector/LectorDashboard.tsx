import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AlertTriangle, CameraOff, CheckCircle2, ChevronRight, Circle, CloudOff, CloudUpload, Download, RefreshCw, Wifi, Zap,
} from 'lucide-react'
import { Spinner } from '../../components/ui/Spinner'
import { Alert } from '../../components/ui/Alert'
import { CambiarClaveModal } from '../../components/CambiarClaveModal'
import { periodoCorto, numero } from '../../utils/format'
import { useAuth } from '../../hooks/useAuth'
import { PLATAFORMA } from '../../config/marca'
import { useLecturasOffline } from '../../offline/useLecturasOffline'
import { descartar, descartarFoto } from '../../offline/lecturas'
import { ordenarRecorrido } from '../../utils/recorrido'

type Filtro = 'pendientes' | 'todas' | 'revisar'

const hora = (iso: string | null) =>
  iso ? new Date(iso).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }) : '—'

/**
 * App del lector. Trabaja sobre el recorrido guardado en el celular (IndexedDB), con o sin señal:
 * las lecturas se guardan primero en el celular y se sincronizan cuando hay conexión.
 */
export default function LectorDashboard() {
  const navigate = useNavigate()
  const { logout, user } = useAuth()
  const [cambiarClave, setCambiarClave] = useState(false)
  const [filtro, setFiltro] = useState<Filtro>('pendientes')
  const { recorrido, pendientes, fotos, cargado, enLinea, ocupado, aviso, ultimaSync, preparar, sincronizarAhora, cerrarAviso } =
    useLecturasOffline()

  const boleta = recorrido?.boleta ?? null
  // El orden del recorrido si la administración lo definió; si no, el numérico (cambio orden-recorrido)
  const parcelas = ordenarRecorrido(recorrido?.parcelas ?? [])
  const porSincronizar = pendientes.filter((p) => p.estado === 'pendiente')
  const aRevisar = pendientes.filter((p) => p.estado !== 'pendiente')
  const pendientePorParcela = new Map(porSincronizar.map((p) => [p.parcela_id, p]))
  const revisarPorParcela = new Map(aRevisar.map((p) => [p.parcela_id, p]))
  const leidasServidor = new Set(recorrido?.lecturas.filter((l) => l.fecha_toma).map((l) => l.parcela_id))
  const leida = (parcelaId: number) => leidasServidor.has(parcelaId) || pendientePorParcela.has(parcelaId)

  // Fotos del medidor (cambio foto-medidor)
  const fotosPorSubir = fotos.filter((f) => f.estado === 'pendiente')
  const fotoRechazadaPorParcela = new Map(fotos.filter((f) => f.estado === 'rechazada').map((f) => [f.parcela_id, f]))
  const fotoEnCelular = new Set(fotos.map((f) => f.parcela_id))
  const conFotoServidor = new Set(recorrido?.lecturas.filter((l) => l.tiene_foto).map((l) => l.parcela_id))
  const sinFoto = (parcelaId: number) => leida(parcelaId) && !fotoEnCelular.has(parcelaId) && !conFotoServidor.has(parcelaId)
  const hayQueSubir = porSincronizar.length > 0 || fotosPorSubir.length > 0
  const porRevisar = (parcelaId: number) => revisarPorParcela.has(parcelaId) || fotoRechazadaPorParcela.has(parcelaId)
  const totalRevisar = new Set([...revisarPorParcela.keys(), ...fotoRechazadaPorParcela.keys()]).size

  const total = parcelas.length
  const completadas = parcelas.filter((p) => leida(p.id)).length
  const leidasSinFoto = parcelas.filter((p) => sinFoto(p.id)).length
  const parcelasFiltradas = parcelas.filter((p) =>
    filtro === 'pendientes' ? !leida(p.id) : filtro === 'revisar' ? porRevisar(p.id) : true)

  const capturar = (parcelaId: number) => boleta && navigate(`/lecturas/capturar/${parcelaId}/${boleta.id}`)

  return (
    <div className="flex h-screen flex-col bg-slate-900">
      <header className="sticky top-0 z-10 border-b border-slate-700 bg-slate-900 px-4 pt-safe">
        <div className="flex items-center justify-between py-3">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-600">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-100">Lecturas</p>
              <p className="text-xs text-slate-500">{user?.nombre}</p>
            </div>
          </div>
          <div className="flex items-center">
            <a href={PLATAFORMA.capacitacion} target="_blank" rel="noopener" className="px-2 py-1 text-xs text-slate-500 hover:text-slate-300">
              Ayuda
            </a>
            <button onClick={() => setCambiarClave(true)} className="px-2 py-1 text-xs text-slate-500 hover:text-slate-300">
              Mi clave
            </button>
            <button
              onClick={() => {
                if (hayQueSubir && !window.confirm(`Hay ${porSincronizar.length} lectura(s) y ${fotosPorSubir.length} foto(s) sin sincronizar. Quedarán guardadas en este celular y se enviarán cuando vuelvas a ingresar. ¿Salir igual?`)) return
                logout()
              }}
              className="px-2 py-1 text-xs text-slate-500 hover:text-slate-300">
              Salir
            </button>
          </div>
        </div>

        {/* Conexión y sincronización */}
        <div className={`mb-3 flex items-center gap-2 rounded-lg px-3 py-2 text-xs ${enLinea ? 'bg-slate-800 text-slate-400' : 'bg-yellow-500/10 text-yellow-300'}`}>
          {enLinea ? <Wifi className="h-4 w-4 flex-shrink-0" /> : <CloudOff className="h-4 w-4 flex-shrink-0" />}
          <span className="flex-1">
            {enLinea ? 'Con conexión' : 'Sin conexión: las lecturas se guardan en el celular'}
            {porSincronizar.length > 0 && <> · <strong>{porSincronizar.length} sin sincronizar</strong></>}
            {fotosPorSubir.length > 0 && <> · <strong>{fotosPorSubir.length} {fotosPorSubir.length === 1 ? 'foto' : 'fotos'} por subir</strong></>}
            {!hayQueSubir && ultimaSync && <> · sincronizado {hora(ultimaSync)}</>}
          </span>
          {enLinea && hayQueSubir && (
            <button onClick={sincronizarAhora} disabled={!!ocupado}
                    className="flex items-center gap-1 rounded-md bg-primary-600 px-2 py-1 font-medium text-white disabled:opacity-50">
              {ocupado === 'sincronizando' ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <CloudUpload className="h-3.5 w-3.5" />}
              Sincronizar
            </button>
          )}
        </div>

        {aviso && (
          <div className="mb-3" onClick={cerrarAviso}>
            <Alert variant={aviso.tipo}>{aviso.texto}</Alert>
          </div>
        )}

        {boleta && (
          <div className="pb-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
                {boleta.tipo === 'lectura_inicial' ? `Lectura inicial · ${periodoCorto(boleta.periodo_mes)}` : periodoCorto(boleta.periodo_mes)}
              </p>
              <button onClick={preparar} disabled={!enLinea || !!ocupado || porSincronizar.length > 0}
                      title={porSincronizar.length ? 'Sincroniza primero las lecturas pendientes' : 'Descargar de nuevo el recorrido'}
                      className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 disabled:opacity-40">
                {ocupado === 'preparando' ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                Recorrido de las {hora(recorrido?.descargado_en ?? null)}
              </button>
            </div>
            <div className="mt-2 flex items-center gap-3">
              <div className="flex-1 overflow-hidden rounded-full bg-slate-700">
                <div className="h-2 rounded-full bg-primary-500 transition-all"
                     style={{ width: total > 0 ? `${(completadas / total) * 100}%` : '0%' }} />
              </div>
              <span className="text-sm font-bold tabular-nums text-slate-200">{completadas}/{total}</span>
            </div>
            {leidasSinFoto > 0 && (
              <p className="mt-1 flex items-center gap-1 text-xs text-slate-500">
                <CameraOff className="h-3.5 w-3.5" /> {leidasSinFoto} leída{leidasSinFoto === 1 ? '' : 's'} sin foto del medidor
              </p>
            )}
          </div>
        )}

        <div className="-mb-px flex gap-1">
          {(['pendientes', 'todas', ...(totalRevisar ? ['revisar'] : [])] as Filtro[]).map((f) => (
            <button key={f} onClick={() => setFiltro(f)}
              className={`flex-1 py-2.5 text-sm font-medium capitalize transition-colors ${
                filtro === f ? 'border-b-2 border-primary-500 text-primary-400' : 'text-slate-500'}`}>
              {f}
              {f === 'pendientes' && total - completadas > 0 && (
                <span className="ml-1.5 rounded-full bg-primary-600/20 px-1.5 py-0.5 text-xs text-primary-400">{total - completadas}</span>
              )}
              {f === 'revisar' && (
                <span className="ml-1.5 rounded-full bg-yellow-500/20 px-1.5 py-0.5 text-xs text-yellow-300">{totalRevisar}</span>
              )}
            </button>
          ))}
        </div>
      </header>

      <div className="flex-1 overflow-y-auto">
        {!cargado || (ocupado === 'preparando' && !recorrido) ? (
          <div className="flex h-48 items-center justify-center"><Spinner size="lg" className="text-primary-500" /></div>
        ) : !recorrido ? (
          <div className="flex h-56 flex-col items-center justify-center gap-3 px-6 text-center">
            <p className="text-slate-300">Aún no hay un recorrido en este celular</p>
            <p className="text-xs text-slate-500">Con señal, descarga las parcelas una vez para poder trabajar sin conexión.</p>
            <button onClick={preparar} disabled={!enLinea || !!ocupado}
                    className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
              <Download className="h-4 w-4" /> Preparar recorrido
            </button>
            {!enLinea && <p className="text-xs text-yellow-300">Necesitas conexión para este paso.</p>}
          </div>
        ) : !boleta ? (
          <div className="flex h-48 flex-col items-center justify-center gap-2 px-6 text-center">
            <p className="text-slate-400">Sin período activo</p>
            <p className="text-xs text-slate-600">El administrador debe crear una boleta</p>
          </div>
        ) : parcelasFiltradas.length === 0 ? (
          <div className="flex h-48 flex-col items-center justify-center gap-2">
            <CheckCircle2 className="h-10 w-10 text-primary-500" />
            <p className="font-medium text-slate-300">
              {filtro === 'revisar' ? 'Nada por revisar' : '¡Todas las lecturas completadas!'}
            </p>
            {filtro !== 'revisar' && hayQueSubir && (
              <p className="text-xs text-slate-500">Recuerda sincronizar cuando tengas señal.</p>
            )}
          </div>
        ) : (
          <ul className="divide-y divide-slate-700/50">
            {parcelasFiltradas.map((p) => {
              const enCelular = pendientePorParcela.get(p.id)
              const problema = revisarPorParcela.get(p.id)
              const fotoRechazada = fotoRechazadaPorParcela.get(p.id)
              const hecho = leida(p.id)
              return (
                <li key={p.id}>
                  <button disabled={boleta.lecturas_cerradas} onClick={() => capturar(p.id)}
                          className="flex w-full items-center gap-4 px-4 py-4 text-left transition-colors hover:bg-slate-800 active:bg-slate-700/50 disabled:opacity-50">
                    <div className={`flex-shrink-0 ${problema || fotoRechazada ? 'text-yellow-400' : hecho ? 'text-primary-500' : 'text-slate-600'}`}>
                      {problema || fotoRechazada ? <AlertTriangle className="h-7 w-7" /> : hecho ? <CheckCircle2 className="h-7 w-7" /> : <Circle className="h-7 w-7" />}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className={`text-lg font-bold ${hecho && !problema ? 'text-slate-400' : 'text-slate-100'}`}>Parcela {p.numero_parcela}</p>
                      {p.propietario_nombre && <p className="truncate text-sm text-slate-500">{p.propietario_nombre}</p>}
                      {enCelular && (
                        <p className="text-xs text-yellow-300">
                          {numero(enCelular.lectura_actual)} · en el celular, sin sincronizar
                        </p>
                      )}
                      {problema && (
                        <p className="text-xs text-yellow-300">
                          Tu lectura {numero(problema.lectura_actual)} no se aplicó: {problema.motivo}
                          {problema.vigente && <> (en el servidor: {numero(problema.vigente.lectura_actual)})</>}
                        </p>
                      )}
                      {fotoRechazada && !problema && (
                        <p className="text-xs text-yellow-300">La foto no se subió: {fotoRechazada.motivo}</p>
                      )}
                      {sinFoto(p.id) && !problema && (
                        <p className="flex items-center gap-1 text-xs text-slate-500"><CameraOff className="h-3 w-3" /> sin foto</p>
                      )}
                    </div>
                    {problema ? (
                      <span role="button" tabIndex={0}
                            onClick={(e) => { e.stopPropagation(); if (window.confirm('¿Descartar tu lectura y quedarte con la del servidor?')) descartar(problema.lectura_id) }}
                            className="flex-shrink-0 rounded-md border border-slate-600 px-2 py-1 text-xs text-slate-300">
                        Descartar
                      </span>
                    ) : fotoRechazada ? (
                      <span role="button" tabIndex={0}
                            onClick={(e) => { e.stopPropagation(); if (window.confirm('¿Descartar la foto guardada en el celular?')) descartarFoto(fotoRechazada.lectura_id) }}
                            className="flex-shrink-0 rounded-md border border-slate-600 px-2 py-1 text-xs text-slate-300">
                        Descartar foto
                      </span>
                    ) : !boleta.lecturas_cerradas && <ChevronRight className="h-5 w-5 flex-shrink-0 text-slate-600" />}
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
      <CambiarClaveModal open={cambiarClave} onClose={() => setCambiarClave(false)} />
    </div>
  )
}
