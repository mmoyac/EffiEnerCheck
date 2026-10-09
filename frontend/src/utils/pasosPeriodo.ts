import type { BoletaMaestra } from '../types'

/**
 * Pasos del ciclo de un período (cambio pasos-del-periodo): cuáles están hechos y cuál sigue.
 * Solo presentación: las reglas del ciclo las impone el backend.
 */
export type ClavePaso =
  | 'datos' | 'corroborar' | 'lecturas' | 'cerrar_lecturas' | 'calcular' | 'cerrar_periodo' | 'publicar' | 'listo'

export interface Paso {
  clave: ClavePaso
  titulo: string
  hecho: boolean
  detalle?: string
}

export interface EstadoPasos {
  pasos: Paso[]
  siguiente: ClavePaso
  /** Explicación en una línea del siguiente paso */
  ayuda: string
  /** El siguiente paso depende del lector: no hay acción que destacar */
  esperaLector: boolean
}

interface Datos {
  boleta: BoletaMaestra
  tomadas: number
  total: number
  liquidaciones: number
}

export function pasosDelPeriodo({ boleta, tomadas, total, liquidaciones }: Datos): EstadoPasos {
  const lecturasCompletas = total > 0 && tomadas >= total
  const avance = `${tomadas} de ${total}`

  if (boleta.tipo === 'lectura_inicial') {
    const pasos: Paso[] = [
      { clave: 'lecturas', titulo: 'Lecturas de partida', hecho: lecturasCompletas || boleta.lecturas_cerradas, detalle: avance },
      { clave: 'cerrar_lecturas', titulo: 'Cerrar lecturas', hecho: boleta.lecturas_cerradas },
      { clave: 'listo', titulo: 'Lista para la primera boleta', hecho: boleta.lecturas_cerradas },
    ]
    if (boleta.lecturas_cerradas) {
      return { pasos, siguiente: 'listo', esperaLector: false,
               ayuda: 'Lectura inicial cerrada. Ya puedes generar la primera boleta desde Boletas.' }
    }
    if (!lecturasCompletas) {
      return { pasos, siguiente: 'lecturas', esperaLector: true,
               ayuda: `Registra la lectura de partida de cada medidor (${avance}): con la app del lector o desde Excel.` }
    }
    return { pasos, siguiente: 'cerrar_lecturas', esperaLector: false,
             ayuda: `Están las ${total} lecturas de partida. Ciérralas para dejar lista la primera boleta.` }
  }

  const datos = boleta.total_kwh_compania != null && boleta.monto_neto_electricidad_consumida != null
    && boleta.monto_total_emision != null
  const corroborado = boleta.estado === 'validada' || boleta.estado === 'publicada'
  const calculado = liquidaciones > 0
  const pasos: Paso[] = [
    { clave: 'datos', titulo: 'Datos de la boleta', hecho: datos },
    { clave: 'corroborar', titulo: 'Corroborar desglose', hecho: corroborado },
    { clave: 'cerrar_lecturas', titulo: 'Lecturas', hecho: boleta.lecturas_cerradas, detalle: avance },
    { clave: 'calcular', titulo: 'Calcular', hecho: calculado || boleta.liquidaciones_cerradas },
    { clave: 'cerrar_periodo', titulo: 'Cerrar período', hecho: boleta.liquidaciones_cerradas },
    { clave: 'publicar', titulo: 'Publicar', hecho: boleta.boleta_visible_usuarios },
  ]

  const r = (siguiente: ClavePaso, ayuda: string, esperaLector = false): EstadoPasos =>
    ({ pasos, siguiente, ayuda, esperaLector })

  if (boleta.boleta_visible_usuarios) return r('listo', 'Período publicado: cada comunero ya ve su liquidación.')
  if (boleta.liquidaciones_cerradas) {
    return r('publicar', 'Publica para que cada comunero vea su liquidación. Después ya no se puede reabrir.')
  }
  if (!datos) {
    return r('datos', 'Ingresa los 3 totales de la boleta (kWh compañía, monto neto y total emisión): súbela en la pestaña Boleta o ingrésala a mano.')
  }
  if (!corroborado) {
    return r('corroborar', 'Revisa los conceptos y su tipo (fijo, variable, informativo) y confírmalos con «Corroborar desglose».')
  }
  if (!boleta.lecturas_cerradas) {
    if (!lecturasCompletas) {
      return r('cerrar_lecturas', `El lector está tomando las lecturas: ${avance}. Cuando estén todas, ciérralas.`, true)
    }
    return r('cerrar_lecturas', `Las ${total} lecturas están tomadas. Ciérralas para certificar el recorrido.`)
  }
  if (!calculado) return r('calcular', 'Calcula cuánto paga cada parcela. Puedes recalcular las veces que necesites.')
  return r('cerrar_periodo', 'Revisa las liquidaciones en su pestaña y cierra el período. Si algo cambia, se descartan solas y habrá que recalcular.')
}
