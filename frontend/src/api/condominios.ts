import { api } from './client'

export type PlanSuscripcion = 'basico' | 'pro' | 'premium'

export interface Condominio {
  id: number
  nombre: string
  rut_comunidad: string
  direccion: string | null
  plan_suscripcion: PlanSuscripcion
  activo: boolean
  created_at: string | null
}

export interface CondominioCreate {
  nombre: string
  rut_comunidad: string
  direccion?: string
  plan_suscripcion: PlanSuscripcion
}

export const condominiosApi = {
  list: async (): Promise<Condominio[]> => {
    const { data } = await api.get<Condominio[]>('/condominios/')
    return data
  },

  get: async (id: number): Promise<Condominio> => {
    const { data } = await api.get<Condominio>(`/condominios/${id}`)
    return data
  },

  create: async (payload: CondominioCreate): Promise<Condominio> => {
    const { data } = await api.post<Condominio>('/condominios/', payload)
    return data
  },

  update: async (id: number, payload: Partial<CondominioCreate>): Promise<Condominio> => {
    const { data } = await api.patch<Condominio>(`/condominios/${id}`, payload)
    return data
  },
}
