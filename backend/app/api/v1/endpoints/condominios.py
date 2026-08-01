from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AnyRoleRequired, CurrentUser, SuperAdminRequired, get_db
from app.models.condominio import Condominio
from app.models.usuario import Usuario
from app.schemas.condominio import CondominioCreate, CondominioResponse, CondominioUpdate

router = APIRouter(prefix="/condominios", tags=["condominios"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/", response_model=list[CondominioResponse])
async def list_condominios(
    current_user: Annotated[Usuario, Depends(AnyRoleRequired)],
    db: DB,
):
    """Super_admin ve todos; el resto solo ve su condominio."""
    stmt = select(Condominio)
    if current_user.rol.nombre != "super_admin":
        if current_user.condominio_id is None:
            return []
        stmt = stmt.where(Condominio.id == current_user.condominio_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=CondominioResponse, status_code=status.HTTP_201_CREATED)
async def crear_condominio(
    data: CondominioCreate,
    _: Annotated[Usuario, Depends(SuperAdminRequired)],
    db: DB,
):
    existe = await db.execute(select(Condominio).where(Condominio.rut_comunidad == data.rut_comunidad))
    if existe.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="RUT de comunidad ya registrado")

    condominio = Condominio(**data.model_dump())
    db.add(condominio)
    await db.commit()
    await db.refresh(condominio)
    return condominio


@router.get("/{condominio_id}", response_model=CondominioResponse)
async def get_condominio(
    condominio_id: int,
    current_user: Annotated[Usuario, Depends(AnyRoleRequired)],
    db: DB,
):
    if current_user.rol.nombre != "super_admin" and current_user.condominio_id != condominio_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a este condominio")

    result = await db.execute(select(Condominio).where(Condominio.id == condominio_id))
    condominio = result.scalar_one_or_none()
    if not condominio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condominio no encontrado")
    return condominio


@router.patch("/{condominio_id}", response_model=CondominioResponse)
async def actualizar_condominio(
    condominio_id: int,
    data: CondominioUpdate,
    _: Annotated[Usuario, Depends(SuperAdminRequired)],
    db: DB,
):
    result = await db.execute(select(Condominio).where(Condominio.id == condominio_id))
    condominio = result.scalar_one_or_none()
    if not condominio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condominio no encontrado")

    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(condominio, campo, valor)

    await db.commit()
    await db.refresh(condominio)
    return condominio


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
