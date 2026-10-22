/**
 * Matrices de cálculo de la luz (espejo de backend/app/core/matrices.py, cambio matriz-calculo-luz).
 * El condominio tiene una por defecto y cada período la copia al crearse; las define el super_admin.
 */
export type MatrizCalculo = 'fijo_y_variable' | 'cargo_fijo'

export const MATRICES: { valor: MatrizCalculo; nombre: string; detalle: string }[] = [
  {
    valor: 'fijo_y_variable',
    nombre: 'Fijo y variable',
    detalle: 'Ítems fijos en partes iguales; ítems variables y diferencial según el consumo de cada parcela.',
  },
  {
    valor: 'cargo_fijo',
    nombre: 'Cargo fijo + consumo',
    detalle: 'Todos los ítems de la boleta en partes iguales (cargo fijo); cada parcela paga además sus kWh.',
  },
]

export const nombreMatriz = (m: MatrizCalculo | string | undefined) =>
  MATRICES.find((x) => x.valor === m)?.nombre ?? MATRICES[0].nombre
