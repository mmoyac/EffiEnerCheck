import { api } from './client'
import type { Sesion, TokenResponse } from '../types'

export const authApi = {
  login: async (email: string, password: string): Promise<TokenResponse> => {
    const form = new URLSearchParams()
    form.append('username', email)
    form.append('password', password)
    const { data } = await api.post<TokenResponse>('/auth/token', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return data
  },

  me: async (): Promise<Sesion> => {
    const { data } = await api.get<Sesion>('/auth/me')
    return data
  },

  /** Siempre responde lo mismo, exista o no la cuenta */
  recuperar: async (email: string): Promise<void> => {
    await api.post('/auth/recuperar', { email })
  },

  /** El token va en el cuerpo, nunca en la URL (spec acceso-por-enlace) */
  verificarEnlace: async (token: string): Promise<{ tipo: 'invitacion' | 'recuperacion'; nombre: string }> => {
    const { data } = await api.post('/auth/verificar-enlace', { token })
    return data
  },

  establecerClave: async (token: string, password: string): Promise<void> => {
    await api.post('/auth/establecer-clave', { token, password })
  },

  /** Devuelve un token nuevo: el anterior deja de valer al cambiar la clave */
  cambiarClave: async (actual: string, nueva: string): Promise<TokenResponse> => {
    const { data } = await api.post<TokenResponse>('/auth/cambiar-clave', { actual, nueva })
    return data
  },
}
