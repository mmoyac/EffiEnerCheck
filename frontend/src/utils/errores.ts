/**
 * Mensaje legible de un error de la API. FastAPI responde `detail` como texto (HTTPException) o como
 * lista de errores de validación (422 de Pydantic): en ese caso se juntan sus mensajes.
 */
export function mensajeError(err: unknown, porDefecto: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const mensajes = detail
      .map((d) => (typeof d?.msg === 'string' ? d.msg.replace(/^Value error, /, '') : null))
      .filter(Boolean)
    if (mensajes.length) return mensajes.join('. ')
  }
  return porDefecto
}
