"""
Flujo de un pago en línea: iniciar, confirmar, cancelar y expirar (spec pagos-en-linea).

Reglas que este módulo hace cumplir:
- El resultado lo decide SIEMPRE una consulta al proveedor; el navegador y el webhook solo identifican.
- Ninguna llamada al proveedor ocurre con una transacción abierta: se hace commit antes de salir a la
  red y luego se toma `SELECT ... FOR UPDATE` de la intención para aplicar el resultado.
- `confirmar` es el único camino de confirmación (retorno, webhook, conciliación y consulta a pedido):
  con el bloqueo de la fila, un pago aprobado se aplica una sola vez aunque lleguen varios avisos.
- Solo se rechaza con una respuesta definitiva del proveedor o tras anular con éxito en el proveedor.
"""
import base64
import logging
import uuid
from datetime import timedelta
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import registrar_auditoria
from app.core.config import settings
from app.models.condominio import Condominio
from app.models.pago import ESTADOS_FINALES, IntencionPago, PasarelaPago
from app.services.pagos import cifrado
from app.services.pagos.consumidores import consumidor
from app.services.pagos.pasarelas import ahora, cotizar, en_uso
from app.services.pagos.proveedores import adaptador
from app.services.pagos.proveedores.base import (
    ErrorProveedor,
    IntencionEnUso,
    Redireccion,
    Resultado,
    Urls,
)

log = logging.getLogger(__name__)

VIGENCIA = timedelta(minutes=15)


class PagoNoIniciado(RuntimeError):
    """El proveedor no creó el cobro: la intención quedó RECHAZADO y lo reservado, libre."""


class PagoInvalido(ValueError):
    """La pasarela no sirve para este pago (inactiva, de otro condominio o monto bajo el mínimo)."""


def orden_comercio(intencion_id: uuid.UUID) -> str:
    """El UUID en base32 sin relleno: 26 caracteres [A-Z2-7], válido como orden en cualquier proveedor."""
    return base64.b32encode(intencion_id.bytes).decode().rstrip("=")


async def base_portal(db: AsyncSession, condominio_id: int) -> str:
    condominio = await db.get(Condominio, condominio_id)
    return ((condominio.portal_url if condominio else None) or settings.PORTAL_URL_POR_DEFECTO).rstrip("/")


def urls(base: str, proveedor: str, intencion_id: uuid.UUID, por_intencion: bool) -> Urls:
    retorno = f"{base}/api/v1/pagos/retorno/{proveedor}"
    cancelacion = retorno
    if por_intencion:
        retorno = f"{retorno}?{urlencode({'intencion': str(intencion_id)})}"
        cancelacion = f"{retorno}&cancelado=1"
    # En desarrollo, un túnel reemplaza solo la base de la notificación (el proveedor llama desde internet)
    base_notificacion = (settings.URL_PUBLICA_PAGOS or base).rstrip("/")
    return Urls(retorno=retorno, cancelacion=cancelacion,
                notificacion=f"{base_notificacion}/api/v1/pagos/webhook/{proveedor}")


def _en_uso(i: IntencionPago) -> IntencionEnUso:
    return IntencionEnUso(
        id=str(i.id), orden_comercio=i.orden_comercio, total=i.total, descripcion=i.descripcion,
        email=i.email_pagador, segundos_restantes=int((i.vence_at - ahora()).total_seconds()),
        token=i.token_proveedor, transaccion=i.transaccion_proveedor,
    )


async def _bloquear(db: AsyncSession, intencion_id: uuid.UUID) -> IntencionPago:
    return (
        await db.execute(
            select(IntencionPago).where(IntencionPago.id == intencion_id)
            .with_for_update().execution_options(populate_existing=True)
        )
    ).scalar_one()


async def _auditar(db: AsyncSession, i: IntencionPago, accion: str, origen: str, **extra) -> None:
    await registrar_auditoria(
        db, usuario_id=i.usuario_id, condominio_id=i.condominio_id, accion=accion,
        detalles={"intencion_pago_id": str(i.id), "concepto": i.concepto, "referencia_id": i.referencia_id,
                  "total": i.total, "estado": i.estado, "origen": origen, **extra},
    )


def _terminar(i: IntencionPago, estado: str, motivo: str | None = None) -> None:
    i.estado = estado
    if motivo:
        i.motivo = motivo
    if estado in ESTADOS_FINALES:
        i.email_pagador = None  # ya no hace falta enviarlo a nadie


# ---------------------------------------------------------------------------
# Iniciar
# ---------------------------------------------------------------------------

async def crear_intencion(
    db: AsyncSession, *, pasarela: PasarelaPago, usuario_id: int, email: str | None, concepto: str,
    referencia_id: int, descripcion: str, monto: int,
) -> IntencionPago:
    """Agrega la intención a la transacción del llamador (sin commit). Lanza PagoInvalido."""
    comision, total, motivo = cotizar(pasarela, monto)
    if motivo:
        raise PagoInvalido(motivo)
    if adaptador(pasarela.proveedor).requiere_email and not email:
        raise PagoInvalido(f"{pasarela.nombre_visible} exige un correo y tu cuenta no tiene uno")
    intencion_id = uuid.uuid4()
    i = IntencionPago(
        id=intencion_id, condominio_id=pasarela.condominio_id, pasarela_id=pasarela.id, usuario_id=usuario_id,
        concepto=concepto, referencia_id=referencia_id, descripcion=descripcion[:255],
        monto=monto, comision=comision, total=total, estado="INICIADO", vence_at=ahora() + VIGENCIA,
        orden_comercio=orden_comercio(intencion_id), email_pagador=email,
    )
    db.add(i)
    await db.flush()
    return i


async def lanzar(db: AsyncSession, intencion_id: uuid.UUID) -> Redireccion:
    """
    Crea el cobro en el proveedor para una intención ya guardada (con commit). Si el proveedor falla,
    la intención queda RECHAZADO, lo reservado se libera y se lanza PagoNoIniciado.
    """
    i = await db.get(IntencionPago, intencion_id, populate_existing=True)
    pasarela = await db.get(PasarelaPago, i.pasarela_id)
    ad = adaptador(pasarela.proveedor)
    direcciones = urls(await base_portal(db, i.condominio_id), pasarela.proveedor, i.id, ad.retorno_por_intencion)
    datos = _en_uso(i)
    error: str | None = None
    try:
        en = en_uso(pasarela)
    except (cifrado.CredencialesIlegibles, cifrado.ClaveMaestraInvalida) as exc:
        log.error("Pasarela %s sin credenciales legibles: %s", pasarela.id, exc)
        error = "La pasarela no tiene credenciales válidas"
    await db.commit()  # sin transacción abierta mientras se llama al proveedor

    redireccion: Redireccion | None = None
    if error is None:
        try:
            redireccion = await ad.crear(en, datos, direcciones)
        except ErrorProveedor as exc:
            log.warning("Pago %s: el proveedor no creó el cobro: %s", intencion_id, exc)
            error = f"{pasarela.nombre_visible} no pudo iniciar el pago"

    i = await _bloquear(db, intencion_id)
    if redireccion is None:
        # Nunca llegó a existir en el proveedor: rechazar es seguro
        if i.estado == "INICIADO":
            await consumidor(i.concepto).liberar(db, i, error)
            _terminar(i, "RECHAZADO", error)
            await _auditar(db, i, "RECHAZAR_PAGO_EN_LINEA", "inicio")
        await db.commit()
        raise PagoNoIniciado(error)

    i.token_proveedor = redireccion.token
    i.transaccion_proveedor = redireccion.transaccion
    await _auditar(db, i, "INICIAR_PAGO_EN_LINEA", "inicio", pasarela_id=pasarela.id, proveedor=pasarela.proveedor)
    await db.commit()
    return redireccion


# ---------------------------------------------------------------------------
# Confirmar (único camino)
# ---------------------------------------------------------------------------

async def _aplicar_resultado(db: AsyncSession, i: IntencionPago, r: Resultado, origen: str) -> None:
    """Con la intención bloqueada. Aplica el resultado del proveedor según el estado actual."""
    if r.orden_comercio and r.orden_comercio != i.orden_comercio:
        log.error("Pago %s: el proveedor respondió por otra orden (%s); se ignora", i.id, r.orden_comercio)
        return

    if r.estado == "APROBADO":
        i.transaccion_proveedor = r.transaccion or i.transaccion_proveedor
        i.autorizacion = r.autorizacion
        i.ultimos_digitos = r.ultimos_digitos
        i.medio = r.medio
        i.monto_confirmado = r.monto
        i.respuesta_proveedor = r.datos
        cons = consumidor(i.concepto)
        if r.monto != i.total:
            motivo = f"El proveedor confirmó ${r.monto or 0:,} y se esperaban ${i.total:,}".replace(",", ".")
            if i.estado == "INICIADO":
                await cons.liberar(db, i, motivo)
            _terminar(i, "EN_REVISION", motivo)
            await _auditar(db, i, "PAGO_EN_LINEA_EN_REVISION", origen, monto_confirmado=r.monto)
            return
        estaba_vencida = i.estado == "EXPIRADO"
        motivo = await cons.aplicar(db, i)
        i.confirmado_at = ahora()
        if motivo:
            _terminar(i, "EN_REVISION", f"Pago aprobado sin aplicar: {motivo}")
            await _auditar(db, i, "PAGO_EN_LINEA_EN_REVISION", origen, monto_confirmado=r.monto)
        else:
            _terminar(i, "CONFIRMADO")
            await _auditar(db, i, "CONFIRMAR_PAGO_EN_LINEA", origen, tardio=estaba_vencida)
        return

    if r.estado == "RECHAZADO":
        i.respuesta_proveedor = r.datos or i.respuesta_proveedor
        motivo = r.motivo or "El proveedor rechazó el pago"
        if i.estado == "INICIADO":
            await consumidor(i.concepto).liberar(db, i, motivo)
        _terminar(i, "RECHAZADO", motivo)
        await _auditar(db, i, "RECHAZAR_PAGO_EN_LINEA", origen)
        return

    # PENDIENTE: solo vence si ya pasó su plazo
    if i.estado == "INICIADO" and ahora() >= i.vence_at:
        motivo = "El pago no se completó a tiempo"
        await consumidor(i.concepto).liberar(db, i, motivo)
        _terminar(i, "EXPIRADO", motivo)
        await _auditar(db, i, "EXPIRAR_PAGO_EN_LINEA", origen)


async def confirmar(db: AsyncSession, intencion_id: uuid.UUID, origen: str) -> IntencionPago:
    """Consulta al proveedor y aplica el resultado. Idempotente. Nunca lanza por errores del proveedor."""
    i = await db.get(IntencionPago, intencion_id, populate_existing=True)
    if i is None or i.estado in ESTADOS_FINALES:
        return i
    pasarela = await db.get(PasarelaPago, i.pasarela_id)
    datos = _en_uso(i)
    try:
        en = en_uso(pasarela)
    except (cifrado.CredencialesIlegibles, cifrado.ClaveMaestraInvalida) as exc:
        log.error("Pago %s: credenciales ilegibles de la pasarela %s: %s", i.id, pasarela.id, exc)
        return i
    proveedor = pasarela.proveedor
    await db.commit()  # nada bloqueado mientras se consulta

    resultado: Resultado | None
    try:
        resultado = await adaptador(proveedor).consultar(en, datos)
    except ErrorProveedor as exc:
        log.warning("Pago %s (%s): no se pudo consultar al proveedor: %s", intencion_id, origen, exc)
        resultado = None

    i = await _bloquear(db, intencion_id)
    i.consultado_at = ahora()
    if resultado is not None and i.estado not in ESTADOS_FINALES:
        await _aplicar_resultado(db, i, resultado, origen)
    await db.commit()
    return i


async def cancelar(db: AsyncSession, intencion_id: uuid.UUID) -> IntencionPago:
    """
    El pagador volvió por la URL de cancelación. Solo se rechaza si el proveedor anula el cobro; si no
    puede (porque ya se pagó, por ejemplo), se consulta el estado real y se aplica.
    """
    i = await db.get(IntencionPago, intencion_id, populate_existing=True)
    if i is None or i.estado != "INICIADO" or not i.token_proveedor:
        return await confirmar(db, intencion_id, "cancelacion") if i else i
    pasarela = await db.get(PasarelaPago, i.pasarela_id)
    try:
        en = en_uso(pasarela)
    except (cifrado.CredencialesIlegibles, cifrado.ClaveMaestraInvalida):
        return i
    token, proveedor = i.token_proveedor, pasarela.proveedor
    await db.commit()

    anulada = await adaptador(proveedor).anular(en, token)
    if not anulada:
        return await confirmar(db, intencion_id, "cancelacion")

    i = await _bloquear(db, intencion_id)
    if i.estado == "INICIADO":
        motivo = "Cancelaste el pago"
        await consumidor(i.concepto).liberar(db, i, motivo)
        _terminar(i, "RECHAZADO", motivo)
        await _auditar(db, i, "RECHAZAR_PAGO_EN_LINEA", "cancelacion")
    await db.commit()
    return i
