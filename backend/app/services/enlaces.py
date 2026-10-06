"""Enlaces de acceso de un solo uso: invitación (7 días) y recuperación (1 hora). Spec acceso-por-enlace.

El token solo existe en el enlace: en la base se guarda su sha256. Va en el fragmento de la URL (#),
que el navegador no envía al servidor, así que no queda en logs ni en el encabezado Referer.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.condominio import Condominio
from app.models.enlace_acceso import EnlaceAcceso
from app.models.usuario import Usuario
from app.services import correo

VIGENCIA = {"invitacion": timedelta(days=7), "recuperacion": timedelta(hours=1)}
RUTA = {"invitacion": "crear-clave", "recuperacion": "restablecer-clave"}


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


async def emitir(db: AsyncSession, usuario: Usuario, tipo: str) -> str:
    """Anula los enlaces vigentes del usuario y del tipo, guarda uno nuevo y devuelve su token."""
    ahora = _ahora()
    await db.execute(
        update(EnlaceAcceso)
        .where(EnlaceAcceso.usuario_id == usuario.id, EnlaceAcceso.tipo == tipo,
               EnlaceAcceso.usado_en.is_(None), EnlaceAcceso.anulado_en.is_(None))
        .values(anulado_en=ahora)
    )
    token = secrets.token_urlsafe(32)   # 256 bits
    db.add(EnlaceAcceso(usuario_id=usuario.id, tipo=tipo, token_hash=_hash(token),
                        creado_en=ahora, expira_en=ahora + VIGENCIA[tipo]))
    await db.flush()
    return token


async def vigente(db: AsyncSession, token: str) -> EnlaceAcceso | None:
    """El enlace del token si sigue vigente (no usado, no anulado, no vencido); si no, None."""
    if not token or len(token) > 200:
        return None
    return (await db.execute(
        select(EnlaceAcceso).where(
            EnlaceAcceso.token_hash == _hash(token),
            EnlaceAcceso.usado_en.is_(None),
            EnlaceAcceso.anulado_en.is_(None),
            EnlaceAcceso.expira_en > _ahora(),
        ).with_for_update()
    )).scalar_one_or_none()


def marcar_usado(enlace: EnlaceAcceso) -> None:
    enlace.usado_en = _ahora()


async def portal_de(db: AsyncSession, usuario: Usuario) -> str:
    portal_url = None
    if usuario.condominio_id is not None:
        portal_url = (await db.execute(
            select(Condominio.portal_url).where(Condominio.id == usuario.condominio_id)
        )).scalar_one_or_none()
    return (portal_url or settings.PORTAL_URL_POR_DEFECTO).rstrip("/")


async def url_de(db: AsyncSession, usuario: Usuario, tipo: str, token: str) -> str:
    return f"{await portal_de(db, usuario)}/{RUTA[tipo]}#{token}"


async def nombre_condominio(db: AsyncSession, usuario: Usuario) -> str:
    """Nombre visible del remitente y del portal en los mensajes."""
    if usuario.condominio_id is None:
        return "Administración"
    return (await db.execute(
        select(Condominio.nombre).where(Condominio.id == usuario.condominio_id)
    )).scalar_one_or_none() or "Administración"


async def preparar_correo(db: AsyncSession, usuario: Usuario, tipo: str) -> tuple[str, dict]:
    """Emite el enlace, lo confirma en la base y arma el correo. Devuelve (url, kwargs de correo.enviar).

    El commit va antes del envío: un correo nunca debe llevar un enlace que no quedó guardado.
    """
    token = await emitir(db, usuario, tipo)
    url = await url_de(db, usuario, tipo, token)
    condominio = await nombre_condominio(db, usuario)
    await db.commit()
    plantilla = correo.invitacion if tipo == "invitacion" else correo.recuperacion
    asunto, texto, html = plantilla(usuario.nombre, condominio, url)
    return url, {"destino": usuario.email, "asunto": asunto, "texto": texto, "html": html,
                 "nombre_remitente": condominio}
