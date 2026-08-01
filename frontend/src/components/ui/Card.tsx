import { type ReactNode } from 'react'

interface Props {
  children: ReactNode
  className?: string
  padding?: boolean
}

export function Card({ children, className = '', padding = true }: Props) {
  return (
    <div className={`rounded-xl border border-slate-700 bg-slate-800 shadow-sm ${padding ? 'p-5' : ''} ${className}`}>
      {children}
    </div>
  )
}

export function CardHeader({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`mb-4 flex items-center justify-between ${className}`}>{children}</div>
}

export function CardTitle({ children }: { children: ReactNode }) {
  return <h3 className="text-base font-semibold text-slate-100">{children}</h3>
}
