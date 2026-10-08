from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .boleta import BoletaMaestra
    from .parcela import Parcela
    from .usuario import Usuario


class LecturaParcela(Base):
    __tablename__ = "lecturas_parcelas"

    id: Mapped[int] = mapped_column(primary_key=True)
    parcela_id: Mapped[int] = mapped_column(ForeignKey("parcelas.id"), nullable=False)
    boleta_id: Mapped[int] = mapped_column(ForeignKey("boletas_maestras.id"), nullable=False)
    lectura_anterior: Mapped[float] = mapped_column(Float, nullable=False)
    lectura_actual: Mapped[float] = mapped_column(Float, nullable=False)
    kwh_consumidos: Mapped[float] = mapped_column(Float, nullable=False)
    lector_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    fecha_toma: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # Foto del medidor (cambio foto-medidor): el archivo vive en /app/privado/lecturas, nunca en /uploads
    foto_archivo: Mapped[Optional[str]] = mapped_column(String(64))
    foto_sha256: Mapped[Optional[str]] = mapped_column(String(64))
    foto_fecha_toma: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    foto_subida_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    @property
    def tiene_foto(self) -> bool:
        return self.foto_archivo is not None

    parcela: Mapped["Parcela"] = relationship("Parcela", back_populates="lecturas")
    boleta: Mapped["BoletaMaestra"] = relationship("BoletaMaestra", back_populates="lecturas")
    lector: Mapped["Usuario"] = relationship("Usuario", back_populates="lecturas_tomadas")
