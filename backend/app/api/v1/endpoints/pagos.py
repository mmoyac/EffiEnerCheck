"""
Pagos en línea (cambio pasarelas-pago): opciones para pagar, estado de una intención, consulta a
pedido, pagos en revisión y los endpoints PÚBLICOS de retorno y notificación de los proveedores.

Retorno y webhook no tienen sesión: lo que traen solo IDENTIFICA la intención, que se busca en la base
ANTES de llamar al proveedor (un token inventado no genera llamadas). El resultado sale siempre de
`flujo.confirmar`, que consulta al proveedor. nginx limita estas rutas por IP (zona enercheck_pagos).
"""
import logging
import uuid
from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import registrar_auditoria
from app.core.config import settings
from app.core.dependencies import AdminRequired, AnyRoleRequired, TenantId, get_current_user, get_db
from app.models.pago import IntencionPago, PasarelaPago
from app.models.usuario import Usuario
from app.schemas.pago import IntencionResponse, IntencionRevisionResponse, OpcionPagoResponse, ResolverRequest
from app.services.pagos import flujo
from app.services.pagos.consumidores import consumidor
from app.services.pagos.pasarelas import ahora, cotizar, pasarelas_ofrecibles
from app.services.pagos.proveedores import REGISTRO

router = APIRouter(prefix="/pagos", tags=["pagos"])
log = logging.getLogger(__name__)

DB = Annotated[AsyncSession, Depends(get_db)]
CONSULTA_MINIMA = timedelta(seconds=10)


def _response(i: IntencionPago, pasarela: PasarelaPago) -> dict[str, Any]:
    return dict(
        id=i.id, estado=i.estado, concepto=i.concepto, descripcion=i.descripcion, monto=i.monto,
        comision=i.comision, total=i.total, pasarela_nombre=pasarela.nombre_visible, vence_at=i.vence_at,
        created_at=i.created_at, confirmado_at=i.confirmado_at, numero_operacion=i.transaccion_proveedor,
        autorizacion=i.autorizacion, ultimos_digitos=i.ultimos_digitos, medio=i.medio, motivo=i.motivo,
        volver_a=consumidor(i.concepto).volver_a(i),
    )


async def _get_intencion_o_404(intencion_id: uuid.UUID, user: Usuario, db: AsyncSession) -> IntencionPago:
    """Solo quien inició el pago y la administración de su condominio la ven (el resto, 404)."""
    i = await db.get(IntencionPago, intencion_id, populate_existing=True)
    if i is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado")
    rol = user.rol.nombre
    es_admin = rol == "super_admin" or (rol == "admin_condominio" and user.condominio_id == i.condominio_id)
    if i.usuario_id != user.id and not es_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado")
    return i


# ---------------------------------------------------------------------------
# Comunero
# ---------------------------------------------------------------------------

@router.get("/disponibles", response_model=list[OpcionPagoResponse])
async def disponibles(
    monto: int,
    current_user: Annotated[Usuario, Depends(AnyRoleRequired)],
    db: DB,
):
    """Pasarelas que se pueden ofrecer para pagar `monto`, con su comisión y total."""
    if monto <= 0 or current_user.condominio_id is None:
        return []
    opciones = []
    for p in await pasarelas_ofrecibles(db, current_user.condominio_id):
        comision, total, motivo = cotizar(p, monto)
        opciones.append(OpcionPagoResponse(
            pasarela_id=p.id, nombre_visible=p.nombre_visible, proveedor=p.proveedor,
            comision_porcentaje=p.comision_porcentaje, comision_fija=p.comision_fija,
            monto=monto, comision=comision, total=total, disponible=motivo is None, motivo=motivo,
        ))
    return opciones


# ---------------------------------------------------------------------------
# Administración: pagos en revisión
# ---------------------------------------------------------------------------

@router.get("/revision", response_model=list[IntencionRevisionResponse])
async def en_revision(
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
    incluir_resueltas: bool = False,
):
    stmt = (
        select(IntencionPago, PasarelaPago, Usuario)
        .join(PasarelaPago, PasarelaPago.id == IntencionPago.pasarela_id)
        .join(Usuario, Usuario.id == IntencionPago.usuario_id)
        .where(IntencionPago.estado == "EN_REVISION")
        .order_by(IntencionPago.updated_at.desc())
    )
    if tenant_id is not None:
        stmt = stmt.where(IntencionPago.condominio_id == tenant_id)
    if not incluir_resueltas:
        stmt = stmt.where(IntencionPago.resuelta_at.is_(None))
    return [
        IntencionRevisionResponse(
            **_response(i, p), usuario_nombre=u.nombre, monto_confirmado=i.monto_confirmado,
            resuelta_at=i.resuelta_at, nota_resolucion=i.nota_resolucion,
        )
        for i, p, u in (await db.execute(stmt)).all()
    ]


@router.post("/{intencion_id}/resolver", response_model=IntencionRevisionResponse)
async def resolver(
    intencion_id: uuid.UUID,
    data: ResolverRequest,
    request: Request,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """Marca resuelto un pago en revisión. El dinero se arregla por fuera (p. ej. devolución en el proveedor)."""
    i = await db.get(IntencionPago, intencion_id, with_for_update=True, populate_existing=True)
    if i is None or (tenant_id is not None and i.condominio_id != tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado")
    if i.estado != "EN_REVISION":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este pago no está en revisión")
    if i.resuelta_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este pago ya está resuelto")
    i.resuelta_at = ahora()
    i.resuelta_por_id = current_user.id
    i.nota_resolucion = data.nota.strip()
    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=i.condominio_id, accion="RESOLVER_PAGO_EN_LINEA",
        detalles={"intencion_pago_id": str(i.id), "nota": i.nota_resolucion, "total": i.total,
                  "monto_confirmado": i.monto_confirmado},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    pasarela = await db.get(PasarelaPago, i.pasarela_id)
    u = await db.get(Usuario, i.usuario_id)
    return IntencionRevisionResponse(
        **_response(i, pasarela), usuario_nombre=u.nombre, monto_confirmado=i.monto_confirmado,
        resuelta_at=i.resuelta_at, nota_resolucion=i.nota_resolucion,
    )


# ---------------------------------------------------------------------------
# Públicos: retorno del navegador y notificación del proveedor
# ---------------------------------------------------------------------------

async def _datos(request: Request) -> dict[str, Any]:
    """Query string + cuerpo de formulario (Flow) o JSON (Khipu). Nunca falla: ante dudas, vacío."""
    datos: dict[str, Any] = dict(request.query_params)
    if request.method != "POST":
        return datos
    tipo = request.headers.get("content-type", "")
    try:
        if "application/json" in tipo:
            cuerpo = await request.json()
            if isinstance(cuerpo, dict):
                datos.update(cuerpo)
        else:
            datos.update({k: v for k, v in (await request.form()).items() if isinstance(v, str)})
    except Exception:  # noqa: BLE001 — un cuerpo mal formado no identifica nada
        log.info("Pagos: cuerpo ilegible en %s", request.url.path)
    return datos


async def _buscar(db: AsyncSession, proveedor: str, datos: dict[str, Any], *, por_intencion: bool) -> IntencionPago | None:
    """Busca la intención en la base, sin llamar al proveedor."""
    stmt = select(IntencionPago).join(PasarelaPago, PasarelaPago.id == IntencionPago.pasarela_id).where(
        PasarelaPago.proveedor == proveedor
    )
    if por_intencion and datos.get("intencion"):
        try:
            stmt = stmt.where(IntencionPago.id == uuid.UUID(str(datos["intencion"])))
        except ValueError:
            return None
    else:
        token = REGISTRO[proveedor].token_de(datos)
        if not token:
            return None
        stmt = stmt.where(IntencionPago.token_proveedor == token)
    return (await db.execute(stmt.limit(1))).scalar_one_or_none()


async def _retorno(proveedor: str, request: Request, db: AsyncSession) -> Response:
    base_defecto = settings.PORTAL_URL_POR_DEFECTO.rstrip("/")
    no_encontrado = RedirectResponse(f"{base_defecto}/pagos/desconocido/resultado", status_code=status.HTTP_303_SEE_OTHER)
    if proveedor not in REGISTRO:
        return no_encontrado
    datos = await _datos(request)
    ad = REGISTRO[proveedor]
    i = await _buscar(db, proveedor, datos, por_intencion=ad.retorno_por_intencion)
    if i is None:
        return no_encontrado
    intencion_id, condominio_id = i.id, i.condominio_id
    try:
        if str(datos.get("cancelado")) == "1":
            await flujo.cancelar(db, intencion_id)
        else:
            await flujo.confirmar(db, intencion_id, "retorno")
    except Exception:  # noqa: BLE001 — el comunero igual llega a su pantalla, que vuelve a consultar
        log.exception("Pagos: error al procesar el retorno de %s", intencion_id)
        await db.rollback()
    base = await flujo.base_portal(db, condominio_id)
    return RedirectResponse(f"{base}/pagos/{intencion_id}/resultado", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/retorno/{proveedor}", include_in_schema=False)
async def retorno_get(proveedor: str, request: Request, db: DB):
    return await _retorno(proveedor, request, db)


@router.post("/retorno/{proveedor}", include_in_schema=False)
async def retorno_post(proveedor: str, request: Request, db: DB):
    return await _retorno(proveedor, request, db)


@router.post("/webhook/{proveedor}", include_in_schema=False)
async def webhook(proveedor: str, request: Request, db: DB):
    if proveedor not in REGISTRO:
        return JSONResponse({"detail": "No encontrado"}, status_code=status.HTTP_404_NOT_FOUND)
    i = await _buscar(db, proveedor, await _datos(request), por_intencion=False)
    if i is None:
        return JSONResponse({"detail": "No encontrado"}, status_code=status.HTTP_404_NOT_FOUND)
    try:
        await flujo.confirmar(db, i.id, "webhook")
    except Exception:  # noqa: BLE001 — la conciliación lo retoma; el proveedor no necesita reintentar
        log.exception("Pagos: error al procesar el webhook de %s", i.id)
        await db.rollback()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Estado de una intención (al final: /{intencion_id} no debe tapar las rutas de arriba)
# ---------------------------------------------------------------------------

@router.get("/{intencion_id}", response_model=IntencionResponse)
async def ver(
    intencion_id: uuid.UUID,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: DB,
):
    i = await _get_intencion_o_404(intencion_id, current_user, db)
    return IntencionResponse(**_response(i, await db.get(PasarelaPago, i.pasarela_id)))


@router.post("/{intencion_id}/consultar", response_model=IntencionResponse)
async def consultar(
    intencion_id: uuid.UUID,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: DB,
):
    """Consulta al proveedor por el mismo camino que la conciliación (máximo una vez cada 10 s)."""
    i = await _get_intencion_o_404(intencion_id, current_user, db)
    if i.consultado_at and ahora() - i.consultado_at < CONSULTA_MINIMA:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Espera unos segundos antes de volver a consultar"
        )
    i = await flujo.confirmar(db, intencion_id, "consulta")
    return IntencionResponse(**_response(i, await db.get(PasarelaPago, i.pasarela_id)))
