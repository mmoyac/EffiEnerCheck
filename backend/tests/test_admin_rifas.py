"""Comunero con permiso de administrar rifas (cambio admin-rifas)."""
import json
import uuid
from datetime import timedelta

from sqlalchemy import delete

from app.models.condominio_modulo import CondominioModulo
from app.models.pago import IntencionPago, PasarelaPago
from app.services.pagos.pasarelas import ahora
from tests.pagos_comun import ADMIN, COMUNERO, PORTERIA, cabecera, usuario


async def _permiso(c, s, email=COMUNERO, valor=True, rol_id=None):
    u = await usuario(s, email)
    cuerpo = {"administra_rifas": valor} | ({"rol_id": rol_id} if rol_id else {})
    return await c.patch(f"/api/v1/usuarios/{u.id}", headers=await cabecera(s, ADMIN), json=cuerpo)


async def _admin_rifas(c, s):
    """Da el permiso al comunero del seed y devuelve su cabecera."""
    assert (await _permiso(c, s)).status_code == 200
    return await cabecera(s, COMUNERO)


async def _rifa(c, cab, **extra):
    cuerpo = {"nombre": "Rifa permiso", "beneficiario": "X", "premios": ["Algo"], "precio_numero": 1000,
              "cantidad_numeros": 50, **extra}
    r = await c.post("/api/v1/rifas/", headers=cab, json=cuerpo)
    assert r.status_code == 201, r.text
    return r.json()


async def _comprar(c, cab, rifa_id, parcela_id, medio, numero):
    datos = {"parcela_id": parcela_id, "numeros": [numero], "medio_pago": medio, "comprador_nombre": "Prueba"}
    return await c.post(f"/api/v1/rifas/{rifa_id}/compras", headers=cab, data={"datos": json.dumps(datos)})


async def _otra_parcela(c, s, cab, rifa_id):
    propias = {p.id for p in (await usuario(s, COMUNERO)).parcelas}
    r = await c.get(f"/api/v1/rifas/{rifa_id}/parcelas", headers=cab)
    assert r.status_code == 200, r.text
    return next(p["id"] for p in r.json() if p["id"] not in propias)


# ---- Cuentas ----------------------------------------------------------------------------------------

async def test_activa_el_permiso_y_queda_auditado(tx):
    c, s = tx
    r = await _permiso(c, s)
    assert r.status_code == 200, r.text
    assert r.json()["administra_rifas"] is True
    lista = await c.get("/api/v1/usuarios/", headers=await cabecera(s, ADMIN))
    assert next(u for u in lista.json() if u["email"] == COMUNERO)["administra_rifas"] is True
    me = await c.get("/api/v1/auth/me", headers=await cabecera(s, COMUNERO))
    assert me.json()["administra_rifas"] is True

    from sqlalchemy import select
    from app.models.auditoria import AuditoriaLog
    log = (await s.execute(select(AuditoriaLog).where(AuditoriaLog.accion == "UPDATE_USER")
                           .order_by(AuditoriaLog.id.desc()).limit(1))).scalar_one()
    assert log.detalles["before"]["administra_rifas"] is False
    assert log.detalles["after"]["administra_rifas"] is True


async def test_permiso_solo_en_comuneros(tx):
    c, s = tx
    r = await _permiso(c, s, email=PORTERIA)
    assert r.status_code == 422
    assert r.json()["detail"] == "Solo una cuenta de comunero puede administrar rifas"
    r = await c.post("/api/v1/usuarios/", headers=await cabecera(s, ADMIN), json={
        "nombre": "Lector X", "email": f"x{uuid.uuid4().hex[:6]}@ejemplo.cl", "rol_id": 3, "administra_rifas": True})
    assert r.status_code == 422


async def test_cambiar_de_rol_quita_el_permiso(tx):
    c, s = tx
    await _permiso(c, s)
    r = await _permiso(c, s, valor=None, rol_id=3)   # pasa a lector sin tocar el permiso
    assert r.status_code == 200, r.text
    assert r.json()["administra_rifas"] is False


# ---- Operación de rifas -----------------------------------------------------------------------------

async def test_opera_las_rifas_como_la_administracion(tx):
    c, s = tx
    cab = await _admin_rifas(c, s)
    rifa = await _rifa(c, cab, medios_pago=["efectivo", "transferencia", "gasto_comun"])
    rid = rifa["id"]
    assert (await c.patch(f"/api/v1/rifas/{rid}", headers=cab, json={"beneficiario": "Y"})).status_code == 200
    otra = await _otra_parcela(c, s, cab, rid)

    # Venta a otra parcela: canal administración, efectivo pagado al registrar
    r = await _comprar(c, cab, rid, otra, "efectivo", 1)
    assert r.status_code == 201, r.text
    efectivo = r.json()["compra"]
    assert efectivo["canal"] == "administracion" and efectivo["pagada"] is True

    transf = (await _comprar(c, cab, rid, otra, "transferencia", 2)).json()["compra"]
    r = await c.post(f"/api/v1/rifas/{rid}/compras/{transf['id']}/confirmar-pago", headers=cab)
    assert r.status_code == 200, r.text
    assert r.json()["pagada"] is True

    anular = (await _comprar(c, cab, rid, otra, "efectivo", 3)).json()["compra"]
    assert (await c.post(f"/api/v1/rifas/{rid}/compras/{anular['id']}/anular", headers=cab)).status_code == 200

    assert (await _comprar(c, cab, rid, otra, "gasto_comun", 4)).status_code == 201
    detalle = (await c.get(f"/api/v1/rifas/{rid}", headers=cab)).json()
    assert len(detalle["compras"]) == 4   # ve todas, no solo las de su parcela

    for ruta in ("caja", "compras", "parcelas", "export.csv"):
        assert (await c.get(f"/api/v1/rifas/{rid}/{ruta}", headers=cab)).status_code == 200, ruta

    cerrada = await c.post(f"/api/v1/rifas/{rid}/cerrar", headers=cab)
    assert cerrada.status_code == 200, cerrada.text
    imp = cerrada.json()["imputaciones"][0]
    r = await c.patch(f"/api/v1/rifas/{rid}/imputaciones/{imp['id']}", headers=cab, json={"cargada": True})
    assert r.status_code == 200, r.text
    assert (await c.get(f"/api/v1/rifas/{rid}/imputaciones.csv", headers=cab)).status_code == 200
    await c.patch(f"/api/v1/rifas/{rid}/imputaciones/{imp['id']}", headers=cab, json={"cargada": False})
    assert (await c.post(f"/api/v1/rifas/{rid}/reabrir", headers=cab)).status_code == 200

    # Eliminar sigue siendo solo del super_admin
    assert (await c.delete(f"/api/v1/rifas/{rid}?confirmacion=Rifa%20permiso", headers=cab)).status_code == 403


async def test_compra_para_su_parcela_va_por_el_portal(tx):
    c, s = tx
    cab = await _admin_rifas(c, s)
    rifa = await _rifa(c, cab)
    propia = (await usuario(s, COMUNERO)).parcelas[0].id
    assert (await _comprar(c, cab, rifa["id"], propia, "efectivo", 1)).status_code == 422
    r = await _comprar(c, cab, rifa["id"], propia, "gasto_comun", 2)
    assert r.status_code == 201, r.text
    assert r.json()["compra"]["canal"] == "portal"


async def test_sin_permiso_no_administra(tx):
    c, s = tx
    rifa = await _rifa(c, await cabecera(s, ADMIN))
    cab = await cabecera(s, COMUNERO)
    assert (await c.post("/api/v1/rifas/", headers=cab, json={"nombre": "X"})).status_code == 403
    assert (await c.post(f"/api/v1/rifas/{rifa['id']}/cerrar", headers=cab)).status_code == 403
    assert (await c.get(f"/api/v1/rifas/{rifa['id']}/caja", headers=cab)).status_code == 403


async def test_permiso_quitado_con_la_sesion_abierta(tx):
    c, s = tx
    cab = await _admin_rifas(c, s)
    rifa = await _rifa(c, cab)
    await _permiso(c, s, valor=False)
    assert (await c.post(f"/api/v1/rifas/{rifa['id']}/cerrar", headers=cab)).status_code == 403


async def test_rifa_de_otro_condominio(tx):
    c, s = tx
    from app.models.condominio import Condominio
    from app.models.rifa import Rifa
    otro = Condominio(nombre=f"Otro {uuid.uuid4().hex[:6]}", rut_comunidad=f"9{uuid.uuid4().int % 10**7}-1", plan_suscripcion="premium", activo=True)
    s.add(otro)
    await s.flush()
    ajena = Rifa(condominio_id=otro.id, nombre="Ajena", beneficiario="X", premios=["a"], precio_numero=1,
                 cantidad_numeros=1, creado_por_id=(await usuario(s, ADMIN)).id)
    s.add(ajena)
    await s.flush()
    cab = await _admin_rifas(c, s)
    assert (await c.post(f"/api/v1/rifas/{ajena.id}/cerrar", headers=cab)).status_code == 403


# ---- Fuera de rifas sigue siendo comunero -----------------------------------------------------------

async def test_fuera_de_rifas_sigue_siendo_comunero(tx):
    c, s = tx
    cab = await _admin_rifas(c, s)
    for metodo, ruta in (("get", "/api/v1/usuarios/"), ("get", "/api/v1/pasarelas/"),
                         ("post", "/api/v1/boletas/"), ("post", "/api/v1/parcelas/")):
        r = await getattr(c, metodo)(ruta, headers=cab, **({"json": {}} if metodo == "post" else {}))
        assert r.status_code == 403, (ruta, r.status_code)
    propias = {p.id for p in (await usuario(s, COMUNERO)).parcelas}
    r = await c.get("/api/v1/liquidaciones/", headers=cab)
    if r.status_code == 200:
        assert all(l["parcela_id"] in propias for l in r.json())


async def test_sin_modulo_rifas_el_permiso_no_vale(tx):
    c, s = tx
    cab = await _admin_rifas(c, s)
    condominio_id = (await usuario(s, COMUNERO)).condominio_id
    await s.execute(delete(CondominioModulo).where(CondominioModulo.condominio_id == condominio_id,
                                                   CondominioModulo.modulo == "rifas"))
    r = await c.post("/api/v1/rifas/", headers=cab, json={"nombre": "X"})
    assert r.status_code == 403
    assert "rifas" in r.json()["detail"]
    assert (await c.get("/api/v1/pagos/revision", headers=cab)).status_code == 403
    menus = (await c.get("/api/v1/menus/me", headers=cab)).json()
    assert "/rifas" not in [m["path"] for m in menus]


# ---- Pagos en revisión y menú -----------------------------------------------------------------------

async def _intencion(s, concepto):
    comunero = await usuario(s, COMUNERO)
    pasarela = PasarelaPago(condominio_id=comunero.condominio_id, proveedor="flow", nombre_visible="Prueba",
                            ambiente="integracion")
    s.add(pasarela)
    await s.flush()
    i = IntencionPago(condominio_id=comunero.condominio_id, pasarela_id=pasarela.id, usuario_id=comunero.id,
                      concepto=concepto, referencia_id=1, descripcion=concepto, monto=1000, comision=0, total=1000,
                      estado="EN_REVISION", vence_at=ahora() + timedelta(hours=1),
                      orden_comercio=uuid.uuid4().hex[:26])
    s.add(i)
    await s.flush()
    return i


async def test_pagos_en_revision_solo_de_rifas(tx, monkeypatch):
    c, s = tx
    # Hoy las rifas son el único concepto: se registra otro para la prueba
    from app.services.pagos import consumidores
    monkeypatch.setitem(consumidores._REGISTRO, "otro_concepto", consumidores._REGISTRO["rifa_compra"])
    rifa = await _intencion(s, "rifa_compra")
    otro = await _intencion(s, "otro_concepto")
    cab = await _admin_rifas(c, s)

    ids = [p["id"] for p in (await c.get("/api/v1/pagos/revision", headers=cab)).json()]
    assert str(rifa.id) in ids and str(otro.id) not in ids
    ids_admin = [p["id"] for p in (await c.get("/api/v1/pagos/revision", headers=await cabecera(s, ADMIN))).json()]
    assert str(otro.id) in ids_admin

    r = await c.post(f"/api/v1/pagos/{otro.id}/resolver", headers=cab, json={"nota": "devuelto"})
    assert r.status_code == 404
    r = await c.post(f"/api/v1/pagos/{rifa.id}/resolver", headers=cab, json={"nota": "devuelto"})
    assert r.status_code == 200, r.text


async def test_menu_del_comunero_con_permiso(tx):
    c, s = tx
    sin = [m["path"] for m in (await c.get("/api/v1/menus/me", headers=await cabecera(s, COMUNERO))).json()]
    assert "/rifas" not in sin
    cab = await _admin_rifas(c, s)
    con = [m["path"] for m in (await c.get("/api/v1/menus/me", headers=cab)).json()]
    assert "/rifas" in con and set(sin) <= set(con)
