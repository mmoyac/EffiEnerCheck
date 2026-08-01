from datetime import date
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .condominio import Condominio
    from .lectura import LecturaParcela
    from .liquidacion import LiquidacionParcela
    from .usuario import Usuario


class BoletaMaestra(Base):
    __tablename__ = "boletas_maestras"

    id: Mapped[int] = mapped_column(primary_key=True)
    condominio_id: Mapped[int] = mapped_column(ForeignKey("condominios.id"), nullable=False)
    periodo_mes: Mapped[date] = mapped_column(Date, nullable=False)
    url_imagen_boleta: Mapped[Optional[str]] = mapped_column(String)

    # Control de transparencia y flujo
    boleta_visible_usuarios: Mapped[bool] = mapped_column(Boolean, default=False)
    estado: Mapped[str] = mapped_column(String, nullable=False, default="borrador")  # borrador, validada, publicada
    # Candados de cierre de período
    lecturas_cerradas: Mapped[bool] = mapped_column(Boolean, default=False)
    liquidaciones_cerradas: Mapped[bool] = mapped_column(Boolean, default=False)

    # Totales para validación OCR y motor de cálculo
    total_kwh_compania: Mapped[Optional[float]] = mapped_column(Float)
    # Total neto SIN IVA que extrae el OCR. No entra en las fórmulas del motor
    # (valor_kwh se despeja desde monto_total_emision); el motor solo lo exige
    # como señal de que la boleta ya fue cargada. Ver services/enercheck.py
    monto_neto_electricidad_consumida: Mapped[Optional[float]] = mapped_column(Float)
    monto_total_emision: Mapped[Optional[int]] = mapped_column(Integer)
    monto_saldo_anterior: Mapped[Optional[int]] = mapped_column(Integer)
    creado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)

    condominio: Mapped["Condominio"] = relationship("Condominio", back_populates="boletas_maestras")
    creado_por_usuario: Mapped["Usuario"] = relationship(
        "Usuario", back_populates="boletas_creadas"
    )
    items_detalle: Mapped[List["BoletaItemDetalle"]] = relationship(
        "BoletaItemDetalle", back_populates="boleta", cascade="all, delete-orphan"
    )
    lecturas: Mapped[List["LecturaParcela"]] = relationship(
        "LecturaParcela", back_populates="boleta"
    )
    liquidaciones: Mapped[List["LiquidacionParcela"]] = relationship(
        "LiquidacionParcela", back_populates="boleta"
    )


class BoletaItemDetalle(Base):
    __tablename__ = "boleta_items_detalle"

    id: Mapped[int] = mapped_column(primary_key=True)
    boleta_id: Mapped[int] = mapped_column(ForeignKey("boletas_maestras.id"), nullable=False)
    descripcion: Mapped[str] = mapped_column(String, nullable=False)  # "Transporte", "Administración", etc.
    monto_neto_clp: Mapped[float] = mapped_column(Float, nullable=False)
    tipo_calculo: Mapped[str] = mapped_column(String, nullable=False)  # fijo, variable, informativo

    boleta: Mapped["BoletaMaestra"] = relationship("BoletaMaestra", back_populates="items_detalle")
