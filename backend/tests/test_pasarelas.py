"""Administración de pasarelas de pago (spec pagos-en-linea)."""
import json
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models.auditoria import AuditoriaLog
from app.models.condominio import Condominio
from app.models.pago import IntencionPago, PasarelaPago
from app.services.pagos.proveedores import REGISTRO
from app.services.pagos.proveedores.base import ErrorCredenciales, ErrorProveedor

from tests.pagos_comun import ADMIN, COMUNERO, FLOW, SECRETO, SUPER, cabecera, crear_pasarela, sin_secretos


async def test_super_admin_crea_pasarela_inactiva_sin_exponer_credenciales(tx):
    c, s = tx
    r = await crear_pasarela(c, await cabecera(s, SUPER))
    assert r.status_code == 201, r.text
    datos = r.json()
    assert datos["activa"] is False and datos["credenciales_cargadas"] is True
    assert datos["comision_porcentaje"] == "3.8000"
    sin_secretos(r.text)
    guardada = await s.get(PasarelaPago, datos["id"])
    assert SECRETO.encode() not in guardada.credenciales_cifradas


async def test_credenciales_incompletas(tx):
    c, s = tx
    r = await crear_pasarela(c, await cabecera(s, SUPER), credenciales={"api_key": "x"})
    assert r.status_code == 422
    assert "Secret Key" in r.json()["detail"]


async def test_admin_condominio_ve_pero_no_modifica(tx):
    c, s = tx
    pid = (await crear_pasarela(c, await cabecera(s, SUPER))).json()["id"]
    cab = await cabecera(s, ADMIN)

    r = await c.get("/api/v1/pasarelas/", headers=cab)
    assert r.status_code == 200
    assert pid in [p["id"] for p in r.json()]
    sin_secretos(r.text)
    assert (await c.get(f"/api/v1/pasarelas/{pid}", headers=cab)).status_code == 200

    assert (await crear_pasarela(c, cab)).status_code == 403
    assert (await c.patch(f"/api/v1/pasarelas/{pid}", headers=cab, json={"orden": 3})).status_code == 403
    assert (await c.post(f"/api/v1/pasarelas/{pid}/probar", headers=cab)).status_code == 403
    assert (await c.post(f"/api/v1/pasarelas/{pid}/activar", headers=cab)).status_code == 403
    assert (await c.delete(f"/api/v1/pasarelas/{pid}", headers=cab)).status_code == 403
    assert (await c.put(f"/api/v1/pasarelas/{pid}/credenciales", headers=cab,
                        json={"credenciales": FLOW["credenciales"]})).status_code == 403


async def test_comunero_no_ve_pasarelas(tx):
    c, s = tx
    r = await c.get("/api/v1/pasarelas/", headers=await cabecera(s, COMUNERO))
    assert r.status_code == 403


async def test_pasarela_de_otro_condominio(tx):
    c, s = tx
    otro = Condominio(nombre="Otro", rut_comunidad="99999999-9", plan_suscripcion="basico", activo=True)
    s.add(otro)
    await s.flush()
    pid = (await crear_pasarela(c, await cabecera(s, SUPER), condominio_id=otro.id)).json()["id"]

    cab = await cabecera(s, ADMIN)
    assert (await c.get(f"/api/v1/pasarelas/{pid}", headers=cab)).status_code == 404
    assert pid not in [p["id"] for p in (await c.get("/api/v1/pasarelas/", headers=cab)).json()]


async def test_prueba_de_conexion(tx, monkeypatch):
    c, s = tx
    cab = await cabecera(s, SUPER)
    pid = (await crear_pasarela(c, cab)).json()["id"]
    recibidas = []

    async def ok(pasarela):
        recibidas.append(pasarela.credenciales)

    monkeypatch.setattr(REGISTRO["flow"], "probar", ok)
    r = await c.post(f"/api/v1/pasarelas/{pid}/probar", headers=cab)
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True and r.json()["pasarela"]["prueba_vigente"] is True
    assert recibidas == [FLOW["credenciales"]]  # el adaptador recibe las credenciales descifradas
    sin_secretos(r.text)

    async def rechazadas(pasarela):
        raise ErrorCredenciales("Invalid ApiKey")

    monkeypatch.setattr(REGISTRO["flow"], "probar", rechazadas)
    r = await c.post(f"/api/v1/pasarelas/{pid}/probar", headers=cab)
    assert r.json()["ok"] is False
    assert r.json()["mensaje"] == "Credenciales rechazadas por el proveedor"
    assert r.json()["pasarela"]["prueba_ok"] is False

    async def caida(pasarela):
        raise ErrorProveedor("timeout")

    monkeypatch.setattr(REGISTRO["flow"], "probar", caida)
    r = await c.post(f"/api/v1/pasarelas/{pid}/probar", headers=cab)
    assert r.json()["ok"] is False and "comunicar" in r.json()["mensaje"]


async def test_activar_produccion_exige_prueba_posterior_a_las_credenciales(tx, monkeypatch):
    c, s = tx
    cab = await cabecera(s, SUPER)
    pid = (await crear_pasarela(c, cab, ambiente="produccion")).json()["id"]

    r = await c.post(f"/api/v1/pasarelas/{pid}/activar", headers=cab)
    assert r.status_code == 409 and "Prueba la conexión" in r.json()["detail"]

    async def ok(pasarela):
        return None

    monkeypatch.setattr(REGISTRO["flow"], "probar", ok)
    await c.post(f"/api/v1/pasarelas/{pid}/probar", headers=cab)
    r = await c.post(f"/api/v1/pasarelas/{pid}/activar", headers=cab)
    assert r.status_code == 200 and r.json()["activa"] is True

    # Reemplazar las credenciales desactiva y deja la prueba vencida
    r = await c.put(f"/api/v1/pasarelas/{pid}/credenciales", headers=cab,
                    json={"credenciales": {"api_key": "OTRA", "secret_key": "otra"}})
    assert r.status_code == 200 and r.json()["activa"] is False and r.json()["prueba_vigente"] is False
    assert (await c.post(f"/api/v1/pasarelas/{pid}/activar", headers=cab)).status_code == 409

    # Una prueba anterior al cambio de credenciales no sirve
    p = await s.get(PasarelaPago, pid)
    p.prueba_ok = True
    p.prueba_at = p.credenciales_at - timedelta(seconds=1)
    await s.flush()
    assert (await c.post(f"/api/v1/pasarelas/{pid}/activar", headers=cab)).status_code == 409


async def test_integracion_se_activa_sin_prueba_y_cambiar_ambiente_desactiva(tx):
    c, s = tx
    cab = await cabecera(s, SUPER)
    pid = (await crear_pasarela(c, cab)).json()["id"]
    assert (await c.post(f"/api/v1/pasarelas/{pid}/activar", headers=cab)).json()["activa"] is True
    r = await c.patch(f"/api/v1/pasarelas/{pid}", headers=cab, json={"ambiente": "produccion"})
    assert r.status_code == 200 and r.json()["activa"] is False and r.json()["ambiente"] == "produccion"


async def test_eliminar_solo_sin_pagos(tx):
    c, s = tx
    cab = await cabecera(s, SUPER)
    libre = (await crear_pasarela(c, cab)).json()["id"]
    assert (await c.delete(f"/api/v1/pasarelas/{libre}", headers=cab)).status_code == 204

    usada = (await crear_pasarela(c, cab)).json()["id"]
    from datetime import datetime, timezone
    s.add(IntencionPago(
        condominio_id=1, pasarela_id=usada, usuario_id=1, concepto="rifa_compra", referencia_id=0,
        descripcion="x", monto=1000, comision=0, total=1000, estado="RECHAZADO",
        vence_at=datetime.now(timezone.utc), orden_comercio="A" * 26,
    ))
    await s.flush()
    r = await c.delete(f"/api/v1/pasarelas/{usada}", headers=cab)
    assert r.status_code == 409 and "desactívala" in r.json()["detail"]


async def test_auditoria_sin_valores_de_credenciales(tx):
    c, s = tx
    cab = await cabecera(s, SUPER)
    pid = (await crear_pasarela(c, cab)).json()["id"]
    await c.put(f"/api/v1/pasarelas/{pid}/credenciales", headers=cab,
                json={"credenciales": {"api_key": "API-KEY-123", "secret_key": SECRETO}})
    registros = (await s.execute(select(AuditoriaLog).where(
        AuditoriaLog.accion.in_(["CREATE_PASARELA_PAGO", "UPDATE_CREDENCIALES_PASARELA"]),
        AuditoriaLog.detalles["pasarela_id"].astext == str(pid),
    ))).scalars().all()
    assert {r.accion for r in registros} == {"CREATE_PASARELA_PAGO", "UPDATE_CREDENCIALES_PASARELA"}
    for r in registros:
        sin_secretos(json.dumps(r.detalles))
    actualizacion = next(r for r in registros if r.accion == "UPDATE_CREDENCIALES_PASARELA")
    assert actualizacion.detalles["campos"] == ["api_key", "secret_key"]


@pytest.mark.parametrize("ruta", ["/api/v1/pasarelas/proveedores"])
async def test_catalogo_de_proveedores(tx, ruta):
    c, s = tx
    r = await c.get(ruta, headers=await cabecera(s, SUPER))
    assert r.status_code == 200
    flow = next(p for p in r.json() if p["proveedor"] == "flow")
    assert [x["nombre"] for x in flow["campos_credenciales"]] == ["api_key", "secret_key"]
    assert flow["monto_minimo"] == 350 and flow["requiere_email"] is True
    assert (await c.get(ruta, headers=await cabecera(s, ADMIN))).status_code == 403


async def test_comision_con_tres_o_mas_decimales(tx):
    """Khipu: 0,69 % + IVA = 0,8211 %. Se aceptan hasta 4 decimales y el resto se redondea."""
    c, s = tx
    cab = await cabecera(s, SUPER)
    r = await crear_pasarela(c, cab, comision_porcentaje="0.821")
    assert r.status_code == 201, r.text
    assert r.json()["comision_porcentaje"] == "0.8210"
    r = await c.patch(f"/api/v1/pasarelas/{r.json()['id']}", headers=cab, json={"comision_porcentaje": "0.82110"})
    assert r.status_code == 200 and r.json()["comision_porcentaje"] == "0.8211"
