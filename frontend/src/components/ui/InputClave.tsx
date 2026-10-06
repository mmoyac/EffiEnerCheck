import { forwardRef, useState, type InputHTMLAttributes } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { Input } from './Input'

interface Props extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string
  error?: string
  hint?: string
}

/** Campo de clave con botón para mostrarla u ocultarla (el "ojito"). */
export const InputClave = forwardRef<HTMLInputElement, Props>((props, ref) => {
  const [visible, setVisible] = useState(false)
  return (
    <Input
      ref={ref}
      {...props}
      type={visible ? 'text' : 'password'}
      rightElement={
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="rounded p-1 text-slate-400 transition-colors hover:text-slate-200 focus:outline-none focus:ring-1 focus:ring-primary-500"
          aria-label={visible ? 'Ocultar clave' : 'Mostrar clave'}
          title={visible ? 'Ocultar clave' : 'Mostrar clave'}
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      }
    />
  )
})
InputClave.displayName = 'InputClave'
