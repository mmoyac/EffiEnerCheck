import { api } from './client'
import type { Usuario } from '../types'

interface UsuarioCreate {
  nombre: string
  email: string
  password: string
  rol_id: number
  condominio_id?: number
  parcela_ids?: number[]
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
}
