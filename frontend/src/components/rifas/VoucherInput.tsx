import { useEffect, useRef, useState } from 'react'
import { Camera, FileText, RotateCcw } from 'lucide-react'
import { Button } from '../ui/Button'

const MAX_LADO = 1600
const MAX_BYTES = 10 * 1024 * 1024

/**
 * Reduce una foto a 1600 px por lado en JPEG: una foto de teléfono de 4–8 MB queda en ~300 KB.
 * PDF y formatos que el navegador no decodifica (p. ej. HEIC en Chrome) se devuelven tal cual.
 */
async function reducirImagen(file: File): Promise<Blob> {
  if (!file.type.startsWith('image/')) return file
  try {
    const bitmap = await createImageBitmap(file)
    const escala = Math.min(1, MAX_LADO / Math.max(bitmap.width, bitmap.height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(bitmap.width * escala)
    canvas.height = Math.round(bitmap.height * escala)
    canvas.getContext('2d')!.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    bitmap.close()
    const blob = await new Promise<Blob | null>((res) => canvas.toBlob(res, 'image/jpeg', 0.82))
    if (!blob) return file
    return new File([blob], file.name.replace(/\.\w+$/, '') + '.jpg', { type: 'image/jpeg' })
  } catch {
    return file
  }
}

interface Props {
  value: Blob | null
  onChange: (voucher: Blob | null) => void
  obligatorio?: boolean
}

export function VoucherInput({ value, onChange, obligatorio = false }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [procesando, setProcesando] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!value || !value.type.startsWith('image/')) { setPreview(null); return }
    const url = URL.createObjectURL(value)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [value])

  const elegir = async (file: File | undefined) => {
    setError('')
    if (!file) return
    setProcesando(true)
    const reducido = await reducirImagen(file)
    setProcesando(false)
    if (reducido.size > MAX_BYTES) {
      setError('El archivo supera los 10 MB')
      onChange(null)
      return
    }
    onChange(reducido)
  }

  return (
    <div className="space-y-2">
      <input
        ref={inputRef}
        type="file"
        // capture abre directo la cámara trasera en tablet o teléfono
        accept="image/*,application/pdf"
        capture="environment"
        className="hidden"
        data-testid="voucher-input"
        onChange={(e) => { elegir(e.target.files?.[0]); e.target.value = '' }}
      />
      {value ? (
        <div className="flex items-center gap-3 rounded-xl border border-slate-600 bg-slate-800 p-2">
          {preview ? (
            <img src={preview} alt="Voucher" className="h-20 w-20 rounded-lg object-cover" />
          ) : (
            <div className="flex h-20 w-20 items-center justify-center rounded-lg bg-slate-700"><FileText className="h-8 w-8 text-slate-400" /></div>
          )}
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-green-400">Voucher listo</p>
            <p className="text-xs text-slate-400">{Math.round(value.size / 1024)} KB</p>
          </div>
          <Button type="button" variant="ghost" size="sm" onClick={() => inputRef.current?.click()}>
            <RotateCcw className="h-4 w-4" /> Repetir
          </Button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={procesando}
          className={`flex min-h-[64px] w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed text-sm font-semibold transition-colors ${
            obligatorio ? 'border-yellow-500/60 text-yellow-300 hover:bg-yellow-500/10' : 'border-slate-600 text-slate-300 hover:bg-slate-700'
          }`}
        >
          <Camera className="h-5 w-5" />
          {procesando ? 'Procesando foto…' : obligatorio ? 'Tomar foto del voucher (obligatorio)' : 'Adjuntar voucher (opcional)'}
        </button>
      )}
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  )
}
