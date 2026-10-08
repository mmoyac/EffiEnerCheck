from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator

from app.schemas.parcela import ParcelaResponse
from app.core.security import validar_clave
from app.schemas.rol import RolResponse
from app.utils.telefono import normalizar_telefono


class UsuarioCreate(BaseModel):
    nombre: str
    email: EmailStr
    # Sin contraseña la cuenta queda pendiente y el usuario crea la suya con una invitación
    password: str | None = None
    rol_id: int
    condominio_id: int | None = None
    parcela_ids: list[int] = []  # IDs de parcelas asignadas (uno o más para comuneros)
    telefono: str | None = None

    @field_validator("telefono", mode="before")
    @classmethod
    def telefono_normalizado(cls, v: str | None) -> str | None:
        return normalizar_telefono(v)

    @field_validator("password")
    @classmethod
    def password_politica(cls, v: str | None) -> str | None:
        return None if v is None else validar_clave(v)


class UsuarioUpdate(BaseModel):
    nombre: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    rol_id: int | None = None
    condominio_id: int | None = None
    parcela_ids: list[int] | None = None  # None = no cambiar; [] = quitar todas
    telefono: str | None = None

    @field_validator("telefono", mode="before")
    @classmethod
    def telefono_normalizado(cls, v: str | None) -> str | None:
        return normalizar_telefono(v)

    @field_validator("password")
    @classmethod
    def password_politica(cls, v: str | None) -> str | None:
        return None if v is None else validar_clave(v)


class UsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: str
    rol_id: int
    condominio_id: int | None
    ultimo_login: datetime | None
    telefono: str | None = None
    parcelas: list[ParcelaResponse] = []
    # Solo para calcular el estado: nunca sale en la respuesta
    password_hash: str | None = Field(default=None, exclude=True, repr=False)

    @computed_field
    @property
    def estado(self) -> Literal["pendiente", "activa"]:
        """pendiente = todavía no crea su clave (no puede iniciar sesión)."""
        return "activa" if self.password_hash else "pendiente"


class UsuarioDetailResponse(UsuarioResponse):
    """Respuesta extendida que incluye el rol completo."""
    rol: RolResponse


class CondominioMarca(BaseModel):
    """Identidad del condominio que el portal muestra (nombre, logo y color)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    logo_url: str | None
    color_primario: str | None


class SesionResponse(UsuarioDetailResponse):
    """GET /auth/me: el usuario, los módulos habilitados de su condominio y su marca."""
    modulos: list[str]
    condominio: CondominioMarca | None = None
