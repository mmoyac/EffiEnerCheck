from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.modulos import MODULOS, Modulo
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.condominio_modulo import CondominioModulo
from app.models.usuario import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# Jerarquía de roles definida en AGENTS.md
ROLES = ("super_admin", "admin_condominio", "lector", "parcelero", "porteria")


SIN_PORTAL = "Tu condominio no tiene contratado el portal de administración"


async def modulos_del_condominio(db: AsyncSession, condominio_id: int | None) -> list[str]:
    """Módulos habilitados del condominio, en el orden del catálogo."""
    if condominio_id is None:
        return []
    filas = await db.execute(
        select(CondominioModulo.modulo).where(CondominioModulo.condominio_id == condominio_id)
    )
    tiene = set(filas.scalars())
    return [m for m in MODULOS if m in tiene]


async def modulos_del_usuario(db: AsyncSession, user: Usuario) -> list[str]:
    """El super_admin tiene el catálogo completo; el resto, los de su condominio."""
    if user.rol.nombre == "super_admin":
        return list(MODULOS)
    return await modulos_del_condominio(db, user.condominio_id)


def exigir_portal(user: Usuario, modulos: list[str]) -> None:
    """Sin el producto `portal`, los usuarios del condominio no entran (spec modulos-plataforma)."""
    if user.rol.nombre != "super_admin" and user.condominio_id is not None and "portal" not in modulos:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SIN_PORTAL)


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
    # Sesiones cerradas por un cambio de clave: el token es anterior a clave_cambiada_en.
    # iat va en segundos enteros; se compara contra la hora del cambio truncada al segundo.
    if user.clave_cambiada_en is not None:
        iat = payload.get("iat")
        if not isinstance(iat, int) or iat < int(user.clave_cambiada_en.timestamp()):
            raise credentials_error

    # Se consulta en cada petición (no va en el JWT): quitar un módulo tiene efecto inmediato.
    # Queda en el objeto para que modulo_requerido no repita la consulta en la misma petición.
    modulos = await modulos_del_usuario(db, user)
    exigir_portal(user, modulos)
    user.modulos = modulos
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

# Cualquier usuario autenticado, EXCEPTO porteria. Es explícito a propósito: varios endpoints
# AnyRoleRequired solo restringen por parcela cuando el rol es parcelero, así que un rol nuevo
# agregado aquí heredaría acceso a todo el condominio.
AnyRoleRequired = require_roles("super_admin", "admin_condominio", "lector", "parcelero")

# Venta de rifas: administración y portería
PorteriaRequired = require_roles("super_admin", "admin_condominio", "porteria")

# Consulta de rifas: los cinco roles. Solo para endpoints de rifas.
RifaAccesoRequired = require_roles(*ROLES)


# ---------------------------------------------------------------------------
# Guarda de módulo: se aplica al incluir el router (app/api/v1/router.py)
# ---------------------------------------------------------------------------

def modulo_requerido(modulo: Modulo):
    """
    Exige que el condominio del usuario tenga habilitado `modulo`, además de la guarda de rol de
    cada endpoint. El super_admin pasa siempre.

    Uso: api_router.include_router(x.router, dependencies=[Depends(modulo_requerido("energia"))])
    """
    async def dependency(
        current_user: Annotated[Usuario, Depends(get_current_user)],
    ) -> None:
        if modulo not in current_user.modulos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"El módulo {modulo} no está habilitado para este condominio",
            )

    return dependency


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
