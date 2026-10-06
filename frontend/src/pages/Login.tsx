import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { Alert } from '../components/ui/Alert'
import { Modal } from '../components/ui/Modal'
import { authApi } from '../api/auth'
import { pantallaDeInicio } from '../config/inicio'
import { IconoPlataforma, PLATAFORMA } from '../config/marca'

export default function Login() {
  const { login, user } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [recuperar, setRecuperar] = useState(false)

  if (user) {
    navigate(pantallaDeInicio(user.rol?.nombre, user.modulos), { replace: true })
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
            <IconoPlataforma className="h-7 w-7 text-white" />
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-bold text-slate-100">{PLATAFORMA.nombre}</h1>
            <p className="text-sm text-slate-500">{PLATAFORMA.lema}</p>
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
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              autoComplete="current-password"
              rightElement={
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="rounded p-1 text-slate-400 transition-colors hover:text-slate-200 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  title={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              }
            />
            <Button type="submit" fullWidth loading={loading} size="lg">
              Ingresar
            </Button>
          </form>
          <button
            type="button"
            onClick={() => setRecuperar(true)}
            className="mt-4 w-full text-center text-sm text-slate-400 transition-colors hover:text-primary-400"
          >
            ¿Olvidaste tu clave? ¿Primera vez?
          </button>
        </div>
        <RecuperarClaveModal open={recuperar} onClose={() => setRecuperar(false)} emailInicial={email} />

        <p className="mt-4 text-center text-xs text-slate-600">
          Desarrollado por{' '}
          <a
            href="https://effi4tech.cl"
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-slate-400 transition-colors hover:text-primary-400"
          >
            Effi4Tech.cl
          </a>
        </p>
      </div>
    </div>
  )
}


/** Siempre muestra el mismo mensaje, exista o no la cuenta: no revela qué correos están registrados. */
function RecuperarClaveModal({ open, onClose, emailInicial }: { open: boolean; onClose: () => void; emailInicial: string }) {
  const [email, setEmail] = useState('')
  const [enviado, setEnviado] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')

  const cerrar = () => { setEnviado(false); setError(''); onClose() }

  const enviar = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setEnviando(true)
    try {
      await authApi.recuperar(email || emailInicial)
      setEnviado(true)
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      setError(status === 429 ? 'Demasiados intentos: espera un minuto y vuelve a intentarlo' : 'No se pudo enviar la solicitud')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Modal open={open} onClose={cerrar} title="Crear o recuperar tu clave" size="sm">
      {enviado ? (
        <div className="space-y-4">
          <Alert variant="success">
            Si el correo está registrado, te enviamos un enlace para crear tu clave. Revisa también la carpeta
            de spam. El enlace vence en 1 hora.
          </Alert>
          <Button fullWidth onClick={cerrar}>Cerrar</Button>
        </div>
      ) : (
        <form onSubmit={enviar} className="space-y-4">
          <p className="text-sm text-slate-400">
            Escribe tu correo y te enviaremos un enlace para crear una clave nueva.
          </p>
          {error && <Alert variant="error">{error}</Alert>}
          <Input
            label="Correo electrónico"
            type="email"
            defaultValue={emailInicial}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
          <Button type="submit" fullWidth loading={enviando}>Enviar enlace</Button>
        </form>
      )}
    </Modal>
  )
}
