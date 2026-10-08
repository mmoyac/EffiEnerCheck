import { api } from './client'
import type { LecturaParcela } from '../types'

interface LecturaCreate {
  parcela_id: number
  boleta_id: number
  lectura_anterior: number
  lectura_actual: number
  /** ISO 8601. Marca la lectura como efectivamente tomada en terreno. */
  fecha_toma?: string
}

export const lecturasApi = {
  list: async (boletaId?: number): Promise<LecturaParcela[]> => {
    const params = boletaId ? { boleta_id: boletaId } : {}
    const { data } = await api.get<LecturaParcela[]>('/lecturas/', { params })
    return data
  },

  get: async (id: number): Promise<LecturaParcela> => {
    const { data } = await api.get<LecturaParcela>(`/lecturas/${id}`)
    return data
  },

  create: async (payload: LecturaCreate): Promise<LecturaParcela> => {
    const { data } = await api.post<LecturaParcela>('/lecturas/', payload)
    return data
  },

  update: async (id: number, payload: Partial<LecturaCreate>): Promise<LecturaParcela> => {
    const { data } = await api.patch<LecturaParcela>(`/lecturas/${id}`, payload)
    return data
  },

  /** La foto del medidor es privada: se pide con el token y se abre como blob (revocar la URL al cerrar). */
  verFoto: async (id: number): Promise<string> => {
    const { data } = await api.get<Blob>(`/lecturas/${id}/foto`, { responseType: 'blob' })
    return URL.createObjectURL(data)
  },
}
