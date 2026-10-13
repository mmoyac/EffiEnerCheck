import { api } from './client'
import type {
  IntencionPago,
  IntencionRevision,
  OpcionPago,
  Pasarela,
  PasarelaInput,
  PasarelaUpdate,
  ProveedorPago,
  PruebaPasarela,
  Redireccion,
} from '../types'

/** Pasarelas de pago (escritura solo super_admin; el admin del condominio las ve). */
export const pasarelasApi = {
  proveedores: async (): Promise<ProveedorPago[]> => {
    const { data } = await api.get<ProveedorPago[]>('/pasarelas/proveedores')
    return data
  },

  list: async (condominioId?: number): Promise<Pasarela[]> => {
    const { data } = await api.get<Pasarela[]>('/pasarelas/', { params: condominioId ? { condominio_id: condominioId } : {} })
    return data
  },

  create: async (body: PasarelaInput): Promise<Pasarela> => {
    const { data } = await api.post<Pasarela>('/pasarelas/', body)
    return data
  },

  update: async (id: number, body: PasarelaUpdate): Promise<Pasarela> => {
    const { data } = await api.patch<Pasarela>(`/pasarelas/${id}`, body)
    return data
  },

  credenciales: async (id: number, credenciales: Record<string, string>): Promise<Pasarela> => {
    const { data } = await api.put<Pasarela>(`/pasarelas/${id}/credenciales`, { credenciales })
    return data
  },

  probar: async (id: number): Promise<PruebaPasarela> => {
    const { data } = await api.post<PruebaPasarela>(`/pasarelas/${id}/probar`)
    return data
  },

  activar: async (id: number, activa: boolean): Promise<Pasarela> => {
    const { data } = await api.post<Pasarela>(`/pasarelas/${id}/${activa ? 'activar' : 'desactivar'}`)
    return data
  },

  remove: async (id: number): Promise<void> => {
    await api.delete(`/pasarelas/${id}`)
  },
}

export const pagosApi = {
  /** Pasarelas que se pueden ofrecer para pagar `monto`, con su comisión y total */
  disponibles: async (monto: number): Promise<OpcionPago[]> => {
    const { data } = await api.get<OpcionPago[]>('/pagos/disponibles', { params: { monto } })
    return data
  },

  get: async (id: string): Promise<IntencionPago> => {
    const { data } = await api.get<IntencionPago>(`/pagos/${id}`)
    return data
  },

  /** Pide al backend consultar al proveedor (máximo una vez cada 10 s) */
  consultar: async (id: string): Promise<IntencionPago> => {
    const { data } = await api.post<IntencionPago>(`/pagos/${id}/consultar`)
    return data
  },

  revision: async (): Promise<IntencionRevision[]> => {
    const { data } = await api.get<IntencionRevision[]>('/pagos/revision')
    return data
  },

  resolver: async (id: string, nota: string): Promise<IntencionRevision> => {
    const { data } = await api.post<IntencionRevision>(`/pagos/${id}/resolver`, { nota })
    return data
  },
}

/** Lleva el navegador a la pasarela: GET directo o formulario POST oculto. */
export function irAPasarela(r: Redireccion): void {
  if (r.metodo === 'GET') {
    window.location.assign(r.url)
    return
  }
  const form = document.createElement('form')
  form.method = 'POST'
  form.action = r.url
  for (const [nombre, valor] of Object.entries(r.campos)) {
    const input = document.createElement('input')
    input.type = 'hidden'
    input.name = nombre
    input.value = valor
    form.appendChild(input)
  }
  document.body.appendChild(form)
  form.submit()
}
