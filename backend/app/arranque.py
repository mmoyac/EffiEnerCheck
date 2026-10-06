"""
Arranque del backend en producción (lo llama entrypoint.sh antes de uvicorn).

    python -m app.arranque

1. Con ENTORNO=produccion, valida que la configuración no tenga valores de ejemplo.
2. Espera a que PostgreSQL acepte conexiones.
3. Aplica las migraciones (alembic upgrade head).
4. Carga los catálogos (roles y menús) y crea el super admin si no existe ninguno.
5. Con ENTORNO=produccion, se niega a seguir si alguna cuenta conserva la clave del seed.
6. Valida los archivos de contenido de la landing (app/sitio/contenido/): uno inválido detiene el arranque.

Los datos del condominio (parcelas y residentes) NO se cargan aquí: vienen de la planilla de
residentes, con `python -m app.db.cargar_residentes` (ver DEPLOY.md). Es idempotente: se corre en
cada arranque y en CI dos veces seguidas.
"""
import asyncio
import os
import subprocess
import sys

from sqlalchemy import select, text

from app.core.config import settings
from app.core.security import CLAVES_CONOCIDAS, hash_password, verify_password
from app.db.seeds.menus import seed_menus
from app.db.seeds.roles import seed_roles
from app.db.session import AsyncSessionLocal, engine
from app.services.sitio import ContenidoSitioInvalido, cargar_contenidos
from app.models.rol import Rol
from app.models.usuario import Usuario

import app.db.base  # noqa: F401 — registra todos los modelos (relaciones por nombre)

VALOR_EJEMPLO_SECRET_KEY = ("changeme-in-production", "your-super-secret-key-change-in-production")


class ArranqueError(RuntimeError):
    pass


def validar_configuracion() -> None:
    errores = [
        f"{nombre} sigue con el valor de ejemplo de .env.prod.example"
        for nombre, valor in sorted(os.environ.items()) if valor.startswith("CAMBIAR")
    ]
    if settings.SECRET_KEY in VALOR_EJEMPLO_SECRET_KEY or len(settings.SECRET_KEY) < 32:
        errores.append("SECRET_KEY debe tener al menos 32 caracteres y no ser el valor de ejemplo")
    if settings.DEBUG:
        errores.append("DEBUG debe ser false (con true se registran las consultas SQL)")
    if not settings.GEMINI_API_KEY:
        errores.append("falta GEMINI_API_KEY (OCR de boletas)")
    if errores:
        raise ArranqueError("Configuración inválida para producción:\n  - " + "\n  - ".join(errores))


async def esperar_base(intentos: int = 30) -> None:
    for i in range(intentos):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001 — cualquier error de conexión se reintenta
            if i == intentos - 1:
                raise ArranqueError(f"PostgreSQL no responde: {exc}") from exc
            await asyncio.sleep(2)


def migrar() -> None:
    resultado = subprocess.run(["alembic", "upgrade", "head"])
    if resultado.returncode != 0:
        raise ArranqueError("Falló alembic upgrade head")


async def crear_super_admin(db) -> None:
    existe = await db.execute(
        select(Usuario.id).join(Rol).where(Rol.nombre == "super_admin").limit(1)
    )
    if existe.first():
        return
    if not settings.SUPERADMIN_EMAIL or not settings.SUPERADMIN_PASSWORD:
        if settings.es_produccion:
            raise ArranqueError("No hay super admin: define SUPERADMIN_EMAIL y SUPERADMIN_PASSWORD en el .env")
        return
    if len(settings.SUPERADMIN_PASSWORD) < 12 or settings.SUPERADMIN_PASSWORD in CLAVES_CONOCIDAS:
        raise ArranqueError("SUPERADMIN_PASSWORD debe tener al menos 12 caracteres y no ser una clave conocida")
    rol = (await db.execute(select(Rol).where(Rol.nombre == "super_admin"))).scalar_one()
    db.add(Usuario(
        nombre=settings.SUPERADMIN_NOMBRE,
        email=settings.SUPERADMIN_EMAIL.strip().lower(),
        password_hash=hash_password(settings.SUPERADMIN_PASSWORD),
        rol_id=rol.id,
        condominio_id=None,
    ))
    await db.commit()
    print(f"  ✓ super admin creado: {settings.SUPERADMIN_EMAIL}")


async def usuarios_con_clave_conocida(db) -> list[str]:
    """Emails de las cuentas cuya clave es una de CLAVES_CONOCIDAS (bcrypt una vez por hash distinto)."""
    filas = (await db.execute(
        select(Usuario.email, Usuario.password_hash).where(Usuario.password_hash.is_not(None))  # sin pendientes
    )).all()
    por_hash: dict[str, list[str]] = {}
    for email, password_hash in filas:
        por_hash.setdefault(password_hash, []).append(email)
    expuestos: list[str] = []
    for password_hash, emails in por_hash.items():
        if any(verify_password(clave, password_hash) for clave in CLAVES_CONOCIDAS):
            expuestos.extend(emails)
    return sorted(expuestos)


def validar_contenido_sitio() -> None:
    try:
        contenidos = cargar_contenidos()
    except ContenidoSitioInvalido as exc:
        raise ArranqueError(f"contenido de la landing inválido: {exc}") from exc
    print(f"  ✓ landing: {len(contenidos)} RUT con contenido")


async def preparar() -> None:
    if settings.es_produccion:
        validar_configuracion()
    validar_contenido_sitio()
    await esperar_base()
    migrar()
    async with AsyncSessionLocal() as db:
        await seed_roles(db)
        await seed_menus(db)
        await crear_super_admin(db)
        if settings.es_produccion:
            expuestos = await usuarios_con_clave_conocida(db)
            if expuestos:
                # Sin los correos: este mensaje llega a los logs públicos del deploy en GitHub Actions.
                raise ArranqueError(
                    f"{len(expuestos)} cuenta(s) tienen la clave pública del seed. Lístalas y cámbialas "
                    "con app.db.cambiar_clave (DEPLOY.md §8)"
                )
    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(preparar())
    except ArranqueError as exc:
        print(f"ERROR de arranque: {exc}", file=sys.stderr)
        sys.exit(1)
