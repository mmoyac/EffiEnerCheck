from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.schemas.parcela import ParcelaResponse
from app.schemas.rol import RolResponse
from app.utils.telefono import normalizar_telefono


class UsuarioCreate(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    rol_id: int
    condominio_id: int | None = None
    parcela_ids: list[int] = []  # IDs de parcelas asignadas (uno o más para parceleros)
    telefono: str | None = None

    @field_validator("telefono", mode="before")
    @classmethod
    def telefono_normalizado(cls, v: str | None) -> str | None:
        return normalizar_telefono(v)

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


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
