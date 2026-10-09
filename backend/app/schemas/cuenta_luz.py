"""Cuenta corriente de luz (cambio cobranza-energia)."""
from datetime import date, datetime

from pydantic import BaseModel, Field


class AbonoItem(BaseModel):
    parcela_id: int
    monto: int = Field(gt=0)


class RegistrarAbonosRequest(BaseModel):
    """Uno o varios abonos con la misma fecha (p. ej. los pagos del gasto común de un día)."""
    fecha: date
    nota: str | None = Field(default=None, max_length=300)
    items: list[AbonoItem] = Field(min_length=1, max_length=500)


class AnularAbonoRequest(BaseModel):
    motivo: str = Field(min_length=5, max_length=300)


class CargoOut(BaseModel):
    tipo: str                       # saldo_inicial | mes
    fecha: date
    boleta_id: int | None
    monto: int
    cubierto: int
    estado: str                     # pagado | parcial | pendiente
    fecha_pago: date | None


class AbonoOut(BaseModel):
    id: int
    fecha: date
    monto: int
    nota: str | None
    creado_por: int
    creado_en: datetime
    anulado: bool
    anulado_en: datetime | None
    motivo_anulacion: str | None


class CuentaOut(BaseModel):
    parcela_id: int
    numero_parcela: str
    propietario_nombre: str | None
    total_cargos: int
    total_abonos: int
    saldo: int                      # negativo = saldo a favor
    cargos: list[CargoOut]
    abonos: list[AbonoOut]          # incluye los anulados (marcados), para auditoría


class TotalesCobranza(BaseModel):
    saldo_inicial: int
    emitido: int                    # liquidaciones publicadas
    cargos: int                     # saldo inicial + emitido
    abonado: int
    por_cobrar: int                 # suma de saldos deudores
    a_favor: int                    # suma de saldos a favor


class PeriodoCobranza(BaseModel):
    tipo: str                       # saldo_inicial | mes
    boleta_id: int | None
    fecha: date
    emitido: int
    cubierto: int
    pendiente: int
    cargos: int
    pagados: int


class DeudorOut(BaseModel):
    parcela_id: int
    numero_parcela: str
    propietario_nombre: str | None
    saldo: int
    pendientes: list[CargoOut]      # cargos no cubiertos del todo (parciales incluidos)
    ultimo_abono: date | None


class ResumenCobranza(BaseModel):
    totales: TotalesCobranza
    periodos: list[PeriodoCobranza]
    deudores: list[DeudorOut]
