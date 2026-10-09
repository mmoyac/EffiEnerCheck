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
  /** Posición en el recorrido del lector (1, 2, 3…); null = sin posición */
  orden_recorrido?: number | null
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
  /** pendiente = todavía no crea su clave (no puede iniciar sesión) */
  estado: 'pendiente' | 'activa'
}

/** Resultado de invitar a un usuario: el enlace vuelve para reenviarlo por WhatsApp */
export interface Invitacion {
  enlace: string
  correo_enviado: boolean
  motivo: string | null
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

export type TipoPeriodo = 'regular' | 'lectura_inicial'

export interface BoletaMaestra {
  id: number
  condominio_id: number
  periodo_mes: string
  url_imagen_boleta: string | null
  boleta_visible_usuarios: boolean
  estado: 'borrador' | 'validada' | 'publicada'
  /** lectura_inicial: solo registra la lectura de partida de cada medidor; no se liquida ni se publica */
  tipo: TipoPeriodo
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
  /** Foto del medidor: si existe y de qué toma es (puede diferir de fecha_toma tras una corrección) */
  tiene_foto: boolean
  foto_fecha_toma: string | null
  /** Solo en el listado por período: la parcela no tiene historial y se puede ingresar su lectura anterior */
  lectura_anterior_editable: boolean
}

export interface LiquidacionParcela {
  id: number
  parcela_id: number
  boleta_id: number
  monto_energia_kwh: number | null
  monto_prorrateo_variable: number | null
  monto_cuota_fija: number | null
  total_pagar_mes: number | null
  /** Lo abonado a este mes según la cuenta corriente de luz (imputación a la deuda más antigua) */
  monto_abonado: number
  pagado: boolean
  fecha_pago: string | null
}

// --- Cuenta corriente de luz (cambio cobranza-energia) ---

export type EstadoCargo = 'pagado' | 'parcial' | 'pendiente'

export interface CargoLuz {
  tipo: 'saldo_inicial' | 'mes'
  fecha: string            // YYYY-MM-DD
  boleta_id: number | null
  monto: number
  cubierto: number
  estado: EstadoCargo
  fecha_pago: string | null
}

export interface AbonoLuz {
  id: number
  fecha: string            // YYYY-MM-DD
  monto: number
  nota: string | null
  creado_por: number
  creado_en: string
  anulado: boolean
  anulado_en: string | null
  motivo_anulacion: string | null
}

export interface CuentaLuz {
  parcela_id: number
  numero_parcela: string
  propietario_nombre: string | null
  total_cargos: number
  total_abonos: number
  /** Negativo = saldo a favor */
  saldo: number
  cargos: CargoLuz[]
  abonos: AbonoLuz[]
}

export interface ResumenCobranza {
  totales: { saldo_inicial: number; emitido: number; cargos: number; abonado: number; por_cobrar: number; a_favor: number }
  periodos: { tipo: 'saldo_inicial' | 'mes'; boleta_id: number | null; fecha: string; emitido: number; cubierto: number; pendiente: number; cargos: number; pagados: number }[]
  deudores: { parcela_id: number; numero_parcela: string; propietario_nombre: string | null; saldo: number; pendientes: CargoLuz[]; ultimo_abono: string | null }[]
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
  /** Confirma crear la boleta aunque haya parcelas activas sin lectura previa (partirán en 0) */
  aceptar_sin_lectura_anterior?: boolean
}

/** Vista previa / resultado de la carga masiva de lecturas iniciales desde Excel */
export interface ImportacionLecturasIniciales {
  /** Saldos iniciales de luz que cambian (columna opcional «Saldo luz») */
  saldos: { parcela_id: number; numero_parcela: string; valor: number; valor_actual: number | null }[]
  a_aplicar: { lectura_id: number; parcela_id: number; numero_parcela: string; valor: number; valor_actual: number | null; reemplaza: boolean }[]
  sin_cambio: number
  vacias: number
  errores: { fila: number; mensaje: string }[]
  aplicadas: number
}

/** 409 de POST /boletas/ cuando hay parcelas sin lectura anterior */
export interface SinLecturaAnterior {
  codigo: 'sin_lectura_anterior'
  mensaje: string
  parcelas: { id: number; numero_parcela: string }[]
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
  /** Formas de pago que acepta la rifa (al menos una) */
  medios_pago: MedioPago[]
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
  medios_pago?: MedioPago[]
}

export type RifaUpdate = Partial<Omit<RifaCreate, 'condominio_id'>>
