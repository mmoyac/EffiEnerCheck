from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .usuario import Usuario


class Rol(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)  # super_admin, admin_condominio, lector, parcelero
    descripcion: Mapped[Optional[str]] = mapped_column(Text)

    usuarios: Mapped[List["Usuario"]] = relationship("Usuario", back_populates="rol")
