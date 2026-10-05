export interface Rol {
  id: number
  nombre: string
}

export interface Parcela {
  id: number
  condominio_id: number
  numero_parcela: string
  propietario_nombre: string | null
  activa: boolean
}

import type { Modulo } from '../config/modulos'

export interface Usuario {
  id: number
  nombre: string
  email: string
  rol_id: number
  rol: Rol
  condominio_id: number | null
  ultimo_login: string | null
  parcelas: Parcela[]
  telefono: string | null
}

/** Identidad del condominio en el portal (nombre, logo y color institucional) */
export interface CondominioMarca {
  id: number
  nombre: string
  logo_url: string | null
  color_primario: string | null
}

/** GET /auth/me: el usuario más los módulos habilitados de su condominio y su marca */
export interface Sesion extends Usuario {
  modulos: Modulo[]
  condominio: CondominioMarca | null
}

/**
 * fijo/variable entran al reparto; informativo es la exclusión deliberada del
 * administrador; pendiente marca lo que el OCR creó y aún nadie ha juzgado.
 */
export type TipoCalculo = 'fijo' | 'variable' | 'informativo' | 'pendiente'

export interface BoletaItemDetalle {
  id: number
  boleta_id: number
  descripcion: string
  monto_neto_clp: number
  tipo_calculo: TipoCalculo
}

export interface BoletaMaestra {
  id: number
  condominio_id: number
  periodo_mes: string
  url_imagen_boleta: string | null
  boleta_visible_usuarios: boolean
  estado: 'borrador' | 'validada' | 'publicada'
  lecturas_cerradas: boolean
  liquidaciones_cerradas: boolean
  total_kwh_compania: number | null
  monto_neto_electricidad_consumida: number | null
  monto_total_emision: number | null
  monto_saldo_anterior: number | null
  creado_por: number
  items_detalle: BoletaItemDetalle[]
}

export interface LecturaParcela {
  id: number
  parcela_id: number
  boleta_id: number
  lectura_anterior: number
  lectura_actual: number
  kwh_consumidos: number
  lector_id: number
  fecha_toma: string | null
}

export interface LiquidacionParcela {
  id: number
  parcela_id: number
  boleta_id: number
  monto_energia_kwh: number | null
  monto_prorrateo_variable: number | null
  monto_cuota_fija: number | null
  total_pagar_mes: number | null
  pagado: boolean
  fecha_pago: string | null
}

export interface MenuItem {
  id: number
  label: string
  path: string
  icon: string
  orden: number
  modulo: Modulo | null  // null = núcleo del portal
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export type ItemDetalleCreate = {
  descripcion: string
  monto_neto_clp: number
  tipo_calculo: TipoCalculo
}

export interface BoletaMaestraCreate {
  condominio_id?: number
  periodo_mes: string
  url_imagen_boleta?: string
  total_kwh_compania?: number
  monto_neto_electricidad_consumida?: number
  monto_total_emision?: number
  monto_saldo_anterior?: number
  items_detalle?: ItemDetalleCreate[]
}

// --- Rifas solidarias (independientes de la boleta eléctrica) ---

export type EstadoRifa = 'abierta' | 'cerrada'
export type MedioPago = 'efectivo' | 'transferencia' | 'gasto_comun'
export type CanalCompra = 'portal' | 'porteria' | 'administracion'

export interface Rifa {
  id: number
  condominio_id: number
  nombre: string
  beneficiario: string
  descripcion: string | null
  premios: string[]
  datos_transferencia: string | null
  precio_numero: number
  cantidad_numeros: number
  estado: EstadoRifa
  created_at: string
  cerrada_at: string | null
  numeros_vendidos_total: number
  recaudado: number
}

export interface CompraRifa {
  id: number
  rifa_id: number
  /** R{rifa}-{correlativo}, p. ej. R3-042 */
  folio: string
  parcela_id: number
  parcela_numero: string
  usuario_id: number
  usuario_nombre: string
  canal: CanalCompra
  comprador_nombre: string | null
  telefono: string | null
  numeros: number[]
  monto: number
  medio_pago: MedioPago
  pagada: boolean
  pagada_at: string | null
  tiene_voucher: boolean
  created_at: string
  anulada: boolean
  anulada_at: string | null
  anulada_por_nombre: string | null
  puede_anular: boolean
  puede_adjuntar_voucher: boolean
}

/** Monto a cargar en el gasto común (Comunidad Feliz), generado al cerrar la rifa. */
export interface ImputacionRifa {
  id: number
  rifa_id: number
  parcela_id: number
  parcela_numero: string
  cantidad_numeros: number
  monto: number
  cargada: boolean
  cargada_at: string | null
}

export interface RifaDetalle extends Rifa {
  /** Todos los números vendidos, sin dueño */
  numeros_vendidos: number[]
  /** Números vigentes de las parcelas del usuario */
  mis_numeros: number[]
  /** Compras e imputaciones de las parcelas del usuario; todas si es admin o portería */
  compras: CompraRifa[]
  imputaciones: ImputacionRifa[]
}

export interface CompraCreada {
  rifa: RifaDetalle
  compra: CompraRifa
}

export interface CompraRifaInput {
  parcela_id: number
  numeros: number[]
  medio_pago: MedioPago
  comprador_nombre?: string | null
  telefono?: string | null
}

export interface ParcelaVenta {
  id: number
  numero_parcela: string
  propietario_nombre: string | null
}

export interface TelefonoSugerido {
  telefono: string
  nombre: string
}

export interface CajaRifa {
  filas: { fecha: string; usuario_id: number; usuario_nombre: string; ventas: number; numeros: number; monto: number }[]
  total_numeros: number
  total_monto: number
}

export interface RifaCreate {
  condominio_id?: number
  nombre: string
  beneficiario: string
  descripcion?: string | null
  premios: string[]
  datos_transferencia?: string | null
  precio_numero: number
  cantidad_numeros: number
}

export type RifaUpdate = Partial<Omit<RifaCreate, 'condominio_id'>>
