import { api } from './client'
import type { BoletaMaestra, BoletaMaestraCreate } from '../types'

export const boletasApi = {
  list: async (): Promise<BoletaMaestra[]> => {
    const { data } = await api.get<BoletaMaestra[]>('/boletas/')
    return data
  },

  get: async (id: number): Promise<BoletaMaestra> => {
    const { data } = await api.get<BoletaMaestra>(`/boletas/${id}`)
    return data
  },

  create: async (payload: BoletaMaestraCreate): Promise<BoletaMaestra> => {
    const { data } = await api.post<BoletaMaestra>('/boletas/', payload)
    return data
  },

  update: async (id: number, payload: Partial<BoletaMaestra>): Promise<BoletaMaestra> => {
    const { data } = await api.patch<BoletaMaestra>(`/boletas/${id}`, payload)
    return data
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/boletas/${id}`)
  },

  procesarOcr: async (id: number): Promise<BoletaMaestra> => {
    const { data } = await api.post<BoletaMaestra>(`/boletas/${id}/procesar-ocr`)
    return data
  },

  updateDetalles: async (id: number, payload: any): Promise<BoletaMaestra> => {
    const { data } = await api.put<BoletaMaestra>(`/boletas/${id}/detalles`, payload)
    return data
  },

  /** El admin corrobora el desglose: borrador → validada. Habilita el cálculo. */
  validarItems: async (id: number): Promise<BoletaMaestra> => {
    const { data } = await api.post<BoletaMaestra>(`/boletas/${id}/validar-items`)
    return data
  },

  cerrarLecturas: async (id: number): Promise<BoletaMaestra> => {
    const { data } = await api.post<BoletaMaestra>(`/boletas/${id}/cerrar-lecturas`)
    return data
  },

  reabrirLecturas: async (id: number): Promise<BoletaMaestra> => {
    const { data } = await api.post<BoletaMaestra>(`/boletas/${id}/reabrir-lecturas`)
    return data
  },

  cerrarLiquidaciones: async (id: number): Promise<BoletaMaestra> => {
    const { data } = await api.post<BoletaMaestra>(`/boletas/${id}/cerrar-liquidaciones`)
    return data
  },

  reabrirLiquidaciones: async (id: number): Promise<BoletaMaestra> => {
    const { data } = await api.post<BoletaMaestra>(`/boletas/${id}/reabrir-liquidaciones`)
    return data
  },

  uploadImagen: async (id: number, file: File): Promise<BoletaMaestra> => {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post<BoletaMaestra>(`/boletas/${id}/imagen`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  ocr: async (file: File): Promise<Record<string, unknown>> => {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post('/boletas/ocr', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },
}
