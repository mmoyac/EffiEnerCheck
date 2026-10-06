from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import CurrentUser, exigir_portal, get_db, modulos_del_usuario
from app.core.security import create_access_token, verify_password
from app.models.condominio import Condominio
from app.models.usuario import Usuario
from app.schemas.auth import TokenResponse
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
