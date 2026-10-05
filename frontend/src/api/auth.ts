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
}
