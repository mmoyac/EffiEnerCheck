"""Cifrado de las credenciales de las pasarelas y su clave maestra (cambio pasarelas-pago)."""
import base64
import os

import pytest

from app import arranque
from app.core.config import settings
from app.db.rotar_clave_pagos import rotar
from app.models.pago import PasarelaPago
from app.services.pagos.cifrado import (
    ClaveMaestraInvalida,
    CredencialesIlegibles,
    aad,
    cifrar,
    descifrar,
    leer_clave,
)

CREDENCIALES = {"api_key": "AAAA-BBBB", "secret_key": "secreto-de-prueba"}


def _clave() -> bytes:
    return os.urandom(32)


def test_ida_y_vuelta():
    clave = _clave()
    cifrado = cifrar(CREDENCIALES, aad(1, 2), clave)
    assert b"secreto-de-prueba" not in cifrado
    assert descifrar(cifrado, aad(1, 2), clave) == CREDENCIALES


def test_otra_pasarela_no_descifra():
    clave = _clave()
    cifrado = cifrar(CREDENCIALES, aad(1, 2), clave)
    with pytest.raises(CredencialesIlegibles):
        descifrar(cifrado, aad(1, 3), clave)
    with pytest.raises(CredencialesIlegibles):
        descifrar(cifrado, aad(2, 2), clave)


def test_otra_clave_no_descifra():
    cifrado = cifrar(CREDENCIALES, aad(1, 2), _clave())
    with pytest.raises(CredencialesIlegibles):
        descifrar(cifrado, aad(1, 2), _clave())


@pytest.mark.parametrize("valor", ["", "no-es-base64!", base64.b64encode(b"corta").decode()])
def test_clave_maestra_invalida(valor):
    with pytest.raises(ClaveMaestraInvalida):
        leer_clave(valor)


async def test_rotar_conserva_los_valores(db):
    actual, nueva = _clave(), _clave()
    p = PasarelaPago(condominio_id=1, proveedor="flow", nombre_visible="Flow", ambiente="integracion")
    db.add(p)
    await db.flush()
    p.credenciales_cifradas = cifrar(CREDENCIALES, aad(1, p.id), actual)
    await db.flush()

    assert await rotar(db, actual, nueva, solo_ids=[p.id]) == 1
    assert descifrar(p.credenciales_cifradas, aad(1, p.id), nueva) == CREDENCIALES
    with pytest.raises(CredencialesIlegibles):
        descifrar(p.credenciales_cifradas, aad(1, p.id), actual)


def test_produccion_y_la_clave_maestra(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", "x" * 40)
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "clave")
    monkeypatch.setattr(settings, "URL_PUBLICA_PAGOS", "")

    # Sin clave: arranca (los pagos en línea son opcionales), pero no se pueden guardar credenciales
    monkeypatch.setattr(settings, "PAGOS_CLAVE_MAESTRA", "")
    arranque.validar_configuracion()
    with pytest.raises(ClaveMaestraInvalida):
        cifrar(CREDENCIALES, aad(1, 2))

    # Mal escrita: no arranca
    monkeypatch.setattr(settings, "PAGOS_CLAVE_MAESTRA", "no-es-una-clave")
    with pytest.raises(arranque.ArranqueError, match="PAGOS_CLAVE_MAESTRA"):
        arranque.validar_configuracion()

    monkeypatch.setattr(settings, "PAGOS_CLAVE_MAESTRA", base64.b64encode(_clave()).decode())
    arranque.validar_configuracion()

    monkeypatch.setattr(settings, "URL_PUBLICA_PAGOS", "https://tunel.trycloudflare.com")
    with pytest.raises(arranque.ArranqueError, match="URL_PUBLICA_PAGOS"):
        arranque.validar_configuracion()
