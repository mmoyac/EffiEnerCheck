import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Zap } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { Alert } from '../components/ui/Alert'

const ROLE_HOME: Record<string, string> = {
  super_admin:      '/dashboard',
  admin_condominio: '/dashboard',
  lector:           '/lecturas',
  parcelero:        '/liquidaciones',
}

export default function Login() {
  const { login, user } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  if (user) {
    navigate(ROLE_HOME[user.rol?.nombre] ?? '/dashboard', { replace: true })
    return null
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      // redirect happens via useEffect in AuthContext or re-render
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Credenciales incorrectas')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-600 shadow-lg shadow-primary-900/50">
            <Zap className="h-7 w-7 text-white" />
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-bold text-slate-100">EnerCheck</h1>
            <p className="text-sm text-slate-500">Condominio Santa Laura</p>
          </div>
        </div>

        {/* Form */}
        <div className="rounded-xl border border-slate-700 bg-slate-800 p-6 shadow-2xl">
          <h2 className="mb-6 text-lg font-semibold text-slate-100">Iniciar sesión</h2>

          {error && (
            <div className="mb-4">
              <Alert variant="error">{error}</Alert>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Correo electrónico"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="usuario@ejemplo.cl"
              required
              autoComplete="email"
            />
            <Input
              label="Contraseña"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              autoComplete="current-password"
            />
            <Button type="submit" fullWidth loading={loading} size="lg">
              Ingresar
            </Button>
          </form>
        </div>

        <p className="mt-4 text-center text-xs text-slate-600">
          EnerCheck v0.1 · Gestión eléctrica
        </p>
      </div>
    </div>
  )
}
