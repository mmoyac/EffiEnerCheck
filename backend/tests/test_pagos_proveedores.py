"""Adaptadores Flow y Khipu contra un doble HTTP (httpx.MockTransport): nunca la red."""
import json
from decimal import Decimal
from urllib.parse import parse_qs

import httpx
import pytest

from app.services.pagos.comision import total_con_comision
from app.services.pagos.proveedores.base import (
    ErrorCredenciales,
    ErrorProveedor,
    IntencionEnUso,
    PasarelaEnUso,
    Urls,
)
from app.services.pagos.proveedores.flow import Flow, firmar
from app.services.pagos.proveedores.khipu import Khipu

FLOW = PasarelaEnUso(id=1, ambiente="integracion", credenciales={"api_key": "KEY-1", "secret_key": "secreto"})
KHIPU = PasarelaEnUso(id=2, ambiente="integracion", credenciales={"api_key": "khipu-key"})
URLS_HTTPS = Urls(
    retorno="https://portal.cl/api/v1/pagos/retorno/x",
    cancelacion="https://portal.cl/api/v1/pagos/retorno/x?cancelado=1",
    notificacion="https://portal.cl/api/v1/pagos/webhook/x",
)
URLS_LOCAL = Urls(
    retorno="http://localhost:3000/api/v1/pagos/retorno/x",
    cancelacion="http://localhost:3000/api/v1/pagos/retorno/x?cancelado=1",
    notificacion="http://localhost:3000/api/v1/pagos/webhook/x",
)


def _intencion(**extra) -> IntencionEnUso:
    datos = dict(id="0d9f7c1e-0000-4000-8000-000000000001", orden_comercio="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                 total=6238, descripcion="Rifa Prueba – números 7, 8", email="vecino@correo.cl",
                 segundos_restantes=900)
    return IntencionEnUso(**{**datos, **extra})


class Doble:
    """Registra las peticiones y responde con la función dada."""

    def __init__(self, responder):
        self.peticiones: list[httpx.Request] = []
        self._responder = responder

    def cliente(self) -> httpx.AsyncClient:
        def handler(request: httpx.Request) -> httpx.Response:
            self.peticiones.append(request)
            return self._responder(request)
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))


# ---------------------------------------------------------------------------
# Comisión
# ---------------------------------------------------------------------------

def test_comision_ejemplos_de_la_spec():
    assert total_con_comision(6000, Decimal("3.8"), 0) == 6238
    assert total_con_comision(6000, 0, 0) == 6000
    assert total_con_comision(6000, 0, 150) == 6150
    # Lo que queda tras descontar la comisión cubre siempre el monto adeudado
    for monto in (350, 1000, 2999, 6000, 123457):
        total = total_con_comision(monto, Decimal("3.19"), 50)
        assert total - (total * Decimal("3.19") / 100) - 50 >= monto


# ---------------------------------------------------------------------------
# Flow
# ---------------------------------------------------------------------------

def test_flow_vector_de_firma():
    parametros = {"amount": 5000, "apiKey": "XXXX-XXXX-XXXX", "currency": "CLP"}
    assert firmar(parametros, "secreto-de-prueba") == (
        "23a2e1765aa31ff2e0e242d8eb5650ae3302d8089159c3a5c968faa14b3578c8"
    )


async def test_flow_crear_firma_y_no_manda_optional():
    doble = Doble(lambda r: httpx.Response(200, json={"url": "https://sandbox.flow.cl/app/web/pay.php",
                                                       "token": "TOK123", "flowOrder": 998}))
    redir = await Flow(doble.cliente()).crear(FLOW, _intencion(), URLS_HTTPS)

    assert redir.url == "https://sandbox.flow.cl/app/web/pay.php?token=TOK123"
    assert (redir.metodo, redir.token, redir.transaccion) == ("GET", "TOK123", "998")
    peticion = doble.peticiones[0]
    assert str(peticion.url) == "https://sandbox.flow.cl/api/payment/create"
    enviado = {k: v[0] for k, v in parse_qs(peticion.content.decode()).items()}
    assert enviado["amount"] == "6238" and enviado["currency"] == "CLP" and enviado["paymentMethod"] == "9"
    assert enviado["commerceOrder"] == "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    assert enviado["timeout"] == "1020"
    assert "optional" not in enviado
    assert enviado["s"] == firmar({k: v for k, v in enviado.items() if k != "s"}, "secreto")


async def test_flow_produccion_usa_otra_url():
    doble = Doble(lambda r: httpx.Response(200, json={"url": "https://www.flow.cl/x", "token": "T", "flowOrder": 1}))
    await Flow(doble.cliente()).crear(PasarelaEnUso(1, "produccion", FLOW.credenciales), _intencion(), URLS_HTTPS)
    assert str(doble.peticiones[0].url).startswith("https://www.flow.cl/api/")


async def test_flow_exige_email():
    with pytest.raises(ErrorProveedor):
        await Flow(Doble(lambda r: httpx.Response(200)).cliente()).crear(FLOW, _intencion(email=None), URLS_HTTPS)


def _estado_flow(status, **extra):
    return {"flowOrder": 998, "commerceOrder": "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "status": status, "amount": "6238",
            "payer": "vecino@correo.cl", "optional": {"rut": "11.111.111-1"},
            "paymentData": {"media": "Webpay", "autorizationCode": "123456", "cardLast4Numbers": "6623",
                            "fee": 199, "mediaType": "Credito"},
            **extra}


@pytest.mark.parametrize("status,esperado", [(1, "PENDIENTE"), (2, "APROBADO"), (3, "RECHAZADO"),
                                             (4, "RECHAZADO"), (9, "PENDIENTE")])
async def test_flow_estados(status, esperado):
    doble = Doble(lambda r: httpx.Response(200, json=_estado_flow(status)))
    resultado = await Flow(doble.cliente()).verificar(FLOW, "TOK123")
    assert resultado.estado == esperado
    assert "payment/getStatusExtended" in str(doble.peticiones[0].url)


async def test_flow_resultado_aprobado_y_filtrado():
    doble = Doble(lambda r: httpx.Response(200, json=_estado_flow(2)))
    r = await Flow(doble.cliente()).verificar(FLOW, "TOK123")
    assert (r.monto, r.transaccion, r.autorizacion, r.ultimos_digitos, r.medio) == (
        6238, "998", "123456", "6623", "Webpay")
    texto = json.dumps(r.datos)
    assert "vecino@correo.cl" not in texto and "11.111.111-1" not in texto
    assert r.datos["paymentData"]["fee"] == 199


async def test_flow_rechazo_con_motivo():
    doble = Doble(lambda r: httpx.Response(200, json=_estado_flow(3, lastError={"code": 1, "message": "Fondos insuficientes"})))
    r = await Flow(doble.cliente()).verificar(FLOW, "TOK123")
    assert r.estado == "RECHAZADO" and r.motivo == "Fondos insuficientes"


async def test_flow_consultar_por_flow_order_o_por_orden_del_comercio():
    doble = Doble(lambda r: httpx.Response(200, json=_estado_flow(2)))
    await Flow(doble.cliente()).consultar(FLOW, _intencion(transaccion="998"))
    assert "getStatusByFlowOrderExtended" in str(doble.peticiones[0].url)

    doble = Doble(lambda r: httpx.Response(400, json={"code": 1700, "message": "Transaction not found"}))
    r = await Flow(doble.cliente()).consultar(FLOW, _intencion())
    assert "getStatusByCommerceId" in str(doble.peticiones[0].url)
    assert r.estado == "PENDIENTE"


@pytest.mark.parametrize("status_http,cuerpo", [
    (401, {"code": 108, "message": "Invalid ApiKey"}),
    (400, {"code": 105, "message": "apiKey not found"}),
    (501, {"code": 105, "message": "apiKey not found"}),
    (400, {"code": 106, "message": "Invalid signature"}),
])
async def test_flow_errores_de_credenciales(status_http, cuerpo):
    doble = Doble(lambda r: httpx.Response(status_http, json=cuerpo))
    with pytest.raises(ErrorCredenciales):
        await Flow(doble.cliente()).verificar(FLOW, "TOK")
    with pytest.raises(ErrorCredenciales):
        await Flow(doble.cliente()).probar(FLOW)


async def test_flow_error_400_generico():
    doble = Doble(lambda r: httpx.Response(400, json={"code": 2000, "message": "amount is required"}))
    with pytest.raises(ErrorProveedor) as exc:
        await Flow(doble.cliente()).crear(FLOW, _intencion(), URLS_HTTPS)
    assert not isinstance(exc.value, ErrorCredenciales)


async def test_flow_prueba_de_conexion_ok():
    doble = Doble(lambda r: httpx.Response(400, json={"code": 1700, "message": "Transaction not found"}))
    await Flow(doble.cliente()).probar(FLOW)
    assert "getStatusByCommerceId" in str(doble.peticiones[0].url)


async def test_flow_sin_red():
    def caido(request):
        raise httpx.ConnectError("sin red")
    with pytest.raises(ErrorProveedor) as exc:
        await Flow(Doble(caido).cliente()).probar(FLOW)
    assert not isinstance(exc.value, ErrorCredenciales)


# ---------------------------------------------------------------------------
# Khipu
# ---------------------------------------------------------------------------

def _creado(r):
    return httpx.Response(201, json={"payment_id": "abc123def456", "payment_url": "https://khipu.com/payment/info/abc123def456"})


async def test_khipu_crear_con_notificacion_https():
    doble = Doble(_creado)
    redir = await Khipu(doble.cliente()).crear(KHIPU, _intencion(), URLS_HTTPS)
    assert (redir.url, redir.token, redir.metodo) == ("https://khipu.com/payment/info/abc123def456", "abc123def456", "GET")
    peticion = doble.peticiones[0]
    assert peticion.headers["x-api-key"] == "khipu-key"
    cuerpo = json.loads(peticion.content)
    assert cuerpo["amount"] == 6238 and cuerpo["currency"] == "CLP"
    assert cuerpo["transaction_id"] == "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    assert cuerpo["custom"] == "0d9f7c1e-0000-4000-8000-000000000001"
    assert cuerpo["return_url"] == URLS_HTTPS.retorno and cuerpo["cancel_url"] == URLS_HTTPS.cancelacion
    assert cuerpo["notify_url"] == URLS_HTTPS.notificacion and cuerpo["notify_api_version"] == "3.0"
    assert cuerpo["expires_date"].endswith("Z")


async def test_khipu_sin_https_no_envia_notify_url():
    doble = Doble(_creado)
    await Khipu(doble.cliente()).crear(KHIPU, _intencion(), URLS_LOCAL)
    cuerpo = json.loads(doble.peticiones[0].content)
    assert "notify_url" not in cuerpo and "notify_api_version" not in cuerpo


def _pago_khipu(status, detalle):
    return {"payment_id": "abc123def456", "status": status, "status_detail": detalle, "amount": 6238,
            "currency": "CLP", "transaction_id": "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "payment_method": "simplified_transfer",
            "payer_name": "Juan Pérez", "payer_email": "vecino@correo.cl", "personal_identifier": "11.111.111-1"}


@pytest.mark.parametrize("status,detalle,esperado", [
    ("done", "normal", "APROBADO"),
    ("pending", "pending", "PENDIENTE"),
    ("verifying", "pending", "PENDIENTE"),
    ("done", "rejected-by-payer", "RECHAZADO"),
    ("done", "reversed", "RECHAZADO"),
    ("done", "marked-paid-by-receiver", "RECHAZADO"),
    ("raro", "nuevo-estado", "PENDIENTE"),
])
async def test_khipu_estados(status, detalle, esperado):
    doble = Doble(lambda r: httpx.Response(200, json=_pago_khipu(status, detalle)))
    r = await Khipu(doble.cliente()).verificar(KHIPU, "abc123def456")
    assert r.estado == esperado
    assert str(doble.peticiones[0].url) == "https://payment-api.khipu.com/v3/payments/abc123def456"
    texto = json.dumps(r.datos)
    assert "Juan" not in texto and "vecino@correo.cl" not in texto and "11.111.111-1" not in texto


@pytest.mark.parametrize("status_http,error", [(200, None), (401, ErrorCredenciales), (403, ErrorCredenciales),
                                               (500, ErrorProveedor)])
async def test_khipu_prueba_de_conexion(status_http, error):
    doble = Doble(lambda r: httpx.Response(status_http, json={"banks": []} if status_http == 200 else {"message": "x"}))
    if error is None:
        await Khipu(doble.cliente()).probar(KHIPU)
    else:
        with pytest.raises(error):
            await Khipu(doble.cliente()).probar(KHIPU)
    assert str(doble.peticiones[0].url).endswith("/v3/banks")


@pytest.mark.parametrize("status_http,esperado", [(200, True), (204, True), (400, False), (404, False)])
async def test_khipu_anular(status_http, esperado):
    doble = Doble(lambda r: httpx.Response(status_http))
    assert await Khipu(doble.cliente()).anular(KHIPU, "abc123def456") is esperado
    assert doble.peticiones[0].method == "DELETE"


async def test_khipu_consultar_sin_identificador_no_llama():
    doble = Doble(lambda r: httpx.Response(200))
    r = await Khipu(doble.cliente()).consultar(KHIPU, _intencion())
    assert r.estado == "PENDIENTE" and doble.peticiones == []
