import { api } from './client'
import type {
  CajaRifa,
  CompraCreada,
  CompraRifa,
  CompraRifaInput,
  EstadoRifa,
  ImputacionRifa,
  ParcelaVenta,
  Rifa,
  RifaCreate,
  RifaDetalle,
  RifaUpdate,
  TelefonoSugerido,
} from '../types'

/** Descarga un archivo con el token (un <a href> directo no enviaría el Authorization). */
async function descargar(url: string, nombre: string): Promise<void> {
  const { data } = await api.get<Blob>(url, { responseType: 'blob' })
  const href = URL.createObjectURL(data)
  const a = document.createElement('a')
  a.href = href
  a.download = nombre
  a.click()
  URL.revokeObjectURL(href)
}

export const rifasApi = {
  list: async (estado?: EstadoRifa): Promise<Rifa[]> => {
    const { data } = await api.get<Rifa[]>('/rifas/', { params: estado ? { estado } : {} })
    return data
  },

  get: async (id: number): Promise<RifaDetalle> => {
    const { data } = await api.get<RifaDetalle>(`/rifas/${id}`)
    return data
  },

  create: async (body: RifaCreate): Promise<Rifa> => {
    const { data } = await api.post<Rifa>('/rifas/', body)
    return data
  },

  update: async (id: number, body: RifaUpdate): Promise<Rifa> => {
    const { data } = await api.patch<Rifa>(`/rifas/${id}`, body)
    return data
  },

  /** Multipart: `datos` (JSON) + `voucher` opcional (obligatorio en transferencias de portería). */
  comprar: async (id: number, datos: CompraRifaInput, voucher?: Blob | null): Promise<CompraCreada> => {
    const form = new FormData()
    form.append('datos', JSON.stringify(datos))
    if (voucher) form.append('voucher', voucher, voucher instanceof File ? voucher.name : 'voucher.jpg')
    const { data } = await api.post<CompraCreada>(`/rifas/${id}/compras`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  anularCompra: async (id: number, compraId: number): Promise<RifaDetalle> => {
    const { data } = await api.post<RifaDetalle>(`/rifas/${id}/compras/${compraId}/anular`)
    return data
  },

  confirmarPago: async (id: number, compraId: number): Promise<CompraRifa> => {
    const { data } = await api.post<CompraRifa>(`/rifas/${id}/compras/${compraId}/confirmar-pago`)
    return data
  },

  adjuntarVoucher: async (id: number, compraId: number, voucher: Blob): Promise<CompraRifa> => {
    const form = new FormData()
    form.append('voucher', voucher, voucher instanceof File ? voucher.name : 'voucher.jpg')
    const { data } = await api.post<CompraRifa>(`/rifas/${id}/compras/${compraId}/voucher`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  /** El voucher es privado: se pide con el token y se abre como blob. */
  verVoucher: async (id: number, compraId: number): Promise<{ url: string; tipo: string }> => {
    const { data } = await api.get<Blob>(`/rifas/${id}/compras/${compraId}/voucher`, { responseType: 'blob' })
    return { url: URL.createObjectURL(data), tipo: data.type }
  },

  buscarCompras: async (id: number, filtros: { parcela_id?: number; folio?: string }): Promise<CompraRifa[]> => {
    const { data } = await api.get<CompraRifa[]>(`/rifas/${id}/compras`, { params: filtros })
    return data
  },

  parcelas: async (id: number): Promise<ParcelaVenta[]> => {
    const { data } = await api.get<ParcelaVenta[]>(`/rifas/${id}/parcelas`)
    return data
  },

  telefonos: async (id: number, parcelaId: number): Promise<TelefonoSugerido[]> => {
    const { data } = await api.get<TelefonoSugerido[]>(`/rifas/${id}/telefonos`, { params: { parcela_id: parcelaId } })
    return data
  },

  caja: async (id: number): Promise<CajaRifa> => {
    const { data } = await api.get<CajaRifa>(`/rifas/${id}/caja`)
    return data
  },

  cerrar: async (id: number): Promise<RifaDetalle> => {
    const { data } = await api.post<RifaDetalle>(`/rifas/${id}/cerrar`)
    return data
  },

  reabrir: async (id: number): Promise<RifaDetalle> => {
    const { data } = await api.post<RifaDetalle>(`/rifas/${id}/reabrir`)
    return data
  },

  marcarImputacion: async (id: number, imputacionId: number, cargada: boolean): Promise<ImputacionRifa> => {
    const { data } = await api.patch<ImputacionRifa>(`/rifas/${id}/imputaciones/${imputacionId}`, { cargada })
    return data
  },

  exportarCsv: (id: number) => descargar(`/rifas/${id}/export.csv`, `rifa-${id}-numeros.csv`),

  exportarImputaciones: (id: number) => descargar(`/rifas/${id}/imputaciones.csv`, `rifa-${id}-imputaciones.csv`),
}
