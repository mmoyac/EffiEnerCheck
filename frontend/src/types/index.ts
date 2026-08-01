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

export interface Usuario {
  id: number
  nombre: string
  email: string
  rol_id: number
  rol: Rol
  condominio_id: number | null
  ultimo_login: string | null
  parcelas: Parcela[]
}

export interface BoletaItemDetalle {
  id: number
  boleta_id: number
  descripcion: string
  monto_neto_clp: number
  tipo_calculo: 'fijo' | 'variable' | 'informativo'
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
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export type ItemDetalleCreate = {
  descripcion: string
  monto_neto_clp: number
  tipo_calculo: 'fijo' | 'variable' | 'informativo'
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
