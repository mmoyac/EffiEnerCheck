/**
 * Lecturas sin conexión (cambio lecturas-sin-conexion).
 *
 * - `recorrido`: lo que se descargó con señal (período, parcelas activas y lecturas como BASE).
 * - `pendientes`: lecturas tomadas en el celular que el servidor todavía no confirma. Una pendiente
 *   nunca se borra hasta que el servidor responde `aplicada`. La base que viaja es la descargada:
 *   así el servidor detecta si alguien cambió la lectura mientras tanto (conflicto) y no la pisa.
 *
 * Todo vive en IndexedDB: sobrevive a recargas, al cierre de sesión y al vencimiento del token.
 */
import { openDB, type DBSchema, type IDBPDatabase } from 'idb'
import { api } from '../api/client'
import { boletasApi } from '../api/boletas'
import { lecturasApi } from '../api/lecturas'
import { parcelasApi } from '../api/parcelas'
import type { BoletaMaestra, LecturaParcela, Parcela } from '../types'

export interface Recorrido {
  clave: 'actual'
  condominio_id: number | null
  boleta: Pick<BoletaMaestra, 'id' | 'periodo_mes' | 'lecturas_cerradas'> | null
  parcelas: Parcela[]
  lecturas: LecturaParcela[]
  descargado_en: string
}

export interface Pendiente {
  lectura_id: number
  parcela_id: number
  boleta_id: number
  lectura_actual: number
  fecha_toma: string
  base: { lectura_actual: number; fecha_toma: string | null }
  estado: 'pendiente' | 'conflicto' | 'rechazada'
  motivo?: string
  /** La lectura vigente en el servidor, cuando quedó en conflicto o rechazada */
  vigente?: LecturaParcela
}

interface Esquema extends DBSchema {
  recorrido: { key: 'actual'; value: Recorrido }
  pendientes: { key: number; value: Pendiente }
}

let conexion: Promise<IDBPDatabase<Esquema>> | null = null
function db() {
  conexion ??= openDB<Esquema>('efficomunidad-lecturas', 1, {
    upgrade(d) {
      d.createObjectStore('recorrido', { keyPath: 'clave' })
      d.createObjectStore('pendientes', { keyPath: 'lectura_id' })
    },
  })
  return conexion
}

// ---- Avisos de cambios (las pantallas se suscriben) ------------------------------------------------------

const oyentes = new Set<() => void>()
export function suscribir(fn: () => void) {
  oyentes.add(fn)
  return () => { oyentes.delete(fn) }
}
const avisar = () => oyentes.forEach((fn) => fn())

// ---- Recorrido -------------------------------------------------------------------------------------------

export async function leerRecorrido(): Promise<Recorrido | undefined> {
  return (await db()).get('recorrido', 'actual')
}

/** Con señal: descarga el período abierto, las parcelas activas y sus lecturas, y las guarda en el celular. */
export async function prepararRecorrido(condominioId: number | null): Promise<Recorrido> {
  const [boletas, parcelas] = await Promise.all([boletasApi.list(), parcelasApi.list()])
  const boleta = boletas.filter((b) => !b.lecturas_cerradas).at(-1) ?? boletas.at(-1) ?? null
  const lecturas = boleta ? await lecturasApi.list(boleta.id) : []
  const recorrido: Recorrido = {
    clave: 'actual',
    condominio_id: condominioId,
    boleta: boleta && { id: boleta.id, periodo_mes: boleta.periodo_mes, lecturas_cerradas: boleta.lecturas_cerradas },
    parcelas: parcelas.filter((p) => p.activa),
    lecturas,
    descargado_en: new Date().toISOString(),
  }
  await (await db()).put('recorrido', recorrido)
  avisar()
  return recorrido
}

// ---- Pendientes ------------------------------------------------------------------------------------------

export async function listarPendientes(): Promise<Pendiente[]> {
  return (await db()).getAll('pendientes')
}

/**
 * Guarda una lectura tomada en el celular. Si la parcela ya tenía una pendiente, se reemplaza el valor
 * pero se conserva la base original (la descargada), para que la detección de conflictos siga siendo válida.
 */
export async function guardarPendiente(lectura: LecturaParcela, valor: number): Promise<void> {
  const d = await db()
  const previa = await d.get('pendientes', lectura.id)
  const base = previa?.estado === 'pendiente'
    ? previa.base
    // tras un conflicto se vuelve a capturar sobre la lectura vigente del servidor
    : { lectura_actual: (previa?.vigente ?? lectura).lectura_actual, fecha_toma: (previa?.vigente ?? lectura).fecha_toma }
  await d.put('pendientes', {
    lectura_id: lectura.id,
    parcela_id: lectura.parcela_id,
    boleta_id: lectura.boleta_id,
    lectura_actual: valor,
    fecha_toma: new Date().toISOString(),
    base,
    estado: 'pendiente',
  })
  avisar()
}

/** Descarta una lectura del celular (p. ej. tras un conflicto, si vale la del servidor). */
export async function descartar(lecturaId: number): Promise<void> {
  await (await db()).delete('pendientes', lecturaId)
  avisar()
}

// ---- Sincronización --------------------------------------------------------------------------------------

export class SesionVencida extends Error {}
export class OtroCondominio extends Error {}

interface Resultado {
  lectura_id: number
  estado: 'aplicada' | 'conflicto' | 'rechazada'
  motivo: string | null
  lectura: LecturaParcela | null
}

let sincronizando: Promise<{ aplicadas: number; conProblemas: number }> | null = null

/**
 * Envía las lecturas pendientes. Una sola sincronización a la vez. Sin red no hace nada (quedan para después).
 * Aplicadas: se borran del celular y actualizan la base del recorrido. Conflicto o rechazo: quedan para revisión.
 */
export function sincronizar(condominioId: number | null): Promise<{ aplicadas: number; conProblemas: number }> {
  sincronizando ??= (async () => {
    try {
      const d = await db()
      const pendientes = (await d.getAll('pendientes')).filter((p) => p.estado === 'pendiente')
      if (!pendientes.length || !navigator.onLine) return { aplicadas: 0, conProblemas: 0 }
      // Las pendientes solo se envían con la sesión de alguien del mismo condominio que las tomó
      const recorrido = await d.get('recorrido', 'actual')
      if (recorrido && recorrido.condominio_id !== condominioId) throw new OtroCondominio()

      let resultados: Resultado[]
      try {
        const { data } = await api.post<{ resultados: Resultado[] }>('/lecturas/sincronizar', {
          items: pendientes.map(({ lectura_id, lectura_actual, fecha_toma, base }) => ({
            lectura_id, lectura_actual, fecha_toma, base,
          })),
        })
        resultados = data.resultados
      } catch (err: unknown) {
        if ((err as { response?: { status?: number } })?.response?.status === 401) throw new SesionVencida()
        throw err
      }

      let aplicadas = 0
      let conProblemas = 0
      const tx = d.transaction(['pendientes', 'recorrido'], 'readwrite')
      const rec = await tx.objectStore('recorrido').get('actual')
      for (const r of resultados) {
        const p = await tx.objectStore('pendientes').get(r.lectura_id)
        if (!p) continue
        if (r.estado === 'aplicada') {
          aplicadas++
          await tx.objectStore('pendientes').delete(r.lectura_id)
        } else {
          conProblemas++
          await tx.objectStore('pendientes').put({ ...p, estado: r.estado, motivo: r.motivo ?? undefined, vigente: r.lectura ?? undefined })
        }
        // La base del recorrido pasa a ser lo que hay en el servidor
        if (rec && r.lectura) rec.lecturas = rec.lecturas.map((l) => (l.id === r.lectura_id ? r.lectura! : l))
      }
      if (rec) await tx.objectStore('recorrido').put(rec)
      await tx.done
      avisar()
      return { aplicadas, conProblemas }
    } finally {
      sincronizando = null
    }
  })()
  return sincronizando
}
