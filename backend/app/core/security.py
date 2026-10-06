from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Claves que nunca se aceptan: la de los usuarios de prueba (app/db/seeds/usuarios.py) es pública.
CLAVES_CONOCIDAS = ("admin123",)
LARGO_MINIMO_CLAVE = 10


def validar_clave(clave: str) -> str:
    """Política única de claves (spec acceso-por-enlace). ValueError con el motivo si no la cumple."""
    if len(clave) < LARGO_MINIMO_CLAVE:
        raise ValueError(f"La clave debe tener al menos {LARGO_MINIMO_CLAVE} caracteres")
    if clave in CLAVES_CONOCIDAS:
        raise ValueError("Esa clave es conocida públicamente: elige otra")
    return clave


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """False para una cuenta pendiente (sin clave): responde igual que una clave incorrecta."""
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: int,
    rol: str,
    condominio_id: int | None = None,
) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "rol": rol,
        "condominio_id": condominio_id,
        # iat: get_current_user rechaza los tokens emitidos antes del último cambio de clave
        "iat": int(ahora.timestamp()),
        "exp": ahora + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decodifica el token. Retorna {} si es inválido o expirado."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return {}
