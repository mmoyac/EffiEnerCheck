import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { authApi } from '../api/auth'
import type { Sesion } from '../types'

interface AuthCtx {
  user: Sesion | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  /** Tras cambiar la clave: el token anterior ya no vale */
  actualizarToken: (token: string) => void
}

const AuthContext = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Sesion | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'))
  const [isLoading, setIsLoading] = useState(true)
  // Menús, módulos y datos dependen del usuario: no deben sobrevivir a un cambio de sesión
  const queryClient = useQueryClient()

  useEffect(() => {
    if (!token) { setIsLoading(false); return }
    authApi.me()
      .then(setUser)
      .catch(() => { localStorage.removeItem('token'); setToken(null) })
      .finally(() => setIsLoading(false))
  }, [token])

  const login = async (email: string, password: string) => {
    const { access_token } = await authApi.login(email, password)
    localStorage.setItem('token', access_token)
    queryClient.clear()
    setToken(access_token)
    const me = await authApi.me()
    setUser(me)
  }

  const actualizarToken = (nuevo: string) => {
    localStorage.setItem('token', nuevo)
    setToken(nuevo)
  }

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
    queryClient.clear()
  }

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout, actualizarToken }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuthContext() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuthContext must be inside AuthProvider')
  return ctx
}
