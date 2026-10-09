"""
Las liquidaciones calculadas se descartan cuando cambian sus insumos (cambio pasos-del-periodo):
reabrir lecturas, editar el desglose, modificar o sincronizar una lectura. Así no se puede cerrar ni
publicar un período con montos desactualizados.
"""
import os
from datetime import date, datetime, timezone

from sqlalchemy import func, select

from app.core.security import create_access_token
from app.models.auditoria import AuditoriaLog
from app.models.boleta import BoletaMaestra
from app.models.condominio import Condominio
from app.models.condominio_modulo import CondominioModulo
from app.models.lectura import LecturaParcela
from app.models.liquidacion import LiquidacionParcela
from app.models.parcela import Parcela
from app.models.rol import Rol
from app.models.usuario import Usuario

TOMA = datetime(2099, 10, 30, 9, 0, tzinfo=timezone.utc)


async def _escenario(session, lecturas_cerradas=True):
    """Período corroborado, con 3 parcelas y sus lecturas tomadas."""
    c = Condominio(nombre="Condominio Vigentes", rut_comunidad=f"vigentes-{os.urandom(4).hex()}",
                   plan_suscripcion="basico", activo=True,
                   modulos=[CondominioModulo(modulo="portal"), CondominioModulo(modulo="energia")])
    session.add(c)
    await session.flush()
    rol_id = (await session.execute(select(Rol.id).where(Rol.nombre == "admin_condominio"))).scalar_one()
    admin = Usuario(nombre="Admin", email=f"vigentes-{os.urandom(3).hex()}@test.cl", password_hash="x",
                    rol_id=rol_id, condominio_id=c.id)
    session.add(admin)
    await session.flush()
    boleta = BoletaMaestra(condominio_id=c.id, periodo_mes=date(2099, 10, 1), estado="validada", creado_por=admin.id,
                           total_kwh_compania=800, monto_neto_electricidad_consumida=100_000,
                           monto_total_emision=119_000, lecturas_cerradas=lecturas_cerradas)
    session.add(boleta)
    await session.flush()
    lecturas = []
    for n, kwh in (("1", 100.0), ("2", 250.0), ("3", 400.0)):
        p = Parcela(condominio_id=c.id, numero_parcela=n, activa=True)
        session.add(p)
        await session.flush()
        lectura = LecturaParcela(parcela_id=p.id, boleta_id=boleta.id, lectura_anterior=1000.0,
                                 lectura_actual=1000.0 + kwh, kwh_consumidos=kwh, lector_id=admin.id, fecha_toma=TOMA)
        session.add(lectura)
        lecturas.append(lectura)
    await session.flush()
    cab = {"Authorization": f"Bearer {create_access_token(user_id=admin.id, rol='admin_condominio', condominio_id=c.id)}"}
    return boleta, lecturas, cab


async def _liquidaciones(session, boleta_id) -> int:
    return (await session.execute(
        select(func.count()).select_from(LiquidacionParcela).where(LiquidacionParcela.boleta_id == boleta_id))).scalar_one()


async def _calcular(c, cab, boleta_id):
    r = await c.post(f"/api/v1/liquidaciones/calcular/{boleta_id}", headers=cab)
    assert r.status_code == 200, r.text


async def test_reabrir_lecturas_descarta_y_obliga_a_recalcular(tx):
    c, session = tx
    boleta, _, cab = await _escenario(session)
    await _calcular(c, cab, boleta.id)
    assert await _liquidaciones(session, boleta.id) == 3

    r = await c.post(f"/api/v1/boletas/{boleta.id}/reabrir-lecturas", headers=cab)
    assert r.status_code == 200, r.text
    assert await _liquidaciones(session, boleta.id) == 0
    auditoria = (await session.execute(select(AuditoriaLog).where(
        AuditoriaLog.accion == "REABRIR_LECTURAS", AuditoriaLog.condominio_id == boleta.condominio_id))).scalar_one()
    assert auditoria.detalles["liquidaciones_descartadas"] == 3

    # Cerrar de nuevo las lecturas no basta: sin recalcular no se puede cerrar el período
    assert (await c.post(f"/api/v1/boletas/{boleta.id}/cerrar-lecturas", headers=cab)).status_code == 200
    assert (await c.post(f"/api/v1/boletas/{boleta.id}/cerrar-liquidaciones", headers=cab)).status_code == 409
    await _calcular(c, cab, boleta.id)
    assert (await c.post(f"/api/v1/boletas/{boleta.id}/cerrar-liquidaciones", headers=cab)).status_code == 200


async def test_editar_el_desglose_descarta(tx):
    c, session = tx
    boleta, _, cab = await _escenario(session)
    await _calcular(c, cab, boleta.id)
    r = await c.put(f"/api/v1/boletas/{boleta.id}/detalles", headers=cab, json={
        "total_kwh_compania": 800, "monto_neto_electricidad_consumida": 100_000, "monto_total_emision": 120_000,
        "items_detalle": []})
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "borrador"
    assert await _liquidaciones(session, boleta.id) == 0
    assert (await c.post(f"/api/v1/boletas/{boleta.id}/cerrar-liquidaciones", headers=cab)).status_code == 409


async def test_corregir_o_sincronizar_una_lectura_descarta(tx):
    c, session = tx
    boleta, lecturas, cab = await _escenario(session, lecturas_cerradas=False)

    await _calcular(c, cab, boleta.id)   # vista previa con las lecturas abiertas
    r = await c.patch(f"/api/v1/lecturas/{lecturas[0].id}", headers=cab, json={"lectura_actual": 1120.0})
    assert r.status_code == 200, r.text
    assert await _liquidaciones(session, boleta.id) == 0

    await _calcular(c, cab, boleta.id)
    await session.refresh(lecturas[1])
    r = await c.post("/api/v1/lecturas/sincronizar", headers=cab, json={"items": [{
        "lectura_id": lecturas[1].id, "lectura_actual": 1260.0, "fecha_toma": datetime.now(timezone.utc).isoformat(),
        "base": {"lectura_actual": lecturas[1].lectura_actual, "fecha_toma": lecturas[1].fecha_toma.isoformat()}}]})
    assert r.status_code == 200, r.text
    assert r.json()["resultados"][0]["estado"] == "aplicada"
    assert await _liquidaciones(session, boleta.id) == 0


async def test_una_sincronizacion_sin_cambios_no_descarta(tx):
    """Un reintento del mismo lote (nada aplicado de nuevo) no toca las liquidaciones."""
    c, session = tx
    boleta, lecturas, cab = await _escenario(session, lecturas_cerradas=False)
    await _calcular(c, cab, boleta.id)
    l = lecturas[2]
    r = await c.post("/api/v1/lecturas/sincronizar", headers=cab, json={"items": [{
        "lectura_id": l.id, "lectura_actual": l.lectura_actual, "fecha_toma": l.fecha_toma.isoformat(),
        "base": {"lectura_actual": 0, "fecha_toma": None}}]})
    assert r.json()["resultados"][0]["estado"] == "aplicada"
    assert await _liquidaciones(session, boleta.id) == 3
