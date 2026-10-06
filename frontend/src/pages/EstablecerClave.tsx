import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { KeyRound } from 'lucide-react'
import type { AxiosError } from 'axios'
import { authApi } from '../api/auth'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { Alert } from '../components/ui/Alert'
import { Spinner } from '../components/ui/Spinner'
import { PLATAFORMA } from '../config/marca'

const LARGO_MINIMO = 10

type Estado =
  | { fase: 'verificando' }
  | { fase: 'invalido' }
  | { fase: 'formulario'; nombre: string; tipo: 'invitacion' | 'recuperacion' }
  | { fase: 'listo' }

/**
 * /crear-clave#<token> (invitación) y /restablecer-clave#<token> (recuperación).
 * El token viaja en el fragmento: el navegador no lo envía al servidor, así que no queda en logs.
 * Se lee una vez y se borra de la barra de direcciones (spec acceso-por-enlace).
 */
export default function EstablecerClave() {
  const [token] = useState(() => {
    const t = window.location.hash.slice(1)
    if (t) window.history.replaceState(null, '', window.location.pathname)
    return t
  })
  const [estado, setEstado] = useState<Estado>({ fase: 'verificando' })
  const [clave, setClave] = useState('')
  const [repetida, setRepetida] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    if (!token) { setEstado({ fase: 'invalido' }); return }
    authApi.verificarEnlace(token)
      .then(({ nombre, tipo }) => setEstado({ fase: 'formulario', nombre, tipo }))
      .catch(() => setEstado({ fase: 'invalido' }))
  }, [token])

  const enviar = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (clave.length < LARGO_MINIMO) { setError(`La clave debe tener al menos ${LARGO_MINIMO} caracteres`); return }
    if (clave !== repetida) { setError('Las claves no coinciden'); return }
    setEnviando(true)
    try {
      await authApi.establecerClave(token, clave)
      setEstado({ fase: 'listo' })
    } catch (err: unknown) {
      const r = (err as AxiosError<{ detail: string }>)?.response
      if (r?.status === 410) setEstado({ fase: 'invalido' })
      else setError(r?.data?.detail ?? 'No se pudo guardar la clave')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-600 shadow-lg shadow-primary-900/50">
            <KeyRound className="h-7 w-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-100">{PLATAFORMA.nombre}</h1>
        </div>

        <div className="rounded-xl border border-slate-700 bg-slate-800 p-6 shadow-2xl">
          {estado.fase === 'verificando' && (
            <div className="flex justify-center py-6"><Spinner /></div>
          )}

          {estado.fase === 'invalido' && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-100">Enlace no válido</h2>
              <Alert variant="warning">
                Este enlace ya fue usado o venció. Puedes pedir uno nuevo con «¿Olvidaste tu clave?» en la
                pantalla de ingreso, o solicitarlo a la administración.
              </Alert>
              <Link to="/login" className="block text-center text-sm font-medium text-primary-400 hover:text-primary-300">
                Ir al ingreso
              </Link>
            </div>
          )}

          {estado.fase === 'formulario' && (
            <>
              <h2 className="mb-1 text-lg font-semibold text-slate-100">
                {estado.tipo === 'invitacion' ? 'Crea tu clave' : 'Crea una clave nueva'}
              </h2>
              <p className="mb-5 text-sm text-slate-400">
                Hola {estado.nombre}. Elige una clave de al menos {LARGO_MINIMO} caracteres; nadie más la conocerá.
              </p>
              {error && <div className="mb-4"><Alert variant="error">{error}</Alert></div>}
              <form onSubmit={enviar} className="space-y-4">
                <Input
                  label="Clave nueva"
                  type="password"
                  value={clave}
                  onChange={(e) => setClave(e.target.value)}
                  required
                  autoComplete="new-password"
                  hint={`${clave.length} de ${LARGO_MINIMO} caracteres como mínimo`}
                />
                <Input
                  label="Repite la clave"
                  type="password"
                  value={repetida}
                  onChange={(e) => setRepetida(e.target.value)}
                  required
                  autoComplete="new-password"
                />
                <Button type="submit" fullWidth loading={enviando} size="lg">Guardar mi clave</Button>
              </form>
            </>
          )}

          {estado.fase === 'listo' && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-100">¡Listo!</h2>
              <Alert variant="success">Tu clave quedó guardada. Ya puedes ingresar con tu correo y tu clave.</Alert>
              <Link to="/login">
                <Button fullWidth size="lg">Ir al ingreso</Button>
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
