from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .rol import Rol

menu_roles = Table(
    "menu_roles",
    Base.metadata,
    Column("menu_id", Integer, ForeignKey("menus.id", ondelete="CASCADE"), primary_key=True),
    Column("rol_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Menu(Base):
    __tablename__ = "menus"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(String)
    orden: Mapped[int] = mapped_column(Integer, default=0)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("menus.id"))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    # NULL = núcleo del portal; si no, un módulo de app/core/modulos.py
    modulo: Mapped[Optional[str]] = mapped_column(String(20))

    roles: Mapped[List["Rol"]] = relationship("Rol", secondary=menu_roles)
    hijos: Mapped[List["Menu"]] = relationship("Menu", back_populates="padre")
    padre: Mapped[Optional["Menu"]] = relationship(
        "Menu", back_populates="hijos", remote_side="Menu.id"
    )
