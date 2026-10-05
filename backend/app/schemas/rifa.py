from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator

from app.utils.telefono import normalizar_telefono

MedioPago = Literal["efectivo", "transferencia", "gasto_comun"]
Canal = Literal["portal", "porteria", "administracion"]


def _limpiar_premios(v: list[str] | None) -> list[str] | None:
    if v is None:
        return None
    premios = [p.strip() for p in v if p and p.strip()]
    if not premios:
        raise ValueError("La rifa debe tener al menos un premio")
    return premios


class RifaCreate(BaseModel):
    # Solo lo usa super_admin; para el resto se toma del tenant
    condominio_id: int | None = None
    nombre: str = Field(min_length=1)
    beneficiario: str = Field(min_length=1)
    descripcion: str | None = None
    premios: list[str]
    datos_transferencia: str | None = None
    precio_numero: PositiveInt
    cantidad_numeros: PositiveInt

    @field_validator("premios")
    @classmethod
    def premios_no_vacios(cls, v: list[str]) -> list[str]:
        return _limpiar_premios(v)


class RifaUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1)
    beneficiario: str | None = Field(default=None, min_length=1)
    descripcion: str | None = None
    premios: list[str] | None = None
    datos_transferencia: str | None = None
    precio_numero: PositiveInt | None = None
    cantidad_numeros: PositiveInt | None = None

    @field_validator("premios")
    @classmethod
    def premios_no_vacios(cls, v: list[str] | None) -> list[str] | None:
        return _limpiar_premios(v)


class RifaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    condominio_id: int
    nombre: str
    beneficiario: str
    descripcion: str | None
    premios: list[str]
    datos_transferencia: str | None
    precio_numero: int
    cantidad_numeros: int
    estado: str
    created_at: datetime
    cerrada_at: datetime | None
    # Calculados
    numeros_vendidos_total: int = 0
    recaudado: int = 0


class CompraRifaRequest(BaseModel):
    """Va en el campo `datos` (JSON) del multipart; el voucher, en el campo `voucher`."""
    parcela_id: int
    numeros: list[int] = Field(min_length=1)
    medio_pago: MedioPago
    comprador_nombre: str | None = None
    telefono: str | None = None

    @field_validator("comprador_nombre")
    @classmethod
    def nombre_limpio(cls, v: str | None) -> str | None:
        return v.strip() or None if v else None

    @field_validator("telefono", mode="before")
    @classmethod
    def telefono_normalizado(cls, v: str | None) -> str | None:
        return normalizar_telefono(v)


class CompraRifaResponse(BaseModel):
    id: int
    rifa_id: int
    folio: str
    parcela_id: int
    parcela_numero: str
    usuario_id: int
    usuario_nombre: str
    canal: Canal
    comprador_nombre: str | None
    telefono: str | None
    numeros: list[int]
    monto: int
    medio_pago: MedioPago
    pagada: bool
    pagada_at: datetime | None
    tiene_voucher: bool
    created_at: datetime
    anulada: bool
    anulada_at: datetime | None
    anulada_por_nombre: str | None
    # Lo que el usuario que consulta puede hacer con la compra ahora
    puede_anular: bool
    puede_adjuntar_voucher: bool


class ImputacionRifaResponse(BaseModel):
    id: int
    rifa_id: int
    parcela_id: int
    parcela_numero: str
    cantidad_numeros: int
    monto: int
    cargada: bool
    cargada_at: datetime | None


class RifaDetalleResponse(RifaResponse):
    # Todos los números vendidos, sin dueño: la grilla no revela a qué parcela pertenecen
    numeros_vendidos: list[int]
    # Números vigentes de las parcelas asociadas al usuario
    mis_numeros: list[int]
    # Compras e imputaciones de las parcelas del usuario; todas si es admin o portería
    compras: list[CompraRifaResponse]
    imputaciones: list[ImputacionRifaResponse]


class CompraCreadaResponse(BaseModel):
    """Respuesta de una compra: el detalle actualizado y la compra recién creada (para el comprobante)."""
    rifa: RifaDetalleResponse
    compra: CompraRifaResponse


class MarcarImputacionRequest(BaseModel):
    cargada: bool


class ParcelaVentaResponse(BaseModel):
    id: int
    numero_parcela: str
    propietario_nombre: str | None


class TelefonoSugeridoResponse(BaseModel):
    telefono: str
    nombre: str


class CajaFilaResponse(BaseModel):
    fecha: str  # YYYY-MM-DD en America/Santiago
    usuario_id: int
    usuario_nombre: str
    ventas: int
    numeros: int
    monto: int


class CajaResponse(BaseModel):
    filas: list[CajaFilaResponse]
    total_numeros: int
    total_monto: int
