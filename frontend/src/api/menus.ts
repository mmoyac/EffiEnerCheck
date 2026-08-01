import { api } from './client'
import type { MenuItem } from '../types'

export const menusApi = {
  me: async (): Promise<MenuItem[]> => {
    const { data } = await api.get<MenuItem[]>('/menus/me')
    return data
  },
}
