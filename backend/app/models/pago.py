"""
Pagos en línea: base común de la plataforma (cambio pasarelas-pago).

Una `PasarelaPago` es la cuenta de un condominio en un proveedor (Flow, Khipu, ...). Una
`IntencionPago` es un intento de cobrar una cosa (`concepto` + `referencia_id`), que el backend
confirma siempre consultando al proveedor. Ver openspec/changes/pasarelas-pago/design.md.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, Integer, LargeBinary, Numeric, String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

AMBIENTES = ("integracion", "produccion")
ESTADOS_INTENCION = ("INICIADO", "CONFIRMADO", "RECHAZADO", "EXPIRADO", "EN_REVISION")
# Estados en los que la intención ya no cambia sola
ESTADOS_FINALES = ("CONFIRMADO", "RECHAZADO", "EN_REVISION")


class PasarelaPago(Base):
    __tablename__ = "pasarelas_pago"
    __table_args__ = (
        CheckConstraint("ambiente IN ('integracion','produccion')", name="ck_pasarelas_pago_ambiente"),
        CheckConstraint("comision_porcentaje >= 0 AND comision_porcentaje < 50", name="ck_pasarelas_pago_comision"),
        CheckConstraint("comision_fija >= 0", name="ck_pasarelas_pago_comision_fija"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    condominio_id: Mapped[int] = mapped_column(ForeignKey("condominios.id"), nullable=False, index=True)
    proveedor: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre_visible: Mapped[str] = mapped_column(String, nullable=False)
    ambiente: Mapped[str] = mapped_column(String(12), nullable=False)
    # nonce(12) || AES-256-GCM; AAD condominio:<id>:pasarela:<id> (services/pagos/cifrado.py)
    credenciales_cifradas: Mapped[Optional[bytes]] = mapped_column(LargeBinary)
    credenciales_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # Comisión que paga el comunero: porcentaje con IVA incluido + monto fijo en pesos
    comision_porcentaje: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False, default=0, server_default="0")
    comision_fija: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    prueba_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    prueba_ok: Mapped[Optional[bool]] = mapped_column(Boolean)
    prueba_mensaje: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IntencionPago(Base):
    __tablename__ = "intenciones_pago"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('INICIADO','CONFIRMADO','RECHAZADO','EXPIRADO','EN_REVISION')",
            name="ck_intenciones_pago_estado",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condominio_id: Mapped[int] = mapped_column(ForeignKey("condominios.id"), nullable=False, index=True)
    pasarela_id: Mapped[int] = mapped_column(ForeignKey("pasarelas_pago.id"), nullable=False, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    # Qué se paga: services/pagos/consumidores.py (p. ej. "rifa_compra" + compra_id)
    concepto: Mapped[str] = mapped_column(String(30), nullable=False)
    referencia_id: Mapped[int] = mapped_column(Integer, nullable=False)
    descripcion: Mapped[str] = mapped_column(String, nullable=False)
    # monto = lo adeudado; total = monto + comisión (lo que cobra la pasarela)
    monto: Mapped[int] = mapped_column(Integer, nullable=False)
    comision: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(String(12), nullable=False, default="INICIADO", index=True)
    vence_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # UUID en base32 sin relleno: 26 caracteres, sirve como orden del comercio en cualquier proveedor
    orden_comercio: Mapped[str] = mapped_column(String(26), nullable=False, unique=True)
    token_proveedor: Mapped[Optional[str]] = mapped_column(String, index=True)
    transaccion_proveedor: Mapped[Optional[str]] = mapped_column(String, index=True)
    # Solo para enviarlo al proveedor; se borra cuando la intención termina
    email_pagador: Mapped[Optional[str]] = mapped_column(String)
    autorizacion: Mapped[Optional[str]] = mapped_column(String)
    ultimos_digitos: Mapped[Optional[str]] = mapped_column(String(4))
    medio: Mapped[Optional[str]] = mapped_column(String)
    monto_confirmado: Mapped[Optional[int]] = mapped_column(Integer)
    # Respuesta del proveedor filtrada por lista blanca: nunca RUT, nombre, correo ni cuenta
    respuesta_proveedor: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    motivo: Mapped[Optional[str]] = mapped_column(Text)
    consultado_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    confirmado_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # Revisión manual de un pago que no se pudo aplicar
    resuelta_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resuelta_por_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"))
    nota_resolucion: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    pasarela: Mapped["PasarelaPago"] = relationship("PasarelaPago")
