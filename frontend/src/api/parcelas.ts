import { api } from './client'
import type { Parcela } from '../types'

interface ParcelaCreate {
  condominio_id: number
  numero_parcela: string
  propietario_nombre?: string
  activa?: boolean
}

export const parcelasApi = {
  list: async (): Promise<Parcela[]> => {
    const { data } = await api.get<Parcela[]>('/parcelas/')
    return data
  },

  get: async (id: number): Promise<Parcela> => {
    const { data } = await api.get<Parcela>(`/parcelas/${id}`)
    return data
  },

  create: async (payload: ParcelaCreate): Promise<Parcela> => {
    const { data } = await api.post<Parcela>('/parcelas/', payload)
    return data
  },

  update: async (id: number, payload: Partial<ParcelaCreate>): Promise<Parcela> => {
    const { data } = await api.patch<Parcela>(`/parcelas/${id}`, payload)
    return data
  },
}
