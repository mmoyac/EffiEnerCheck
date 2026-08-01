from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .condominio import Condominio
    from .usuario import Usuario


class AuditoriaLog(Base):
    __tablename__ = "auditoria_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    # NULL cuando la acción la ejecuta un super_admin sin condominio asignado
    condominio_id: Mapped[Optional[int]] = mapped_column(ForeignKey("condominios.id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    accion: Mapped[str] = mapped_column(String, nullable=False)  # LOGIN, UPLOAD_BOLETA, TOGGLE_VISIBILITY, DELETE_USER
    detalles: Mapped[Optional[Any]] = mapped_column(JSONB)  # {"before": {...}, "after": {...}}
    ip_address: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    condominio: Mapped[Optional["Condominio"]] = relationship(
        "Condominio", back_populates="auditoria_logs"
    )
    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="auditoria_logs")
