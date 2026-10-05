import re

# Misma regla que frontend/src/utils/telefono.ts: mantener ambas sincronizadas.


def normalizar_telefono(valor: str | int | None) -> str | None:
    """
    Normaliza un teléfono chileno al formato internacional solo con dígitos (56XXXXXXXXX).

    - 8 dígitos (celular sin el 9 inicial, formato antiguo) → 569 + dígitos
    - 9 dígitos (celular 9XXXXXXXX o fijo 2XXXXXXXX)        → 56 + dígitos
    - 11 dígitos que empiezan en 56                          → tal cual

    Retorna None si viene vacío. Lanza ValueError si no calza con ninguna regla.
    """
    if valor is None:
        return None
    digitos = re.sub(r"\D", "", str(valor))
    if not digitos:
        return None
    if len(digitos) == 8:
        return "569" + digitos
    if len(digitos) == 9:
        return "56" + digitos
    if len(digitos) == 11 and digitos.startswith("56"):
        return digitos
    raise ValueError(f"Teléfono inválido: {valor}")
