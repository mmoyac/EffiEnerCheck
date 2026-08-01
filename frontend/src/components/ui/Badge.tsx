type Color = 'green' | 'yellow' | 'red' | 'blue' | 'slate' | 'purple'

interface Props {
  children: React.ReactNode
  color?: Color
  dot?: boolean
}

const colors: Record<Color, string> = {
  green:  'bg-green-500/10 text-green-400 ring-green-500/20',
  yellow: 'bg-yellow-500/10 text-yellow-400 ring-yellow-500/20',
  red:    'bg-red-500/10 text-red-400 ring-red-500/20',
  blue:   'bg-blue-500/10 text-blue-400 ring-blue-500/20',
  slate:  'bg-slate-500/10 text-slate-400 ring-slate-500/20',
  purple: 'bg-purple-500/10 text-purple-400 ring-purple-500/20',
}

const dotColors: Record<Color, string> = {
  green:  'fill-green-400',
  yellow: 'fill-yellow-400',
  red:    'fill-red-400',
  blue:   'fill-blue-400',
  slate:  'fill-slate-400',
  purple: 'fill-purple-400',
}

export function Badge({ children, color = 'slate', dot = false }: Props) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${colors[color]}`}>
      {dot && (
        <svg viewBox="0 0 6 6" className={`h-1.5 w-1.5 ${dotColors[color]}`}>
          <circle cx="3" cy="3" r="3" />
        </svg>
      )}
      {children}
    </span>
  )
}
