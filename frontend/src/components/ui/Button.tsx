import { type ButtonHTMLAttributes, type ReactNode } from 'react'
import { Spinner } from './Spinner'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost'
type Size = 'sm' | 'md' | 'lg'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  children: ReactNode
  fullWidth?: boolean
}

const variants: Record<Variant, string> = {
  primary:   'bg-primary-600 hover:bg-primary-500 text-white shadow-sm',
  secondary: 'bg-slate-700 hover:bg-slate-600 text-slate-100 shadow-sm',
  danger:    'bg-red-600 hover:bg-red-500 text-white shadow-sm',
  ghost:     'bg-transparent hover:bg-slate-700 text-slate-300',
}

const sizes: Record<Size, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'px-5 py-3 text-base',
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  fullWidth = false,
  className = '',
  disabled,
  children,
  ...props
}: Props) {
  return (
    <button
      {...props}
      disabled={disabled ?? loading}
      className={[
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed',
        variants[variant],
        sizes[size],
        fullWidth ? 'w-full' : '',
        className,
      ].join(' ')}
    >
      {loading && <Spinner size="sm" />}
      {children}
    </button>
  )
}
