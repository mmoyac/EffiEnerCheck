import { type InputHTMLAttributes, forwardRef } from 'react'

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
}

export const Input = forwardRef<HTMLInputElement, Props>(
  ({ label, error, hint, className = '', id, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-')
    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-slate-300">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          {...props}
          className={[
            'rounded-lg border bg-slate-800 px-3 py-2 text-slate-100 placeholder-slate-500 transition-colors',
            'focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500',
            error ? 'border-red-500' : 'border-slate-600',
            className,
          ].join(' ')}
        />
        {error && <p className="text-xs text-red-400">{error}</p>}
        {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
      </div>
    )
  },
)
Input.displayName = 'Input'
