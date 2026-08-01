from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

EstadoBoleta = Literal["borrador", "validada", "publicada"]
TipoCalculo = Literal["fijo", "variable", "informativo"]


# ---------------------------------------------------------------------------
# Boleta Item Detalle
# ---------------------------------------------------------------------------

class BoletaItemDetalleCreate(BaseModel):
    descripcion: str
    monto_neto_clp: float
    tipo_calculo: TipoCalculo


class BoletaItemDetalleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    boleta_id: int
    descripcion: str
    monto_neto_clp: float
    tipo_calculo: str


# ---------------------------------------------------------------------------
# Boleta Maestra
# ---------------------------------------------------------------------------

class BoletaMaestraCreate(BaseModel):
    # super_admin debe proveerlo; otros roles lo reciben del contexto de tenant
    condominio_id: int | None = None
    periodo_mes: date | None = None
    url_imagen_boleta: str | None = None
    total_kwh_compania: float | None = None
    monto_neto_electricidad_consumida: float | None = None
    monto_total_emision: int | None = None
    monto_saldo_anterior: int | None = None
    # Items se pueden cargar junto con la boleta en una sola operación
    items_detalle: list[BoletaItemDetalleCreate] = []

    @field_validator("periodo_mes")
    @classmethod
    def debe_ser_primer_dia(cls, v: date | None) -> date | None:
        if v is not None and v.day != 1:
            raise ValueError("periodo_mes debe ser el primer día del mes (ej: 2025-03-01)")
        return v


class BoletaMaestraUpdate(BaseModel):
    url_imagen_boleta: str | None = None
    estado: EstadoBoleta | None = None
    boleta_visible_usuarios: bool | None = None
    total_kwh_compania: float | None = None
    monto_neto_electricidad_consumida: float | None = None
    monto_total_emision: int | None = None
    monto_saldo_anterior: int | None = None


class BoletaMaestraDetallesUpdate(BaseModel):
    total_kwh_compania: float | None = None
    monto_neto_electricidad_consumida: float | None = None
    monto_total_emision: int | None = None
    monto_saldo_anterior: int | None = None
    items_detalle: list[BoletaItemDetalleCreate] = []


class BoletaMaestraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    condominio_id: int
    periodo_mes: date
    url_imagen_boleta: str | None
    boleta_visible_usuarios: bool
    estado: str
    lecturas_cerradas: bool
    liquidaciones_cerradas: bool
    total_kwh_compania: float | None
    monto_neto_electricidad_consumida: float | None
    monto_total_emision: int | None
    monto_saldo_anterior: int | None
    creado_por: int
    items_detalle: list[BoletaItemDetalleResponse] = []


class BoletaMaestraParceleroResponse(BaseModel):
    """Vista restringida para parceleros: oculta url_imagen cuando boleta_visible_usuarios=False."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    condominio_id: int
    periodo_mes: date
    # La URL solo se expone si boleta_visible_usuarios es True
    url_imagen_boleta: str | None
    estado: str
