"""Normalización de dominios y hosts: la misma regla al guardar un dominio y al resolver una petición."""
import re

_HOSTNAME = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


def normalizar_host(host: str) -> str:
    """'WWW.Condominio.cl:443' → 'condominio.cl'. Sin esquema, puerto, punto final ni prefijo www."""
    h = host.strip().lower()
    h = re.sub(r"^[a-z]+://", "", h).split("/", 1)[0]
    h = h.rsplit(":", 1)[0] if ":" in h else h
    h = h.rstrip(".")
    return h[4:] if h.startswith("www.") else h


def normalizar_dominio(valor: str) -> str:
    """Como normalizar_host, pero exige un nombre de dominio válido (ValueError si no)."""
    dominio = normalizar_host(valor)
    if not _HOSTNAME.match(dominio):
        raise ValueError(f"Dominio inválido: {valor}")
    return dominio
