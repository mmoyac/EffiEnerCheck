from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import registrar_auditoria
from app.core.dependencies import AdminRequired, CurrentUser, SuperAdminRequired, get_db
from app.core.security import hash_password
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioDetailResponse, UsuarioResponse, UsuarioUpdate

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/", response_model=list[UsuarioDetailResponse])
async def list_usuarios(
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    db: DB,
):
    """Admin ve los usuarios de su condominio; super_admin los ve todos."""
    stmt = select(Usuario).options(selectinload(Usuario.rol), selectinload(Usuario.parcelas))
    if current_user.rol.nombre != "super_admin":
        stmt = stmt.where(Usuario.condominio_id == current_user.condominio_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    data: UsuarioCreate,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    db: DB,
):
    """
    Admin puede crear usuarios en su propio condominio.
    Super_admin puede crear usuarios en cualquier condominio.
    """
    if current_user.rol.nombre != "super_admin":
        if data.condominio_id and data.condominio_id != current_user.condominio_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puede crear usuarios en otro condominio")
        data = data.model_copy(update={"condominio_id": current_user.condominio_id})

    existe = await db.execute(select(Usuario).where(Usuario.email == data.email))
    if existe.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado")

    usuario = Usuario(
        nombre=data.nombre,
        email=data.email,
        password_hash=hash_password(data.password),
        rol_id=data.rol_id,
        condominio_id=data.condominio_id,
        telefono=data.telefono,
    )
    db.add(usuario)
    await db.flush()

    if data.parcela_ids:
        from sqlalchemy import insert
        from app.models.usuario_parcela import usuario_parcelas
        await db.execute(
            insert(usuario_parcelas),
            [{"usuario_id": usuario.id, "parcela_id": pid} for pid in data.parcela_ids],
        )
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=current_user.id,
        condominio_id=current_user.condominio_id,
        accion="CREATE_USER",
        detalles={"nuevo_usuario_id": usuario.id, "email": usuario.email},
    )
    await db.commit()
    result2 = await db.execute(
        select(Usuario).options(selectinload(Usuario.rol), selectinload(Usuario.parcelas)).where(Usuario.id == usuario.id)
    )
    return result2.scalar_one()


@router.patch("/{usuario_id}", response_model=UsuarioDetailResponse)
async def actualizar_usuario(
    usuario_id: int,
    data: UsuarioUpdate,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    db: DB,
):
    result = await db.execute(
        select(Usuario).options(selectinload(Usuario.rol), selectinload(Usuario.parcelas)).where(Usuario.id == usuario_id)
    )
    usuario = result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    if current_user.rol.nombre != "super_admin" and usuario.condominio_id != current_user.condominio_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a este usuario")

    cambios = data.model_dump(exclude_unset=True)
    parcela_ids = cambios.pop("parcela_ids", None)

    if "password" in cambios:
        cambios["password_hash"] = hash_password(cambios.pop("password"))

    estado_anterior = {k: getattr(usuario, k) for k in cambios if k != "password_hash"}
    for campo, valor in cambios.items():
        setattr(usuario, campo, valor)

    if parcela_ids is not None:
        from sqlalchemy import delete, insert
        from app.models.usuario_parcela import usuario_parcelas
        await db.execute(delete(usuario_parcelas).where(usuario_parcelas.c.usuario_id == usuario.id))
        if parcela_ids:
            await db.execute(
                insert(usuario_parcelas),
                [{"usuario_id": usuario.id, "parcela_id": pid} for pid in parcela_ids],
            )

    await registrar_auditoria(
        db,
        usuario_id=current_user.id,
        condominio_id=current_user.condominio_id,
        accion="UPDATE_USER",
        detalles={"before": estado_anterior, "after": data.model_dump(exclude_unset=True, exclude={"password"})},
    )
    await db.commit()
    result2 = await db.execute(
        select(Usuario).options(selectinload(Usuario.rol), selectinload(Usuario.parcelas)).where(Usuario.id == usuario.id)
    )
    return result2.scalar_one()


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_usuario(
    usuario_id: int,
    current_user: Annotated[Usuario, Depends(SuperAdminRequired)],
    db: DB,
):
    result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    await registrar_auditoria(
        db,
        usuario_id=current_user.id,
        condominio_id=usuario.condominio_id,
        accion="DELETE_USER",
        detalles={"email": usuario.email},
    )
    await db.delete(usuario)
    await db.commit()
