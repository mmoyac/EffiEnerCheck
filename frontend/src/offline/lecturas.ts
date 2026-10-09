/**
 * Lecturas sin conexión (cambio lecturas-sin-conexion).
 *
 * - `recorrido`: lo que se descargó con señal (período, parcelas activas y lecturas como BASE).
 * - `pendientes`: lecturas tomadas en el celular que el servidor todavía no confirma. Una pendiente
 *   nunca se borra hasta que el servidor responde `aplicada`. La base que viaja es la descargada:
 *   así el servidor detecta si alguien cambió la lectura mientras tanto (conflicto) y no la pisa.
 *
 * - `fotos`: foto del medidor por lectura (cambio foto-medidor), amarrada a la `fecha_toma` de la toma que
 *   documenta. Se sube después de que su lectura quedó aplicada y no se borra hasta que el servidor la recibe.
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
  /** `tipo` falta en recorridos descargados antes del cambio lectura-inicial: se trata como regular */
  boleta: (Pick<BoletaMaestra, 'id' | 'periodo_mes' | 'lecturas_cerradas'> & { tipo?: BoletaMaestra['tipo'] }) | null
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

export interface FotoPendiente {
  lectura_id: number
  parcela_id: number
  /** La toma que documenta la foto: el servidor solo la acepta si sigue vigente */
  fecha_toma: string
  blob: Blob
  estado: 'pendiente' | 'rechazada'
  motivo?: string
}

interface Esquema extends DBSchema {
  recorrido: { key: 'actual'; value: Recorrido }
  pendientes: { key: number; value: Pendiente }
  fotos: { key: number; value: FotoPendiente }
}

let conexion: Promise<IDBPDatabase<Esquema>> | null = null
function db() {
  conexion ??= openDB<Esquema>('efficomunidad-lecturas', 2, {
    upgrade(d, versionAnterior) {
      if (versionAnterior < 1) {
        d.createObjectStore('recorrido', { keyPath: 'clave' })
        d.createObjectStore('pendientes', { keyPath: 'lectura_id' })
      }
      // v2 (foto-medidor): solo se agrega el almacén; los pendientes existentes no se tocan
      if (versionAnterior < 2) d.createObjectStore('fotos', { keyPath: 'lectura_id' })
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
    boleta: boleta && { id: boleta.id, periodo_mes: boleta.periodo_mes, lecturas_cerradas: boleta.lecturas_cerradas, tipo: boleta.tipo },
    parcelas: parcelas.filter((p) => p.activa),
    lecturas,
    descargado_en: new Date().toISOString(),
  }
  // Pide que el navegador no purgue los datos del recorrido (fotos incluidas) por falta de espacio
  navigator.storage?.persist?.().catch(() => {})
  await (await db()).put('recorrido', recorrido)
  avisar()
  return recorrido
}

// ---- Pendientes ------------------------------------------------------------------------------------------

export async function listarPendientes(): Promise<Pendiente[]> {
  return (await db()).getAll('pendientes')
}

/**
 * Guarda una lectura tomada en el celular, con su foto del medidor si la hay (misma `fecha_toma`).
 * Si la parcela ya tenía una pendiente, se reemplaza el valor pero se conserva la base original (la
 * descargada), para que la detección de conflictos siga siendo válida. `foto` null quita la foto.
 */
export async function guardarPendiente(lectura: LecturaParcela, valor: number, foto: Blob | null = null): Promise<void> {
  const tx = (await db()).transaction(['pendientes', 'fotos'], 'readwrite')
  const previa = await tx.objectStore('pendientes').get(lectura.id)
  const base = previa?.estado === 'pendiente'
    ? previa.base
    // tras un conflicto se vuelve a capturar sobre la lectura vigente del servidor
    : { lectura_actual: (previa?.vigente ?? lectura).lectura_actual, fecha_toma: (previa?.vigente ?? lectura).fecha_toma }
  const fecha_toma = new Date().toISOString()
  await tx.objectStore('pendientes').put({
    lectura_id: lectura.id,
    parcela_id: lectura.parcela_id,
    boleta_id: lectura.boleta_id,
    lectura_actual: valor,
    fecha_toma,
    base,
    estado: 'pendiente',
  })
  if (foto) {
    await tx.objectStore('fotos').put({
      lectura_id: lectura.id, parcela_id: lectura.parcela_id, fecha_toma, blob: foto, estado: 'pendiente',
    })
  } else {
    await tx.objectStore('fotos').delete(lectura.id)
  }
  await tx.done
  avisar()
}

/** Agrega (o reemplaza) la foto de una lectura ya sincronizada, sin tocar su valor: se amarra a su toma vigente. */
export async function guardarFotoDeLectura(lectura: LecturaParcela, foto: Blob): Promise<void> {
  if (!lectura.fecha_toma) throw new Error('La lectura aún no se ha tomado')
  await (await db()).put('fotos', {
    lectura_id: lectura.id, parcela_id: lectura.parcela_id, fecha_toma: lectura.fecha_toma, blob: foto, estado: 'pendiente',
  })
  avisar()
}

export async function listarFotos(): Promise<FotoPendiente[]> {
  return (await db()).getAll('fotos')
}

export async function leerFoto(lecturaId: number): Promise<FotoPendiente | undefined> {
  return (await db()).get('fotos', lecturaId)
}

/** Descarta una lectura del celular (p. ej. tras un conflicto, si vale la del servidor), con su foto. */
export async function descartar(lecturaId: number): Promise<void> {
  const tx = (await db()).transaction(['pendientes', 'fotos'], 'readwrite')
  await tx.objectStore('pendientes').delete(lecturaId)
  await tx.objectStore('fotos').delete(lecturaId)
  await tx.done
  avisar()
}

/** Descarta solo la foto (p. ej. si el servidor la rechazó). */
export async function descartarFoto(lecturaId: number): Promise<void> {
  await (await db()).delete('fotos', lecturaId)
  avisar()
}

// ---- Foto del medidor ------------------------------------------------------------------------------------

const LADO_MAXIMO = 1600

export class FotoIlegible extends Error {}

/** «09-10-2026 10:35» en hora de Chile */
const fechaHoraFoto = (fecha: Date) =>
  fecha.toLocaleString('es-CL', {
    timeZone: 'America/Santiago', day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).replace(',', '')

/**
 * Reduce la foto de la cámara (lado mayor 1600 px) y la reencodea en JPEG. El canvas descarta el EXIF,
 * incluida la ubicación GPS. ~200–400 KB por foto.
 *
 * Debajo de la imagen (sin tapar el medidor) agrega una franja con `leyenda` (p. ej. «Parcela 23») y la
 * fecha y hora en que se sacó la foto: la marca de tiempo del archivo, o el momento de la captura si no la
 * trae. Queda quemada en la imagen como evidencia; una foto vieja de la galería se nota por su fecha.
 */
export async function procesarFoto(archivo: File, leyenda = ''): Promise<Blob> {
  let imagen: ImageBitmap
  try {
    imagen = await createImageBitmap(archivo, { imageOrientation: 'from-image' })
  } catch {
    throw new FotoIlegible()
  }
  const escala = Math.min(1, LADO_MAXIMO / Math.max(imagen.width, imagen.height))
  const ancho = Math.round(imagen.width * escala)
  const alto = Math.round(imagen.height * escala)
  const franja = Math.max(28, Math.round(Math.max(ancho, alto) * 0.045))
  const canvas = document.createElement('canvas')
  canvas.width = ancho
  canvas.height = alto + franja
  const ctx = canvas.getContext('2d')!
  ctx.drawImage(imagen, 0, 0, ancho, alto)
  imagen.close()

  const sacada = archivo.lastModified > 0 && archivo.lastModified <= Date.now() + 60_000
    ? new Date(archivo.lastModified) : new Date()
  const texto = [leyenda, fechaHoraFoto(sacada)].filter(Boolean).join(' · ')
  ctx.fillStyle = '#0f172a'
  ctx.fillRect(0, alto, ancho, franja)
  let tamano = Math.round(franja * 0.55)
  ctx.font = `600 ${tamano}px system-ui, sans-serif`
  while (tamano > 8 && ctx.measureText(texto).width > ancho - 12) {   // que quepa en fotos angostas
    tamano -= 1
    ctx.font = `600 ${tamano}px system-ui, sans-serif`
  }
  ctx.fillStyle = '#ffffff'
  ctx.textBaseline = 'middle'
  ctx.fillText(texto, 6, alto + franja / 2)
  const blob = await new Promise<Blob | null>((ok) => canvas.toBlob(ok, 'image/jpeg', 0.7))
  if (!blob) throw new FotoIlegible()
  return blob
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

export interface ResultadoSync {
  aplicadas: number
  conProblemas: number
  fotosSubidas: number
  fotosConProblemas: number
}

let sincronizando: Promise<ResultadoSync> | null = null

/**
 * Envía las lecturas pendientes y después las fotos. Una sola sincronización a la vez. Sin red no hace
 * nada (quedan para después). Aplicadas: se borran del celular y actualizan la base del recorrido.
 * Conflicto o rechazo: quedan para revisión.
 */
export function sincronizar(condominioId: number | null): Promise<ResultadoSync> {
  sincronizando ??= (async () => {
    try {
      const d = await db()
      const nada: ResultadoSync = { aplicadas: 0, conProblemas: 0, fotosSubidas: 0, fotosConProblemas: 0 }
      if (!navigator.onLine) return nada
      const pendientes = (await d.getAll('pendientes')).filter((p) => p.estado === 'pendiente')
      const fotos = (await d.getAll('fotos')).filter((f) => f.estado === 'pendiente')
      if (!pendientes.length && !fotos.length) return nada
      // Lo pendiente solo se envía con la sesión de alguien del mismo condominio que lo tomó
      const recorrido = await d.get('recorrido', 'actual')
      if (recorrido && recorrido.condominio_id !== condominioId) throw new OtroCondominio()
      const lecturas = pendientes.length ? await enviarLecturas(d, pendientes) : { aplicadas: 0, conProblemas: 0 }
      return { ...lecturas, ...(await enviarFotos(d)) }
    } finally {
      sincronizando = null
    }
  })()
  return sincronizando
}

async function enviarLecturas(d: IDBPDatabase<Esquema>, pendientes: Pendiente[]) {
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
}

/**
 * Sube una por una las fotos cuya lectura ya no está pendiente en el celular (aplicada, o foto agregada a
 * una lectura ya sincronizada). La de una lectura sin enviar, en conflicto o rechazada espera.
 * Sin respuesta (señal mala): se detiene y queda para la próxima sincronización.
 */
/** Motivo legible de un rechazo: el texto del servidor o, en un error de validación, el campo y su problema. */
function motivoDe(status: number | undefined, detalle: unknown): string {
  if (typeof detalle === 'string') return detalle
  if (Array.isArray(detalle) && detalle.length) {
    return detalle.map((e: { loc?: unknown[]; msg?: string }) => `${e.loc?.at(-1) ?? 'dato'}: ${e.msg ?? 'inválido'}`).join(' · ')
  }
  return `El servidor no aceptó la foto (código ${status ?? '?'})`
}

async function enviarFotos(d: IDBPDatabase<Esquema>) {
  let fotosSubidas = 0
  let fotosConProblemas = 0
  const conLecturaPendiente = new Set(await d.getAllKeys('pendientes'))
  const fotos = (await d.getAll('fotos')).filter((f) => f.estado === 'pendiente' && !conLecturaPendiente.has(f.lectura_id))
  const recorrido = await d.get('recorrido', 'actual')
  for (const foto of fotos) {
    // Una foto sin la fecha de su toma se amarra a la toma vigente de su lectura en el recorrido
    const fechaToma = foto.fecha_toma || recorrido?.lecturas.find((l) => l.id === foto.lectura_id)?.fecha_toma
    if (!fechaToma) {
      fotosConProblemas++
      await d.put('fotos', { ...foto, estado: 'rechazada', motivo: 'La lectura de esta foto aún no está tomada' })
      continue
    }
    const form = new FormData()
    form.append('foto', foto.blob, 'medidor.jpg')
    form.append('fecha_toma', fechaToma)
    try {
      const { data } = await api.put<LecturaParcela>(`/lecturas/${foto.lectura_id}/foto`, form)
      fotosSubidas++
      const tx = d.transaction(['fotos', 'recorrido'], 'readwrite')
      // Solo se borra si nadie la retomó mientras subía
      const actual = await tx.objectStore('fotos').get(foto.lectura_id)
      if (actual && actual.fecha_toma === foto.fecha_toma && actual.blob.size === foto.blob.size) {
        await tx.objectStore('fotos').delete(foto.lectura_id)
      }
      const rec = await tx.objectStore('recorrido').get('actual')
      if (rec) {
        rec.lecturas = rec.lecturas.map((l) => (l.id === data.id ? data : l))
        await tx.objectStore('recorrido').put(rec)
      }
      await tx.done
    } catch (err: unknown) {
      const respuesta = (err as { response?: { status?: number; data?: { detail?: unknown } } })?.response
      if (!respuesta) break
      if (respuesta.status === 401) throw new SesionVencida()
      fotosConProblemas++
      await d.put('fotos', { ...foto, estado: 'rechazada', motivo: motivoDe(respuesta.status, respuesta.data?.detail) })
    }
  }
  avisar()
  return { fotosSubidas, fotosConProblemas }
}
