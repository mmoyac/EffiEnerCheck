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

  marcarPago: async (
    id: number,
    pagado: boolean,
    fechaPago?: string,
  ): Promise<LiquidacionParcela> => {
    const { data } = await api.patch<LiquidacionParcela>(`/liquidaciones/${id}/pago`, {
      pagado,
      fecha_pago: fechaPago ?? null,
    })
    return data
  },
}
