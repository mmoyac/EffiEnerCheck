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

// Última sesión conocida: permite abrir la app sin señal (la sesión real la sigue validando el servidor)
const CLAVE_SESION = 'sesion'
function guardarSesion(s: Sesion) {
  try { localStorage.setItem(CLAVE_SESION, JSON.stringify(s)) } catch { /* sin almacenamiento: no es crítico */ }
}
function sesionGuardada(): Sesion | null {
  try { return JSON.parse(localStorage.getItem(CLAVE_SESION) ?? 'null') } catch { return null }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Sesion | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'))
  const [isLoading, setIsLoading] = useState(true)
  // Menús, módulos y datos dependen del usuario: no deben sobrevivir a un cambio de sesión
  const queryClient = useQueryClient()

  useEffect(() => {
    if (!token) { setIsLoading(false); return }
    authApi.me()
      .then((sesion) => { setUser(sesion); guardarSesion(sesion) })
      .catch((err: unknown) => {
        // Sin red (no hubo respuesta): se trabaja con la última sesión conocida, como en la app de lecturas
        // en terreno. Si el servidor respondió (401 u otro), la sesión ya no vale.
        const sinRespuesta = !(err as { response?: unknown })?.response
        const guardada = sinRespuesta ? sesionGuardada() : null
        if (guardada) { setUser(guardada); return }
        localStorage.removeItem('token'); localStorage.removeItem(CLAVE_SESION); setToken(null)
      })
      .finally(() => setIsLoading(false))
  }, [token])

  const login = async (email: string, password: string) => {
    const { access_token } = await authApi.login(email, password)
    localStorage.setItem('token', access_token)
    queryClient.clear()
    setToken(access_token)
    const me = await authApi.me()
    setUser(me)
    guardarSesion(me)
  }

  const actualizarToken = (nuevo: string) => {
    localStorage.setItem('token', nuevo)
    setToken(nuevo)
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem(CLAVE_SESION)
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
