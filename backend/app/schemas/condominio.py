import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.modulos import MODULOS, validar_modulos
from app.utils.dominio import normalizar_dominio

PlanSuscripcion = Literal["basico", "pro", "premium"]

_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
# http solo para el portal local de desarrollo
_URL_PORTAL = re.compile(r"^(https://[^\s/]+|http://(localhost|127\.0\.0\.1)(:\d+)?)(/\S*)?$")


class _Parametrizacion(BaseModel):
    """Campos comerciales que define el super_admin (specs gestion-condominios y modulos-plataforma)."""

    @field_validator("modulos", check_fields=False)
    @classmethod
    def _modulos(cls, v: list[str] | None) -> list[str] | None:
        return None if v is None else validar_modulos(v)

    @field_validator("portal_url", check_fields=False)
    @classmethod
    def _portal_url(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        v = v.strip()
        if not _URL_PORTAL.match(v):
            raise ValueError("La URL del portal debe comenzar con https://")
        return v

    @field_validator("dominios_sitio", check_fields=False)
    @classmethod
    def _dominios(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        normalizados = [normalizar_dominio(d) for d in v if d.strip()]
        return list(dict.fromkeys(normalizados))  # sin repetidos, conserva el orden

    @field_validator("color_primario", check_fields=False)
    @classmethod
    def _color(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not _COLOR.match(v.strip()):
            raise ValueError("El color debe tener el formato #RRGGBB")
        return v.strip().upper()


class CondominioCreate(_Parametrizacion):
    nombre: str
    rut_comunidad: str
    direccion: str | None = None
    plan_suscripcion: PlanSuscripcion
    activo: bool = True
    modulos: list[str] | None = None  # None = todos los del catálogo
    portal_url: str | None = None
    dominios_sitio: list[str] = []
    color_primario: str | None = None


class CondominioUpdate(_Parametrizacion):
    nombre: str | None = None
    direccion: str | None = None
    plan_suscripcion: PlanSuscripcion | None = None
    activo: bool | None = None
    # Las listas reemplazan por completo a las anteriores; un campo omitido no cambia
    modulos: list[str] | None = None
    portal_url: str | None = None
    dominios_sitio: list[str] | None = None
    color_primario: str | None = None  # null explícito = volver al color por defecto


class CondominioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    rut_comunidad: str
    direccion: str | None
    plan_suscripcion: str
    activo: bool
    created_at: datetime | None
    modulos: list[str]
    portal_url: str | None
    dominios_sitio: list[str]
    logo_url: str | None
    color_primario: str | None


MODULOS_POR_DEFECTO = list(MODULOS)
