from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    # Foto del medidor: si existe y de qué toma es. Nunca la ruta del archivo.
    tiene_foto: bool = False
    foto_fecha_toma: datetime | None = None
    # La lectura anterior solo se ingresa si la parcela no tiene historial (cambio lectura-inicial).
    # Lo informa el listado por período; en las demás respuestas va en falso.
    lectura_anterior_editable: bool = False


# ---- Sincronización de lecturas tomadas sin conexión (cambio lecturas-sin-conexion) ----------------------

class BaseLectura(BaseModel):
    """Lo que el dispositivo descargó al preparar el recorrido: detecta cambios hechos en el servidor."""
    lectura_actual: float
    fecha_toma: datetime | None = None


class LecturaSinConexion(BaseModel):
    lectura_id: int
    lectura_actual: float
    fecha_toma: datetime          # hora real de la toma en terreno
    base: BaseLectura


class SincronizarLecturasRequest(BaseModel):
    items: list[LecturaSinConexion] = Field(min_length=1, max_length=200)


class ResultadoSincronizacion(BaseModel):
    lectura_id: int
    estado: Literal["aplicada", "conflicto", "rechazada"]
    motivo: str | None = None
    lectura: LecturaParcelaResponse | None = None   # la vigente en el servidor


class SincronizarLecturasResponse(BaseModel):
    resultados: list[ResultadoSincronizacion]
