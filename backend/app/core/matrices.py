"""
Matrices de cálculo de la luz (cambio matriz-calculo-luz). El condominio tiene una por defecto y cada
período la copia al crearse; las define el super_admin. Ver services/enercheck.py.

- fijo_y_variable: ítems `fijo` en partes iguales; ítems `variable` y diferencial según el consumo.
- cargo_fijo:      todos los ítems del reparto en partes iguales (cargo fijo); la energía y el
                   diferencial, según el consumo.
"""
from typing import Literal

FIJO_Y_VARIABLE = "fijo_y_variable"
CARGO_FIJO = "cargo_fijo"

MATRICES = (FIJO_Y_VARIABLE, CARGO_FIJO)
MatrizCalculo = Literal["fijo_y_variable", "cargo_fijo"]

CHECK_SQL = "{col} IN ('fijo_y_variable', 'cargo_fijo')"
