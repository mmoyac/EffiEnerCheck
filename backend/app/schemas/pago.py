"""Pagos en línea: pasarelas (administración) e intenciones (comunero). Las credenciales nunca salen."""
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

Ambiente = Literal["integracion", "produccion"]
EstadoIntencion = Literal["INICIADO", "CONFIRMADO", "RECHAZADO", "EXPIRADO", "EN_REVISION"]


def _porcentaje(v: Decimal | None) -> Decimal | None:
    """Hasta 4 decimales (p. ej. 0,69 % + IVA = 0,8211 %): se redondea en vez de rechazar."""
    return None if v is None else v.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _credenciales_limpias(v: dict[str, str] | None) -> dict[str, str] | None:
    if v is None:
        return v
    return {k.strip(): (val or "").strip() for k, val in v.items()}


class CampoCredencialResponse(BaseModel):
    nombre: str
    etiqueta: str
    secreto: bool


class ProveedorResponse(BaseModel):
    proveedor: str
    nombre: str
    campos_credenciales: list[CampoCredencialResponse]
    requiere_email: bool
    monto_minimo: int


class PasarelaCreate(BaseModel):
    condominio_id: int
    proveedor: str
    nombre_visible: str = Field(min_length=1, max_length=60)
    ambiente: Ambiente
    credenciales: dict[str, str]
    comision_porcentaje: Decimal = Field(default=Decimal(0), ge=0, lt=50)
    comision_fija: int = Field(default=0, ge=0)
    orden: int = 0

    @field_validator("comision_porcentaje")
    @classmethod
    def redondear(cls, v: Decimal | None) -> Decimal | None:
        return _porcentaje(v)

    @field_validator("credenciales")
    @classmethod
    def limpiar(cls, v: dict[str, str]) -> dict[str, str]:
        return _credenciales_limpias(v)


class PasarelaUpdate(BaseModel):
    nombre_visible: str | None = Field(default=None, min_length=1, max_length=60)
    ambiente: Ambiente | None = None
    comision_porcentaje: Decimal | None = Field(default=None, ge=0, lt=50)
    comision_fija: int | None = Field(default=None, ge=0)
    orden: int | None = None

    @field_validator("comision_porcentaje")
    @classmethod
    def redondear(cls, v: Decimal | None) -> Decimal | None:
        return _porcentaje(v)


class CredencialesRequest(BaseModel):
    credenciales: dict[str, str]

    @field_validator("credenciales")
    @classmethod
    def limpiar(cls, v: dict[str, str]) -> dict[str, str]:
        return _credenciales_limpias(v)


class PasarelaResponse(BaseModel):
    id: int
    condominio_id: int
    proveedor: str
    proveedor_nombre: str
    nombre_visible: str
    ambiente: Ambiente
    comision_porcentaje: Decimal
    comision_fija: int
    orden: int
    activa: bool
    # Nunca los valores: solo si están cargadas
    credenciales_cargadas: bool
    credenciales_at: datetime | None
    prueba_at: datetime | None
    prueba_ok: bool | None
    prueba_mensaje: str | None
    # Producción: hay una prueba exitosa posterior al último cambio de credenciales
    prueba_vigente: bool
    tiene_pagos: bool


class PruebaResponse(BaseModel):
    ok: bool
    mensaje: str
    pasarela: PasarelaResponse


# ---------------------------------------------------------------------------
# Comunero
# ---------------------------------------------------------------------------

class OpcionPagoResponse(BaseModel):
    pasarela_id: int
    nombre_visible: str
    proveedor: str
    comision_porcentaje: Decimal
    comision_fija: int
    monto: int
    comision: int
    total: int
    disponible: bool
    # Por qué no se ofrece (monto bajo el mínimo del proveedor)
    motivo: str | None = None


class RedireccionResponse(BaseModel):
    url: str
    metodo: Literal["GET", "POST"]
    campos: dict[str, str] = {}


class IntencionResponse(BaseModel):
    id: UUID
    estado: EstadoIntencion
    concepto: str
    descripcion: str
    monto: int
    comision: int
    total: int
    pasarela_nombre: str
    vence_at: datetime
    created_at: datetime
    confirmado_at: datetime | None
    numero_operacion: str | None
    autorizacion: str | None
    ultimos_digitos: str | None
    medio: str | None
    motivo: str | None
    # A dónde volver después de ver el resultado (p. ej. /mis-rifas)
    volver_a: str | None = None


class IntencionRevisionResponse(IntencionResponse):
    usuario_nombre: str
    monto_confirmado: int | None
    resuelta_at: datetime | None
    nota_resolucion: str | None


class ResolverRequest(BaseModel):
    nota: str = Field(min_length=3, max_length=1000)
