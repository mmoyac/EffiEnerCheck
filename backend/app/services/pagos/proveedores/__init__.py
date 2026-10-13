"""Registro de proveedores de pago. Un proveedor nuevo se agrega aquí y en nada más."""
from .base import Adaptador
from .flow import Flow
from .khipu import Khipu

REGISTRO: dict[str, Adaptador] = {a.proveedor: a for a in (Flow(), Khipu())}


def adaptador(proveedor: str) -> Adaptador:
    return REGISTRO[proveedor]
