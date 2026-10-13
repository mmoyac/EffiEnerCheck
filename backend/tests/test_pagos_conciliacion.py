"""Conciliación de pagos en línea en segundo plano (spec pagos-en-linea: «Conciliación automática»)."""
from datetime import timedelta

from sqlalchemy import text

from app.db.session import engine
from app.services.pagos import conciliacion
from app.services.pagos.pasarelas import ahora
from tests.test_pagos_flujo import _compra, _iniciar, _intencion, _numeros, falso  # noqa: F401 — fixture


async def _envejecer(s, intencion_id, *, minutos=6, vencida=False):
    i = await _intencion(s, intencion_id)
    i.created_at = ahora() - timedelta(minutes=minutos)
    if vencida:
        i.vence_at = ahora() - timedelta(minutes=1)
    await s.flush()


async def test_aviso_perdido_se_confirma(tx, falso):
    c, s = tx
    _, compra, pago = await _iniciar(c, s, falso)
    await _envejecer(s, pago["intencion_id"])
    falso.estado = "APROBADO"

    assert await conciliacion.vuelta(s) >= 1
    assert (await _intencion(s, pago["intencion_id"])).estado == "CONFIRMADO"
    assert (await _compra(s, compra["id"])).pagada is True


async def test_recien_iniciada_no_se_consulta(tx, falso):
    c, s = tx
    _, _, pago = await _iniciar(c, s, falso)
    falso.llamadas.clear()
    await conciliacion.vuelta(s)
    assert falso.llamadas == []
    assert (await _intencion(s, pago["intencion_id"])).estado == "INICIADO"


async def test_vencida_y_pendiente_expira_y_libera(tx, falso):
    c, s = tx
    rifa, compra, pago = await _iniciar(c, s, falso)
    await _envejecer(s, pago["intencion_id"], minutos=20, vencida=True)

    await conciliacion.vuelta(s)
    assert (await _intencion(s, pago["intencion_id"])).estado == "EXPIRADO"
    assert (await _compra(s, compra["id"])).anulada is True
    assert await _numeros(s, rifa["id"]) == []

    # La siguiente vuelta revisa las expiradas: si el proveedor la aprobó tarde, se aplica
    falso.estado = "APROBADO"
    await conciliacion.vuelta(s)
    assert (await _intencion(s, pago["intencion_id"])).estado == "CONFIRMADO"


async def test_con_el_candado_tomado_no_hace_nada(tx, falso):
    c, s = tx
    _, _, pago = await _iniciar(c, s, falso)
    await _envejecer(s, pago["intencion_id"])
    falso.estado = "APROBADO"
    falso.llamadas.clear()

    async with engine.connect() as otro_proceso:
        assert await otro_proceso.scalar(text("SELECT pg_try_advisory_lock(:c)"), {"c": conciliacion.CANDADO})
        try:
            assert await conciliacion.vuelta(s) is None
        finally:
            await otro_proceso.execute(text("SELECT pg_advisory_unlock(:c)"), {"c": conciliacion.CANDADO})

    assert falso.llamadas == []
    assert (await _intencion(s, pago["intencion_id"])).estado == "INICIADO"


async def test_error_en_una_no_detiene_las_demas(tx, falso, monkeypatch):
    c, s = tx
    _, _, pago = await _iniciar(c, s, falso)
    await _envejecer(s, pago["intencion_id"])
    original = conciliacion.flujo.confirmar
    llamadas = []

    async def falla_una(db, intencion_id, origen):
        llamadas.append(intencion_id)
        if len(llamadas) == 1:
            raise RuntimeError("boom")
        return await original(db, intencion_id, origen)

    monkeypatch.setattr(conciliacion.flujo, "confirmar", falla_una)
    # No lanza aunque la primera falle
    assert await conciliacion.vuelta(s) is not None
