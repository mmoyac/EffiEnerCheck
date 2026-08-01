from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class LecturaParcelaCreate(BaseModel):
    parcela_id: int
    boleta_id: int
    lectura_anterior: float
    lectura_actual: float
    fecha_toma: datetime | None = None

    @field_validator("lectura_actual")
    @classmethod
    def actual_mayor_que_anterior(cls, v: float, info) -> float:
        anterior = info.data.get("lectura_anterior")
        if anterior is not None and v < anterior:
            raise ValueError("lectura_actual no puede ser menor que lectura_anterior")
        return v

    @property
    def kwh_consumidos(self) -> float:
        return self.lectura_actual - self.lectura_anterior


class LecturaParcelaUpdate(BaseModel):
    lectura_anterior: float | None = None
    lectura_actual: float | None = None
    fecha_toma: datetime | None = None


class LecturaParcelaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parcela_id: int
    boleta_id: int
    lectura_anterior: float
    lectura_actual: float
    kwh_consumidos: float
    lector_id: int
    fecha_toma: datetime | None
