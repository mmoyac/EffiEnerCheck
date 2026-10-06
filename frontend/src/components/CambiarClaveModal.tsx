import { FormEvent, useState } from 'react'
import type { AxiosError } from 'axios'
import { authApi } from '../api/auth'
import { useAuth } from '../hooks/useAuth'
import { Modal } from './ui/Modal'
import { Input } from './ui/Input'
import { Button } from './ui/Button'
import { Alert } from './ui/Alert'

const LARGO_MINIMO = 10

/** Cambio de la propia clave: la sesión sigue con el token nuevo y las de otros dispositivos se cierran. */
export function CambiarClaveModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { actualizarToken } = useAuth()
  const [actual, setActual] = useState('')
  const [nueva, setNueva] = useState('')
  const [repetida, setRepetida] = useState('')
  const [error, setError] = useState('')
  const [listo, setListo] = useState(false)
  const [enviando, setEnviando] = useState(false)

  const cerrar = () => {
    setActual(''); setNueva(''); setRepetida(''); setError(''); setListo(false)
    onClose()
  }

  const enviar = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (nueva.length < LARGO_MINIMO) { setError(`La clave nueva debe tener al menos ${LARGO_MINIMO} caracteres`); return }
    if (nueva !== repetida) { setError('Las claves nuevas no coinciden'); return }
    setEnviando(true)
    try {
      const { access_token } = await authApi.cambiarClave(actual, nueva)
      actualizarToken(access_token)
      setListo(true)
    } catch (err: unknown) {
      setError((err as AxiosError<{ detail: string }>)?.response?.data?.detail ?? 'No se pudo cambiar la clave')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Modal open={open} onClose={cerrar} title="Cambiar mi clave" size="sm">
      {listo ? (
        <div className="space-y-4">
          <Alert variant="success">
            Tu clave cambió. Si tenías la sesión abierta en otros dispositivos, allí tendrás que volver a ingresar.
          </Alert>
          <Button fullWidth onClick={cerrar}>Cerrar</Button>
        </div>
      ) : (
        <form onSubmit={enviar} className="space-y-4">
          {error && <Alert variant="error">{error}</Alert>}
          <Input label="Clave actual" type="password" value={actual} onChange={(e) => setActual(e.target.value)}
                 required autoComplete="current-password" />
          <Input label="Clave nueva" type="password" value={nueva} onChange={(e) => setNueva(e.target.value)}
                 required autoComplete="new-password" hint={`Al menos ${LARGO_MINIMO} caracteres`} />
          <Input label="Repite la clave nueva" type="password" value={repetida}
                 onChange={(e) => setRepetida(e.target.value)} required autoComplete="new-password" />
          <Button type="submit" fullWidth loading={enviando}>Guardar</Button>
        </form>
      )}
    </Modal>
  )
}
