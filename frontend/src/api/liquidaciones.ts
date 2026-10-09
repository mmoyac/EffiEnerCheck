import { api } from './client'
import type { LiquidacionParcela } from '../types'

export const liquidacionesApi = {
  list: async (boletaId?: number): Promise<LiquidacionParcela[]> => {
    const params = boletaId ? { boleta_id: boletaId } : {}
    const { data } = await api.get<LiquidacionParcela[]>('/liquidaciones/', { params })
    return data
  },

  calcular: async (boletaId: number): Promise<LiquidacionParcela[]> => {
    const { data } = await api.post<LiquidacionParcela[]>(`/liquidaciones/calcular/${boletaId}`)
    return data
  },

  /** PDF del período: desglose de la boleta, una fila por parcela y el cuadre contra el total emisión */
  descargarPdf: async (boletaId: number, nombre: string): Promise<void> => {
    const { data } = await api.get<Blob>(`/liquidaciones/pdf/${boletaId}`, { responseType: 'blob' })
    const href = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = href
    a.download = nombre
    a.click()
    URL.revokeObjectURL(href)
  },
}
