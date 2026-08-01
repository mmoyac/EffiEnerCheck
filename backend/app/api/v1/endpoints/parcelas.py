from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import registrar_auditoria
from app.core.dependencies import AdminRequired, AnyRoleRequired, CurrentUser, TenantId, get_db
from app.models.parcela import Parcela
from app.models.usuario import Usuario
from app.schemas.parcela import ParcelaCreate, ParcelaResponse, ParcelaUpdate

router = APIRouter(prefix="/parcelas", tags=["parcelas"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/", response_model=list[ParcelaResponse])
async def list_parcelas(
    current_user: Annotated[Usuario, Depends(AnyRoleRequired)],
    tenant_id: TenantId,
    db: DB,
):
    stmt = select(Parcela)
    if tenant_id is not None:
        stmt = stmt.where(Parcela.condominio_id == tenant_id)
    if current_user.rol.nombre == "parcelero":
        ids = [p.id for p in current_user.parcelas]
        stmt = stmt.where(Parcela.id.in_(ids))
    numeric_key = cast(
        func.coalesce(func.nullif(func.regexp_replace(Parcela.numero_parcela, '[^0-9]', '', 'g'), ''), '0'),
        Integer,
    )
    stmt = stmt.order_by(numeric_key, Parcela.numero_parcela)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=ParcelaResponse, status_code=status.HTTP_201_CREATED)
async def crear_parcela(
    data: ParcelaCreate,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    effective_cid = tenant_id if tenant_id is not None else data.condominio_id
    if not effective_cid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debe especificar condominio_id")

    parcela = Parcela(**{**data.model_dump(), "condominio_id": effective_cid})
    db.add(parcela)
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=current_user.id,
        condominio_id=effective_cid,
        accion="CREATE_PARCELA",
        detalles={"parcela_id": parcela.id, "numero": parcela.numero_parcela},
    )
    await db.commit()
    await db.refresh(parcela)
    return parcela


@router.get("/{parcela_id}", response_model=ParcelaResponse)
async def get_parcela(
    parcela_id: int,
    current_user: Annotated[Usuario, Depends(AnyRoleRequired)],
    tenant_id: TenantId,
    db: DB,
):
    result = await db.execute(select(Parcela).where(Parcela.id == parcela_id))
    parcela = result.scalar_one_or_none()
    if not parcela:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcela no encontrada")

    if tenant_id is not None and parcela.condominio_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a esta parcela")

    if current_user.rol.nombre == "parcelero" and parcela_id not in [p.id for p in current_user.parcelas]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a esta parcela")

    return parcela


@router.patch("/{parcela_id}", response_model=ParcelaResponse)
async def actualizar_parcela(
    parcela_id: int,
    data: ParcelaUpdate,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    result = await db.execute(select(Parcela).where(Parcela.id == parcela_id))
    parcela = result.scalar_one_or_none()
    if not parcela:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcela no encontrada")

    if tenant_id is not None and parcela.condominio_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a esta parcela")

    cambios = data.model_dump(exclude_unset=True)
    estado_anterior = {k: getattr(parcela, k) for k in cambios}
    for campo, valor in cambios.items():
        setattr(parcela, campo, valor)

    await registrar_auditoria(
        db,
        usuario_id=current_user.id,
        condominio_id=parcela.condominio_id,
        accion="UPDATE_PARCELA",
        detalles={"before": estado_anterior, "after": cambios},
    )
    await db.commit()
    await db.refresh(parcela)
    return parcela
