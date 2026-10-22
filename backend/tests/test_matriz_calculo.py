"""
Matriz de cálculo de la luz (cambio matriz-calculo-luz): el condominio tiene una por defecto, cada período la
copia al crearse y solo el super_admin la cambia, con el período abierto.
"""
import os

from sqlalchemy import func, select

from app.core.security import create_access_token
from app.models.auditoria import AuditoriaLog
from app.models.boleta import BoletaMaestra
from app.models.liquidacion import LiquidacionParcela
from app.models.rol import Rol
from app.models.usuario import Usuario
from tests.test_liquidaciones_vigentes import _calcular, _escenario


async def _super_admin(session):
    rol_id = (await session.execute(select(Rol.id).where(Rol.nombre == "super_admin"))).scalar_one()
    u = Usuario(nombre="Super", email=f"super-{os.urandom(3).hex()}@test.cl", password_hash="x", rol_id=rol_id)
    session.add(u)
    await session.flush()
    return {"Authorization": f"Bearer {create_access_token(user_id=u.id, rol='super_admin', condominio_id=None)}"}


async def _liquidaciones(session, boleta_id):
    return (await session.execute(select(LiquidacionParcela).where(LiquidacionParcela.boleta_id == boleta_id))).scalars().all()


async def test_super_admin_cambia_la_matriz_y_descarta_lo_calculado(tx):
    c, session = tx
    boleta, _, cab = await _escenario(session)
    sup = await _super_admin(session)
    await _calcular(c, cab, boleta.id)

    r = await c.put(f"/api/v1/boletas/{boleta.id}/matriz-calculo", json={"matriz_calculo": "cargo_fijo"}, headers=sup)
    assert r.status_code == 200, r.text
    assert r.json()["matriz_calculo"] == "cargo_fijo"
    assert await _liquidaciones(session, boleta.id) == []
    auditoria = (await session.execute(select(AuditoriaLog).where(
        AuditoriaLog.accion == "CAMBIAR_MATRIZ_CALCULO", AuditoriaLog.condominio_id == boleta.condominio_id))).scalar_one()
    assert auditoria.detalles == {"boleta_id": boleta.id, "antes": "fijo_y_variable", "despues": "cargo_fijo",
                                  "liquidaciones_descartadas": 3}

    # Recalculado con la nueva matriz: sin prorrateo variable y cuadrado con la emisión
    await _calcular(c, cab, boleta.id)
    liqs = await _liquidaciones(session, boleta.id)
    assert sum(l.total_pagar_mes for l in liqs) == 119_000
    assert all(l.monto_prorrateo_variable == 0 for l in liqs)


async def test_admin_condominio_no_cambia_la_matriz(tx):
    c, session = tx
    boleta, _, cab = await _escenario(session)
    r = await c.put(f"/api/v1/boletas/{boleta.id}/matriz-calculo", json={"matriz_calculo": "cargo_fijo"}, headers=cab)
    assert r.status_code == 403


async def test_periodo_cerrado_no_cambia_la_matriz(tx):
    c, session = tx
    boleta, _, cab = await _escenario(session)
    sup = await _super_admin(session)
    await _calcular(c, cab, boleta.id)
    assert (await c.post(f"/api/v1/boletas/{boleta.id}/cerrar-liquidaciones", headers=cab)).status_code == 200

    r = await c.put(f"/api/v1/boletas/{boleta.id}/matriz-calculo", json={"matriz_calculo": "cargo_fijo"}, headers=sup)
    assert r.status_code == 409
    assert len(await _liquidaciones(session, boleta.id)) == 3


async def test_matriz_invalida(tx):
    c, session = tx
    boleta, _, _ = await _escenario(session)
    sup = await _super_admin(session)
    r = await c.put(f"/api/v1/boletas/{boleta.id}/matriz-calculo", json={"matriz_calculo": "otra"}, headers=sup)
    assert r.status_code == 422


async def test_el_periodo_nuevo_copia_la_matriz_del_condominio(tx):
    c, session = tx
    boleta, _, cab = await _escenario(session)
    sup = await _super_admin(session)
    # Cerrar el período existente para poder crear el siguiente
    await _calcular(c, cab, boleta.id)
    assert (await c.post(f"/api/v1/boletas/{boleta.id}/cerrar-liquidaciones", headers=cab)).status_code == 200

    r = await c.patch(f"/api/v1/condominios/{boleta.condominio_id}", json={"matriz_calculo_luz": "cargo_fijo"},
                      headers=sup)
    assert r.status_code == 200, r.text
    assert r.json()["matriz_calculo_luz"] == "cargo_fijo"
    auditoria = (await session.execute(select(AuditoriaLog).where(
        AuditoriaLog.accion == "UPDATE_CONDOMINIO", AuditoriaLog.condominio_id == boleta.condominio_id))).scalar_one()
    assert auditoria.detalles["despues"] == {"matriz_calculo_luz": "cargo_fijo"}

    r = await c.post("/api/v1/boletas/", json={"aceptar_sin_lectura_anterior": True}, headers=cab)
    assert r.status_code == 201, r.text
    assert r.json()["matriz_calculo"] == "cargo_fijo"
    # El período anterior conserva la suya
    await session.refresh(boleta)
    assert boleta.matriz_calculo == "fijo_y_variable"


async def test_admin_condominio_no_cambia_la_matriz_del_condominio(tx):
    c, session = tx
    boleta, _, cab = await _escenario(session)
    r = await c.patch(f"/api/v1/condominios/{boleta.condominio_id}", json={"matriz_calculo_luz": "cargo_fijo"},
                      headers=cab)
    assert r.status_code == 403
