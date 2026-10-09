import { api } from './client'
import type { CuentaLuz, ResumenCobranza } from '../types'

/** Cuenta corriente de luz y cobranza (cambio cobranza-energia) */
export const cuentaLuzApi = {
  resumen: async (condominioId?: number): Promise<ResumenCobranza> => {
    const { data } = await api.get<ResumenCobranza>('/cuenta-luz/resumen', {
      params: condominioId ? { condominio_id: condominioId } : {},
    })
    return data
  },

  cuenta: async (parcelaId: number): Promise<CuentaLuz> => {
    const { data } = await api.get<CuentaLuz>(`/cuenta-luz/parcelas/${parcelaId}`)
    return data
  },

  /** Uno o varios abonos con la misma fecha (todo o nada). fecha: YYYY-MM-DD */
  abonar: async (fecha: string, items: { parcela_id: number; monto: number }[], nota?: string): Promise<CuentaLuz[]> => {
    const { data } = await api.post<CuentaLuz[]>('/cuenta-luz/abonos', { fecha, nota: nota || null, items })
    return data
  },

  /** Un abono nunca se borra: se anula con motivo */
  anular: async (abonoId: number, motivo: string): Promise<CuentaLuz> => {
    const { data } = await api.post<CuentaLuz>(`/cuenta-luz/abonos/${abonoId}/anular`, { motivo })
    return data
  },
}
