from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.schemas.parcela import ParcelaResponse
from app.schemas.rol import RolResponse


class UsuarioCreate(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    rol_id: int
    condominio_id: int | None = None
    parcela_ids: list[int] = []  # IDs de parcelas asignadas (uno o más para parceleros)

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


class UsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: str
    rol_id: int
    condominio_id: int | None
    ultimo_login: datetime | None
    parcelas: list[ParcelaResponse] = []


class UsuarioDetailResponse(UsuarioResponse):
    """Respuesta extendida que incluye el rol completo."""
    rol: RolResponse
