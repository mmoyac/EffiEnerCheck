import { api } from './client'
import type { Invitacion, Usuario } from '../types'

interface UsuarioCreate {
  nombre: string
  email: string
  /** Sin contraseña la cuenta queda pendiente y se invita */
  password?: string
  rol_id: number
  condominio_id?: number
  parcela_ids?: number[]
  telefono?: string | null
}

export const usuariosApi = {
  list: async (): Promise<Usuario[]> => {
    const { data } = await api.get<Usuario[]>('/usuarios/')
    return data
  },

  get: async (id: number): Promise<Usuario> => {
    const { data } = await api.get<Usuario>(`/usuarios/${id}`)
    return data
  },

  create: async (payload: UsuarioCreate): Promise<Usuario> => {
    const { data } = await api.post<Usuario>('/usuarios/', payload)
    return data
  },

  update: async (id: number, payload: Partial<UsuarioCreate>): Promise<Usuario> => {
    const { data } = await api.patch<Usuario>(`/usuarios/${id}`, payload)
    return data
  },

  invitar: async (id: number): Promise<Invitacion> => {
    const { data } = await api.post<Invitacion>(`/usuarios/${id}/invitacion`)
    return data
  },

  /** Invita por correo a todos los pendientes del condominio (super_admin: indicar condominio) */
  invitarPendientes: async (condominio_id?: number): Promise<{ enviados: number; fallidos: number; pendientes: number; limite_alcanzado: boolean }> => {
    const { data } = await api.post('/usuarios/invitaciones', { condominio_id })
    return data
  },
}
