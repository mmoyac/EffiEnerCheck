"""
Flujo de pago en línea de punta a punta contra Postgres, con un proveedor falso (sin red):
inicio, retorno, webhook, confirmación idempotente, rechazo, vencimiento, pago tardío, cancelación,
consulta a pedido y las reglas de rifas (specs pagos-en-linea y rifas-solidarias del cambio pasarelas-pago).
"""
import json
from datetime import timedelta

import pytest
from sqlalchemy import func, select, update

from app.api.v1.endpoints import rifas as rifas_endpoint
from app.core.config import settings
from app.models.auditoria import AuditoriaLog
from app.models.pago import IntencionPago, PasarelaPago
from app.models.rifa import CompraRifa, RifaNumero
from app.services.pagos import flujo
from app.services.pagos.proveedores import REGISTRO
from app.services.pagos.proveedores.base import (
    Adaptador,
    CampoCredencial,
    ErrorProveedor,
    Redireccion,
    Resultado,
)
from app.services.pagos.pasarelas import ahora
from tests.pagos_comun import ADMIN, COMUNERO, PORTERIA, SUPER, cabecera, crear_pasarela, usuario

OTRO_COMUNERO = "gchacon@santalaura.cl"


class Falso(Adaptador):
    """Proveedor de mentira: cuenta las llamadas y responde lo que diga la prueba."""
    nombre = "Falso"
    campos_credenciales = [CampoCredencial("api_key", "API Key"), CampoCredencial("secret_key", "Secret Key")]
    requiere_email = True
    monto_minimo = 350

    def __init__(self, proveedor: str, por_intencion: bool = False):
        super().__init__()
        self.proveedor = proveedor
        self.retorno_por_intencion = por_intencion
        self.estado = "PENDIENTE"
        self.monto: int | None = None  # None = el total de la intención
        self.falla_crear = False
        self.anula = False
        self.llamadas: list[str] = []
        self.creadas: list = []

    async def crear(self, pasarela, intencion, urls):
        self.llamadas.append("crear")
        if self.falla_crear:
            raise ErrorProveedor("caído")
        self.creadas.append((intencion, urls))
        return Redireccion(url=f"https://pasarela.test/pagar?token=T-{intencion.orden_comercio}",
                           token=f"T-{intencion.orden_comercio}", transaccion="OP-1")

    def token_de(self, datos):
        return datos.get("token") or datos.get("payment_id")

    async def verificar(self, pasarela, token):
        raise AssertionError("el flujo debe usar consultar")

    async def consultar(self, pasarela, intencion):
        self.llamadas.append("consultar")
        return Resultado(
            estado=self.estado, monto=intencion.total if self.monto is None else self.monto,
            transaccion="OP-1", orden_comercio=intencion.orden_comercio, autorizacion="123456",
            ultimos_digitos="6623", medio="Webpay", motivo="Fondos insuficientes" if self.estado == "RECHAZADO" else None,
            datos={"status": self.estado},
        )

    async def probar(self, pasarela):
        return None

    async def anular(self, pasarela, token):
        self.llamadas.append("anular")
        return self.anula


@pytest.fixture
def falso(monkeypatch):
    f = Falso("flow")
    monkeypatch.setitem(REGISTRO, "flow", f)
    return f


@pytest.fixture
def falso_khipu(monkeypatch):
    f = Falso("khipu", por_intencion=True)
    f.campos_credenciales = [CampoCredencial("api_key", "API Key")]
    f.requiere_email = False
    f.monto_minimo = 1
    monkeypatch.setitem(REGISTRO, "khipu", f)
    return f


@pytest.fixture
def vouchers(tmp_path, monkeypatch):
    monkeypatch.setattr(rifas_endpoint, "VOUCHERS_DIR", str(tmp_path))


async def _escenario(c, s, *, proveedor="flow", medios=("en_linea", "gasto_comun"), activar=True, **pasarela):
    """Pasarela activa + rifa abierta. Devuelve (rifa, pasarela_id, parcela del comunero)."""
    cab_super = await cabecera(s, SUPER)
    extra = {"proveedor": proveedor, "nombre_visible": proveedor.capitalize(), **pasarela}
    if proveedor == "khipu":
        extra["credenciales"] = {"api_key": "k"}
    pid = (await crear_pasarela(c, cab_super, **extra)).json()["id"]
    if activar:
        assert (await c.post(f"/api/v1/pasarelas/{pid}/activar", headers=cab_super)).status_code == 200
    r = await c.post("/api/v1/rifas/", headers=await cabecera(s, ADMIN), json={
        "nombre": "Rifa en línea", "beneficiario": "Club", "premios": ["Bicicleta"], "precio_numero": 2000,
        "cantidad_numeros": 100, "medios_pago": list(medios), "datos_transferencia": "Banco X",
    })
    assert r.status_code == 201, r.text
    parcela = (await usuario(s, COMUNERO)).parcelas[0].id
    return r.json(), pid, parcela


async def _comprar(c, s, rifa_id, parcela_id, numeros, medio="en_linea", pasarela_id=None, email=COMUNERO, voucher=False):
    datos = {"parcela_id": parcela_id, "numeros": numeros, "medio_pago": medio, "pasarela_id": pasarela_id}
    files = {"voucher": ("v.jpg", b"\xff\xd8\xff", "image/jpeg")} if voucher else None
    return await c.post(f"/api/v1/rifas/{rifa_id}/compras", headers=await cabecera(s, email),
                        data={"datos": json.dumps(datos)}, files=files)


async def _intencion(s, intencion_id) -> IntencionPago:
    return await s.get(IntencionPago, intencion_id, populate_existing=True)


async def _compra(s, compra_id) -> CompraRifa:
    return await s.get(CompraRifa, compra_id, populate_existing=True)


async def _numeros(s, rifa_id) -> list[int]:
    return sorted((await s.execute(select(RifaNumero.numero).where(RifaNumero.rifa_id == rifa_id))).scalars())


async def _iniciar(c, s, falso, numeros=(7, 8), **kw):
    rifa, pid, parcela = await _escenario(c, s, **kw)
    r = await _comprar(c, s, rifa["id"], parcela, list(numeros), pasarela_id=pid)
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    return rifa, cuerpo["compra"], cuerpo["pago"]


# ---------------------------------------------------------------------------
# Inicio
# ---------------------------------------------------------------------------

async def test_inicio_reserva_numeros_y_redirige(tx, falso):
    c, s = tx
    rifa, compra, pago = await _iniciar(c, s, falso)
    assert pago["redireccion"]["url"].startswith("https://pasarela.test/pagar?token=")
    assert compra["medio_pago"] == "en_linea" and compra["pagada"] is False
    assert compra["pago_en_linea_estado"] == "INICIADO" and compra["puede_anular"] is False
    assert await _numeros(s, rifa["id"]) == [7, 8]

    i = await _intencion(s, pago["intencion_id"])
    assert (i.estado, i.monto, i.comision, i.total) == ("INICIADO", 4000, 159, 4159)  # 3,8 % a cargo del comunero
    assert len(i.orden_comercio) == 26 and i.token_proveedor == f"T-{i.orden_comercio}"
    assert i.descripcion == "Rifa en línea – números 7, 8"  # sin repetir «Rifa»
    intencion_en_uso, urls = falso.creadas[0]
    assert intencion_en_uso.email == COMUNERO and intencion_en_uso.total == 4159
    assert urls.retorno == "http://localhost:3000/api/v1/pagos/retorno/flow"
    assert urls.notificacion == "http://localhost:3000/api/v1/pagos/webhook/flow"


async def test_url_publica_reemplaza_solo_la_notificacion(tx, falso, monkeypatch):
    c, s = tx
    monkeypatch.setattr(settings, "URL_PUBLICA_PAGOS", "https://abc.trycloudflare.com/")
    await _iniciar(c, s, falso)
    _, urls = falso.creadas[0]
    assert urls.notificacion == "https://abc.trycloudflare.com/api/v1/pagos/webhook/flow"
    assert urls.retorno.startswith("http://localhost:3000/")


async def test_falla_del_proveedor_al_crear_libera(tx, falso):
    c, s = tx
    falso.falla_crear = True
    rifa, pid, parcela = await _escenario(c, s)
    r = await _comprar(c, s, rifa["id"], parcela, [5], pasarela_id=pid)
    assert r.status_code == 502 and "quedaron libres" in r.json()["detail"]
    i = (await s.execute(select(IntencionPago).where(IntencionPago.pasarela_id == pid))).scalar_one()
    assert i.estado == "RECHAZADO"
    assert (await _compra(s, i.referencia_id)).anulada is True
    assert await _numeros(s, rifa["id"]) == []


async def test_una_sola_intencion_en_curso_por_rifa(tx, falso):
    c, s = tx
    rifa, pid, parcela = await _escenario(c, s)
    assert (await _comprar(c, s, rifa["id"], parcela, [1], pasarela_id=pid)).status_code == 201
    r = await _comprar(c, s, rifa["id"], parcela, [2], pasarela_id=pid)
    assert r.status_code == 409 and "en curso" in r.json()["detail"]


async def test_numero_reservado_no_se_vende(tx, falso):
    c, s = tx
    rifa, compra, _ = await _iniciar(c, s, falso, numeros=(9,))
    r = await _comprar(c, s, rifa["id"], compra["parcela_id"], [9], medio="gasto_comun", email=ADMIN)
    assert r.status_code == 409 and "9" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Confirmación
# ---------------------------------------------------------------------------

async def test_retorno_y_webhook_registran_un_solo_pago(tx, falso):
    c, s = tx
    rifa, compra, pago = await _iniciar(c, s, falso)
    i = await _intencion(s, pago["intencion_id"])
    falso.estado = "APROBADO"

    r = await c.post("/api/v1/pagos/webhook/flow", data={"token": i.token_proveedor})
    assert r.status_code == 200
    r = await c.post("/api/v1/pagos/retorno/flow", data={"token": i.token_proveedor}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == f"http://localhost:3000/pagos/{i.id}/resultado"

    i = await _intencion(s, i.id)
    assert i.estado == "CONFIRMADO" and i.transaccion_proveedor == "OP-1" and i.email_pagador is None
    c_db = await _compra(s, compra["id"])
    assert c_db.pagada is True and c_db.anulada is False
    confirmaciones = await s.scalar(select(func.count()).select_from(AuditoriaLog).where(
        AuditoriaLog.accion == "CONFIRMAR_PAGO_EN_LINEA", AuditoriaLog.detalles["intencion_pago_id"].astext == str(i.id)))
    assert confirmaciones == 1
    # La segunda vía encontró la intención confirmada y no volvió a consultar
    assert falso.llamadas.count("consultar") == 1


async def test_retorno_pendiente_no_confirma(tx, falso):
    c, s = tx
    _, _, pago = await _iniciar(c, s, falso)
    i = await _intencion(s, pago["intencion_id"])
    r = await c.post("/api/v1/pagos/retorno/flow", data={"token": i.token_proveedor}, follow_redirects=False)
    assert r.status_code == 303
    assert (await _intencion(s, i.id)).estado == "INICIADO"


async def test_token_inventado_no_llama_al_proveedor(tx, falso):
    c, s = tx
    await _iniciar(c, s, falso)
    falso.llamadas.clear()
    assert (await c.post("/api/v1/pagos/webhook/flow", data={"token": "inventado"})).status_code == 404
    r = await c.post("/api/v1/pagos/retorno/flow", data={"token": "inventado"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].endswith("/pagos/desconocido/resultado")
    assert (await c.post("/api/v1/pagos/webhook/nadie", json={})).status_code == 404
    assert falso.llamadas == []


async def test_webhook_json_y_proveedor_cruzado(tx, falso, falso_khipu):
    c, s = tx
    _, _, pago = await _iniciar(c, s, falso_khipu, proveedor="khipu")
    i = await _intencion(s, pago["intencion_id"])
    falso_khipu.estado = "APROBADO"
    # El token de Khipu presentado como si fuera de Flow no encuentra nada
    assert (await c.post("/api/v1/pagos/webhook/flow", json={"payment_id": i.token_proveedor})).status_code == 404
    r = await c.get(f"/api/v1/pagos/retorno/flow?intencion={i.id}", follow_redirects=False)
    assert r.headers["location"].endswith("/pagos/desconocido/resultado")
    assert falso.llamadas == []
    # Khipu notifica por JSON
    assert (await c.post("/api/v1/pagos/webhook/khipu", json={"payment_id": i.token_proveedor})).status_code == 200
    assert (await _intencion(s, i.id)).estado == "CONFIRMADO"


async def test_monto_distinto_queda_en_revision(tx, falso):
    c, s = tx
    rifa, compra, pago = await _iniciar(c, s, falso)
    falso.estado, falso.monto = "APROBADO", 100
    await flujo.confirmar(s, pago["intencion_id"], "prueba")
    i = await _intencion(s, pago["intencion_id"])
    assert i.estado == "EN_REVISION" and "$100" in i.motivo
    c_db = await _compra(s, compra["id"])
    assert c_db.pagada is False and c_db.anulada is True


async def test_rechazo_libera_y_no_acepta_aprobado_posterior(tx, falso):
    c, s = tx
    rifa, compra, pago = await _iniciar(c, s, falso)
    falso.estado = "RECHAZADO"
    await flujo.confirmar(s, pago["intencion_id"], "prueba")
    i = await _intencion(s, pago["intencion_id"])
    assert i.estado == "RECHAZADO" and i.motivo == "Fondos insuficientes"
    assert (await _compra(s, compra["id"])).anulada is True
    assert await _numeros(s, rifa["id"]) == []

    falso.estado = "APROBADO"
    await flujo.confirmar(s, pago["intencion_id"], "prueba")
    assert (await _intencion(s, pago["intencion_id"])).estado == "RECHAZADO"
    assert (await _compra(s, compra["id"])).pagada is False


# ---------------------------------------------------------------------------
# Vencimiento y pago tardío
# ---------------------------------------------------------------------------

async def _vencer(s, intencion_id):
    i = await _intencion(s, intencion_id)
    i.vence_at = ahora() - timedelta(minutes=1)
    await s.flush()


async def test_vencida_y_aprobada_tarde_con_numeros_libres(tx, falso):
    c, s = tx
    rifa, compra, pago = await _iniciar(c, s, falso)
    await _vencer(s, pago["intencion_id"])
    await flujo.confirmar(s, pago["intencion_id"], "conciliacion")
    assert (await _intencion(s, pago["intencion_id"])).estado == "EXPIRADO"
    assert await _numeros(s, rifa["id"]) == []

    falso.estado = "APROBADO"
    await flujo.confirmar(s, pago["intencion_id"], "conciliacion")
    i = await _intencion(s, pago["intencion_id"])
    assert i.estado == "CONFIRMADO"
    c_db = await _compra(s, compra["id"])
    assert c_db.pagada is True and c_db.anulada is False
    assert await _numeros(s, rifa["id"]) == [7, 8]


async def test_aprobada_tarde_con_numeros_vendidos_queda_en_revision(tx, falso):
    c, s = tx
    rifa, compra, pago = await _iniciar(c, s, falso)
    await _vencer(s, pago["intencion_id"])
    await flujo.confirmar(s, pago["intencion_id"], "conciliacion")
    # Otro compra el 8 mientras tanto
    r = await _comprar(c, s, rifa["id"], compra["parcela_id"], [8], medio="gasto_comun", email=ADMIN)
    assert r.status_code == 201, r.text

    falso.estado = "APROBADO"
    await flujo.confirmar(s, pago["intencion_id"], "conciliacion")
    i = await _intencion(s, pago["intencion_id"])
    assert i.estado == "EN_REVISION" and "Números ya vendidos" in i.motivo and "8" in i.motivo
    assert (await _compra(s, compra["id"])).anulada is True

    # La administración lo ve y lo resuelve
    cab = await cabecera(s, ADMIN)
    pendientes = (await c.get("/api/v1/pagos/revision", headers=cab)).json()
    assert str(i.id) in [p["id"] for p in pendientes]
    r = await c.post(f"/api/v1/pagos/{i.id}/resolver", headers=cab, json={"nota": "Se devolvió en Flow"})
    assert r.status_code == 200 and r.json()["resuelta_at"]
    assert str(i.id) not in [p["id"] for p in (await c.get("/api/v1/pagos/revision", headers=cab)).json()]


# ---------------------------------------------------------------------------
# Cancelación (Khipu)
# ---------------------------------------------------------------------------

async def test_cancelacion_anulada_en_el_proveedor(tx, falso_khipu):
    c, s = tx
    rifa, compra, pago = await _iniciar(c, s, falso_khipu, proveedor="khipu")
    _, urls = falso_khipu.creadas[0]
    assert urls.cancelacion == f"{urls.retorno}&cancelado=1" and f"intencion={pago['intencion_id']}" in urls.retorno
    falso_khipu.anula = True
    r = await c.get(f"/api/v1/pagos/retorno/khipu?intencion={pago['intencion_id']}&cancelado=1", follow_redirects=False)
    assert r.status_code == 303
    i = await _intencion(s, pago["intencion_id"])
    assert i.estado == "RECHAZADO" and i.motivo == "Cancelaste el pago"
    assert await _numeros(s, rifa["id"]) == []


async def test_cancelacion_sin_anulacion_posible_consulta_y_aplica(tx, falso_khipu):
    c, s = tx
    _, compra, pago = await _iniciar(c, s, falso_khipu, proveedor="khipu")
    falso_khipu.anula = False
    falso_khipu.estado = "APROBADO"
    await c.get(f"/api/v1/pagos/retorno/khipu?intencion={pago['intencion_id']}&cancelado=1", follow_redirects=False)
    assert (await _intencion(s, pago["intencion_id"])).estado == "CONFIRMADO"
    assert (await _compra(s, compra["id"])).pagada is True


# ---------------------------------------------------------------------------
# Estado y consulta a pedido
# ---------------------------------------------------------------------------

async def test_estado_consulta_y_acceso(tx, falso):
    c, s = tx
    _, _, pago = await _iniciar(c, s, falso)
    iid = pago["intencion_id"]
    cab = await cabecera(s, COMUNERO)

    r = await c.get(f"/api/v1/pagos/{iid}", headers=cab)
    assert r.status_code == 200 and r.json()["estado"] == "INICIADO" and r.json()["volver_a"] == "/mis-rifas"
    assert (await c.get(f"/api/v1/pagos/{iid}", headers=await cabecera(s, OTRO_COMUNERO))).status_code == 404
    assert (await c.get(f"/api/v1/pagos/{iid}", headers=await cabecera(s, ADMIN))).status_code == 200

    falso.estado = "APROBADO"
    r = await c.post(f"/api/v1/pagos/{iid}/consultar", headers=cab)
    assert r.status_code == 200
    assert r.json()["estado"] == "CONFIRMADO" and r.json()["numero_operacion"] == "OP-1"
    assert (await c.post(f"/api/v1/pagos/{iid}/consultar", headers=cab)).status_code == 429


# ---------------------------------------------------------------------------
# Reglas de rifas
# ---------------------------------------------------------------------------

async def test_disponibles_con_comision_y_minimo(tx, falso):
    c, s = tx
    await _escenario(c, s)
    cab = await cabecera(s, COMUNERO)
    opciones = (await c.get("/api/v1/pagos/disponibles?monto=4000", headers=cab)).json()
    mia = [o for o in opciones if o["nombre_visible"] == "Flow"][-1]
    assert (mia["total"], mia["comision"], mia["disponible"]) == (4159, 159, True)
    opciones = (await c.get("/api/v1/pagos/disponibles?monto=100", headers=cab)).json()
    mia = [o for o in opciones if o["nombre_visible"] == "Flow"][-1]
    assert mia["disponible"] is False and "$350" in mia["motivo"]


async def test_en_produccion_no_se_ofrece_integracion(tx, falso, monkeypatch):
    c, s = tx
    rifa, pid, parcela = await _escenario(c, s)
    monkeypatch.setattr(settings, "ENTORNO", "produccion")
    cab = await cabecera(s, COMUNERO)
    assert pid not in [o["pasarela_id"] for o in (await c.get("/api/v1/pagos/disponibles?monto=4000", headers=cab)).json()]
    r = await _comprar(c, s, rifa["id"], parcela, [3], pasarela_id=pid)
    assert r.status_code == 422


async def test_porteria_no_cobra_en_linea(tx, falso):
    c, s = tx
    rifa, pid, parcela = await _escenario(c, s, medios=("en_linea", "efectivo"))
    r = await _comprar(c, s, rifa["id"], parcela, [4], pasarela_id=pid, email=PORTERIA)
    assert r.status_code == 422 and "comunero" in r.json()["detail"]


async def test_comunero_con_pasarela_no_usa_transferencia_manual(tx, falso, vouchers):
    c, s = tx
    rifa, _, parcela = await _escenario(c, s, medios=("en_linea", "transferencia"))
    r = await _comprar(c, s, rifa["id"], parcela, [4], medio="transferencia", voucher=True)
    assert r.status_code == 422 and "en línea" in r.json()["detail"]


async def test_sin_pasarela_el_comunero_transfiere_con_voucher(tx, falso, vouchers):
    c, s = tx
    rifa, pid, parcela = await _escenario(c, s, activar=False)
    # Sin ninguna pasarela activa en el condominio (la base de desarrollo puede tener alguna; se revierte al final)
    await s.execute(update(PasarelaPago).where(PasarelaPago.condominio_id == 1).values(activa=False))
    r = await _comprar(c, s, rifa["id"], parcela, [4], pasarela_id=pid)
    assert r.status_code == 422 and "transferencia" in r.json()["detail"]
    r = await _comprar(c, s, rifa["id"], parcela, [4], medio="transferencia")
    assert r.status_code == 422 and r.json()["detail"] == "Adjunta la foto del voucher de la transferencia"
    r = await _comprar(c, s, rifa["id"], parcela, [4], medio="transferencia", voucher=True)
    assert r.status_code == 201, r.text
    assert r.json()["compra"]["medio_pago"] == "transferencia" and r.json()["pago"] is None


async def test_compra_en_linea_no_se_confirma_ni_anula_a_mano_y_bloquea_el_cierre(tx, falso):
    c, s = tx
    rifa, compra, _ = await _iniciar(c, s, falso)
    base = f"/api/v1/rifas/{rifa['id']}"
    cab_admin = await cabecera(s, ADMIN)
    r = await c.post(f"{base}/compras/{compra['id']}/confirmar-pago", headers=cab_admin)
    assert r.status_code == 409
    r = await c.post(f"{base}/compras/{compra['id']}/anular", headers=await cabecera(s, COMUNERO))
    assert r.status_code == 409 and "en curso" in r.json()["detail"]
    r = await c.post(f"{base}/cerrar", headers=cab_admin)
    assert r.status_code == 409 and r.json()["detail"] == "Hay 1 pago en línea en curso; espera a que termine"

    falso.estado = "APROBADO"
    await flujo.confirmar(s, compra["intencion_pago_id"], "prueba")
    r = await c.post(f"{base}/cerrar", headers=cab_admin)
    assert r.status_code == 200, r.text
    assert r.json()["imputaciones"] == []  # lo pagado en línea no se imputa al gasto común
