export const clp = (amount: number | null | undefined): string => {
  if (amount == null) return '—'
  return new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    maximumFractionDigits: 0,
  }).format(amount)
}

export const numero = (amount: number | null | undefined): string => {
  if (amount == null) return '—'
  return new Intl.NumberFormat('es-CL').format(amount)
}

export const kwh = (amount: number | null | undefined): string => {
  if (amount == null) return '—'
  return `${new Intl.NumberFormat('es-CL').format(amount)} kWh`
}

export const periodo = (isoDate: string): string => {
  const date = new Date(isoDate + 'T12:00:00Z')
  return date.toLocaleDateString('es-CL', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  })
}

export const periodoCorto = (isoDate: string): string => {
  const date = new Date(isoDate + 'T12:00:00Z')
  const mes = date.toLocaleDateString('es-CL', { month: 'short', timeZone: 'UTC' })
  const year = date.getUTCFullYear()
  return `${mes.charAt(0).toUpperCase() + mes.slice(1)} ${year}`
}

export const fecha = (isoDate: string | null | undefined): string => {
  if (!isoDate) return '—'
  return new Date(isoDate).toLocaleDateString('es-CL', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

export const fechaHora = (isoDate: string | null | undefined): string => {
  if (!isoDate) return '—'
  return new Date(isoDate).toLocaleString('es-CL', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
