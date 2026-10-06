from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    rol: str
    condominio_id: int | None = None


# ---- Enlaces de acceso y gestión de la propia clave (spec acceso-por-enlace) ----------------------------

class RecuperarRequest(BaseModel):
    email: EmailStr


class EnlaceRequest(BaseModel):
    token: str


class EnlaceInfo(BaseModel):
    tipo: str          # invitacion | recuperacion
    nombre: str


class EstablecerClaveRequest(BaseModel):
    token: str
    password: str


class CambiarClaveRequest(BaseModel):
    actual: str
    nueva: str
