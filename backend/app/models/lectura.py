from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey
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

    parcela: Mapped["Parcela"] = relationship("Parcela", back_populates="lecturas")
    boleta: Mapped["BoletaMaestra"] = relationship("BoletaMaestra", back_populates="lecturas")
    lector: Mapped["Usuario"] = relationship("Usuario", back_populates="lecturas_tomadas")
