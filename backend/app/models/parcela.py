from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .usuario_parcela import usuario_parcelas

if TYPE_CHECKING:
    from .condominio import Condominio
    from .lectura import LecturaParcela
    from .liquidacion import LiquidacionParcela
    from .usuario import Usuario


class Parcela(Base):
    __tablename__ = "parcelas"

    id: Mapped[int] = mapped_column(primary_key=True)
    condominio_id: Mapped[int] = mapped_column(ForeignKey("condominios.id"), nullable=False)
    numero_parcela: Mapped[str] = mapped_column(String, nullable=False)
    propietario_nombre: Mapped[Optional[str]] = mapped_column(String)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)

    condominio: Mapped["Condominio"] = relationship("Condominio", back_populates="parcelas")
    usuarios: Mapped[List["Usuario"]] = relationship(
        "Usuario", secondary=usuario_parcelas, back_populates="parcelas"
    )
    lecturas: Mapped[List["LecturaParcela"]] = relationship(
        "LecturaParcela", back_populates="parcela"
    )
    liquidaciones: Mapped[List["LiquidacionParcela"]] = relationship(
        "LiquidacionParcela", back_populates="parcela"
    )
