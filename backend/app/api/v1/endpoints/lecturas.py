import os
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import registrar_auditoria
from app.core.dependencies import AnyRoleRequired, LectorRequired, TenantId, get_db
from app.models.boleta import BoletaMaestra
from app.models.lectura import LecturaParcela
from app.models.parcela import Parcela
from app.models.usuario import Usuario
from app.schemas.lectura import (
    LecturaParcelaCreate, LecturaParcelaResponse, LecturaParcelaUpdate,
    ResultadoSincronizacion, SincronizarLecturasRequest, SincronizarLecturasResponse,
)
from app.services import fotos_lectura
from app.services.periodos import descartar_liquidaciones, es_lectura_inicial

router = APIRouter(prefix="/lecturas", tags=["lecturas"])

DB = Annotated[AsyncSession, Depends(get_db)]


async def _parcelas_con_historial(boleta: BoletaMaestra, db: AsyncSession) -> set[int]:
    """Parcelas con alguna lectura en un período anterior del mismo condominio."""
    filas = await db.execute(
        select(LecturaParcela.parcela_id)
        .join(BoletaMaestra, LecturaParcela.boleta_id == BoletaMaestra.id)
        .where(BoletaMaestra.condominio_id == boleta.condominio_id, BoletaMaestra.periodo_mes < boleta.periodo_mes)
        .distinct()
    )
    return set(filas.scalars().all())


async def _verificar_boleta_abierta(boleta_id: int, db: AsyncSession) -> BoletaMaestra:
    """Lanza 409 si las lecturas del período ya fueron cerradas."""
    result = await db.execute(select(BoletaMaestra).where(BoletaMaestra.id == boleta_id))
    boleta = result.scalar_one_or_none()
    if not boleta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Boleta no encontrada")
    if boleta.lecturas_cerradas:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Las lecturas de este período están cerradas y no se pueden modificar",
        )
    return boleta


@router.get("/", response_model=list[LecturaParcelaResponse])
async def list_lecturas(
    current_user: Annotated[Usuario, Depends(AnyRoleRequired)],
    tenant_id: TenantId,
    boleta_id: int | None = None,
    db: DB = None,
):
    stmt = select(LecturaParcela).join(Parcela, LecturaParcela.parcela_id == Parcela.id)
    if tenant_id is not None:
        stmt = stmt.where(Parcela.condominio_id == tenant_id)
    if boleta_id:
        stmt = stmt.where(LecturaParcela.boleta_id == boleta_id)
    if current_user.rol.nombre == "comunero":
        ids = [p.id for p in current_user.parcelas]
        stmt = stmt.where(LecturaParcela.parcela_id.in_(ids))

    lecturas = (await db.execute(stmt)).scalars().all()
    respuesta = [LecturaParcelaResponse.model_validate(l) for l in lecturas]
    # Por período: la lectura anterior solo es editable en parcelas sin historial (cambio lectura-inicial)
    boleta = await db.get(BoletaMaestra, boleta_id) if boleta_id else None
    if boleta and not es_lectura_inicial(boleta):
        con_historial = await _parcelas_con_historial(boleta, db)
        for r in respuesta:
            r.lectura_anterior_editable = r.parcela_id not in con_historial
    return respuesta


@router.post("/", response_model=LecturaParcelaResponse, status_code=status.HTTP_201_CREATED)
async def crear_lectura(
    data: LecturaParcelaCreate,
    current_user: Annotated[Usuario, Depends(LectorRequired)],
    tenant_id: TenantId,
    db: DB,
):
    await _verificar_boleta_abierta(data.boleta_id, db)

    parcela_result = await db.execute(select(Parcela).where(Parcela.id == data.parcela_id))
    parcela = parcela_result.scalar_one_or_none()
    if not parcela:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcela no encontrada")
    if tenant_id is not None and parcela.condominio_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Parcela no pertenece a su condominio")

    lectura = LecturaParcela(
        parcela_id=data.parcela_id,
        boleta_id=data.boleta_id,
        lectura_anterior=data.lectura_anterior,
        lectura_actual=data.lectura_actual,
        kwh_consumidos=data.kwh_consumidos,
        lector_id=current_user.id,
        fecha_toma=data.fecha_toma,
    )
    db.add(lectura)
    await db.flush()

    descartadas = await descartar_liquidaciones(db, data.boleta_id)
    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=parcela.condominio_id,
        accion="CREATE_LECTURA",
        detalles={"lectura_id": lectura.id, "parcela_id": data.parcela_id, "kwh_consumidos": lectura.kwh_consumidos,
                  "liquidaciones_descartadas": descartadas},
    )
    await db.commit()
    await db.refresh(lectura)
    return lectura


@router.patch("/{lectura_id}", response_model=LecturaParcelaResponse)
async def actualizar_lectura(
    lectura_id: int,
    data: LecturaParcelaUpdate,
    current_user: Annotated[Usuario, Depends(LectorRequired)],
    tenant_id: TenantId,
    db: DB,
):
    result = await db.execute(
        select(LecturaParcela).join(Parcela, LecturaParcela.parcela_id == Parcela.id)
        .where(LecturaParcela.id == lectura_id)
    )
    lectura = result.scalar_one_or_none()
    if not lectura:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lectura no encontrada")

    await _verificar_boleta_abierta(lectura.boleta_id, db)

    parcela_result = await db.execute(select(Parcela).where(Parcela.id == lectura.parcela_id))
    parcela = parcela_result.scalar_one_or_none()
    if tenant_id is not None and parcela.condominio_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a esta lectura")

    cambios = data.model_dump(exclude_unset=True)
    # La lectura anterior viene del período anterior: solo se ingresa en parcelas sin historial
    if "lectura_anterior" in cambios and cambios["lectura_anterior"] != lectura.lectura_anterior:
        boleta = await db.get(BoletaMaestra, lectura.boleta_id)
        if es_lectura_inicial(boleta):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="En la lectura inicial no hay lectura anterior")
        if lectura.parcela_id in await _parcelas_con_historial(boleta, db):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="La lectura anterior viene del período anterior y no se modifica aquí")

    nueva_actual = cambios.get("lectura_actual", lectura.lectura_actual)
    nueva_anterior = cambios.get("lectura_anterior", lectura.lectura_anterior)
    if nueva_actual < nueva_anterior:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La lectura actual ({nueva_actual}) no puede ser menor que la anterior ({nueva_anterior})",
        )

    estado_anterior = {k: getattr(lectura, k) for k in cambios}
    estado_anterior["lector_id"] = lectura.lector_id

    for campo, valor in cambios.items():
        setattr(lectura, campo, valor)
    if "lectura_anterior" in cambios or "lectura_actual" in cambios:
        lectura.kwh_consumidos = lectura.lectura_actual - lectura.lectura_anterior

    lectura.lector_id = current_user.id
    cambios["lector_id"] = current_user.id

    audit_before = {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in estado_anterior.items()}
    audit_after = {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in cambios.items()}

    descartadas = await descartar_liquidaciones(db, lectura.boleta_id)
    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=parcela.condominio_id,
        accion="UPDATE_LECTURA",
        detalles={"before": audit_before, "after": audit_after, "liquidaciones_descartadas": descartadas},
    )
    await db.commit()
    await db.refresh(lectura)
    return lectura


# ---- Sincronización de lecturas tomadas sin conexión (cambio lecturas-sin-conexion) ----------------------

def _mismo_instante(a: datetime | None, b: datetime | None) -> bool:
    """Igualdad al milisegundo: el navegador guarda la hora con milisegundos y la base con microsegundos."""
    if a is None or b is None:
        return a is b
    return abs((a - b).total_seconds()) < 0.001


def _mismo_valor(a: float, b: float) -> bool:
    return abs(a - b) < 1e-9


@router.post("/sincronizar", response_model=SincronizarLecturasResponse)
async def sincronizar_lecturas(
    data: SincronizarLecturasRequest,
    current_user: Annotated[Usuario, Depends(LectorRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """
    Aplica un lote de lecturas tomadas sin conexión. Cada una se resuelve por separado (savepoint propio):
    - aplicada: coincidía con la base descargada (o ya estaba aplicada: reintento idempotente);
    - conflicto: alguien la cambió en el servidor después de la descarga; no se pisa;
    - rechazada: período cerrado, contador regresivo u otro condominio.
    """
    resultados: list[ResultadoSincronizacion] = []
    periodos_modificados: set[int] = set()
    for item in data.items:
        lectura = (await db.execute(
            select(LecturaParcela).where(LecturaParcela.id == item.lectura_id)
        )).scalar_one_or_none()
        if lectura is None:
            resultados.append(ResultadoSincronizacion(lectura_id=item.lectura_id, estado="rechazada",
                                                      motivo="La lectura no existe"))
            continue
        parcela = await db.get(Parcela, lectura.parcela_id)
        if tenant_id is not None and parcela.condominio_id != tenant_id:
            resultados.append(ResultadoSincronizacion(lectura_id=item.lectura_id, estado="rechazada",
                                                      motivo="La lectura no pertenece a su condominio"))
            continue
        vigente = LecturaParcelaResponse.model_validate(lectura)

        # Reintento: ya está exactamente lo que se envía
        if _mismo_valor(lectura.lectura_actual, item.lectura_actual) and _mismo_instante(lectura.fecha_toma, item.fecha_toma):
            resultados.append(ResultadoSincronizacion(lectura_id=lectura.id, estado="aplicada", lectura=vigente))
            continue

        boleta = await db.get(BoletaMaestra, lectura.boleta_id)
        if boleta.lecturas_cerradas:
            resultados.append(ResultadoSincronizacion(lectura_id=lectura.id, estado="rechazada", lectura=vigente,
                                                      motivo="Las lecturas del período ya están cerradas"))
            continue
        if not (_mismo_valor(lectura.lectura_actual, item.base.lectura_actual)
                and _mismo_instante(lectura.fecha_toma, item.base.fecha_toma)):
            resultados.append(ResultadoSincronizacion(
                lectura_id=lectura.id, estado="conflicto", lectura=vigente,
                motivo="La lectura cambió en el servidor después de preparar el recorrido"))
            continue
        if item.lectura_actual < lectura.lectura_anterior:
            resultados.append(ResultadoSincronizacion(
                lectura_id=lectura.id, estado="rechazada", lectura=vigente,
                motivo=f"La lectura actual ({item.lectura_actual:g}) no puede ser menor que la anterior "
                       f"({lectura.lectura_anterior:g})"))
            continue

        async with db.begin_nested():
            antes = {"lectura_actual": lectura.lectura_actual,
                     "fecha_toma": lectura.fecha_toma.isoformat() if lectura.fecha_toma else None,
                     "lector_id": lectura.lector_id}
            lectura.lectura_actual = item.lectura_actual
            lectura.fecha_toma = item.fecha_toma
            lectura.kwh_consumidos = lectura.lectura_actual - lectura.lectura_anterior
            lectura.lector_id = current_user.id
            await registrar_auditoria(
                db, usuario_id=current_user.id, condominio_id=parcela.condominio_id, accion="UPDATE_LECTURA",
                detalles={"before": antes, "origen": "sin_conexion",
                          "after": {"lectura_actual": item.lectura_actual, "fecha_toma": item.fecha_toma.isoformat(),
                                    "lector_id": current_user.id}},
            )
        await db.flush()
        periodos_modificados.add(lectura.boleta_id)
        resultados.append(ResultadoSincronizacion(lectura_id=lectura.id, estado="aplicada",
                                                  lectura=LecturaParcelaResponse.model_validate(lectura)))
    # Lecturas nuevas: las liquidaciones calculadas antes quedan desactualizadas
    for boleta_id in periodos_modificados:
        await descartar_liquidaciones(db, boleta_id)
    await db.commit()
    return SincronizarLecturasResponse(resultados=resultados)


# ---- Foto del medidor (cambio foto-medidor) ---------------------------------------------------------------

@router.put("/{lectura_id}/foto", response_model=LecturaParcelaResponse)
async def subir_foto(
    lectura_id: int,
    current_user: Annotated[Usuario, Depends(LectorRequired)],
    tenant_id: TenantId,
    db: DB,
    foto: UploadFile = File(...),
    fecha_toma: datetime = Form(...),
):
    """
    Sube (o reemplaza) la foto del medidor de una lectura. La foto queda amarrada a la toma que documenta:
    solo se acepta si `fecha_toma` es la vigente de la lectura. Reenviar la misma foto no cambia nada.
    """
    lectura = await db.get(LecturaParcela, lectura_id)
    if not lectura:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lectura no encontrada")
    parcela = await db.get(Parcela, lectura.parcela_id)
    if tenant_id is not None and parcela.condominio_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a esta lectura")

    contenido = await foto.read(fotos_lectura.FOTO_MAX_BYTES + 1)
    if len(contenido) > fotos_lectura.FOTO_MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La foto supera los 3 MB")
    extension = fotos_lectura.tipo_por_bytes(contenido)
    if extension is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="La foto debe ser una imagen JPEG o WEBP")
    sha = fotos_lectura.sha256(contenido)

    # Reintento: esta misma foto ya está guardada para esta misma toma
    if lectura.foto_sha256 == sha and _mismo_instante(lectura.foto_fecha_toma, fecha_toma):
        return lectura

    boleta = await db.get(BoletaMaestra, lectura.boleta_id)
    if boleta.lecturas_cerradas:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Las lecturas del período ya están cerradas")
    if not _mismo_instante(lectura.fecha_toma, fecha_toma):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="La foto es de una toma que ya no está vigente en el servidor")

    anterior = lectura.foto_archivo
    nuevo = fotos_lectura.guardar(contenido, extension)
    try:
        lectura.foto_archivo = nuevo
        lectura.foto_sha256 = sha
        lectura.foto_fecha_toma = lectura.fecha_toma
        lectura.foto_subida_en = datetime.now(timezone.utc)
        await registrar_auditoria(
            db, usuario_id=current_user.id, condominio_id=parcela.condominio_id, accion="SUBIR_FOTO_LECTURA",
            detalles={"lectura_id": lectura.id, "parcela_id": lectura.parcela_id, "sha256": sha,
                      "bytes": len(contenido), "reemplaza": anterior is not None},
        )
        await db.commit()
    except Exception:
        await db.rollback()
        fotos_lectura.borrar(nuevo)
        raise
    fotos_lectura.borrar(anterior)
    await db.refresh(lectura)
    return lectura


@router.get("/{lectura_id}/foto")
async def ver_foto(
    lectura_id: int,
    current_user: Annotated[Usuario, Depends(AnyRoleRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """
    Entrega la foto del medidor. Staff y lector: las de su condominio. Comunero: solo las de sus parcelas y
    con el período publicado. Portería queda fuera por la guarda. Cualquier denegación responde 404.
    """
    no_encontrada = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La lectura no tiene foto")
    lectura = await db.get(LecturaParcela, lectura_id)
    if not lectura or not lectura.foto_archivo:
        raise no_encontrada
    parcela = await db.get(Parcela, lectura.parcela_id)
    if tenant_id is not None and parcela.condominio_id != tenant_id:
        raise no_encontrada
    if current_user.rol.nombre == "comunero":
        boleta = await db.get(BoletaMaestra, lectura.boleta_id)
        if lectura.parcela_id not in [p.id for p in current_user.parcelas] or not boleta.boleta_visible_usuarios:
            raise no_encontrada
    ruta = fotos_lectura.ruta(lectura.foto_archivo)
    if not os.path.isfile(ruta):
        raise no_encontrada
    return FileResponse(
        ruta,
        media_type="image/webp" if lectura.foto_archivo.endswith(".webp") else "image/jpeg",
        content_disposition_type="inline",
        headers={"Cache-Control": "private, no-store"},
    )
