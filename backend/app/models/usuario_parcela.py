from sqlalchemy import Column, ForeignKey, Integer, Table

from .base import Base

# Tabla puente: un parcelero puede tener una o más parcelas asignadas
usuario_parcelas = Table(
    "usuario_parcelas",
    Base.metadata,
    Column("usuario_id", Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True),
    Column("parcela_id", Integer, ForeignKey("parcelas.id", ondelete="CASCADE"), primary_key=True),
)
