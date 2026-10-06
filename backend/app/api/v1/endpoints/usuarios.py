import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import registrar_auditoria
from app.core.dependencies import AdminRequired, CurrentUser, SuperAdminRequired, get_db, modulos_del_condominio
from app.models.usuario import Usuario
from app.services import correo, enlaces
from app.services.claves import asignar_clave
from app.schemas.usuario import UsuarioCreate, UsuarioDetailResponse, UsuarioResponse, UsuarioUpdate

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

DB = Annotated[AsyncSession, Depends(get_db)]
PAUSA_ENTRE_CORREOS = 0.6   # segundos


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
        rol_id=data.rol_id,
        condominio_id=data.condominio_id,
        telefono=data.telefono,
    )
    if data.password is not None:   # sin clave: cuenta pendiente, se invita después
        asignar_clave(usuario, data.password)
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

    nueva_clave = cambios.pop("password", None)
    if nueva_clave is not None:
        asignar_clave(usuario, nueva_clave)   # cierra las sesiones abiertas del usuario

    estado_anterior = {k: getattr(usuario, k) for k in cambios}
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


# ---- Invitaciones (spec acceso-por-enlace) -------------------------------------------------------------

class InvitacionResponse(BaseModel):
    """El enlace vuelve al administrador para que pueda reenviarlo por WhatsApp."""
    enlace: str
    correo_enviado: bool
    motivo: str | None = None


class InvitacionesMasivasRequest(BaseModel):
    condominio_id: int | None = None   # obligatorio para super_admin


class InvitacionesMasivasResponse(BaseModel):
    enviados: int
    fallidos: int
    pendientes: int = 0                 # sin intentar: se detuvo al alcanzar el límite del servicio de correo
    limite_alcanzado: bool = False


async def _exigir_portal_contratado(db: AsyncSession, condominio_id: int | None) -> None:
    if condominio_id is not None and "portal" not in await modulos_del_condominio(db, condominio_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="El condominio no tiene contratado el portal de administración")


@router.post("/{usuario_id}/invitacion", response_model=InvitacionResponse)
async def invitar_usuario(
    usuario_id: int,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    db: DB,
):
    """Emite una invitación (anula la anterior) y la envía por correo. Solo a cuentas pendientes."""
    usuario = await db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if current_user.rol.nombre != "super_admin" and usuario.condominio_id != current_user.condominio_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a este usuario")
    if usuario.password_hash is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="La cuenta ya está activa: el usuario puede usar «¿Olvidaste tu clave?»")
    await _exigir_portal_contratado(db, usuario.condominio_id)

    url, mensaje = await enlaces.preparar_correo(db, usuario, "invitacion")
    resultado = await correo.enviar(**mensaje)
    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=usuario.condominio_id, accion="INVITACION_ENVIADA",
        detalles={"invitado_id": usuario.id, "email": usuario.email, "correo_enviado": resultado.ok},
    )
    await db.commit()
    return InvitacionResponse(enlace=url, correo_enviado=resultado.ok, motivo=resultado.motivo)


@router.post("/invitaciones", response_model=InvitacionesMasivasResponse)
async def invitar_pendientes(
    data: InvitacionesMasivasRequest,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    db: DB,
):
    """Invita por correo a todas las cuentas pendientes de un condominio. Sin correo configurado: 503."""
    if current_user.rol.nombre == "super_admin":
        if data.condominio_id is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Indica el condominio")
        condominio_id = data.condominio_id
    else:
        condominio_id = current_user.condominio_id
    if not correo.configurado():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="El envío de correos no está configurado")
    await _exigir_portal_contratado(db, condominio_id)

    pendientes = (await db.execute(
        select(Usuario).where(Usuario.condominio_id == condominio_id, Usuario.password_hash.is_(None))
        .order_by(Usuario.id)
    )).scalars().all()
    enviados = fallidos = 0
    for i, usuario in enumerate(pendientes):
        if i:
            await asyncio.sleep(PAUSA_ENTRE_CORREOS)   # límite de envíos por segundo de Resend
        _, mensaje = await enlaces.preparar_correo(db, usuario, "invitacion")
        resultado = await correo.enviar(**mensaje)
        enviados += resultado.ok
        fallidos += not resultado.ok
        await registrar_auditoria(
            db, usuario_id=current_user.id, condominio_id=condominio_id, accion="INVITACION_ENVIADA",
            detalles={"invitado_id": usuario.id, "email": usuario.email, "correo_enviado": resultado.ok,
                      "masiva": True},
        )
        await db.commit()
        if resultado.limite_alcanzado:   # el resto queda pendiente para otro día; sin enlaces emitidos de más
            return InvitacionesMasivasResponse(enviados=enviados, fallidos=fallidos,
                                               pendientes=len(pendientes) - i - 1, limite_alcanzado=True)
    return InvitacionesMasivasResponse(enviados=enviados, fallidos=fallidos)
