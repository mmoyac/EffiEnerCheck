from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.usuario import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# Jerarquía de roles definida en AGENTS.md
ROLES = ("super_admin", "admin_condominio", "lector", "parcelero")


# ---------------------------------------------------------------------------
# Dependencia base: extrae y valida el usuario del JWT
# ---------------------------------------------------------------------------

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Usuario:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise credentials_error

    result = await db.execute(
        select(Usuario)
        .options(selectinload(Usuario.rol), selectinload(Usuario.parcelas))
        .where(Usuario.id == int(user_id))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_error
    return user


# ---------------------------------------------------------------------------
# Fábrica de guardas RBAC
# ---------------------------------------------------------------------------

def require_roles(*roles: str):
    """
    Retorna una dependencia FastAPI que valida que el usuario autenticado
    tenga uno de los roles indicados.

    Uso: Depends(require_roles("super_admin", "admin_condominio"))
    """
    async def dependency(
        current_user: Annotated[Usuario, Depends(get_current_user)],
    ) -> Usuario:
        if current_user.rol.nombre not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Roles permitidos: {', '.join(roles)}",
            )
        return current_user

    return dependency


# ---------------------------------------------------------------------------
# Guardas pre-construidas (usar directamente con Depends)
# ---------------------------------------------------------------------------

# Solo super_admin
SuperAdminRequired = require_roles("super_admin")

# Administración del condominio
AdminRequired = require_roles("super_admin", "admin_condominio")

# Quienes toman lecturas de remarcadores
LectorRequired = require_roles("super_admin", "admin_condominio", "lector")

# Cualquier usuario autenticado
AnyRoleRequired = require_roles(*ROLES)


# ---------------------------------------------------------------------------
# Dependencia de multitenancy
# ---------------------------------------------------------------------------

async def get_tenant_id(
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> int | None:
    """
    Retorna el condominio_id activo para filtrar queries.

    - super_admin  → None  (puede consultar todos los condominios)
    - resto        → condominio_id del usuario (garantiza aislamiento)

    Los servicios deben aplicar WHERE condominio_id = tenant_id cuando
    tenant_id no sea None.
    """
    if current_user.rol.nombre == "super_admin":
        return None
    if current_user.condominio_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario sin condominio asignado. Contacta al administrador.",
        )
    return current_user.condominio_id


# ---------------------------------------------------------------------------
# Tipos anotados listos para usar en firmas de endpoints
# ---------------------------------------------------------------------------

CurrentUser = Annotated[Usuario, Depends(get_current_user)]
TenantId = Annotated[int | None, Depends(get_tenant_id)]
