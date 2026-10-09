"""
Tipos de período (cambio lectura-inicial).

- `regular`: período facturado por la compañía (boleta, ítems, OCR, liquidaciones, publicación).
- `lectura_inicial`: solo registra la lectura de partida de cada medidor. No se liquida ni se publica;
  queda "cerrado" al cerrar sus lecturas y la primera boleta toma sus valores como lectura anterior.
"""
from fastapi import HTTPException, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.boleta import BoletaMaestra

REGULAR = "regular"
LECTURA_INICIAL = "lectura_inicial"


def es_lectura_inicial(boleta: BoletaMaestra) -> bool:
    return boleta.tipo == LECTURA_INICIAL


async def descartar_liquidaciones(db: AsyncSession, boleta_id: int) -> int:
    """
    Descarta las liquidaciones calculadas de un período abierto cuando cambia algo de lo que las produjo
    (lecturas, desglose, reapertura): son un borrador y quedarían desactualizadas. Así no se puede cerrar ni
    publicar un período con montos viejos; hay que recalcular (cambio pasos-del-periodo).
    """
    from app.models.liquidacion import LiquidacionParcela
    resultado = await db.execute(delete(LiquidacionParcela).where(LiquidacionParcela.boleta_id == boleta_id))
    return resultado.rowcount or 0


def exigir_periodo_regular(boleta: BoletaMaestra) -> None:
    """409 para todo lo que es propio de la boleta de la compañía (cálculo, OCR, ítems, cierre, publicación)."""
    if es_lectura_inicial(boleta):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El período de lectura inicial no se liquida")
