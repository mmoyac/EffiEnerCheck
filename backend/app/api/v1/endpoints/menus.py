from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AnyRoleRequired, get_db
from app.models.menu import Menu, menu_roles
from app.models.usuario import Usuario
from app.schemas.menu import MenuResponse

router = APIRouter(prefix="/menus", tags=["menus"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/me", response_model=list[MenuResponse])
async def get_my_menus(
    current_user: Annotated[Usuario, Depends(AnyRoleRequired)],
    db: DB,
):
    """
    Ítems de menú visibles para el rol del usuario autenticado, sin los de módulos que su
    condominio no tiene habilitados (el super_admin tiene todos: current_user.modulos).
    """
    result = await db.execute(
        select(Menu)
        .join(menu_roles, Menu.id == menu_roles.c.menu_id)
        .where(menu_roles.c.rol_id == current_user.rol_id)
        .where(Menu.activo == True)  # noqa: E712
        .where(Menu.parent_id == None)  # noqa: E711 — solo menús raíz
        .where(or_(Menu.modulo == None, Menu.modulo.in_(current_user.modulos)))  # noqa: E711
        .order_by(Menu.orden)
    )
    return result.scalars().all()
