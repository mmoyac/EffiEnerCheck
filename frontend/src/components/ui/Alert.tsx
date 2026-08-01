import { AlertCircle, CheckCircle2, Info, XCircle } from 'lucide-react'
import type { ReactNode } from 'react'

type Variant = 'info' | 'success' | 'warning' | 'error'

interface Props {
  variant?: Variant
  children: ReactNode
}

const config: Record<Variant, { icon: typeof Info; classes: string }> = {
  info:    { icon: Info,          classes: 'bg-blue-500/10 border-blue-500/30 text-blue-300' },
  success: { icon: CheckCircle2,  classes: 'bg-green-500/10 border-green-500/30 text-green-300' },
  warning: { icon: AlertCircle,   classes: 'bg-yellow-500/10 border-yellow-500/30 text-yellow-300' },
  error:   { icon: XCircle,       classes: 'bg-red-500/10 border-red-500/30 text-red-300' },
}

export function Alert({ variant = 'info', children }: Props) {
  const { icon: Icon, classes } = config[variant]
  return (
    <div className={`flex items-start gap-3 rounded-lg border px-4 py-3 text-sm ${classes}`}>
      <Icon className="mt-0.5 h-4 w-4 flex-shrink-0" />
      <span>{children}</span>
    </div>
  )
}
