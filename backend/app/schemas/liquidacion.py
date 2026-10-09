from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LiquidacionParcelaResponse(BaseModel):
    """Solo lectura: las liquidaciones las genera el Motor EnerCheck, no el usuario."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    parcela_id: int
    boleta_id: int
    monto_energia_kwh: int | None
    monto_prorrateo_variable: int | None
    monto_cuota_fija: int | None
    total_pagar_mes: int | None
    # Derivados de la cuenta corriente de luz: lo abonado a este mes (imputación a la deuda más antigua)
    monto_abonado: int = 0
    pagado: bool
    fecha_pago: datetime | None
