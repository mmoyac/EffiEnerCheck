import { useEffect, useState } from 'react'
import { lecturasApi } from '../api/lecturas'
import { Modal } from './ui/Modal'
import { Spinner } from './ui/Spinner'
import { Alert } from './ui/Alert'
import { fechaHora, numero } from '../utils/format'
import type { LecturaParcela } from '../types'

interface Props {
  lectura: LecturaParcela | null
  titulo: string
  onClose: () => void
}

/**
 * Foto del medidor junto al valor digitado (cambio foto-medidor). La foto es privada: se descarga con el
 * token y se muestra como blob. Si después se corrigió el valor, avisa de qué toma es la foto.
 */
export function FotoMedidorModal({ lectura, titulo, onClose }: Props) {
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!lectura) return
    let vigente = true
    let creada: string | null = null
    setUrl(null)
    setError('')
    lecturasApi.verFoto(lectura.id)
      .then((u) => { creada = u; if (vigente) setUrl(u); else URL.revokeObjectURL(u) })
      .catch(() => vigente && setError('No se pudo cargar la foto del medidor.'))
    return () => { vigente = false; if (creada) URL.revokeObjectURL(creada) }
  }, [lectura])

  const otraToma = lectura?.foto_fecha_toma && lectura.fecha_toma
    && new Date(lectura.foto_fecha_toma).getTime() !== new Date(lectura.fecha_toma).getTime()

  return (
    <Modal open={!!lectura} onClose={onClose} title={titulo} size="xl">
      {lectura && (
        <div className="space-y-3">
          <p className="text-sm text-slate-400">
            Lectura registrada: <span className="font-mono font-semibold text-slate-100">{numero(lectura.lectura_actual)}</span>
            {' · '}{fechaHora(lectura.fecha_toma)}
          </p>
          {otraToma && (
            <Alert variant="warning">
              Foto de la toma del {fechaHora(lectura.foto_fecha_toma)}. El valor se corrigió después.
            </Alert>
          )}
          {error ? <Alert variant="error">{error}</Alert> : url ? (
            <img src={url} alt="Foto del medidor" className="max-h-[70vh] w-full rounded-lg object-contain" />
          ) : (
            <div className="flex h-48 items-center justify-center"><Spinner size="lg" className="text-primary-500" /></div>
          )}
        </div>
      )}
    </Modal>
  )
}
