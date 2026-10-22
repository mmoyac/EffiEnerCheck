"""
Consumidor de pagos en línea de las rifas: una intención paga una CompraRifa (`referencia_id`).

Mientras la intención está INICIADO, la compra queda pendiente con sus números reservados. Al
liberarla se anula como cualquier compra (sus números quedan libres). Un pago aprobado después de
anulada la compra la reactiva si sus números siguen libres y la rifa sigue abierta; si no, queda en
revisión. Ver openspec/changes/pasarelas-pago/specs/rifas-solidarias.
"""
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import registrar_auditoria
from app.models.pago import IntencionPago
from app.models.rifa import CompraRifa, Rifa, RifaNumero


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def medios_permitidos(rifa: Rifa, canal: str, hay_pasarela: bool) -> list[str]:
    """
    Formas de pago disponibles por canal, dentro de las que acepta la rifa:
    - portal (comunero): pago en línea y gasto común. Sin pasarela disponible (o si la rifa no acepta
      pago en línea), la transferencia manual con voucher, igual que en portería.
    - portería y administración: las de la rifa, salvo el pago en línea.
    """
    if canal != "portal":
        return [m for m in rifa.medios_pago if m != "en_linea"]
    permitidos = []
    if "en_linea" in rifa.medios_pago and hay_pasarela:
        permitidos.append("en_linea")
    elif "en_linea" in rifa.medios_pago or "transferencia" in rifa.medios_pago:
        permitidos.append("transferencia")
    if "gasto_comun" in rifa.medios_pago:
        permitidos.append("gasto_comun")
    return permitidos


def descripcion(rifa: Rifa, numeros: list[int]) -> str:
    etiqueta = "número" if len(numeros) == 1 else "números"
    nombre = rifa.nombre if rifa.nombre.lower().startswith("rifa") else f"Rifa {rifa.nombre}"
    return f"{nombre} – {etiqueta} {', '.join(map(str, sorted(numeros)))}"


# Concepto de las intenciones de pago de las rifas (también filtra la bandeja de quien administra rifas)
CONCEPTO_RIFA = "rifa_compra"


class _ConsumidorRifa:
    concepto = CONCEPTO_RIFA

    async def _compra_y_rifa(self, db: AsyncSession, intencion: IntencionPago) -> tuple[CompraRifa | None, Rifa | None]:
        compra = await db.get(CompraRifa, intencion.referencia_id, populate_existing=True)
        if compra is None:
            return None, None
        # Serializa con compras, anulaciones y el cierre de la misma rifa
        rifa = (
            await db.execute(select(Rifa).where(Rifa.id == compra.rifa_id).with_for_update().execution_options(populate_existing=True))
        ).scalar_one()
        return compra, rifa

    async def aplicar(self, db: AsyncSession, intencion: IntencionPago) -> str | None:
        compra, rifa = await self._compra_y_rifa(db, intencion)
        if compra is None or compra.intencion_pago_id != intencion.id:
            return "La compra ya no corresponde a este pago"
        if compra.anulada:
            if rifa.estado != "abierta":
                return "La compra estaba anulada y la rifa ya está cerrada"
            tomados = (
                await db.execute(
                    select(RifaNumero.numero).where(RifaNumero.rifa_id == rifa.id, RifaNumero.numero.in_(compra.numeros))
                )
            ).scalars().all()
            if tomados:
                return f"Números ya vendidos a otra compra: {', '.join(map(str, sorted(tomados)))}"
            db.add_all(RifaNumero(compra_id=compra.id, rifa_id=rifa.id, numero=n) for n in compra.numeros)
            compra.anulada = False
            compra.anulada_at = None
            compra.anulada_por_id = None
            await registrar_auditoria(
                db, usuario_id=intencion.usuario_id, condominio_id=rifa.condominio_id, accion="REACTIVAR_COMPRA_RIFA",
                detalles={"rifa_id": rifa.id, "compra_id": compra.id, "folio": compra.folio_texto,
                          "numeros": compra.numeros, "intencion_pago_id": str(intencion.id)},
            )
        if not compra.pagada:
            compra.pagada = True
            compra.pagada_at = _ahora()
        return None

    async def liberar(self, db: AsyncSession, intencion: IntencionPago, motivo: str) -> None:
        compra, rifa = await self._compra_y_rifa(db, intencion)
        if compra is None or compra.anulada or compra.pagada or compra.intencion_pago_id != intencion.id:
            return
        await db.execute(delete(RifaNumero).where(RifaNumero.compra_id == compra.id))
        compra.anulada = True
        compra.anulada_at = _ahora()
        await registrar_auditoria(
            db, usuario_id=intencion.usuario_id, condominio_id=rifa.condominio_id, accion="ANULAR_COMPRA_RIFA",
            detalles={
                "rifa_id": rifa.id, "compra_id": compra.id, "folio": compra.folio_texto,
                "parcela_id": compra.parcela_id, "numeros": compra.numeros, "monto": compra.monto,
                "medio_pago": compra.medio_pago, "pagada": False, "canal": compra.canal,
                "origen": "pago_en_linea", "motivo": motivo, "intencion_pago_id": str(intencion.id),
            },
        )

    def volver_a(self, intencion: IntencionPago) -> str | None:
        return "/mis-rifas"


CONSUMIDOR = _ConsumidorRifa()
