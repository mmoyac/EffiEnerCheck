"""Comisión de la pasarela a cargo del pagador (spec pagos-en-linea: «Comisión a cargo del pagador»)."""
import math
from decimal import Decimal


def total_con_comision(monto: int, porcentaje: Decimal | float | int, fija: int) -> int:
    """
    Total a cobrar para que, descontada la comisión (porcentaje con IVA incluido + monto fijo), quede al
    menos `monto`: ⌈(monto + fija) / (1 − porcentaje/100)⌉. Con Decimal para no arrastrar errores de float.
    """
    pct = Decimal(str(porcentaje))
    if pct == 0:
        return monto + fija
    bruto = (Decimal(monto) + Decimal(fija)) / (1 - pct / 100)
    return math.ceil(bruto)
