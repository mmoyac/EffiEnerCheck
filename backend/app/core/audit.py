from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auditoria import AuditoriaLog


async def registrar_auditoria(
    db: AsyncSession,
    *,
    usuario_id: int,
    condominio_id: int | None,
    accion: str,
    detalles: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """Agrega un log de auditoría a la sesión actual (sin commit propio)."""
    log = AuditoriaLog(
        usuario_id=usuario_id,
        condominio_id=condominio_id,
        accion=accion,
        detalles=detalles,
        ip_address=ip_address,
    )
    db.add(log)
