from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.matrices import CHECK_SQL, FIJO_Y_VARIABLE

from .base import Base

if TYPE_CHECKING:
    from .auditoria import AuditoriaLog
    from .boleta import BoletaMaestra
    from .condominio_modulo import CondominioDominio, CondominioModulo
    from .parcela import Parcela
    from .usuario import Usuario


class Condominio(Base):
    __tablename__ = "condominios"
    __table_args__ = (
        CheckConstraint("color_primario ~ '^#[0-9A-F]{6}$'", name="ck_condominios_color_primario"),
        CheckConstraint(CHECK_SQL.format(col="matriz_calculo_luz"), name="ck_condominios_matriz_calculo_luz"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    rut_comunidad: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    direccion: Mapped[Optional[str]] = mapped_column(String)
    plan_suscripcion: Mapped[str] = mapped_column(String, nullable=False)  # basico, pro, premium
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    # Parametrización comercial (la define el super_admin; ver specs gestion-condominios y modulos-plataforma)
    portal_url: Mapped[Optional[str]] = mapped_column(String)
    logo_url: Mapped[Optional[str]] = mapped_column(String)
    color_primario: Mapped[Optional[str]] = mapped_column(String(7))  # #RRGGBB en mayúsculas
    # Matriz con que se liquida la luz por defecto; cada período la copia al crearse (core/matrices.py)
    matriz_calculo_luz: Mapped[str] = mapped_column(
        String(20), nullable=False, default=FIJO_Y_VARIABLE, server_default=FIJO_Y_VARIABLE
    )
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
    modulos: Mapped[List["CondominioModulo"]] = relationship(
        "CondominioModulo", back_populates="condominio", cascade="all, delete-orphan"
    )
    dominios_sitio: Mapped[List["CondominioDominio"]] = relationship(
        "CondominioDominio", back_populates="condominio", cascade="all, delete-orphan"
    )

    @property
    def modulos_habilitados(self) -> list[str]:
        """Requiere haber cargado `modulos` con selectinload."""
        from app.core.modulos import MODULOS
        tiene = {m.modulo for m in self.modulos}
        return [m for m in MODULOS if m in tiene]
