"""
Cifrado de las credenciales de las pasarelas: AES-256-GCM con la clave maestra PAGOS_CLAVE_MAESTRA.

El dato asociado (AAD) amarra el texto cifrado a su condominio y su pasarela: copiado a otra fila,
no se descifra. Formato guardado: nonce (12 bytes) || texto cifrado con su etiqueta.
"""
import base64
import binascii
import json
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

NONCE_BYTES = 12


class ClaveMaestraInvalida(RuntimeError):
    """Falta PAGOS_CLAVE_MAESTRA o no son 32 bytes en base64."""


class CredencialesIlegibles(RuntimeError):
    """El texto cifrado no corresponde a esta clave o a esta pasarela."""


def leer_clave(valor: str | None = None) -> bytes:
    valor = settings.PAGOS_CLAVE_MAESTRA if valor is None else valor
    if not valor:
        raise ClaveMaestraInvalida("Falta PAGOS_CLAVE_MAESTRA: sin ella no se pueden guardar credenciales de pasarelas")
    try:
        clave = base64.b64decode(valor, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ClaveMaestraInvalida("PAGOS_CLAVE_MAESTRA no es base64 válido") from exc
    if len(clave) != 32:
        raise ClaveMaestraInvalida("PAGOS_CLAVE_MAESTRA debe ser de 32 bytes (AES-256) en base64")
    return clave


def aad(condominio_id: int, pasarela_id: int) -> bytes:
    return f"condominio:{condominio_id}:pasarela:{pasarela_id}".encode()


def cifrar(datos: dict[str, str], dato_asociado: bytes, clave: bytes | None = None) -> bytes:
    nonce = os.urandom(NONCE_BYTES)
    texto = json.dumps(datos, separators=(",", ":"), sort_keys=True).encode()
    return nonce + AESGCM(clave or leer_clave()).encrypt(nonce, texto, dato_asociado)


def descifrar(cifrado: bytes, dato_asociado: bytes, clave: bytes | None = None) -> dict[str, str]:
    if not cifrado or len(cifrado) <= NONCE_BYTES:
        raise CredencialesIlegibles("Sin credenciales")
    try:
        texto = AESGCM(clave or leer_clave()).decrypt(cifrado[:NONCE_BYTES], cifrado[NONCE_BYTES:], dato_asociado)
    except InvalidTag as exc:
        raise CredencialesIlegibles("Las credenciales no corresponden a esta pasarela o a esta clave") from exc
    return json.loads(texto)
