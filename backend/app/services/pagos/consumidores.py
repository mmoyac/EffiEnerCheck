"""
Consumidores de pagos: qué se paga con una intención y qué pasa al aprobarla o liberarla.

El núcleo de pagos no sabe de rifas: llama al consumidor del `concepto` de la intención. Un módulo
que quiera cobrar en línea (p. ej. los abonos de la luz) implementa este contrato y se registra aquí.
"""
from importlib import import_module
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pago import IntencionPago


class Consumidor(Protocol):
    concepto: str

    async def aplicar(self, db: AsyncSession, intencion: IntencionPago) -> str | None:
        """Aplica un pago aprobado. None = aplicado; un texto = motivo para dejarlo en revisión.
        Debe ser idempotente: puede llamarse sobre algo ya aplicado."""

    async def liberar(self, db: AsyncSession, intencion: IntencionPago, motivo: str) -> None:
        """Deja libre lo que la intención reservaba (el pago no se hizo o venció)."""

    def volver_a(self, intencion: IntencionPago) -> str | None:
        """Ruta del portal a la que vuelve el pagador desde la pantalla de resultado."""


# concepto → "módulo:atributo" (import diferido: el consumidor depende de sus propios modelos)
_REGISTRO = {
    "rifa_compra": "app.services.rifas_pago:CONSUMIDOR",
}


def consumidor(concepto: str) -> Consumidor:
    modulo, atributo = _REGISTRO[concepto].split(":")
    return getattr(import_module(modulo), atributo)
