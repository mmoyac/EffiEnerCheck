from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .boleta import BoletaMaestra
    from .parcela import Parcela


class LiquidacionParcela(Base):
    __tablename__ = "liquidaciones_parcelas"

    id: Mapped[int] = mapped_column(primary_key=True)
    parcela_id: Mapped[int] = mapped_column(ForeignKey("parcelas.id"), nullable=False)
    boleta_id: Mapped[int] = mapped_column(ForeignKey("boletas_maestras.id"), nullable=False)

    monto_energia_kwh: Mapped[Optional[int]] = mapped_column(Integer)
    monto_prorrateo_variable: Mapped[Optional[int]] = mapped_column(Integer)
    monto_cuota_fija: Mapped[Optional[int]] = mapped_column(Integer)

    total_pagar_mes: Mapped[Optional[int]] = mapped_column(Integer)
    # Derivados de la cuenta corriente de luz (cambio cobranza-energia): los abonos se imputan a la deuda
    # más antigua. No se marcan a mano; los recalcula services/cuenta_luz.recalcular().
    monto_abonado: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    pagado: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_pago: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    parcela: Mapped["Parcela"] = relationship("Parcela", back_populates="liquidaciones")
    boleta: Mapped["BoletaMaestra"] = relationship("BoletaMaestra", back_populates="liquidaciones")
