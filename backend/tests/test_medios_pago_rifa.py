"""Formas de pago configurables por rifa."""
import json

EMAIL_ADMIN = "hhernandez@santalaura.cl"
CLAVE_SEED = "admin123"


async def _cabecera(c):
    r = await c.post("/api/v1/auth/token", data={"username": EMAIL_ADMIN, "password": CLAVE_SEED})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _rifa(c, cab, **extra):
    cuerpo = {"nombre": "Rifa medios", "beneficiario": "X", "premios": ["Algo"], "precio_numero": 1000,
              "cantidad_numeros": 50, **extra}
    return await c.post("/api/v1/rifas/", headers=cab, json=cuerpo)


async def _parcela(c, cab, rifa_id):
    r = await c.get(f"/api/v1/rifas/{rifa_id}/parcelas", headers=cab)
    return r.json()[0]["id"]


async def _comprar(c, cab, rifa_id, parcela_id, medio, numero):
    datos = {"parcela_id": parcela_id, "numeros": [numero], "medio_pago": medio, "comprador_nombre": "Prueba"}
    return await c.post(f"/api/v1/rifas/{rifa_id}/compras", headers=cab, data={"datos": json.dumps(datos)})


async def test_por_defecto_acepta_las_tres(tx):
    c, _ = tx
    r = await _rifa(c, await _cabecera(c))
    assert r.status_code == 201, r.text
    assert r.json()["medios_pago"] == ["efectivo", "transferencia", "gasto_comun"]


async def test_solo_transferencia_rechaza_las_demas(tx):
    c, _ = tx
    cab = await _cabecera(c)
    rifa = (await _rifa(c, cab, medios_pago=["transferencia"])).json()
    assert rifa["medios_pago"] == ["transferencia"]
    parcela = await _parcela(c, cab, rifa["id"])

    r = await _comprar(c, cab, rifa["id"], parcela, "efectivo", 1)
    assert r.status_code == 422
    assert r.json()["detail"] == "Esta rifa no acepta pagos con efectivo"
    r = await _comprar(c, cab, rifa["id"], parcela, "gasto_comun", 2)
    assert r.status_code == 422
    r = await _comprar(c, cab, rifa["id"], parcela, "transferencia", 3)
    assert r.status_code == 201, r.text


async def test_al_menos_una_forma_y_edicion(tx):
    c, _ = tx
    cab = await _cabecera(c)
    assert (await _rifa(c, cab, medios_pago=[])).status_code == 422
    rifa = (await _rifa(c, cab)).json()
    r = await c.patch(f"/api/v1/rifas/{rifa['id']}", headers=cab, json={"medios_pago": ["gasto_comun", "transferencia"]})
    assert r.status_code == 200, r.text
    assert r.json()["medios_pago"] == ["transferencia", "gasto_comun"]   # orden del catálogo
    assert (await c.patch(f"/api/v1/rifas/{rifa['id']}", headers=cab, json={"medios_pago": []})).status_code == 422
