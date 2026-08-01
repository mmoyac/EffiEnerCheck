from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .auditoria import AuditoriaLog
    from .boleta import BoletaMaestra
    from .parcela import Parcela
    from .usuario import Usuario


class Condominio(Base):
    __tablename__ = "condominios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    rut_comunidad: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    direccion: Mapped[Optional[str]] = mapped_column(String)
    plan_suscripcion: Mapped[str] = mapped_column(String, nullable=False)  # basico, pro, premium
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    parcelas: Mapped[List["Parcela"]] = relationship("Parcela", back_populates="condominio")
    usuarios: Mapped[List["Usuario"]] = relationship(
        "Usuario", back_populates="condominio", foreign_keys="[Usuario.condominio_id]"
    )
    boletas_maestras: Mapped[List["BoletaMaestra"]] = relationship(
        "BoletaMaestra", back_populates="condominio"
    )
    auditoria_logs: Mapped[List["AuditoriaLog"]] = relationship(
        "AuditoriaLog", back_populates="condominio"
    )
