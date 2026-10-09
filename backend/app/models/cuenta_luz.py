from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class MovimientoLuz(Base):
    """
    Movimiento de la cuenta corriente de luz de una parcela (cambio cobranza-energia).

    - `saldo_inicial`: deuda por luz anterior a la plataforma, cargada en el onboarding (planilla de la
      lectura inicial). Es un cargo.
    - `abono`: pago del comunero, de cualquier monto, registrado por la administración.

    Los cargos mensuales NO se copian aquí: son las liquidaciones publicadas. Saldo = saldo inicial +
    liquidaciones publicadas − abonos. Un movimiento NUNCA se borra: se anula con motivo, quién y cuándo
    (queda para auditorías futuras).
    """
    __tablename__ = "movimientos_luz"
    __table_args__ = (
        CheckConstraint("tipo IN ('saldo_inicial', 'abono')", name="ck_movimientos_luz_tipo"),
        CheckConstraint("monto > 0", name="ck_movimientos_luz_monto"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    condominio_id: Mapped[int] = mapped_column(ForeignKey("condominios.id"), nullable=False, index=True)
    parcela_id: Mapped[int] = mapped_column(ForeignKey("parcelas.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    monto: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)          # fecha del pago o de la deuda
    nota: Mapped[Optional[str]] = mapped_column(Text)
    boleta_id: Mapped[Optional[int]] = mapped_column(ForeignKey("boletas_maestras.id"))   # lectura inicial
    creado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    anulado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    anulado_por: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"))
    anulado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    motivo_anulacion: Mapped[Optional[str]] = mapped_column(Text)
