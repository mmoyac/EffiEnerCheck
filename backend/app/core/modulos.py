"""
Catálogo de módulos de la plataforma (ver openspec/specs/modulos-plataforma).

Cada condominio cliente tiene un subconjunto habilitado (tabla condominio_modulos), que define
el super_admin:

- `sitio`   → producto: landing pública del condominio (aplicación landing/, aparte del portal).
- `portal`  → producto: portal de administración. Sin él, los usuarios del condominio no inician sesión.
- `energia` → módulo del portal: boletas, lecturas y liquidaciones (EnerCheck).
- `rifas`   → módulo del portal: rifas solidarias.

El catálogo vive en código porque cada módulo nuevo exige endpoints y pantallas. Si agregas uno,
replica su grupo de menú en frontend/src/config/modulos.ts y amplía el CHECK de condominio_modulos.
"""
from typing import Literal

Modulo = Literal["sitio", "portal", "energia", "rifas"]

MODULOS: tuple[Modulo, ...] = ("sitio", "portal", "energia", "rifas")

ETIQUETAS: dict[Modulo, str] = {
    "sitio": "Landing",
    "portal": "Administración",
    "energia": "Energía",
    "rifas": "Rifas",
}

# Módulos que viven dentro del portal y por lo tanto lo exigen
REQUIEREN_PORTAL: tuple[Modulo, ...] = ("energia", "rifas")


def validar_modulos(modulos: list[str]) -> list[Modulo]:
    """Normaliza (sin repetidos, en el orden del catálogo) y valida la dependencia con `portal`."""
    desconocidos = sorted(set(modulos) - set(MODULOS))
    if desconocidos:
        raise ValueError(f"Módulos desconocidos: {', '.join(desconocidos)}")
    if any(m in modulos for m in REQUIEREN_PORTAL) and "portal" not in modulos:
        raise ValueError("Los módulos energia y rifas requieren el módulo portal")
    return [m for m in MODULOS if m in modulos]
