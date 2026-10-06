from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import CurrentUser, exigir_portal, get_db, modulos_del_usuario
from app.core.audit import registrar_auditoria
from app.core.security import create_access_token, verify_password
from app.models.condominio import Condominio
from app.models.usuario import Usuario
from app.schemas.auth import (
    CambiarClaveRequest, EnlaceInfo, EnlaceRequest, EstablecerClaveRequest, RecuperarRequest, TokenResponse,
)
from app.services import correo, enlaces
from app.services.claves import asignar_clave
from app.schemas.usuario import CondominioMarca, SesionResponse, UsuarioDetailResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Login con email (campo username) y contraseña. Retorna JWT Bearer."""
    result = await db.execute(
        select(Usuario)
        .options(selectinload(Usuario.rol))
        .where(Usuario.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Credenciales válidas, pero el condominio no contrató el portal: 403, sin token
    exigir_portal(user, await modulos_del_usuario(db, user))

    user.ultimo_login = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token(
        user_id=user.id,
        rol=user.rol.nombre,
        condominio_id=user.condominio_id,
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=SesionResponse)
async def get_me(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Perfil del usuario autenticado, módulos habilitados de su condominio y marca del condominio."""
    condominio = None
    if current_user.condominio_id is not None:
        condominio = await db.get(Condominio, current_user.condominio_id)
    # Sin model_validate(current_user) directo: leería la relación lazy `condominio` (MissingGreenlet)
    return SesionResponse(
        **UsuarioDetailResponse.model_validate(current_user).model_dump(exclude={"estado"}),
        password_hash=current_user.password_hash,   # para el estado; no sale en la respuesta
        modulos=list(current_user.modulos),
        condominio=CondominioMarca.model_validate(condominio) if condominio else None,
    )


# ---- Enlaces de acceso y gestión de la propia clave (spec acceso-por-enlace) ----------------------------

ENLACE_INVALIDO = "El enlace ya fue usado o venció"
RECUPERAR_RESPUESTA = {"detail": "Si el correo está registrado, te enviamos un enlace para crear una clave nueva"}


def _token_de(user: Usuario) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(
        user_id=user.id, rol=user.rol.nombre, condominio_id=user.condominio_id))


@router.post("/recuperar", status_code=status.HTTP_202_ACCEPTED)
async def recuperar_clave(
    data: RecuperarRequest,
    tareas: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Siempre la misma respuesta 202: no revela si el correo tiene cuenta. El correo sale en segundo plano."""
    user = (await db.execute(
        select(Usuario).options(selectinload(Usuario.rol)).where(func.lower(Usuario.email) == data.email.lower())
    )).scalar_one_or_none()
    if user is not None:
        modulos = await modulos_del_usuario(db, user)
        sin_portal = user.rol.nombre != "super_admin" and user.condominio_id is not None and "portal" not in modulos
        if not sin_portal:
            _, mensaje = await enlaces.preparar_correo(db, user, "recuperacion")
            await registrar_auditoria(db, usuario_id=user.id, condominio_id=user.condominio_id,
                                      accion="RECUPERACION_SOLICITADA", detalles={})
            await db.commit()
            tareas.add_task(correo.enviar, **mensaje)
    return RECUPERAR_RESPUESTA


@router.post("/verificar-enlace", response_model=EnlaceInfo)
async def verificar_enlace(data: EnlaceRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    enlace = await enlaces.vigente(db, data.token)
    if enlace is None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=ENLACE_INVALIDO)
    usuario = await db.get(Usuario, enlace.usuario_id)
    return EnlaceInfo(tipo=enlace.tipo, nombre=usuario.nombre)


@router.post("/establecer-clave", status_code=status.HTTP_204_NO_CONTENT)
async def establecer_clave(data: EstablecerClaveRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    """Crea o restablece la clave con un enlace vigente. El enlace queda usado y se cierran las sesiones."""
    enlace = await enlaces.vigente(db, data.token)
    if enlace is None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=ENLACE_INVALIDO)
    usuario = await db.get(Usuario, enlace.usuario_id)
    try:
        asignar_clave(usuario, data.password)
    except ValueError as exc:   # el enlace sigue vigente: puede intentar otra clave
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    enlaces.marcar_usado(enlace)
    await registrar_auditoria(db, usuario_id=usuario.id, condominio_id=usuario.condominio_id,
                              accion="CLAVE_ESTABLECIDA", detalles={"tipo": enlace.tipo})
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/cambiar-clave", response_model=TokenResponse)
async def cambiar_clave(
    data: CambiarClaveRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Cambia la propia clave. Cierra las demás sesiones y entrega un token nuevo para la sesión en curso."""
    if not verify_password(data.actual, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La clave actual no es correcta")
    try:
        asignar_clave(current_user, data.nueva)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    await registrar_auditoria(db, usuario_id=current_user.id, condominio_id=current_user.condominio_id,
                              accion="CLAVE_CAMBIADA", detalles={})
    await db.commit()
    return _token_de(current_user)
