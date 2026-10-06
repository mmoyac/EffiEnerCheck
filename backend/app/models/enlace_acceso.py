from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CHAR, CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .usuario import Usuario


class EnlaceAcceso(Base):
    """Enlace de un solo uso para crear (invitación) o restablecer (recuperación) la clave.

    Solo se guarda el sha256 del token: el token viaja únicamente en el enlace (ver services/enlaces.py).
    """
    __tablename__ = "enlaces_acceso"
    __table_args__ = (
        CheckConstraint("tipo IN ('invitacion', 'recuperacion')", name="ck_enlaces_acceso_tipo"),
        Index("ix_enlaces_acceso_usuario_tipo", "usuario_id", "tipo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    usado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    anulado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    usuario: Mapped["Usuario"] = relationship("Usuario")
