import os
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import registrar_auditoria
from app.core.dependencies import AnyRoleRequired, SuperAdminRequired, get_db
from app.models.condominio import Condominio
from app.models.condominio_modulo import CondominioDominio, CondominioModulo
from app.models.usuario import Usuario
from app.schemas.condominio import (
    MODULOS_POR_DEFECTO,
    CondominioCreate,
    CondominioResponse,
    CondominioUpdate,
)

router = APIRouter(prefix="/condominios", tags=["condominios"])

DB = Annotated[AsyncSession, Depends(get_db)]

# El logo es público: vive en el estático /uploads (nunca en /app/privado)
UPLOADS_DIR = "/app/uploads"
LOGO_MAX_BYTES = 1024 * 1024


def _con_parametrizacion(stmt):
    return stmt.options(selectinload(Condominio.modulos), selectinload(Condominio.dominios_sitio))


async def _get_condominio_o_404(condominio_id: int, db: AsyncSession) -> Condominio:
    result = await db.execute(_con_parametrizacion(select(Condominio)).where(Condominio.id == condominio_id))
    condominio = result.scalar_one_or_none()
    if not condominio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condominio no encontrado")
    return condominio


def _condominio_response(c: Condominio) -> CondominioResponse:
    return CondominioResponse(
        id=c.id,
        nombre=c.nombre,
        rut_comunidad=c.rut_comunidad,
        direccion=c.direccion,
        plan_suscripcion=c.plan_suscripcion,
        activo=c.activo,
        created_at=c.created_at,
        modulos=c.modulos_habilitados,
        portal_url=c.portal_url,
        dominios_sitio=sorted(d.dominio for d in c.dominios_sitio),
        logo_url=c.logo_url,
        color_primario=c.color_primario,
    )


def _parametrizacion(c: Condominio) -> dict[str, Any]:
    """Foto de los campos comerciales, para la auditoría antes/después."""
    return {
        "modulos": c.modulos_habilitados,
        "portal_url": c.portal_url,
        "dominios_sitio": sorted(d.dominio for d in c.dominios_sitio),
        "color_primario": c.color_primario,
    }


async def _validar_dominios_libres(dominios: list[str], condominio_id: int | None, db: AsyncSession) -> None:
    if not dominios:
        return
    stmt = select(CondominioDominio.dominio).where(CondominioDominio.dominio.in_(dominios))
    if condominio_id is not None:
        stmt = stmt.where(CondominioDominio.condominio_id != condominio_id)
    if (await db.execute(stmt)).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El dominio ya está asignado a otro condominio")


def _sincronizar_modulos(c: Condominio, modulos: list[str]) -> None:
    # Por diferencia (no reemplazando la lista): evita insertar y borrar la misma PK en un flush
    for m in [m for m in c.modulos if m.modulo not in modulos]:
        c.modulos.remove(m)
    actuales = {m.modulo for m in c.modulos}
    c.modulos.extend(CondominioModulo(modulo=m) for m in modulos if m not in actuales)


def _sincronizar_dominios(c: Condominio, dominios: list[str]) -> None:
    for d in [d for d in c.dominios_sitio if d.dominio not in dominios]:
        c.dominios_sitio.remove(d)
    actuales = {d.dominio for d in c.dominios_sitio}
    c.dominios_sitio.extend(CondominioDominio(dominio=d) for d in dominios if d not in actuales)


@router.get("/", response_model=list[CondominioResponse])
async def list_condominios(
    current_user: Annotated[Usuario, Depends(AnyRoleRequired)],
    db: DB,
):
    """Super_admin ve todos; el resto solo ve su condominio."""
    stmt = _con_parametrizacion(select(Condominio)).order_by(Condominio.id)
    if current_user.rol.nombre != "super_admin":
        if current_user.condominio_id is None:
            return []
        stmt = stmt.where(Condominio.id == current_user.condominio_id)
    result = await db.execute(stmt)
    return [_condominio_response(c) for c in result.scalars().all()]


@router.post("/", response_model=CondominioResponse, status_code=status.HTTP_201_CREATED)
async def crear_condominio(
    data: CondominioCreate,
    current_user: Annotated[Usuario, Depends(SuperAdminRequired)],
    db: DB,
):
    existe = await db.execute(select(Condominio).where(Condominio.rut_comunidad == data.rut_comunidad))
    if existe.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="RUT de comunidad ya registrado")
    await _validar_dominios_libres(data.dominios_sitio, None, db)

    condominio = Condominio(
        **data.model_dump(exclude={"modulos", "dominios_sitio"}),
        modulos=[CondominioModulo(modulo=m) for m in (data.modulos if data.modulos is not None else MODULOS_POR_DEFECTO)],
        dominios_sitio=[CondominioDominio(dominio=d) for d in data.dominios_sitio],
    )
    db.add(condominio)
    await db.flush()
    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=condominio.id, accion="CREATE_CONDOMINIO",
        detalles={"nombre": condominio.nombre, **_parametrizacion(condominio)},
    )
    await db.commit()
    return _condominio_response(await _get_condominio_o_404(condominio.id, db))


@router.get("/{condominio_id}", response_model=CondominioResponse)
async def get_condominio(
    condominio_id: int,
    current_user: Annotated[Usuario, Depends(AnyRoleRequired)],
    db: DB,
):
    if current_user.rol.nombre != "super_admin" and current_user.condominio_id != condominio_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a este condominio")
    return _condominio_response(await _get_condominio_o_404(condominio_id, db))


@router.patch("/{condominio_id}", response_model=CondominioResponse)
async def actualizar_condominio(
    condominio_id: int,
    data: CondominioUpdate,
    current_user: Annotated[Usuario, Depends(SuperAdminRequired)],
    db: DB,
):
    condominio = await _get_condominio_o_404(condominio_id, db)
    antes = _parametrizacion(condominio)
    cambios = data.model_dump(exclude_unset=True)

    if cambios.get("modulos") is not None:
        _sincronizar_modulos(condominio, cambios.pop("modulos"))
    cambios.pop("modulos", None)
    if cambios.get("dominios_sitio") is not None:
        dominios = cambios.pop("dominios_sitio")
        await _validar_dominios_libres(dominios, condominio.id, db)
        _sincronizar_dominios(condominio, dominios)
    cambios.pop("dominios_sitio", None)
    for campo, valor in cambios.items():
        setattr(condominio, campo, valor)

    despues = _parametrizacion(condominio)
    if antes != despues:
        await registrar_auditoria(
            db, usuario_id=current_user.id, condominio_id=condominio.id, accion="UPDATE_CONDOMINIO",
            detalles={
                "antes": {k: v for k, v in antes.items() if despues[k] != v},
                "despues": {k: v for k, v in despues.items() if antes[k] != v},
            },
        )
    await db.commit()
    return _condominio_response(await _get_condominio_o_404(condominio_id, db))


# ---------------------------------------------------------------------------
# Logo (spec gestion-condominios: PNG, JPEG o WEBP de hasta 1 MB; nunca SVG)
# ---------------------------------------------------------------------------

def _tipo_imagen(contenido: bytes) -> str | None:
    """Extensión según los bytes iniciales, no según el nombre ni el content-type declarados."""
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if contenido.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "webp"
    return None


def _borrar_logo(url: str | None) -> None:
    if url and url.startswith("/uploads/condominios/"):
        ruta = os.path.join(UPLOADS_DIR, url.removeprefix("/uploads/"))
        if os.path.isfile(ruta):
            os.remove(ruta)


@router.post("/{condominio_id}/logo", response_model=CondominioResponse)
async def subir_logo(
    condominio_id: int,
    current_user: Annotated[Usuario, Depends(SuperAdminRequired)],
    db: DB,
    archivo: UploadFile = File(...),
):
    """Sube o reemplaza el logo. Cada reemplazo genera una URL nueva y borra el archivo anterior."""
    condominio = await _get_condominio_o_404(condominio_id, db)
    contenido = await archivo.read(LOGO_MAX_BYTES + 1)
    if len(contenido) > LOGO_MAX_BYTES:
        raise HTTPException(status_code=413, detail="El logo no puede superar 1 MB")
    ext = _tipo_imagen(contenido)
    if ext is None:
        raise HTTPException(status_code=422, detail="El logo debe ser PNG, JPEG o WEBP")

    carpeta = os.path.join(UPLOADS_DIR, "condominios", str(condominio.id))
    os.makedirs(carpeta, exist_ok=True)
    nombre = f"logo-{uuid.uuid4().hex[:8]}.{ext}"
    with open(os.path.join(carpeta, nombre), "wb") as f:
        f.write(contenido)

    anterior = condominio.logo_url
    condominio.logo_url = f"/uploads/condominios/{condominio.id}/{nombre}"
    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=condominio.id, accion="UPDATE_CONDOMINIO_LOGO",
        detalles={"antes": anterior, "despues": condominio.logo_url},
    )
    try:
        await db.commit()
    except Exception:
        _borrar_logo(f"/uploads/condominios/{condominio.id}/{nombre}")
        raise
    _borrar_logo(anterior)  # recién después de confirmar
    return _condominio_response(condominio)


@router.delete("/{condominio_id}/logo", response_model=CondominioResponse)
async def quitar_logo(
    condominio_id: int,
    current_user: Annotated[Usuario, Depends(SuperAdminRequired)],
    db: DB,
):
    condominio = await _get_condominio_o_404(condominio_id, db)
    anterior = condominio.logo_url
    if anterior:
        condominio.logo_url = None
        await registrar_auditoria(
            db, usuario_id=current_user.id, condominio_id=condominio.id, accion="UPDATE_CONDOMINIO_LOGO",
            detalles={"antes": anterior, "despues": None},
        )
        await db.commit()
        _borrar_logo(anterior)
    return _condominio_response(condominio)


@router.delete("/{condominio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def desactivar_condominio(
    condominio_id: int,
    _: Annotated[Usuario, Depends(SuperAdminRequired)],
    db: DB,
):
    """Soft-delete: marca activo=False en lugar de eliminar."""
    result = await db.execute(select(Condominio).where(Condominio.id == condominio_id))
    condominio = result.scalar_one_or_none()
    if not condominio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condominio no encontrado")

    condominio.activo = False
    await db.commit()
