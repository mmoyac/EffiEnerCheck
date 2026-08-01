import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { authApi } from '../api/auth'
import type { Usuario } from '../types'

interface AuthCtx {
  user: Usuario | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Usuario | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'))
  const [isLoading, setIsLoading] = useState(true)

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
    setToken(access_token)
    const me = await authApi.me()
    setUser(me)
  }

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuthContext() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuthContext must be inside AuthProvider')
  return ctx
}
