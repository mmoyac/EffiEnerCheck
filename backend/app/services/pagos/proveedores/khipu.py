"""
Khipu (API de Pagos Instantáneos 3.0): transferencia bancaria.

No hay sandbox aparte: misma URL; la cuenta en "modo desarrollador" (banco DemoBank) va en una
pasarela de integración y la cuenta real en una de producción. Las llamadas llevan `x-api-key`.
El retorno no trae datos de Khipu: la intención viaja en la URL (`?intencion=<id>`).
"""
from datetime import datetime, timedelta, timezone
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

URL_BASE = "https://payment-api.khipu.com/v3"

# Con status=done, solo status_detail=normal es un pago; el resto no se registra
DETALLES_NO_PAGO = {
    "rejected-by-payer", "marked-as-abuse", "reversed", "partially-refunded", "fully-refunded",
    "marked-paid-by-receiver",
}
# Sin payer_name, payer_email, personal_identifier ni cuentas bancarias
CLAVES_RESPUESTA = {
    "payment_id", "status", "status_detail", "amount", "currency", "transaction_id", "custom",
    "payment_method", "funds_source", "conciliation_date", "out_of_date_conciliation", "bank",
}


class Khipu(Adaptador):
    proveedor = "khipu"
    nombre = "Khipu"
    campos_credenciales = [CampoCredencial("api_key", "API Key")]
    requiere_email = False
    monto_minimo = 1
    retorno_por_intencion = True

    def _request(self, pasarela: PasarelaEnUso, metodo: str, ruta: str, json: dict | None = None) -> httpx.Request:
        return httpx.Request(
            metodo, f"{URL_BASE}{ruta}", json=json,
            headers={"x-api-key": pasarela.credenciales["api_key"], "Accept": "application/json"},
        )

    async def _llamar(self, pasarela: PasarelaEnUso, metodo: str, ruta: str, json: dict | None = None) -> dict:
        respuesta = await self._enviar(self._request(pasarela, metodo, ruta, json))
        if respuesta.status_code in (401, 403):
            raise ErrorCredenciales("Khipu rechazó la API Key")
        if respuesta.status_code >= 300:
            try:
                mensaje = respuesta.json().get("message") or respuesta.text[:200]
            except ValueError:
                mensaje = respuesta.text[:200]
            raise ErrorProveedor(f"Khipu respondió {respuesta.status_code}: {mensaje}")
        try:
            return respuesta.json()
        except ValueError as exc:
            raise ErrorProveedor("Khipu respondió algo que no es JSON") from exc

    async def crear(self, pasarela: PasarelaEnUso, intencion: IntencionEnUso, urls: Urls) -> Redireccion:
        vence = datetime.now(timezone.utc) + timedelta(seconds=max(intencion.segundos_restantes, 0) + 120)
        cuerpo: dict[str, Any] = {
            "amount": intencion.total,
            "currency": "CLP",
            "subject": intencion.descripcion[:255],
            "transaction_id": intencion.orden_comercio,
            "custom": intencion.id,  # no se muestra al pagador
            "return_url": urls.retorno,
            "cancel_url": urls.cancelacion,
            "expires_date": vence.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        if intencion.email:
            cuerpo["payer_email"] = intencion.email
        if urls.notificacion_publica:
            # Khipu notifica desde internet: una URL http (localhost) solo generaría errores
            cuerpo["notify_url"] = urls.notificacion
            cuerpo["notify_api_version"] = "3.0"
        respuesta = await self._llamar(pasarela, "POST", "/payments", cuerpo)
        payment_id, payment_url = respuesta.get("payment_id"), respuesta.get("payment_url")
        if not payment_id or not payment_url:
            raise ErrorProveedor("Khipu no devolvió la dirección de pago")
        return Redireccion(url=payment_url, metodo="GET", token=payment_id, transaccion=payment_id)

    def token_de(self, datos: dict[str, Any]) -> str | None:
        payment_id = datos.get("payment_id")
        return str(payment_id) if payment_id else None

    def _resultado(self, cuerpo: dict) -> Resultado:
        status, detalle = cuerpo.get("status"), cuerpo.get("status_detail")
        if status == "done" and detalle == "normal":
            estado, motivo = "APROBADO", None
        elif detalle in DETALLES_NO_PAGO:
            estado, motivo = "RECHAZADO", f"Khipu informa el pago como {detalle}"
        else:
            # pending, verifying o cualquier estado que no conozcamos: nunca se aprueba por omisión
            estado, motivo = "PENDIENTE", None
        try:
            monto = int(float(cuerpo["amount"])) if cuerpo.get("amount") is not None else None
        except (TypeError, ValueError):
            monto = None
        return Resultado(
            estado=estado,
            monto=monto,
            transaccion=cuerpo.get("payment_id"),
            orden_comercio=cuerpo.get("transaction_id"),
            medio=cuerpo.get("payment_method") or "Transferencia",
            motivo=motivo,
            datos=filtrar(cuerpo, CLAVES_RESPUESTA),
        )

    async def verificar(self, pasarela: PasarelaEnUso, token: str) -> Resultado:
        return self._resultado(await self._llamar(pasarela, "GET", f"/payments/{token}"))

    async def consultar(self, pasarela: PasarelaEnUso, intencion: IntencionEnUso) -> Resultado:
        token = intencion.token or intencion.transaccion
        if not token:
            return Resultado(estado="PENDIENTE", motivo="Sin identificador de pago de Khipu")
        return await self.verificar(pasarela, token)

    async def probar(self, pasarela: PasarelaEnUso) -> None:
        await self._llamar(pasarela, "GET", "/banks")

    async def anular(self, pasarela: PasarelaEnUso, token: str) -> bool:
        try:
            respuesta = await self._enviar(self._request(pasarela, "DELETE", f"/payments/{token}"))
        except ErrorProveedor:
            return False
        return 200 <= respuesta.status_code < 300
