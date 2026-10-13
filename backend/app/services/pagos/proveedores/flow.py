"""
Flow (API REST 3.0.1): tarjetas, Webpay, Mach y otros medios.

Integración (sandbox.flow.cl) y producción (www.flow.cl) son cuentas distintas con keys distintas.
Cada llamada se firma: `s` = HMAC-SHA256 en hex, con la secretKey, de `nombre+valor` de todos los
parámetros ordenados alfabéticamente.
"""
import hashlib
import hmac
import secrets
from typing import Any

import httpx

from .base import (
    Adaptador,
    CampoCredencial,
    ErrorCredenciales,
    ErrorProveedor,
    IntencionEnUso,
    PasarelaEnUso,
    Redireccion,
    Resultado,
    Urls,
    filtrar,
)

URLS_BASE = {"integracion": "https://sandbox.flow.cl/api", "produccion": "https://www.flow.cl/api"}

# status de Flow: 1 pendiente, 2 pagada, 3 rechazada, 4 anulada
ESTADOS = {1: "PENDIENTE", 2: "APROBADO", 3: "RECHAZADO", 4: "RECHAZADO"}
# Código de "Transaction not found": con credenciales válidas, la prueba de conexión lo recibe
NO_ENCONTRADA = 1700

# Se guarda solo esto de la respuesta: sin `payer` (correo del pagador) ni `optional`
CLAVES_RESPUESTA = {"flowOrder", "commerceOrder", "status", "amount", "currency", "requestDate"}
CLAVES_PAGO = {"date", "media", "mediaType", "amount", "currency", "fee", "balance", "transferDate"}


def firmar(parametros: dict[str, Any], secret_key: str) -> str:
    texto = "".join(f"{k}{parametros[k]}" for k in sorted(parametros) if k != "s")
    return hmac.new(secret_key.encode(), texto.encode(), hashlib.sha256).hexdigest()


def _es_error_de_credenciales(mensaje: str) -> bool:
    # Trampa: "apiKey not found" también contiene "not found". Si menciona la key, la firma o el
    # secreto, es SIEMPRE un problema de credenciales.
    m = mensaje.lower()
    return any(p in m for p in ("apikey", "api key", "firma", "signature", "secret", "invalid key"))


class Flow(Adaptador):
    proveedor = "flow"
    nombre = "Flow"
    campos_credenciales = [
        CampoCredencial("api_key", "API Key"),
        CampoCredencial("secret_key", "Secret Key"),
    ]
    requiere_email = True
    monto_minimo = 350

    def _base(self, pasarela: PasarelaEnUso) -> str:
        return URLS_BASE[pasarela.ambiente]

    def _firmados(self, pasarela: PasarelaEnUso, parametros: dict[str, Any]) -> dict[str, Any]:
        datos = {**parametros, "apiKey": pasarela.credenciales["api_key"]}
        return {**datos, "s": firmar(datos, pasarela.credenciales["secret_key"])}

    async def _llamar(self, pasarela: PasarelaEnUso, metodo: str, ruta: str, parametros: dict[str, Any]) -> dict:
        url = f"{self._base(pasarela)}/{ruta}"
        datos = self._firmados(pasarela, parametros)
        if metodo == "GET":
            request = httpx.Request("GET", url, params=datos)
        else:
            request = httpx.Request("POST", url, data=datos)
        respuesta = await self._enviar(request)
        try:
            cuerpo = respuesta.json()
        except ValueError:
            cuerpo = {}
        if respuesta.status_code == 200:
            return cuerpo
        mensaje = str(cuerpo.get("message") or respuesta.text[:200])
        codigo = cuerpo.get("code")
        if respuesta.status_code in (401, 403) or _es_error_de_credenciales(mensaje):
            raise ErrorCredenciales(f"Flow rechazó las credenciales: {mensaje}")
        raise ErrorFlow(respuesta.status_code, codigo, mensaje)

    async def crear(self, pasarela: PasarelaEnUso, intencion: IntencionEnUso, urls: Urls) -> Redireccion:
        if not intencion.email:
            raise ErrorProveedor("Flow exige el correo del pagador")
        cuerpo = await self._llamar(pasarela, "POST", "payment/create", {
            "commerceOrder": intencion.orden_comercio,
            "subject": intencion.descripcion[:255],
            "currency": "CLP",
            "amount": intencion.total,
            "email": intencion.email,
            "paymentMethod": 9,  # todos los medios habilitados en la cuenta
            "urlConfirmation": urls.notificacion,
            "urlReturn": urls.retorno,
            # Un poco más que la intención: la conciliación decide qué hacer con un pago tardío
            "timeout": max(intencion.segundos_restantes, 0) + 120,
            # Sin `optional`: Flow se lo muestra al pagador
        })
        url, token = cuerpo.get("url"), cuerpo.get("token")
        if not url or not token:
            raise ErrorProveedor("Flow no devolvió la dirección de pago")
        return Redireccion(
            url=f"{url}?token={token}", metodo="GET", token=token,
            transaccion=str(cuerpo["flowOrder"]) if cuerpo.get("flowOrder") is not None else None,
        )

    def token_de(self, datos: dict[str, Any]) -> str | None:
        token = datos.get("token")
        return str(token) if token else None

    def _resultado(self, cuerpo: dict) -> Resultado:
        try:
            estado_flow = int(cuerpo.get("status"))
        except (TypeError, ValueError):
            estado_flow = None
        estado = ESTADOS.get(estado_flow, "PENDIENTE")
        pago = cuerpo.get("paymentData") or {}
        error = cuerpo.get("lastError") or {}
        motivo = None
        if estado == "RECHAZADO":
            motivo = error.get("message") or ("Pago anulado" if estado_flow == 4 else "Pago rechazado")
        try:
            monto = int(float(cuerpo["amount"])) if cuerpo.get("amount") is not None else None
        except (TypeError, ValueError):
            monto = None
        datos = filtrar(cuerpo, CLAVES_RESPUESTA)
        if pago:
            datos["paymentData"] = filtrar(pago, CLAVES_PAGO)
        if error:
            datos["lastError"] = filtrar(error, {"code", "message"})
        ultimos = pago.get("cardLast4Numbers")
        return Resultado(
            estado=estado,
            monto=monto,
            transaccion=str(cuerpo["flowOrder"]) if cuerpo.get("flowOrder") is not None else None,
            orden_comercio=cuerpo.get("commerceOrder"),
            # Flow lo escribe sin "h"; se acepta también con ella por si lo corrigen
            autorizacion=pago.get("autorizationCode") or pago.get("authorizationCode") or None,
            ultimos_digitos=str(ultimos)[-4:] if ultimos else None,
            medio=pago.get("media") or None,
            motivo=motivo,
            datos=datos,
        )

    async def verificar(self, pasarela: PasarelaEnUso, token: str) -> Resultado:
        return self._resultado(await self._llamar(pasarela, "GET", "payment/getStatusExtended", {"token": token}))

    async def consultar(self, pasarela: PasarelaEnUso, intencion: IntencionEnUso) -> Resultado:
        if intencion.transaccion:
            cuerpo = await self._llamar(
                pasarela, "GET", "payment/getStatusByFlowOrderExtended", {"flowOrder": intencion.transaccion}
            )
            return self._resultado(cuerpo)
        if intencion.token:
            return await self.verificar(pasarela, intencion.token)
        try:
            cuerpo = await self._llamar(
                pasarela, "GET", "payment/getStatusByCommerceId", {"commerceId": intencion.orden_comercio}
            )
        except ErrorFlow as exc:
            if exc.codigo == NO_ENCONTRADA:
                return Resultado(estado="PENDIENTE", motivo="Flow no registra la orden")
            raise
        return self._resultado(cuerpo)

    async def probar(self, pasarela: PasarelaEnUso) -> None:
        try:
            await self._llamar(
                pasarela, "GET", "payment/getStatusByCommerceId",
                {"commerceId": f"prueba-conexion-{secrets.token_hex(6)}"},
            )
        except ErrorFlow as exc:
            if exc.codigo == NO_ENCONTRADA or "not found" in exc.mensaje.lower():
                return  # credenciales válidas: la orden inventada no existe
            raise


class ErrorFlow(ErrorProveedor):
    def __init__(self, status_http: int, codigo: Any, mensaje: str):
        self.status_http = status_http
        try:
            self.codigo = int(codigo) if codigo is not None else None
        except (TypeError, ValueError):
            self.codigo = None
        self.mensaje = mensaje
        super().__init__(f"Flow respondió {status_http}: {mensaje}")
