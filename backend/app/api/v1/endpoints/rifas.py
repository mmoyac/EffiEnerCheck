"""
Rifas solidarias: módulo aparte de la boleta eléctrica.

Lo recaudado NO participa de las liquidaciones ni del Motor EnerCheck: se paga en efectivo o por
transferencia, o se imputa al gasto común (que se cobra en Comunidad Feliz).
Ver openspec/changes/rifas-solidarias/design.md.
"""
import csv
import io
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import registrar_auditoria
from app.core.dependencies import (
    AdminRequired,
    PorteriaRequired,
    RifaAccesoRequired,
    TenantId,
    get_db,
)
from app.models.parcela import Parcela
from app.models.rifa import CompraRifa, ImputacionRifa, Rifa, RifaNumero
from app.models.usuario import Usuario
from app.models.usuario_parcela import usuario_parcelas
from app.schemas.rifa import (
    CajaFilaResponse,
    CajaResponse,
    CompraCreadaResponse,
    CompraRifaRequest,
    CompraRifaResponse,
    ImputacionRifaResponse,
    MarcarImputacionRequest,
    ParcelaVentaResponse,
    RifaCreate,
    RifaDetalleResponse,
    RifaResponse,
    RifaUpdate,
    TelefonoSugeridoResponse,
)

router = APIRouter(prefix="/rifas", tags=["rifas"])

DB = Annotated[AsyncSession, Depends(get_db)]

ADMIN_ROLES = ("super_admin", "admin_condominio")
STAFF_ROLES = (*ADMIN_ROLES, "porteria")

# Hora local para la caja y los CSV
ZONA_HORARIA = ZoneInfo("America/Santiago")

# Vouchers de transferencia: fuera de /app/uploads, que se sirve como estático público
VOUCHERS_DIR = "/app/privado/vouchers"
VOUCHER_MIME_EXT = {
    "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp",
    "image/heic": "heic", "application/pdf": "pdf",
}
VOUCHER_MAX_BYTES = 10 * 1024 * 1024


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _es_admin(user: Usuario) -> bool:
    return user.rol.nombre in ADMIN_ROLES


def _es_staff(user: Usuario) -> bool:
    """Administración o portería: ven todas las compras de la rifa."""
    return user.rol.nombre in STAFF_ROLES


def _orden_natural(numero_parcela: str) -> tuple[int, str]:
    """Mismo criterio que el listado de parcelas: parte numérica primero, luego el texto."""
    digitos = re.sub(r"[^0-9]", "", numero_parcela)
    return (int(digitos) if digitos else 0, numero_parcela)


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


async def _get_rifa_o_404(
    rifa_id: int, tenant_id: int | None, db: AsyncSession, *, for_update: bool = False
) -> Rifa:
    stmt = select(Rifa).where(Rifa.id == rifa_id)
    if for_update:
        # Serializa compras, anulaciones y cierre de una misma rifa (y el contador de folio)
        stmt = stmt.with_for_update()
    rifa = (await db.execute(stmt)).scalar_one_or_none()
    if not rifa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rifa no encontrada")
    if tenant_id is not None and rifa.condominio_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a esta rifa")
    return rifa


def _exigir_abierta(rifa: Rifa) -> None:
    if rifa.estado != "abierta":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La rifa está cerrada")


async def _numeros_vendidos(rifa_id: int, db: AsyncSession) -> list[int]:
    result = await db.execute(
        select(RifaNumero.numero).where(RifaNumero.rifa_id == rifa_id).order_by(RifaNumero.numero)
    )
    return list(result.scalars().all())


async def _estadisticas(rifa_ids: list[int], db: AsyncSession) -> dict[int, int]:
    """Cantidad de números vigentes por rifa."""
    if not rifa_ids:
        return {}
    result = await db.execute(
        select(RifaNumero.rifa_id, func.count())
        .where(RifaNumero.rifa_id.in_(rifa_ids))
        .group_by(RifaNumero.rifa_id)
    )
    return dict(result.all())


def _rifa_response(rifa: Rifa, vendidos: int) -> RifaResponse:
    return RifaResponse.model_validate(rifa).model_copy(
        update={"numeros_vendidos_total": vendidos, "recaudado": vendidos * rifa.precio_numero}
    )


def _es_autor_portal(compra: CompraRifa, user: Usuario) -> bool:
    return compra.canal == "portal" and compra.usuario_id == user.id


def _puede_anular(compra: CompraRifa, rifa: Rifa, user: Usuario) -> bool:
    if compra.anulada or rifa.estado != "abierta":
        return False
    if _es_admin(user):
        return True
    # La portería no anula (el efectivo no se "des-registra" sin la administración).
    # El vecino anula lo que compró él desde el portal, mientras no esté pagado.
    return _es_autor_portal(compra, user) and not compra.pagada


def _puede_adjuntar_voucher(compra: CompraRifa, user: Usuario) -> bool:
    if compra.anulada or compra.pagada or compra.medio_pago != "transferencia":
        return False
    return _es_staff(user) or _es_autor_portal(compra, user)


def _compra_response(compra: CompraRifa, rifa: Rifa, user: Usuario) -> CompraRifaResponse:
    return CompraRifaResponse(
        id=compra.id,
        rifa_id=compra.rifa_id,
        folio=compra.folio_texto,
        parcela_id=compra.parcela_id,
        parcela_numero=compra.parcela.numero_parcela,
        usuario_id=compra.usuario_id,
        usuario_nombre=compra.usuario.nombre,
        canal=compra.canal,
        comprador_nombre=compra.comprador_nombre,
        telefono=compra.telefono,
        numeros=sorted(compra.numeros),
        monto=compra.monto,
        medio_pago=compra.medio_pago,
        pagada=compra.pagada,
        pagada_at=compra.pagada_at,
        tiene_voucher=bool(compra.voucher_archivo),
        created_at=compra.created_at,
        anulada=compra.anulada,
        anulada_at=compra.anulada_at,
        anulada_por_nombre=compra.anulada_por.nombre if compra.anulada_por else None,
        puede_anular=_puede_anular(compra, rifa, user),
        puede_adjuntar_voucher=_puede_adjuntar_voucher(compra, user),
    )


def _imputacion_response(imp: ImputacionRifa) -> ImputacionRifaResponse:
    return ImputacionRifaResponse(
        id=imp.id,
        rifa_id=imp.rifa_id,
        parcela_id=imp.parcela_id,
        parcela_numero=imp.parcela.numero_parcela,
        cantidad_numeros=imp.cantidad_numeros,
        monto=imp.monto,
        cargada=imp.cargada,
        cargada_at=imp.cargada_at,
    )


def _compras_stmt(rifa_id: int):
    return (
        select(CompraRifa)
        .options(
            selectinload(CompraRifa.parcela),
            selectinload(CompraRifa.usuario),
            selectinload(CompraRifa.anulada_por),
        )
        .where(CompraRifa.rifa_id == rifa_id)
        .order_by(CompraRifa.created_at.desc())
    )


async def _get_compra_o_404(rifa: Rifa, compra_id: int, db: AsyncSession) -> CompraRifa:
    compra = (
        await db.execute(_compras_stmt(rifa.id).where(CompraRifa.id == compra_id))
    ).scalar_one_or_none()
    if not compra:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compra no encontrada")
    return compra


async def _detalle(rifa: Rifa, user: Usuario, db: AsyncSession) -> RifaDetalleResponse:
    mis_parcelas = [p.id for p in user.parcelas]
    ve_todo = _es_staff(user)

    vendidos = await _numeros_vendidos(rifa.id, db)

    mis_numeros: list[int] = []
    if mis_parcelas:
        result = await db.execute(
            select(RifaNumero.numero)
            .join(CompraRifa, RifaNumero.compra_id == CompraRifa.id)
            .where(RifaNumero.rifa_id == rifa.id, CompraRifa.parcela_id.in_(mis_parcelas))
            .order_by(RifaNumero.numero)
        )
        mis_numeros = list(result.scalars().all())

    compras_stmt = _compras_stmt(rifa.id)
    imp_stmt = (
        select(ImputacionRifa).options(selectinload(ImputacionRifa.parcela))
        .where(ImputacionRifa.rifa_id == rifa.id)
    )
    if not ve_todo:
        compras_stmt = compras_stmt.where(CompraRifa.parcela_id.in_(mis_parcelas))
        imp_stmt = imp_stmt.where(ImputacionRifa.parcela_id.in_(mis_parcelas))

    compras = (await db.execute(compras_stmt)).scalars().all()
    imputaciones = sorted(
        (await db.execute(imp_stmt)).scalars().all(),
        key=lambda i: _orden_natural(i.parcela.numero_parcela),
    )

    base = _rifa_response(rifa, len(vendidos))
    return RifaDetalleResponse(
        **base.model_dump(),
        numeros_vendidos=vendidos,
        mis_numeros=mis_numeros,
        compras=[_compra_response(c, rifa, user) for c in compras],
        imputaciones=[_imputacion_response(i) for i in imputaciones],
    )


async def _leer_voucher(voucher: UploadFile) -> tuple[bytes, str]:
    if voucher.content_type not in VOUCHER_MIME_EXT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Tipo de archivo no soportado: {voucher.content_type}. Use JPG, PNG, WEBP, HEIC o PDF.",
        )
    contenido = await voucher.read()
    if len(contenido) > VOUCHER_MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El voucher supera los 10 MB")
    if not contenido:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El voucher está vacío")
    return contenido, voucher.content_type


def _guardar_voucher(contenido: bytes, mime: str) -> str:
    os.makedirs(VOUCHERS_DIR, exist_ok=True)
    nombre = f"{uuid.uuid4().hex}.{VOUCHER_MIME_EXT[mime]}"
    with open(os.path.join(VOUCHERS_DIR, nombre), "wb") as f:
        f.write(contenido)
    return nombre


def _borrar_voucher(nombre: str | None) -> None:
    if nombre:
        try:
            os.remove(os.path.join(VOUCHERS_DIR, nombre))
        except FileNotFoundError:
            pass


def _parsear_folio(texto: str, rifa_id: int) -> int | None:
    """Acepta 'R4-012', '4-012', '012' o '12'."""
    m = re.fullmatch(r"\s*(?:R?(\d+)-)?(\d+)\s*", texto, flags=re.IGNORECASE)
    if not m or (m.group(1) and int(m.group(1)) != rifa_id):
        return None
    return int(m.group(2))


# ---------------------------------------------------------------------------
# Rifa
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[RifaResponse])
async def list_rifas(
    current_user: Annotated[Usuario, Depends(RifaAccesoRequired)],
    tenant_id: TenantId,
    db: DB,
    estado: str | None = None,
):
    stmt = select(Rifa).order_by(Rifa.created_at.desc())
    if tenant_id is not None:
        stmt = stmt.where(Rifa.condominio_id == tenant_id)
    if estado:
        stmt = stmt.where(Rifa.estado == estado)
    rifas = (await db.execute(stmt)).scalars().all()
    stats = await _estadisticas([r.id for r in rifas], db)
    return [_rifa_response(r, stats.get(r.id, 0)) for r in rifas]


@router.post("/", response_model=RifaResponse, status_code=status.HTTP_201_CREATED)
async def crear_rifa(
    data: RifaCreate,
    request: Request,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    condominio_id = tenant_id if tenant_id is not None else data.condominio_id
    if not condominio_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debe especificar condominio_id")

    rifa = Rifa(
        **data.model_dump(exclude={"condominio_id"}),
        condominio_id=condominio_id,
        estado="abierta",
        creado_por_id=current_user.id,
    )
    db.add(rifa)
    await db.flush()

    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=condominio_id, accion="CREATE_RIFA",
        detalles={"rifa_id": rifa.id, **data.model_dump(exclude={"condominio_id"})},
        ip_address=_ip(request),
    )
    await db.commit()
    await db.refresh(rifa)
    return _rifa_response(rifa, 0)


@router.get("/{rifa_id}", response_model=RifaDetalleResponse)
async def get_rifa(
    rifa_id: int,
    current_user: Annotated[Usuario, Depends(RifaAccesoRequired)],
    tenant_id: TenantId,
    db: DB,
):
    rifa = await _get_rifa_o_404(rifa_id, tenant_id, db)
    return await _detalle(rifa, current_user, db)


@router.patch("/{rifa_id}", response_model=RifaResponse)
async def actualizar_rifa(
    rifa_id: int,
    data: RifaUpdate,
    request: Request,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    rifa = await _get_rifa_o_404(rifa_id, tenant_id, db, for_update=True)
    _exigir_abierta(rifa)

    cambios = {k: v for k, v in data.model_dump(exclude_unset=True).items() if getattr(rifa, k) != v}
    vendidos = await _numeros_vendidos(rifa.id, db)

    if "precio_numero" in cambios and vendidos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El precio no puede cambiar porque ya hay números vendidos",
        )
    if "cantidad_numeros" in cambios and vendidos and cambios["cantidad_numeros"] < max(vendidos):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La cantidad no puede ser menor que {max(vendidos)}, el mayor número vendido",
        )

    estado_anterior = {k: getattr(rifa, k) for k in cambios}
    for campo, valor in cambios.items():
        setattr(rifa, campo, valor)

    if cambios:
        await registrar_auditoria(
            db, usuario_id=current_user.id, condominio_id=rifa.condominio_id, accion="UPDATE_RIFA",
            detalles={"rifa_id": rifa.id, "before": estado_anterior, "after": cambios},
            ip_address=_ip(request),
        )
    await db.commit()
    await db.refresh(rifa)
    return _rifa_response(rifa, len(vendidos))


# ---------------------------------------------------------------------------
# Apoyo a la venta en portería
# ---------------------------------------------------------------------------

@router.get("/{rifa_id}/parcelas", response_model=list[ParcelaVentaResponse])
async def parcelas_para_venta(
    rifa_id: int,
    current_user: Annotated[Usuario, Depends(PorteriaRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """La portería no accede a /parcelas: este listado le basta para buscar a nombre de quién vende."""
    rifa = await _get_rifa_o_404(rifa_id, tenant_id, db)
    parcelas = (
        await db.execute(
            select(Parcela).where(Parcela.condominio_id == rifa.condominio_id, Parcela.activa == True)  # noqa: E712
        )
    ).scalars().all()
    return [
        ParcelaVentaResponse(id=p.id, numero_parcela=p.numero_parcela, propietario_nombre=p.propietario_nombre)
        for p in sorted(parcelas, key=lambda p: _orden_natural(p.numero_parcela))
    ]


@router.get("/{rifa_id}/telefonos", response_model=list[TelefonoSugeridoResponse])
async def telefonos_de_parcela(
    rifa_id: int,
    parcela_id: int,
    current_user: Annotated[Usuario, Depends(PorteriaRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """Teléfonos registrados de los usuarios vinculados a la parcela, para proponerlos en la venta."""
    rifa = await _get_rifa_o_404(rifa_id, tenant_id, db)
    filas = (
        await db.execute(
            select(Usuario.telefono, Usuario.nombre)
            .join(usuario_parcelas, usuario_parcelas.c.usuario_id == Usuario.id)
            .join(Parcela, Parcela.id == usuario_parcelas.c.parcela_id)
            .where(
                usuario_parcelas.c.parcela_id == parcela_id,
                Parcela.condominio_id == rifa.condominio_id,
                Usuario.telefono.is_not(None),
            )
            .order_by(Usuario.nombre)
        )
    ).all()
    vistos: set[str] = set()
    sugeridos = []
    for telefono, nombre in filas:
        if telefono not in vistos:
            vistos.add(telefono)
            sugeridos.append(TelefonoSugeridoResponse(telefono=telefono, nombre=nombre))
    return sugeridos


@router.get("/{rifa_id}/caja", response_model=CajaResponse)
async def caja(
    rifa_id: int,
    current_user: Annotated[Usuario, Depends(PorteriaRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """Efectivo vigente recibido, por día (hora de Chile) y por cuenta que registró la venta."""
    rifa = await _get_rifa_o_404(rifa_id, tenant_id, db)
    dia = func.to_char(func.timezone("America/Santiago", CompraRifa.created_at), "YYYY-MM-DD")
    filas = (
        await db.execute(
            select(
                dia.label("fecha"), Usuario.id, Usuario.nombre,
                func.count(CompraRifa.id), func.sum(func.cardinality(CompraRifa.numeros)), func.sum(CompraRifa.monto),
            )
            .join(Usuario, CompraRifa.usuario_id == Usuario.id)
            .where(
                CompraRifa.rifa_id == rifa.id,
                CompraRifa.medio_pago == "efectivo",
                CompraRifa.anulada == False,  # noqa: E712
            )
            .group_by(dia, Usuario.id, Usuario.nombre)
            .order_by(dia.desc(), Usuario.nombre)
        )
    ).all()
    resultado = [
        CajaFilaResponse(fecha=f, usuario_id=uid, usuario_nombre=nom, ventas=v, numeros=n or 0, monto=m or 0)
        for f, uid, nom, v, n, m in filas
    ]
    return CajaResponse(
        filas=resultado,
        total_numeros=sum(f.numeros for f in resultado),
        total_monto=sum(f.monto for f in resultado),
    )


# ---------------------------------------------------------------------------
# Compras
# ---------------------------------------------------------------------------

@router.get("/{rifa_id}/compras", response_model=list[CompraRifaResponse])
async def buscar_compras(
    rifa_id: int,
    current_user: Annotated[Usuario, Depends(PorteriaRequired)],
    tenant_id: TenantId,
    db: DB,
    parcela_id: int | None = None,
    folio: str | None = None,
):
    """Búsqueda para responder consultas en portería: por parcela o por folio (R4-012)."""
    rifa = await _get_rifa_o_404(rifa_id, tenant_id, db)
    stmt = _compras_stmt(rifa.id)
    if parcela_id is not None:
        stmt = stmt.where(CompraRifa.parcela_id == parcela_id)
    if folio:
        n = _parsear_folio(folio, rifa.id)
        if n is None:
            return []
        stmt = stmt.where(CompraRifa.folio == n)
    compras = (await db.execute(stmt)).scalars().all()
    return [_compra_response(c, rifa, current_user) for c in compras]


@router.post("/{rifa_id}/compras", response_model=CompraCreadaResponse, status_code=status.HTTP_201_CREATED)
async def comprar_numeros(
    rifa_id: int,
    request: Request,
    current_user: Annotated[Usuario, Depends(RifaAccesoRequired)],
    tenant_id: TenantId,
    db: DB,
    datos: str = Form(..., description="JSON con parcela_id, numeros, medio_pago, comprador_nombre y telefono"),
    voucher: UploadFile | None = File(None),
):
    try:
        data = CompraRifaRequest.model_validate_json(datos)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[{k: err[k] for k in ("loc", "msg", "type")} for err in e.errors()],
        )

    voucher_datos = await _leer_voucher(voucher) if voucher is not None and voucher.filename else None

    rifa = await _get_rifa_o_404(rifa_id, tenant_id, db, for_update=True)
    _exigir_abierta(rifa)

    numeros = data.numeros
    if len(set(numeros)) != len(numeros):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Hay números repetidos")
    fuera = [n for n in numeros if n < 1 or n > rifa.cantidad_numeros]
    if fuera:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Números fuera de rango (1 a {rifa.cantidad_numeros}): {', '.join(map(str, fuera))}",
        )

    parcela = (await db.execute(select(Parcela).where(Parcela.id == data.parcela_id))).scalar_one_or_none()
    if not parcela or parcela.condominio_id != rifa.condominio_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a esta parcela")

    mis_parcelas = [p.id for p in current_user.parcelas]
    if current_user.rol.nombre == "porteria":
        canal = "porteria"
    elif _es_admin(current_user) and parcela.id not in mis_parcelas:
        canal = "administracion"
    else:
        # El vecino, o un admin comprando a nombre de su propia parcela
        canal = "portal"

    if canal == "portal":
        if parcela.id not in mis_parcelas:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Solo puedes comprar a nombre de tus parcelas"
            )
        if data.medio_pago == "efectivo":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El pago en efectivo se registra en la portería",
            )
    elif not parcela.activa:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La parcela no está activa")

    if data.medio_pago != "transferencia" and voucher_datos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El voucher solo corresponde a pagos por transferencia",
        )
    if canal == "porteria" and data.medio_pago == "transferencia" and not voucher_datos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Adjunta la foto del voucher de la transferencia",
        )

    vendidos = set(await _numeros_vendidos(rifa.id, db))
    tomados = sorted(n for n in numeros if n in vendidos)
    if tomados:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Números no disponibles: {', '.join(map(str, tomados))}",
        )

    voucher_archivo = _guardar_voucher(*voucher_datos) if voucher_datos else None
    try:
        rifa.ultimo_folio += 1
        pagada = data.medio_pago == "efectivo"
        compra = CompraRifa(
            rifa_id=rifa.id,
            folio=rifa.ultimo_folio,
            parcela_id=parcela.id,
            usuario_id=current_user.id,
            canal=canal,
            comprador_nombre=data.comprador_nombre,
            telefono=data.telefono,
            numeros=sorted(numeros),
            monto=len(numeros) * rifa.precio_numero,
            medio_pago=data.medio_pago,
            pagada=pagada,
            pagada_at=_ahora() if pagada else None,
            pago_confirmado_por_id=current_user.id if pagada else None,
            voucher_archivo=voucher_archivo,
            voucher_mime=voucher_datos[1] if voucher_datos else None,
            numeros_vigentes=[RifaNumero(rifa_id=rifa.id, numero=n) for n in numeros],
        )
        db.add(compra)
        await db.flush()

        await registrar_auditoria(
            db, usuario_id=current_user.id, condominio_id=rifa.condominio_id, accion="COMPRAR_RIFA",
            detalles={
                "rifa_id": rifa.id, "compra_id": compra.id, "folio": compra.folio_texto,
                "parcela_id": parcela.id, "numeros": sorted(numeros), "monto": compra.monto,
                "medio_pago": data.medio_pago, "canal": canal, "comprador_nombre": data.comprador_nombre,
                "voucher": voucher_archivo,
            },
            ip_address=_ip(request),
        )
        await db.commit()
    except IntegrityError:
        # Respaldo ante una carrera que el bloqueo de la rifa no haya cubierto
        await db.rollback()
        _borrar_voucher(voucher_archivo)
        vendidos = set(await _numeros_vendidos(rifa_id, db))
        tomados = sorted(n for n in numeros if n in vendidos)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Números no disponibles: {', '.join(map(str, tomados))}",
        )
    except Exception:
        await db.rollback()
        _borrar_voucher(voucher_archivo)
        raise

    compra = await _get_compra_o_404(rifa, compra.id, db)
    return CompraCreadaResponse(
        rifa=await _detalle(rifa, current_user, db),
        compra=_compra_response(compra, rifa, current_user),
    )


@router.post("/{rifa_id}/compras/{compra_id}/anular", response_model=RifaDetalleResponse)
async def anular_compra(
    rifa_id: int,
    compra_id: int,
    request: Request,
    current_user: Annotated[Usuario, Depends(RifaAccesoRequired)],
    tenant_id: TenantId,
    db: DB,
):
    rifa = await _get_rifa_o_404(rifa_id, tenant_id, db, for_update=True)
    compra = await _get_compra_o_404(rifa, compra_id, db)

    _exigir_abierta(rifa)
    if compra.anulada:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La compra ya está anulada")
    if not _puede_anular(compra, rifa, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo la administración, o quien compró desde el portal si aún no está pagada, puede anularla",
        )

    await db.execute(delete(RifaNumero).where(RifaNumero.compra_id == compra.id))
    compra.anulada = True
    compra.anulada_at = _ahora()
    compra.anulada_por = current_user

    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=rifa.condominio_id, accion="ANULAR_COMPRA_RIFA",
        detalles={
            "rifa_id": rifa.id, "compra_id": compra.id, "folio": compra.folio_texto,
            "parcela_id": compra.parcela_id, "numeros": compra.numeros, "monto": compra.monto,
            "medio_pago": compra.medio_pago, "pagada": compra.pagada, "canal": compra.canal,
        },
        ip_address=_ip(request),
    )
    await db.commit()
    return await _detalle(rifa, current_user, db)


@router.post("/{rifa_id}/compras/{compra_id}/confirmar-pago", response_model=CompraRifaResponse)
async def confirmar_pago(
    rifa_id: int,
    compra_id: int,
    request: Request,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """Confirma una transferencia. Funciona también con la rifa cerrada."""
    rifa = await _get_rifa_o_404(rifa_id, tenant_id, db)
    compra = await _get_compra_o_404(rifa, compra_id, db)
    if compra.medio_pago != "transferencia":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo se confirman pagos por transferencia")
    if compra.anulada:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La compra está anulada")
    if compra.pagada:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El pago ya está confirmado")

    compra.pagada = True
    compra.pagada_at = _ahora()
    compra.pago_confirmado_por_id = current_user.id

    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=rifa.condominio_id, accion="CONFIRMAR_PAGO_RIFA",
        detalles={
            "rifa_id": rifa.id, "compra_id": compra.id, "folio": compra.folio_texto,
            "parcela_id": compra.parcela_id, "monto": compra.monto, "tenia_voucher": bool(compra.voucher_archivo),
        },
        ip_address=_ip(request),
    )
    await db.commit()
    return _compra_response(compra, rifa, current_user)


@router.post("/{rifa_id}/compras/{compra_id}/voucher", response_model=CompraRifaResponse)
async def adjuntar_voucher(
    rifa_id: int,
    compra_id: int,
    request: Request,
    current_user: Annotated[Usuario, Depends(RifaAccesoRequired)],
    tenant_id: TenantId,
    db: DB,
    voucher: UploadFile = File(...),
):
    rifa = await _get_rifa_o_404(rifa_id, tenant_id, db)
    compra = await _get_compra_o_404(rifa, compra_id, db)
    if not _puede_adjuntar_voucher(compra, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo se adjunta a transferencias no confirmadas, por quien compró o por la portería",
        )
    contenido, mime = await _leer_voucher(voucher)
    anterior = compra.voucher_archivo
    nuevo = _guardar_voucher(contenido, mime)
    try:
        compra.voucher_archivo = nuevo
        compra.voucher_mime = mime
        await registrar_auditoria(
            db, usuario_id=current_user.id, condominio_id=rifa.condominio_id, accion="UPDATE_RIFA",
            detalles={"rifa_id": rifa.id, "compra_id": compra.id, "before": {"voucher": anterior}, "after": {"voucher": nuevo}},
            ip_address=_ip(request),
        )
        await db.commit()
    except Exception:
        await db.rollback()
        _borrar_voucher(nuevo)
        raise
    _borrar_voucher(anterior)
    return _compra_response(compra, rifa, current_user)


@router.get("/{rifa_id}/compras/{compra_id}/voucher")
async def ver_voucher(
    rifa_id: int,
    compra_id: int,
    current_user: Annotated[Usuario, Depends(RifaAccesoRequired)],
    tenant_id: TenantId,
    db: DB,
):
    rifa = await _get_rifa_o_404(rifa_id, tenant_id, db)
    compra = await _get_compra_o_404(rifa, compra_id, db)
    if not _es_staff(current_user) and compra.parcela_id not in [p.id for p in current_user.parcelas]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a este voucher")
    ruta = os.path.join(VOUCHERS_DIR, compra.voucher_archivo or "")
    if not compra.voucher_archivo or not os.path.isfile(ruta):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La compra no tiene voucher")
    return FileResponse(
        ruta,
        media_type=compra.voucher_mime,
        filename=f"voucher-{compra.folio_texto}.{VOUCHER_MIME_EXT.get(compra.voucher_mime, 'bin')}",
        content_disposition_type="inline",
        headers={"Cache-Control": "private, no-store"},
    )


# ---------------------------------------------------------------------------
# Cierre, reapertura e imputaciones al gasto común
# ---------------------------------------------------------------------------

@router.post("/{rifa_id}/cerrar", response_model=RifaDetalleResponse)
async def cerrar_rifa(
    rifa_id: int,
    request: Request,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    rifa = await _get_rifa_o_404(rifa_id, tenant_id, db, for_update=True)
    _exigir_abierta(rifa)

    # Solo lo comprado con gasto común se imputa; efectivo y transferencia se pagan por fuera
    por_parcela = (
        await db.execute(
            select(CompraRifa.parcela_id, func.count(RifaNumero.id))
            .join(RifaNumero, RifaNumero.compra_id == CompraRifa.id)
            .where(CompraRifa.rifa_id == rifa.id, CompraRifa.medio_pago == "gasto_comun")
            .group_by(CompraRifa.parcela_id)
        )
    ).all()

    for parcela_id, cantidad in por_parcela:
        db.add(ImputacionRifa(
            rifa_id=rifa.id, parcela_id=parcela_id, cantidad_numeros=cantidad,
            monto=cantidad * rifa.precio_numero, cargada=False,
        ))
    rifa.estado = "cerrada"
    rifa.cerrada_at = _ahora()

    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=rifa.condominio_id, accion="CERRAR_RIFA",
        detalles={
            "rifa_id": rifa.id,
            "imputaciones": [
                {"parcela_id": p, "cantidad": c, "monto": c * rifa.precio_numero} for p, c in por_parcela
            ],
            "total_imputado": sum(c for _, c in por_parcela) * rifa.precio_numero,
        },
        ip_address=_ip(request),
    )
    await db.commit()
    return await _detalle(rifa, current_user, db)


@router.post("/{rifa_id}/reabrir", response_model=RifaDetalleResponse)
async def reabrir_rifa(
    rifa_id: int,
    request: Request,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    rifa = await _get_rifa_o_404(rifa_id, tenant_id, db, for_update=True)
    if rifa.estado != "cerrada":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La rifa ya está abierta")

    cargadas = (
        await db.execute(
            select(func.count()).select_from(ImputacionRifa)
            .where(ImputacionRifa.rifa_id == rifa.id, ImputacionRifa.cargada == True)  # noqa: E712
        )
    ).scalar_one()
    if cargadas:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede reabrir: ya hay imputaciones cargadas en el gasto común. Desmárcalas primero.",
        )

    await db.execute(delete(ImputacionRifa).where(ImputacionRifa.rifa_id == rifa.id))
    rifa.estado = "abierta"
    rifa.cerrada_at = None

    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=rifa.condominio_id, accion="REABRIR_RIFA",
        detalles={"rifa_id": rifa.id}, ip_address=_ip(request),
    )
    await db.commit()
    return await _detalle(rifa, current_user, db)


@router.patch("/{rifa_id}/imputaciones/{imputacion_id}", response_model=ImputacionRifaResponse)
async def marcar_imputacion(
    rifa_id: int,
    imputacion_id: int,
    data: MarcarImputacionRequest,
    request: Request,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    rifa = await _get_rifa_o_404(rifa_id, tenant_id, db)
    imp = (
        await db.execute(
            select(ImputacionRifa).options(selectinload(ImputacionRifa.parcela))
            .where(ImputacionRifa.id == imputacion_id, ImputacionRifa.rifa_id == rifa.id)
        )
    ).scalar_one_or_none()
    if not imp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imputación no encontrada")

    imp.cargada = data.cargada
    imp.cargada_at = _ahora() if data.cargada else None

    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=rifa.condominio_id, accion="MARCAR_IMPUTACION_RIFA",
        detalles={
            "rifa_id": rifa.id, "imputacion_id": imp.id, "parcela_id": imp.parcela_id,
            "monto": imp.monto, "cargada": data.cargada,
        },
        ip_address=_ip(request),
    )
    await db.commit()
    await db.refresh(imp)
    return _imputacion_response(imp)


# ---------------------------------------------------------------------------
# Exportaciones (CSV en UTF-8 con BOM y ';' para Excel en es-CL)
# ---------------------------------------------------------------------------

def _csv(encabezado: list[str], filas: list[list], nombre: str) -> Response:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(encabezado)
    writer.writerows(filas)
    # BOM para que Excel reconozca UTF-8 y muestre bien las tildes
    return Response(
        content="﻿" + buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


_MEDIO_PAGO_TEXTO = {"efectivo": "Efectivo", "transferencia": "Transferencia", "gasto_comun": "Gasto común"}
_CANAL_TEXTO = {"portal": "Portal", "porteria": "Portería", "administracion": "Administración"}


@router.get("/{rifa_id}/imputaciones.csv")
async def exportar_imputaciones(
    rifa_id: int,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """Cargos a imputar en el gasto común (Comunidad Feliz), uno por parcela."""
    rifa = await _get_rifa_o_404(rifa_id, tenant_id, db)
    if rifa.estado != "cerrada":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Las imputaciones se generan al cerrar la rifa"
        )
    imps = (
        await db.execute(
            select(ImputacionRifa).options(selectinload(ImputacionRifa.parcela))
            .where(ImputacionRifa.rifa_id == rifa.id)
        )
    ).scalars().all()
    imps = sorted(imps, key=lambda i: _orden_natural(i.parcela.numero_parcela))
    return _csv(
        ["Unidad", "Propietario", "Cantidad de números", "Monto", "Concepto"],
        [
            [i.parcela.numero_parcela, i.parcela.propietario_nombre or "", i.cantidad_numeros, i.monto,
             f"Rifa {rifa.nombre}"]
            for i in imps
        ],
        f"rifa-{rifa.id}-imputaciones.csv",
    )


@router.get("/{rifa_id}/export.csv")
async def exportar_csv(
    rifa_id: int,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """Lista para el sorteo: un número vigente por fila. El sorteo se hace fuera del sistema."""
    rifa = await _get_rifa_o_404(rifa_id, tenant_id, db)
    filas = (
        await db.execute(
            select(RifaNumero.numero, CompraRifa, Parcela.numero_parcela, Parcela.propietario_nombre, Usuario.nombre)
            .join(CompraRifa, RifaNumero.compra_id == CompraRifa.id)
            .join(Parcela, CompraRifa.parcela_id == Parcela.id)
            .join(Usuario, CompraRifa.usuario_id == Usuario.id)
            .where(RifaNumero.rifa_id == rifa.id)
            .order_by(RifaNumero.numero)
        )
    ).all()
    return _csv(
        ["Número", "Folio", "Parcela", "Propietario", "Comprador", "Registrada por", "Canal",
         "Forma de pago", "Pagada", "Teléfono", "Fecha de compra"],
        [
            [
                numero, compra.folio_texto, parcela, propietario or "",
                compra.comprador_nombre or (registrador if compra.canal == "portal" else ""),
                registrador, _CANAL_TEXTO[compra.canal], _MEDIO_PAGO_TEXTO[compra.medio_pago],
                "Sí" if compra.pagada else "No", compra.telefono or "",
                compra.created_at.astimezone(ZONA_HORARIA).strftime("%d-%m-%Y %H:%M"),
            ]
            for numero, compra, parcela, propietario, registrador in filas
        ],
        f"rifa-{rifa.id}-numeros.csv",
    )
