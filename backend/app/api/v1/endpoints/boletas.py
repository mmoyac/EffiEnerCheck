from typing import Annotated, Union

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import registrar_auditoria
from app.core.dependencies import AdminRequired, AnyRoleRequired, LectorRequired, TenantId, get_db
from app.models.boleta import BoletaItemDetalle, BoletaMaestra
from app.models.usuario import Usuario
from app.schemas.boleta import (
    BoletaMaestraCreate,
    BoletaMaestraParceleroResponse,
    BoletaMaestraResponse,
    BoletaMaestraUpdate,
    BoletaMaestraDetallesUpdate,
)

router = APIRouter(prefix="/boletas", tags=["boletas"])

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/heic", "application/pdf"}
MIME_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/heic": "heic", "application/pdf": "pdf"}


@router.post("/ocr", tags=["boletas"])
async def ocr_boleta(
    _: Annotated[Usuario, Depends(AdminRequired)],
    file: UploadFile = File(...),
):
    """Extrae datos de una boleta con Gemini Vision y guarda la imagen en el servidor."""
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Tipo de archivo no soportado: {file.content_type}. Use JPG, PNG, WEBP, HEIC o PDF.",
        )

    import uuid, os
    from app.services.ocr import extraer_datos_boleta

    image_bytes = await file.read()

    # Guardar archivo
    ext = MIME_EXT[file.content_type]
    filename = f"{uuid.uuid4().hex}.{ext}"
    uploads_dir = "/app/uploads/boletas"
    os.makedirs(uploads_dir, exist_ok=True)
    filepath = os.path.join(uploads_dir, filename)
    with open(filepath, "wb") as f:
        f.write(image_bytes)

    # Extraer datos con Gemini
    try:
        data = await extraer_datos_boleta(image_bytes, file.content_type)
    except ValueError as exc:
        os.unlink(filepath)  # borrar si OCR falla
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    data["file_url"] = f"/uploads/boletas/{filename}"
    return data

DB = Annotated[AsyncSession, Depends(get_db)]


def _boleta_query():
    return select(BoletaMaestra).options(selectinload(BoletaMaestra.items_detalle))


async def _get_boleta_o_404(boleta_id: int, db: AsyncSession) -> BoletaMaestra:
    result = await db.execute(_boleta_query().where(BoletaMaestra.id == boleta_id))
    boleta = result.scalar_one_or_none()
    if not boleta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Boleta no encontrada")
    return boleta


def _validar_tenant(boleta: BoletaMaestra, tenant_id: int | None) -> None:
    if tenant_id is not None and boleta.condominio_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a esta boleta")


@router.get("/", response_model=list[BoletaMaestraResponse])
async def list_boletas(
    current_user: Annotated[Usuario, Depends(AnyRoleRequired)],
    tenant_id: TenantId,
    db: DB,
):
    stmt = _boleta_query()
    if tenant_id is not None:
        stmt = stmt.where(BoletaMaestra.condominio_id == tenant_id)
    if current_user.rol.nombre == "parcelero":
        stmt = stmt.where(BoletaMaestra.estado == "publicada")
    
    stmt = stmt.order_by(BoletaMaestra.periodo_mes.desc())
    
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=BoletaMaestraResponse, status_code=status.HTTP_201_CREATED)
async def crear_boleta(
    data: BoletaMaestraCreate,
    request: Request,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    effective_cid = tenant_id if tenant_id is not None else data.condominio_id
    if not effective_cid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="super_admin debe especificar condominio_id")

    # Validar que no exista una boleta sin cerrar en el mismo condominio
    resultado_abierta = await db.execute(
        select(BoletaMaestra)
        .where(BoletaMaestra.condominio_id == effective_cid)
        .where(BoletaMaestra.liquidaciones_cerradas == False)  # noqa: E712
        .order_by(BoletaMaestra.periodo_mes.desc())
        .limit(1)
    )
    boleta_abierta = resultado_abierta.scalar_one_or_none()
    if boleta_abierta:
        from app.utils.format import periodo_label
        label = periodo_label(boleta_abierta.periodo_mes)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El período {label} aún no está cerrado. Cierra las liquidaciones antes de cargar una nueva boleta.",
        )

    # Buscar última boleta para calcular mes siguiente
    from sqlalchemy.orm import selectinload
    resultado_ultima = await db.execute(
        select(BoletaMaestra)
        .options(selectinload(BoletaMaestra.items_detalle))
        .where(BoletaMaestra.condominio_id == effective_cid)
        .order_by(BoletaMaestra.periodo_mes.desc())
        .limit(1)
    )
    ultima = resultado_ultima.scalar_one_or_none()

    if data.periodo_mes:
        periodo = data.periodo_mes
    else:
        import datetime
        if ultima:
            y, m = ultima.periodo_mes.year, ultima.periodo_mes.month
            m += 1
            if m > 12:
                m = 1
                y += 1
            periodo = datetime.date(y, m, 1)
        else:
            hoy = datetime.date.today()
            periodo = datetime.date(hoy.year, hoy.month, 1)

    boleta = BoletaMaestra(
        condominio_id=effective_cid,
        periodo_mes=periodo,
        url_imagen_boleta=data.url_imagen_boleta,
        total_kwh_compania=data.total_kwh_compania,
        monto_neto_electricidad_consumida=data.monto_neto_electricidad_consumida,
        monto_total_emision=data.monto_total_emision,
        monto_saldo_anterior=data.monto_saldo_anterior,
        creado_por=current_user.id,
    )
    db.add(boleta)
    await db.flush()

    # Auto-generar lecturas
    from app.models.parcela import Parcela
    from app.models.lectura import LecturaParcela
    parcelas_result = await db.execute(select(Parcela).where(Parcela.condominio_id == effective_cid))
    parcelas = parcelas_result.scalars().all()
    
    for p in parcelas:
        ult_lectura_res = await db.execute(
            select(LecturaParcela)
            .join(BoletaMaestra, LecturaParcela.boleta_id == BoletaMaestra.id)
            .where(LecturaParcela.parcela_id == p.id)
            .where(BoletaMaestra.condominio_id == effective_cid)
            .order_by(BoletaMaestra.periodo_mes.desc())
            .limit(1)
        )
        ult_lectura = ult_lectura_res.scalar_one_or_none()
        lect_ant = ult_lectura.lectura_actual if ult_lectura else 0.0
        
        nueva_lectura = LecturaParcela(
            parcela_id=p.id,
            boleta_id=boleta.id,
            lectura_anterior=lect_ant,
            lectura_actual=0.0,
            kwh_consumidos=0.0,
            lector_id=current_user.id
        )
        db.add(nueva_lectura)

    if data.items_detalle:
        for item in data.items_detalle:
            db.add(BoletaItemDetalle(**item.model_dump(), boleta_id=boleta.id))
    elif ultima and ultima.items_detalle:
        for item in ultima.items_detalle:
            nuevo_item = BoletaItemDetalle(
                boleta_id=boleta.id,
                descripcion=item.descripcion,
                monto_neto_clp=0,
                tipo_calculo=item.tipo_calculo
            )
            db.add(nuevo_item)

    ip = request.client.host if request.client else None
    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=effective_cid,
        accion="UPLOAD_BOLETA",
        detalles={"boleta_id": boleta.id, "periodo_mes": str(periodo)},
        ip_address=ip,
    )
    await db.commit()
    return await _get_boleta_o_404(boleta.id, db)


@router.get("/{boleta_id}", response_model=Union[BoletaMaestraResponse, BoletaMaestraParceleroResponse])
async def get_boleta(
    boleta_id: int,
    current_user: Annotated[Usuario, Depends(AnyRoleRequired)],
    tenant_id: TenantId,
    db: DB,
):
    boleta = await _get_boleta_o_404(boleta_id, db)
    _validar_tenant(boleta, tenant_id)

    if current_user.rol.nombre == "parcelero":
        if boleta.estado != "publicada":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Boleta no disponible")
        return BoletaMaestraParceleroResponse(
            id=boleta.id,
            condominio_id=boleta.condominio_id,
            periodo_mes=boleta.periodo_mes,
            url_imagen_boleta=boleta.url_imagen_boleta if boleta.boleta_visible_usuarios else None,
            estado=boleta.estado,
        )
    return boleta


@router.patch("/{boleta_id}", response_model=BoletaMaestraResponse)
async def actualizar_boleta(
    boleta_id: int,
    data: BoletaMaestraUpdate,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    boleta = await _get_boleta_o_404(boleta_id, db)
    _validar_tenant(boleta, tenant_id)

    cambios_solicitados = data.model_dump(exclude_unset=True)
    solo_publicacion = set(cambios_solicitados.keys()) <= {"boleta_visible_usuarios"}
    if boleta.liquidaciones_cerradas and not solo_publicacion:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El período está cerrado y no permite modificaciones")

    cambios = cambios_solicitados
    # Al publicar, marcar estado como "publicada" automáticamente
    if cambios.get("boleta_visible_usuarios") is True:
        cambios["estado"] = "publicada"
    estado_anterior = {k: getattr(boleta, k) for k in cambios}
    for campo, valor in cambios.items():
        setattr(boleta, campo, valor)

    accion = "TOGGLE_VISIBILITY" if "boleta_visible_usuarios" in cambios else "UPDATE_BOLETA"
    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=boleta.condominio_id,
        accion=accion, detalles={"before": estado_anterior, "after": cambios},
    )
    await db.commit()
    return await _get_boleta_o_404(boleta.id, db)


@router.post("/{boleta_id}/imagen", response_model=BoletaMaestraResponse)
async def upload_imagen_boleta(
    boleta_id: int,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
    file: UploadFile = File(...),
):
    """Sube o reemplaza la imagen de la boleta. Permitido incluso en períodos cerrados."""
    boleta = await _get_boleta_o_404(boleta_id, db)
    _validar_tenant(boleta, tenant_id)

    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Tipo de archivo no soportado: {file.content_type}. Use JPG, PNG, WEBP, HEIC o PDF.",
        )

    import uuid, os
    image_bytes = await file.read()
    ext = MIME_EXT[file.content_type]
    filename = f"{uuid.uuid4().hex}.{ext}"
    uploads_dir = "/app/uploads/boletas"
    os.makedirs(uploads_dir, exist_ok=True)
    filepath = os.path.join(uploads_dir, filename)
    with open(filepath, "wb") as f:
        f.write(image_bytes)

    boleta.url_imagen_boleta = f"/uploads/boletas/{filename}"
    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=boleta.condominio_id,
        accion="UPLOAD_IMAGEN_BOLETA",
        detalles={"boleta_id": boleta_id, "filename": filename},
    )
    await db.commit()
    return await _get_boleta_o_404(boleta.id, db)


@router.post("/{boleta_id}/procesar-ocr", response_model=BoletaMaestraResponse)
async def procesar_ocr_boleta(
    boleta_id: int,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """Procesa la imagen subida de la boleta con Gemini y extrae los datos."""
    boleta = await _get_boleta_o_404(boleta_id, db)
    _validar_tenant(boleta, tenant_id)

    if not boleta.url_imagen_boleta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La boleta no tiene una imagen subida. Sube la imagen primero."
        )

    if boleta.liquidaciones_cerradas:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El período está cerrado. No se puede procesar."
        )

    import os
    filename = boleta.url_imagen_boleta.split("/")[-1]
    filepath = os.path.join("/app/uploads/boletas", filename)

    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el archivo físico de la imagen en el servidor."
        )

    with open(filepath, "rb") as f:
        image_bytes = f.read()

    ext = filename.split(".")[-1].lower()
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "heic": "image/heic", "pdf": "application/pdf"}
    mime_type = mime_map.get(ext, "image/jpeg")

    from app.services.ocr import extraer_datos_boleta
    try:
        data = await extraer_datos_boleta(image_bytes, mime_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    if data.get("total_kwh_compania") is not None:
        boleta.total_kwh_compania = float(data["total_kwh_compania"])
    if data.get("monto_neto_electricidad_consumida") is not None:
        boleta.monto_neto_electricidad_consumida = float(data["monto_neto_electricidad_consumida"])
    if data.get("monto_total_emision") is not None:
        boleta.monto_total_emision = int(data["monto_total_emision"])
    if data.get("monto_saldo_anterior") is not None:
        boleta.monto_saldo_anterior = int(data["monto_saldo_anterior"])

    from app.models.boleta import BoletaItemDetalle
    import re
    import unicodedata
    from difflib import SequenceMatcher

    resultado_items = await db.execute(select(BoletaItemDetalle).where(BoletaItemDetalle.boleta_id == boleta.id))
    items_existentes = resultado_items.scalars().all()
    
    def normalizar(texto: str) -> str:
        t = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').lower()
        t = re.sub(r'\b(de|del|la|el|los|las|por|en|y)\b', '', t)
        t = re.sub(r'[^a-z0-9]', '', t)
        return t

    mapa_existentes = {item.id: item for item in items_existentes}
    norm_existentes = {item.id: normalizar(item.descripcion) for item in items_existentes}
    
    items_data = data.get("items_detalle", [])
    for item_data in items_data:
        desc_ocr = item_data.get("descripcion", "")
        monto_sin_iva = item_data.get("monto_neto_clp", 0)
        monto_con_iva = round(monto_sin_iva * 1.19)
        
        norm_ocr = normalizar(desc_ocr)
        if not norm_ocr:
            continue
            
        mejor_match_id = None
        mejor_score = 0.0
        
        for item_id, norm_ext in norm_existentes.items():
            if norm_ocr == norm_ext:
                mejor_match_id = item_id
                mejor_score = 1.0
                break
            score = SequenceMatcher(None, norm_ocr, norm_ext).ratio()
            if score > mejor_score:
                mejor_score = score
                mejor_match_id = item_id
                
        if mejor_match_id and mejor_score > 0.6:
            mapa_existentes[mejor_match_id].monto_neto_clp = monto_con_iva

    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=boleta.condominio_id,
        accion="PROCESS_OCR", detalles={"boleta_id": boleta_id},
    )
    await db.commit()
    return await _get_boleta_o_404(boleta.id, db)


@router.put("/{boleta_id}/detalles", response_model=BoletaMaestraResponse)
async def actualizar_detalles_boleta(
    boleta_id: int,
    data: BoletaMaestraDetallesUpdate,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """Actualiza manualmente los totales y los ítems de la boleta."""
    boleta = await _get_boleta_o_404(boleta_id, db)
    _validar_tenant(boleta, tenant_id)

    if boleta.liquidaciones_cerradas:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El período está cerrado. No se puede modificar."
        )

    boleta.total_kwh_compania = data.total_kwh_compania
    boleta.monto_neto_electricidad_consumida = data.monto_neto_electricidad_consumida
    boleta.monto_total_emision = data.monto_total_emision
    boleta.monto_saldo_anterior = data.monto_saldo_anterior

    from sqlalchemy import delete
    from app.models.boleta import BoletaItemDetalle
    await db.execute(delete(BoletaItemDetalle).where(BoletaItemDetalle.boleta_id == boleta.id))
    
    for item in data.items_detalle:
        db.add(BoletaItemDetalle(**item.model_dump(), boleta_id=boleta.id))

    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=boleta.condominio_id,
        accion="UPDATE_DETALLES_BOLETA", detalles={"boleta_id": boleta_id},
    )
    await db.commit()
    return await _get_boleta_o_404(boleta.id, db)


# ---------------------------------------------------------------------------
# Candados de cierre de período
# ---------------------------------------------------------------------------

@router.post("/{boleta_id}/cerrar-lecturas", response_model=BoletaMaestraResponse)
async def cerrar_lecturas(
    boleta_id: int,
    current_user: Annotated[Usuario, Depends(LectorRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """Lector certifica que todas las lecturas están ingresadas. Habilita el Motor EnerCheck."""
    boleta = await _get_boleta_o_404(boleta_id, db)
    _validar_tenant(boleta, tenant_id)

    if boleta.lecturas_cerradas:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Las lecturas de este período ya están cerradas")

    from app.models.lectura import LecturaParcela
    lecturas_pendientes = await db.execute(
        select(LecturaParcela)
        .where(LecturaParcela.boleta_id == boleta_id)
        .where(LecturaParcela.fecha_toma.is_(None))
        .limit(1)
    )
    if lecturas_pendientes.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Faltan lecturas por ingresar. No se pueden cerrar las lecturas hasta que todas las parcelas tengan su lectura registrada."
        )

    boleta.lecturas_cerradas = True
    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=boleta.condominio_id,
        accion="CERRAR_LECTURAS", detalles={"boleta_id": boleta_id},
    )
    await db.commit()
    return await _get_boleta_o_404(boleta.id, db)


@router.post("/{boleta_id}/reabrir-lecturas", response_model=BoletaMaestraResponse)
async def reabrir_lecturas(
    boleta_id: int,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """Admin reabre las lecturas para permitir correcciones. Solo posible antes de cerrar el período."""
    boleta = await _get_boleta_o_404(boleta_id, db)
    _validar_tenant(boleta, tenant_id)

    if boleta.liquidaciones_cerradas:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El período ya está cerrado y no se puede reabrir")
    if not boleta.lecturas_cerradas:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Las lecturas ya están abiertas")

    boleta.lecturas_cerradas = False
    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=boleta.condominio_id,
        accion="REABRIR_LECTURAS", detalles={"boleta_id": boleta_id},
    )
    await db.commit()
    return await _get_boleta_o_404(boleta.id, db)


@router.post("/{boleta_id}/cerrar-liquidaciones", response_model=BoletaMaestraResponse)
async def cerrar_liquidaciones(
    boleta_id: int,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """Admin cierra el período. Las liquidaciones quedan bloqueadas para el parcelero y no se pueden modificar."""
    boleta = await _get_boleta_o_404(boleta_id, db)
    _validar_tenant(boleta, tenant_id)

    if not boleta.lecturas_cerradas:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Debes cerrar las lecturas antes de cerrar las liquidaciones")

    if boleta.liquidaciones_cerradas:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Las liquidaciones de este período ya están cerradas")

    from app.models.liquidacion import LiquidacionParcela
    liq_check = await db.execute(
        select(LiquidacionParcela).where(LiquidacionParcela.boleta_id == boleta_id).limit(1)
    )
    if not liq_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No hay liquidaciones calculadas. Usa 'Calcular liquidaciones' antes de cerrar el período.",
        )

    boleta.liquidaciones_cerradas = True
    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=boleta.condominio_id,
        accion="CERRAR_LIQUIDACIONES", detalles={"boleta_id": boleta_id},
    )
    await db.commit()
    return await _get_boleta_o_404(boleta.id, db)


@router.post("/{boleta_id}/reabrir-liquidaciones", response_model=BoletaMaestraResponse)
async def reabrir_liquidaciones(
    boleta_id: int,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """Admin reabre el período cerrado para corregir liquidaciones. Solo si aún no está publicado."""
    boleta = await _get_boleta_o_404(boleta_id, db)
    _validar_tenant(boleta, tenant_id)

    if not boleta.liquidaciones_cerradas:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El período no está cerrado")
    if boleta.boleta_visible_usuarios:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La boleta ya fue publicada a los parceleros y no se puede reabrir",
        )

    boleta.liquidaciones_cerradas = False
    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=boleta.condominio_id,
        accion="REABRIR_LIQUIDACIONES", detalles={"boleta_id": boleta_id},
    )
    await db.commit()
    return await _get_boleta_o_404(boleta.id, db)


@router.delete("/{boleta_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_boleta_borrador(
    boleta_id: int,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """Elimina una boleta y todo su contenido, solo si las lecturas no han sido cerradas."""
    boleta = await _get_boleta_o_404(boleta_id, db)
    _validar_tenant(boleta, tenant_id)

    if boleta.lecturas_cerradas:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar la boleta porque las lecturas ya están cerradas. Reabre las lecturas primero."
        )

    # Eliminar lecturas y liquidaciones asociadas
    from app.models.lectura import LecturaParcela
    from app.models.liquidacion import LiquidacionParcela
    from sqlalchemy import delete
    
    await db.execute(delete(LiquidacionParcela).where(LiquidacionParcela.boleta_id == boleta_id))
    await db.execute(delete(LecturaParcela).where(LecturaParcela.boleta_id == boleta_id))
    
    # BoletaItemDetalle se elimina en cascada por SQLAlchemy
    await db.delete(boleta)
    
    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=boleta.condominio_id,
        accion="DELETE_BOLETA", detalles={"boleta_id": boleta_id, "periodo_mes": str(boleta.periodo_mes)},
    )
    await db.commit()

