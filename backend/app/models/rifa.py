from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .parcela import Parcela
    from .usuario import Usuario

# Formas de pago de una compra
MEDIOS_PAGO = ("efectivo", "transferencia", "gasto_comun")
# Quién registró la compra: el propio vecino, la portería o la administración
CANALES = ("portal", "porteria", "administracion")


class Rifa(Base):
    """Rifa solidaria del condominio. Independiente de la boleta eléctrica y de las liquidaciones."""
    __tablename__ = "rifas"

    id: Mapped[int] = mapped_column(primary_key=True)
    condominio_id: Mapped[int] = mapped_column(ForeignKey("condominios.id"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    beneficiario: Mapped[str] = mapped_column(String, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    # En orden: el primero es el primer premio
    premios: Mapped[List[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    # Texto libre: banco, tipo y número de cuenta, titular, RUT, correo
    datos_transferencia: Mapped[Optional[str]] = mapped_column(Text)
    precio_numero: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad_numeros: Mapped[int] = mapped_column(Integer, nullable=False)
    # abierta | cerrada
    estado: Mapped[str] = mapped_column(String, nullable=False, default="abierta")
    # Contador del folio correlativo de las compras; no se reutiliza al anular
    ultimo_folio: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    creado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cerrada_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    compras: Mapped[List["CompraRifa"]] = relationship("CompraRifa", back_populates="rifa")
    imputaciones: Mapped[List["ImputacionRifa"]] = relationship("ImputacionRifa", back_populates="rifa")


class CompraRifa(Base):
    """
    Unidad que ve y anula el usuario. Al anularla se borran sus RifaNumero (el número queda
    libre) pero la compra se conserva con anulada=True como historial.
    """
    __tablename__ = "compras_rifa"
    __table_args__ = (UniqueConstraint("rifa_id", "folio", name="uq_compra_rifa_folio"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    rifa_id: Mapped[int] = mapped_column(ForeignKey("rifas.id", ondelete="CASCADE"), nullable=False, index=True)
    # Correlativo dentro de la rifa; se muestra como R{rifa_id}-{folio:03d}
    folio: Mapped[int] = mapped_column(Integer, nullable=False)
    parcela_id: Mapped[int] = mapped_column(ForeignKey("parcelas.id"), nullable=False, index=True)
    # Cuenta que registró la compra (el vecino, la portería o un administrador)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    canal: Mapped[str] = mapped_column(String, nullable=False)
    # Texto libre: el comprador puede no ser residente
    comprador_nombre: Mapped[Optional[str]] = mapped_column(String)
    # Normalizado (56XXXXXXXXX); destino del comprobante por WhatsApp
    telefono: Mapped[Optional[str]] = mapped_column(String)
    # Números originales de la compra; se conservan aunque se anule
    numeros: Mapped[List[int]] = mapped_column(ARRAY(Integer), nullable=False)
    # Congelado al comprar: cantidad de números × precio_numero
    monto: Mapped[int] = mapped_column(Integer, nullable=False)
    medio_pago: Mapped[str] = mapped_column(String, nullable=False)
    # efectivo: pagada al registrar | transferencia: al confirmar | gasto_comun: nunca (se imputa)
    pagada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pagada_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    pago_confirmado_por_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"))
    # Archivo en /app/privado/vouchers (nunca en el estático público /uploads)
    voucher_archivo: Mapped[Optional[str]] = mapped_column(String)
    voucher_mime: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    anulada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    anulada_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    anulada_por_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"))

    rifa: Mapped["Rifa"] = relationship("Rifa", back_populates="compras")
    parcela: Mapped["Parcela"] = relationship("Parcela")
    usuario: Mapped["Usuario"] = relationship("Usuario", foreign_keys=[usuario_id])
    anulada_por: Mapped[Optional["Usuario"]] = relationship("Usuario", foreign_keys=[anulada_por_id])
    numeros_vigentes: Mapped[List["RifaNumero"]] = relationship(
        "RifaNumero", back_populates="compra", cascade="all, delete-orphan"
    )

    @property
    def folio_texto(self) -> str:
        return f"R{self.rifa_id}-{self.folio:03d}"


class RifaNumero(Base):
    """Número vigente. La restricción única impide vender dos veces el mismo número."""
    __tablename__ = "rifa_numeros"
    __table_args__ = (UniqueConstraint("rifa_id", "numero", name="uq_rifa_numero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    compra_id: Mapped[int] = mapped_column(ForeignKey("compras_rifa.id", ondelete="CASCADE"), nullable=False)
    rifa_id: Mapped[int] = mapped_column(ForeignKey("rifas.id", ondelete="CASCADE"), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)

    compra: Mapped["CompraRifa"] = relationship("CompraRifa", back_populates="numeros_vigentes")


class ImputacionRifa(Base):
    """
    Monto a cargar en el gasto común de una parcela (en Comunidad Feliz), generado al cerrar
    la rifa con sus compras `gasto_comun`. No participa de las liquidaciones eléctricas.
    """
    __tablename__ = "imputaciones_rifa"
    __table_args__ = (UniqueConstraint("rifa_id", "parcela_id", name="uq_imputacion_rifa_parcela"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    rifa_id: Mapped[int] = mapped_column(ForeignKey("rifas.id", ondelete="CASCADE"), nullable=False)
    parcela_id: Mapped[int] = mapped_column(ForeignKey("parcelas.id"), nullable=False)
    cantidad_numeros: Mapped[int] = mapped_column(Integer, nullable=False)
    monto: Mapped[int] = mapped_column(Integer, nullable=False)
    # Marcada por el administrador cuando la cargó en el sistema de gasto común
    cargada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cargada_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    rifa: Mapped["Rifa"] = relationship("Rifa", back_populates="imputaciones")
    parcela: Mapped["Parcela"] = relationship("Parcela")
