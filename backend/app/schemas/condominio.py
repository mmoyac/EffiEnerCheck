from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

PlanSuscripcion = Literal["basico", "pro", "premium"]


class CondominioCreate(BaseModel):
    nombre: str
    rut_comunidad: str
    direccion: str | None = None
    plan_suscripcion: PlanSuscripcion
    activo: bool = True


class CondominioUpdate(BaseModel):
    nombre: str | None = None
    direccion: str | None = None
    plan_suscripcion: PlanSuscripcion | None = None
    activo: bool | None = None


class CondominioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    rut_comunidad: str
    direccion: str | None
    plan_suscripcion: str
    activo: bool
    created_at: datetime | None
