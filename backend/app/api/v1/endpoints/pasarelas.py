"""
Pasarelas de pago de cada condominio (cambio pasarelas-pago).

Solo el super_admin las crea, modifica, prueba, activa y elimina. El admin_condominio las ve (sin
credenciales). Las credenciales se cifran al guardarlas y NUNCA vuelven por la API ni a la auditoría:
solo se informa si están cargadas y los nombres de los campos cambiados.
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import registrar_auditoria
from app.core.dependencies import AdminRequired, SuperAdminRequired, TenantId, get_db
from app.models.condominio import Condominio
from app.models.pago import IntencionPago, PasarelaPago
from app.models.usuario import Usuario
from app.schemas.pago import (
    CampoCredencialResponse,
    CredencialesRequest,
    PasarelaCreate,
    PasarelaResponse,
    PasarelaUpdate,
    ProveedorResponse,
    PruebaResponse,
)
from app.services.pagos import cifrado
from app.services.pagos.pasarelas import (
    CredencialesInvalidas,
    ahora,
    en_uso,
    guardar_credenciales,
    prueba_vigente,
)
from app.services.pagos.proveedores import REGISTRO, adaptador
from app.services.pagos.proveedores.base import ErrorCredenciales, ErrorProveedor

router = APIRouter(prefix="/pasarelas", tags=["pasarelas"])
log = logging.getLogger(__name__)

DB = Annotated[AsyncSession, Depends(get_db)]


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def _tiene_pagos(pasarela_id: int, db: AsyncSession) -> bool:
    return bool(await db.scalar(select(exists().where(IntencionPago.pasarela_id == pasarela_id))))


async def _response(p: PasarelaPago, db: AsyncSession) -> PasarelaResponse:
    return PasarelaResponse(
        id=p.id,
        condominio_id=p.condominio_id,
        proveedor=p.proveedor,
        proveedor_nombre=REGISTRO[p.proveedor].nombre if p.proveedor in REGISTRO else p.proveedor,
        nombre_visible=p.nombre_visible,
        ambiente=p.ambiente,
        comision_porcentaje=p.comision_porcentaje,
        comision_fija=p.comision_fija,
        orden=p.orden,
        activa=p.activa,
        credenciales_cargadas=bool(p.credenciales_cifradas),
        credenciales_at=p.credenciales_at,
        prueba_at=p.prueba_at,
        prueba_ok=p.prueba_ok,
        prueba_mensaje=p.prueba_mensaje,
        prueba_vigente=prueba_vigente(p),
        tiene_pagos=await _tiene_pagos(p.id, db),
    )


async def _get_pasarela_o_404(pasarela_id: int, tenant_id: int | None, db: AsyncSession) -> PasarelaPago:
    p = await db.get(PasarelaPago, pasarela_id)
    # Otro condominio = no existe (no se revela)
    if not p or (tenant_id is not None and p.condominio_id != tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pasarela no encontrada")
    return p


def _resumen(p: PasarelaPago) -> dict:
    """Para la auditoría: sin credenciales."""
    return {
        "pasarela_id": p.id, "proveedor": p.proveedor, "nombre_visible": p.nombre_visible,
        "ambiente": p.ambiente, "comision_porcentaje": str(p.comision_porcentaje),
        "comision_fija": p.comision_fija, "orden": p.orden, "activa": p.activa,
    }


def _exigir_clave_maestra() -> None:
    """Sin PAGOS_CLAVE_MAESTRA (pagos en línea aún no habilitados en el servidor) no se guarda nada."""
    try:
        cifrado.leer_clave()
    except cifrado.ClaveMaestraInvalida as exc:
        log.error("Pasarelas: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El servidor no tiene configurada la clave para guardar credenciales (PAGOS_CLAVE_MAESTRA)",
        )


def _guardar(p: PasarelaPago, credenciales: dict[str, str]) -> None:
    try:
        guardar_credenciales(p, credenciales)
    except CredencialesInvalidas as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except cifrado.ClaveMaestraInvalida as exc:
        log.error("Pasarelas: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El servidor no tiene configurada la clave para guardar credenciales (PAGOS_CLAVE_MAESTRA)",
        )


@router.get("/proveedores", response_model=list[ProveedorResponse])
async def proveedores(current_user: Annotated[Usuario, Depends(SuperAdminRequired)]):
    """Catálogo para el formulario dinámico de credenciales."""
    return [
        ProveedorResponse(
            proveedor=a.proveedor, nombre=a.nombre,
            campos_credenciales=[CampoCredencialResponse(**vars(c)) for c in a.campos_credenciales],
            requiere_email=a.requiere_email, monto_minimo=a.monto_minimo,
        )
        for a in REGISTRO.values()
    ]


@router.get("/", response_model=list[PasarelaResponse])
async def listar(
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
    condominio_id: int | None = None,
):
    stmt = select(PasarelaPago).order_by(PasarelaPago.condominio_id, PasarelaPago.orden, PasarelaPago.id)
    filtro = tenant_id if tenant_id is not None else condominio_id
    if filtro is not None:
        stmt = stmt.where(PasarelaPago.condominio_id == filtro)
    return [await _response(p, db) for p in (await db.execute(stmt)).scalars().all()]


@router.get("/{pasarela_id}", response_model=PasarelaResponse)
async def ver(
    pasarela_id: int,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    return await _response(await _get_pasarela_o_404(pasarela_id, tenant_id, db), db)


@router.post("/", response_model=PasarelaResponse, status_code=status.HTTP_201_CREATED)
async def crear(
    data: PasarelaCreate,
    request: Request,
    current_user: Annotated[Usuario, Depends(SuperAdminRequired)],
    db: DB,
):
    if data.proveedor not in REGISTRO:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Proveedor desconocido")
    _exigir_clave_maestra()
    if not await db.get(Condominio, data.condominio_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condominio no encontrado")

    p = PasarelaPago(
        condominio_id=data.condominio_id, proveedor=data.proveedor, nombre_visible=data.nombre_visible.strip(),
        ambiente=data.ambiente, comision_porcentaje=data.comision_porcentaje, comision_fija=data.comision_fija,
        orden=data.orden, activa=False,
    )
    db.add(p)
    await db.flush()  # la AAD del cifrado necesita el id
    _guardar(p, data.credenciales)

    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=p.condominio_id, accion="CREATE_PASARELA_PAGO",
        detalles={**_resumen(p), "campos_credenciales": sorted(data.credenciales)},
        ip_address=_ip(request),
    )
    await db.commit()
    await db.refresh(p)
    return await _response(p, db)


@router.patch("/{pasarela_id}", response_model=PasarelaResponse)
async def actualizar(
    pasarela_id: int,
    data: PasarelaUpdate,
    request: Request,
    current_user: Annotated[Usuario, Depends(SuperAdminRequired)],
    db: DB,
):
    p = await _get_pasarela_o_404(pasarela_id, None, db)
    cambios = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None and getattr(p, k) != v}
    if not cambios:
        return await _response(p, db)
    antes = _resumen(p)
    for campo, valor in cambios.items():
        setattr(p, campo, valor.strip() if isinstance(valor, str) and campo == "nombre_visible" else valor)
    if "ambiente" in cambios:
        # Otro ambiente = otra cuenta del proveedor: hay que volver a probar antes de usarla
        p.activa = False
        p.prueba_ok = None
        p.prueba_at = None
        p.prueba_mensaje = None

    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=p.condominio_id, accion="UPDATE_PASARELA_PAGO",
        detalles={"pasarela_id": p.id, "before": antes, "after": _resumen(p)},
        ip_address=_ip(request),
    )
    await db.commit()
    await db.refresh(p)
    return await _response(p, db)


@router.put("/{pasarela_id}/credenciales", response_model=PasarelaResponse)
async def reemplazar_credenciales(
    pasarela_id: int,
    data: CredencialesRequest,
    request: Request,
    current_user: Annotated[Usuario, Depends(SuperAdminRequired)],
    db: DB,
):
    p = await _get_pasarela_o_404(pasarela_id, None, db)
    estaba_activa = p.activa
    _guardar(p, data.credenciales)
    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=p.condominio_id, accion="UPDATE_CREDENCIALES_PASARELA",
        detalles={"pasarela_id": p.id, "campos": sorted(data.credenciales), "desactivada": estaba_activa},
        ip_address=_ip(request),
    )
    await db.commit()
    await db.refresh(p)
    return await _response(p, db)


@router.post("/{pasarela_id}/probar", response_model=PruebaResponse)
async def probar(
    pasarela_id: int,
    request: Request,
    current_user: Annotated[Usuario, Depends(SuperAdminRequired)],
    db: DB,
):
    """Prueba de conexión sin crear cobros. Sin bloqueos abiertos durante la llamada al proveedor."""
    p = await _get_pasarela_o_404(pasarela_id, None, db)
    proveedor = p.proveedor
    try:
        en = en_uso(p)
    except (cifrado.CredencialesIlegibles, cifrado.ClaveMaestraInvalida):
        ok, mensaje = False, "No se pudieron leer las credenciales guardadas: vuelve a cargarlas"
    else:
        await db.commit()  # cierra la transacción de lectura antes de salir a la red
        try:
            await adaptador(proveedor).probar(en)
            ok, mensaje = True, "Conexión correcta"
        except ErrorCredenciales:
            ok, mensaje = False, "Credenciales rechazadas por el proveedor"
        except ErrorProveedor as exc:
            log.warning("Prueba de pasarela %s: %s", pasarela_id, exc)
            ok, mensaje = False, "No se pudo comunicar con el proveedor; intenta de nuevo en unos minutos"

    p = await _get_pasarela_o_404(pasarela_id, None, db)
    p.prueba_at = ahora()
    p.prueba_ok = ok
    p.prueba_mensaje = mensaje
    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=p.condominio_id, accion="PROBAR_PASARELA_PAGO",
        detalles={"pasarela_id": p.id, "ok": ok, "mensaje": mensaje}, ip_address=_ip(request),
    )
    await db.commit()
    await db.refresh(p)
    return PruebaResponse(ok=ok, mensaje=mensaje, pasarela=await _response(p, db))


async def _cambiar_activa(
    pasarela_id: int, activa: bool, request: Request, current_user: Usuario, db: AsyncSession
) -> PasarelaResponse:
    p = await _get_pasarela_o_404(pasarela_id, None, db)
    if activa:
        if not p.credenciales_cifradas:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Carga las credenciales primero")
        if p.ambiente == "produccion" and not prueba_vigente(p):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Prueba la conexión antes de activar: no hay una prueba exitosa posterior al último cambio de credenciales",
            )
    if p.activa != activa:
        p.activa = activa
        await registrar_auditoria(
            db, usuario_id=current_user.id, condominio_id=p.condominio_id,
            accion="ACTIVAR_PASARELA_PAGO" if activa else "DESACTIVAR_PASARELA_PAGO",
            detalles={"pasarela_id": p.id, "ambiente": p.ambiente}, ip_address=_ip(request),
        )
        await db.commit()
        await db.refresh(p)
    return await _response(p, db)


@router.post("/{pasarela_id}/activar", response_model=PasarelaResponse)
async def activar(
    pasarela_id: int, request: Request, current_user: Annotated[Usuario, Depends(SuperAdminRequired)], db: DB,
):
    return await _cambiar_activa(pasarela_id, True, request, current_user, db)


@router.post("/{pasarela_id}/desactivar", response_model=PasarelaResponse)
async def desactivar(
    pasarela_id: int, request: Request, current_user: Annotated[Usuario, Depends(SuperAdminRequired)], db: DB,
):
    return await _cambiar_activa(pasarela_id, False, request, current_user, db)


@router.delete("/{pasarela_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar(
    pasarela_id: int, request: Request, current_user: Annotated[Usuario, Depends(SuperAdminRequired)], db: DB,
):
    p = await _get_pasarela_o_404(pasarela_id, None, db)
    if await _tiene_pagos(p.id, db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La pasarela tiene pagos registrados: desactívala en lugar de eliminarla",
        )
    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=p.condominio_id, accion="ELIMINAR_PASARELA_PAGO",
        detalles=_resumen(p), ip_address=_ip(request),
    )
    await db.delete(p)
    await db.commit()
