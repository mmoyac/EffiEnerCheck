"""Asignación de claves: un solo lugar que aplica la política, guarda el hash y cierra las sesiones abiertas."""
from datetime import datetime, timezone

from app.core.security import hash_password, validar_clave
from app.models.usuario import Usuario


def asignar_clave(usuario: Usuario, clave: str) -> None:
    """Valida la clave (ValueError si no cumple), guarda su hash y marca clave_cambiada_en.

    Desde ese momento get_current_user rechaza los JWT del usuario emitidos antes (spec autenticacion).
    """
    validar_clave(clave)
    usuario.password_hash = hash_password(clave)
    usuario.clave_cambiada_en = datetime.now(timezone.utc)
