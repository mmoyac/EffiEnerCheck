import { api } from './client'
import type { Modulo } from '../config/modulos'

export type PlanSuscripcion = 'basico' | 'pro' | 'premium'

export interface Condominio {
  id: number
  nombre: string
  rut_comunidad: string
  direccion: string | null
  plan_suscripcion: PlanSuscripcion
  activo: boolean
  created_at: string | null
  // Parametrización comercial (solo la modifica el super_admin)
  modulos: Modulo[]
  portal_url: string | null
  dominios_sitio: string[]
  logo_url: string | null
  color_primario: string | null
}

export interface CondominioCreate {
  nombre: string
  rut_comunidad: string
  direccion?: string
  plan_suscripcion: PlanSuscripcion
  modulos?: Modulo[]
  portal_url?: string | null
  dominios_sitio?: string[]
  color_primario?: string | null
}

export type CondominioUpdate = Partial<Omit<CondominioCreate, 'rut_comunidad'>>

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

  update: async (id: number, payload: CondominioUpdate): Promise<Condominio> => {
    const { data } = await api.patch<Condominio>(`/condominios/${id}`, payload)
    return data
  },

  subirLogo: async (id: number, archivo: File): Promise<Condominio> => {
    const form = new FormData()
    form.append('archivo', archivo)
    const { data } = await api.post<Condominio>(`/condominios/${id}/logo`, form)
    return data
  },

  quitarLogo: async (id: number): Promise<Condominio> => {
    const { data } = await api.delete<Condominio>(`/condominios/${id}/logo`)
    return data
  },
}
