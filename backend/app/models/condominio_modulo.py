from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .condominio import Condominio


class CondominioModulo(Base):
    """Módulo contratado por un condominio (catálogo en app/core/modulos.py)."""

    __tablename__ = "condominio_modulos"
    __table_args__ = (
        CheckConstraint(
            "modulo IN ('sitio', 'portal', 'energia', 'rifas')", name="ck_condominio_modulos_modulo"
        ),
    )

    condominio_id: Mapped[int] = mapped_column(
        ForeignKey("condominios.id", ondelete="CASCADE"), primary_key=True
    )
    modulo: Mapped[str] = mapped_column(String(20), primary_key=True)

    condominio: Mapped["Condominio"] = relationship("Condominio", back_populates="modulos")


class CondominioDominio(Base):
    """Dominio en que se publica la landing de un condominio (sin www., en minúsculas)."""

    __tablename__ = "condominio_dominios"

    dominio: Mapped[str] = mapped_column(String(253), primary_key=True)
    condominio_id: Mapped[int] = mapped_column(
        ForeignKey("condominios.id", ondelete="CASCADE"), nullable=False, index=True
    )

    condominio: Mapped["Condominio"] = relationship("Condominio", back_populates="dominios_sitio")
