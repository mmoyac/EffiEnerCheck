from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import CurrentUser, get_db
from app.core.security import create_access_token, verify_password
from app.models.usuario import Usuario
from app.schemas.auth import TokenResponse
from app.schemas.usuario import UsuarioDetailResponse

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

    user.ultimo_login = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token(
        user_id=user.id,
        rol=user.rol.nombre,
        condominio_id=user.condominio_id,
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UsuarioDetailResponse)
async def get_me(current_user: CurrentUser):
    """Retorna el perfil del usuario autenticado."""
    return current_user
