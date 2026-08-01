from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import registrar_auditoria
from app.core.dependencies import AnyRoleRequired, LectorRequired, TenantId, get_db
from app.models.boleta import BoletaMaestra
from app.models.lectura import LecturaParcela
from app.models.parcela import Parcela
from app.models.usuario import Usuario
from app.schemas.lectura import LecturaParcelaCreate, LecturaParcelaResponse, LecturaParcelaUpdate

router = APIRouter(prefix="/lecturas", tags=["lecturas"])

DB = Annotated[AsyncSession, Depends(get_db)]


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
    if current_user.rol.nombre == "parcelero":
        ids = [p.id for p in current_user.parcelas]
        stmt = stmt.where(LecturaParcela.parcela_id.in_(ids))

    result = await db.execute(stmt)
    return result.scalars().all()


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

    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=parcela.condominio_id,
        accion="CREATE_LECTURA",
        detalles={"lectura_id": lectura.id, "parcela_id": data.parcela_id, "kwh_consumidos": lectura.kwh_consumidos},
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

    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=parcela.condominio_id,
        accion="UPDATE_LECTURA", detalles={"before": audit_before, "after": audit_after},
    )
    await db.commit()
    await db.refresh(lectura)
    return lectura
