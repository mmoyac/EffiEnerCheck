"""
Conciliación de pagos en línea en segundo plano (spec pagos-en-linea: «Conciliación automática»).

Cada 2 minutos revisa, consultando al proveedor por el mismo camino que el retorno y el webhook:
- las intenciones INICIADO de más de 5 minutos (avisos perdidos y las que ya vencieron);
- las EXPIRADO de las últimas 24 horas (pagos aprobados tarde).

Producción corre varios workers de uvicorn: un candado de PostgreSQL (pg_try_advisory_lock) hace que
una sola vuelta se ejecute a la vez. Sin túnel en desarrollo, los pagos se registran igual por aquí.
"""
import asyncio
import logging
from datetime import timedelta

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, engine
from app.models.pago import IntencionPago
from app.services.pagos import flujo
from app.services.pagos.pasarelas import ahora

log = logging.getLogger(__name__)

INTERVALO_SEGUNDOS = 120
ANTIGUEDAD_INICIADO = timedelta(minutes=5)
VENTANA_EXPIRADO = timedelta(hours=24)
# Identificador del candado de asesoría (cualquier entero fijo y propio de este proceso)
CANDADO = 731_406_221


async def pendientes(db: AsyncSession) -> list:
    momento = ahora()
    return list((
        await db.execute(
            select(IntencionPago.id)
            .where(or_(
                (IntencionPago.estado == "INICIADO") & (IntencionPago.created_at < momento - ANTIGUEDAD_INICIADO),
                (IntencionPago.estado == "EXPIRADO") & (IntencionPago.updated_at > momento - VENTANA_EXPIRADO),
            ))
            .order_by(IntencionPago.created_at)
        )
    ).scalars())


async def vuelta(db: AsyncSession) -> int | None:
    """Una pasada. None si otro proceso tiene el candado; si no, cuántas intenciones revisó."""
    # Candado de sesión en una conexión propia: `confirmar` hace commit por cada intención y un candado
    # de transacción se soltaría a la primera
    async with engine.connect() as candado:
        if not await candado.scalar(text("SELECT pg_try_advisory_lock(:c)"), {"c": CANDADO}):
            return None
        try:
            revisadas = 0
            for intencion_id in await pendientes(db):
                try:
                    await flujo.confirmar(db, intencion_id, "conciliacion")
                    revisadas += 1
                except Exception:  # noqa: BLE001 — una intención con problemas no detiene las demás
                    log.exception("Conciliación: error con el pago %s", intencion_id)
                    await db.rollback()
            await db.commit()
            return revisadas
        finally:
            await candado.execute(text("SELECT pg_advisory_unlock(:c)"), {"c": CANDADO})


async def bucle() -> None:
    """Tarea del lifespan: una vuelta cada INTERVALO_SEGUNDOS hasta que se cancele al apagar."""
    while True:
        await asyncio.sleep(INTERVALO_SEGUNDOS)
        try:
            async with AsyncSessionLocal() as db:
                revisadas = await vuelta(db)
            if revisadas:
                log.info("Conciliación de pagos: %s intención(es) revisada(s)", revisadas)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — la próxima vuelta lo reintenta
            log.exception("Conciliación de pagos: la vuelta falló")
