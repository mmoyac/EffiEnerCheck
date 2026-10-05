// Misma regla que backend/app/utils/telefono.py: mantener ambas sincronizadas.

/**
 * Normaliza un teléfono chileno a 56XXXXXXXXX (solo dígitos).
 * 8 dígitos → 569…, 9 dígitos → 56…, 11 dígitos que empiezan en 56 → tal cual.
 * Retorna null si viene vacío y undefined si es inválido.
 */
export function normalizarTelefono(valor: string | null | undefined): string | null | undefined {
  const digitos = (valor ?? '').replace(/\D/g, '')
  if (!digitos) return null
  if (digitos.length === 8) return '569' + digitos
  if (digitos.length === 9) return '56' + digitos
  if (digitos.length === 11 && digitos.startsWith('56')) return digitos
  return undefined
}

/** 56993327142 → +56 9 9332 7142 */
export function formatearTelefono(normalizado: string): string {
  const m = normalizado.match(/^56(9)(\d{4})(\d{4})$/)
  if (m) return `+56 ${m[1]} ${m[2]} ${m[3]}`
  return '+' + normalizado
}
