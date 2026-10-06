from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .usuario_parcela import usuario_parcelas

if TYPE_CHECKING:
    from .auditoria import AuditoriaLog
    from .boleta import BoletaMaestra
    from .condominio import Condominio
    from .lectura import LecturaParcela
    from .parcela import Parcela
    from .rol import Rol


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # NULL = invitación pendiente: la cuenta existe pero no puede iniciar sesión hasta crear su clave
    password_hash: Mapped[Optional[str]] = mapped_column(String)
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    # NULL para super_admin
    condominio_id: Mapped[Optional[int]] = mapped_column(ForeignKey("condominios.id"))
    ultimo_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # Normalizado a 56XXXXXXXXX (ver app/utils/telefono.py)
    telefono: Mapped[Optional[str]] = mapped_column(String)
    # Último establecimiento o cambio de clave: los JWT emitidos antes dejan de valer
    clave_cambiada_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    rol: Mapped["Rol"] = relationship("Rol", back_populates="usuarios")
    condominio: Mapped[Optional["Condominio"]] = relationship(
        "Condominio", back_populates="usuarios", foreign_keys=[condominio_id]
    )
    # M2M: un parcelero puede tener una o más parcelas
    parcelas: Mapped[List["Parcela"]] = relationship(
        "Parcela", secondary=usuario_parcelas, back_populates="usuarios"
    )
    boletas_creadas: Mapped[List["BoletaMaestra"]] = relationship(
        "BoletaMaestra", back_populates="creado_por_usuario"
    )
    lecturas_tomadas: Mapped[List["LecturaParcela"]] = relationship(
        "LecturaParcela", back_populates="lector"
    )
    auditoria_logs: Mapped[List["AuditoriaLog"]] = relationship(
        "AuditoriaLog", back_populates="usuario"
    )

    # No es columna: lo completa get_current_user con los módulos habilitados de su condominio
    modulos = ()
