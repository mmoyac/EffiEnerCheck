"""Sincronización de lecturas tomadas sin conexión (cambio lecturas-sin-conexion)."""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.models.auditoria import AuditoriaLog
from app.models.boleta import BoletaMaestra
from app.models.condominio import Condominio
from app.models.lectura import LecturaParcela
from app.models.parcela import Parcela
from app.models.usuario import Usuario

EMAIL_LECTOR = "cportero@santalaura.cl"
EMAIL_ADMIN = "hhernandez@santalaura.cl"
CLAVE_SEED = "admin123"
URL = "/api/v1/lecturas/sincronizar"


async def _cabecera(c, email=EMAIL_LECTOR):
    r = await c.post("/api/v1/auth/token", data={"username": email, "password": CLAVE_SEED})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _lectura(session, *, condominio_id=None, cerrada=False, actual=100.0, fecha_toma=None) -> LecturaParcela:
    """Período propio (no depende de los datos de desarrollo) con una lectura pendiente de tomar."""
    admin = (await session.execute(select(Usuario).where(Usuario.email == EMAIL_ADMIN))).scalar_one()
    condominio_id = condominio_id or admin.condominio_id
    parcela = Parcela(condominio_id=condominio_id, numero_parcela="T-1", activa=True)
    boleta = BoletaMaestra(condominio_id=condominio_id, periodo_mes=date(2099, 1, 1), creado_por=admin.id,
                           lecturas_cerradas=cerrada)
    session.add_all([parcela, boleta])
    await session.flush()
    lectura = LecturaParcela(parcela_id=parcela.id, boleta_id=boleta.id, lectura_anterior=100.0,
                             lectura_actual=actual, kwh_consumidos=actual - 100.0, lector_id=admin.id,
                             fecha_toma=fecha_toma)
    session.add(lectura)
    await session.flush()
    return lectura


def _item(lectura: LecturaParcela, valor: float, cuando: datetime, base_valor=100.0, base_fecha=None) -> dict:
    return {"lectura_id": lectura.id, "lectura_actual": valor, "fecha_toma": cuando.isoformat(),
            "base": {"lectura_actual": base_valor, "fecha_toma": base_fecha.isoformat() if base_fecha else None}}


async def test_aplica_y_es_idempotente(tx):
    c, session = tx
    lectura = await _lectura(session)
    cuando = datetime(2099, 1, 15, 10, 30, 12, 345000, tzinfo=timezone.utc)
    cab = await _cabecera(c)

    r = await c.post(URL, headers=cab, json={"items": [_item(lectura, 150.5, cuando)]})
    assert r.status_code == 200, r.text
    res = r.json()["resultados"][0]
    assert res["estado"] == "aplicada"
    assert res["lectura"]["kwh_consumidos"] == 50.5
    await session.refresh(lectura)
    assert lectura.lectura_actual == 150.5 and lectura.fecha_toma == cuando

    auditorias = lambda: session.execute(select(AuditoriaLog).where(AuditoriaLog.accion == "UPDATE_LECTURA"))
    antes = len((await auditorias()).scalars().all())
    # Reintento del mismo lote (se cortó la red antes de la respuesta): no cambia nada ni audita de nuevo
    r = await c.post(URL, headers=cab, json={"items": [_item(lectura, 150.5, cuando)]})
    assert r.json()["resultados"][0]["estado"] == "aplicada"
    assert len((await auditorias()).scalars().all()) == antes


async def test_conflicto_si_cambio_en_el_servidor(tx):
    c, session = tx
    corregida = datetime(2099, 1, 14, 9, 0, tzinfo=timezone.utc)
    lectura = await _lectura(session, actual=140.0, fecha_toma=corregida)   # el admin ya la registró
    r = await c.post(URL, headers=await _cabecera(c),
                     json={"items": [_item(lectura, 155.0, datetime.now(timezone.utc))]})   # base: sin tomar
    res = r.json()["resultados"][0]
    assert res["estado"] == "conflicto"
    assert res["lectura"]["lectura_actual"] == 140.0
    await session.refresh(lectura)
    assert lectura.lectura_actual == 140.0   # no se pisó


async def test_rechazos(tx):
    c, session = tx
    cab = await _cabecera(c)
    ahora = datetime.now(timezone.utc)

    cerrada = await _lectura(session, cerrada=True)
    r = await c.post(URL, headers=cab, json={"items": [_item(cerrada, 150.0, ahora)]})
    assert r.json()["resultados"][0] == {**r.json()["resultados"][0], "estado": "rechazada",
                                         "motivo": "Las lecturas del período ya están cerradas"}

    regresiva = await _lectura(session)
    r = await c.post(URL, headers=cab, json={"items": [_item(regresiva, 90.0, ahora)]})
    assert r.json()["resultados"][0]["estado"] == "rechazada"
    assert "no puede ser menor" in r.json()["resultados"][0]["motivo"]

    otro = Condominio(nombre="Otro", rut_comunidad="44444444-4", plan_suscripcion="basico", activo=True)
    session.add(otro)
    await session.flush()
    ajena = await _lectura(session, condominio_id=otro.id)
    r = await c.post(URL, headers=cab, json={"items": [_item(ajena, 150.0, ahora)]})
    assert r.json()["resultados"][0]["estado"] == "rechazada"
    await session.refresh(ajena)
    assert ajena.lectura_actual == 100.0


async def test_un_rechazo_no_revierte_los_demas(tx):
    c, session = tx
    buena = await _lectura(session)
    mala = await _lectura(session)
    ahora = datetime.now(timezone.utc)
    r = await c.post(URL, headers=await _cabecera(c), json={"items": [
        _item(mala, 50.0, ahora), _item(buena, 120.0, ahora + timedelta(seconds=1))]})
    assert [x["estado"] for x in r.json()["resultados"]] == ["rechazada", "aplicada"]
    await session.refresh(buena)
    assert buena.lectura_actual == 120.0


async def test_lote_demasiado_grande(tx):
    c, session = tx
    lectura = await _lectura(session)
    item = _item(lectura, 120.0, datetime.now(timezone.utc))
    r = await c.post(URL, headers=await _cabecera(c), json={"items": [item] * 201})
    assert r.status_code == 422


async def test_comunero_no_puede_sincronizar(tx):
    c, session = tx
    lectura = await _lectura(session)
    r = await c.post(URL, headers=await _cabecera(c, "gchacon@santalaura.cl"),
                     json={"items": [_item(lectura, 120.0, datetime.now(timezone.utc))]})
    assert r.status_code == 403
