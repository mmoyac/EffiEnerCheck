"""Política de claves, cuentas pendientes y cierre de sesiones al cambiar la clave."""
import time

import jwt
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import validar_clave, verify_password
from app.models.usuario import Usuario

EMAIL_ADMIN = "hhernandez@santalaura.cl"
CLAVE_SEED = "admin123"


async def _token(c, email, clave):
    r = await c.post("/api/v1/auth/token", data={"username": email, "password": clave})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _rol_comunero(session) -> int:
    from app.models.rol import Rol
    return (await session.execute(select(Rol.id).where(Rol.nombre == "comunero"))).scalar_one()


@pytest.mark.parametrize("clave", ["corta", "123456789", "admin123"])
def test_politica_rechaza_claves_debiles(clave):
    with pytest.raises(ValueError):
        validar_clave(clave)


def test_politica_acepta_diez_caracteres():
    assert validar_clave("diez-carac") == "diez-carac"


def test_cuenta_pendiente_no_verifica_ninguna_clave():
    assert verify_password("cualquier-cosa", None) is False


async def test_alta_sin_clave_queda_pendiente_y_no_inicia_sesion(tx):
    c, session = tx
    admin = await _token(c, EMAIL_ADMIN, CLAVE_SEED)
    r = await c.post("/api/v1/usuarios/", headers=admin, json={
        "nombre": "Vecina Pendiente", "email": "pendiente@ejemplo.cl", "rol_id": await _rol_comunero(session)})
    assert r.status_code == 201, r.text
    assert r.json()["estado"] == "pendiente"
    assert "password_hash" not in r.json()

    login = await c.post("/api/v1/auth/token", data={"username": "pendiente@ejemplo.cl", "password": "lo-que-sea-123"})
    assert login.status_code == 401
    assert login.json()["detail"] == "Email o contraseña incorrectos"

    lista = await c.get("/api/v1/usuarios/", headers=admin)
    estados = {u["email"]: u["estado"] for u in lista.json()}
    assert estados["pendiente@ejemplo.cl"] == "pendiente"
    assert estados[EMAIL_ADMIN] == "activa"


async def test_alta_con_clave_debil_se_rechaza(tx):
    c, session = tx
    admin = await _token(c, EMAIL_ADMIN, CLAVE_SEED)
    r = await c.post("/api/v1/usuarios/", headers=admin, json={
        "nombre": "X", "email": "debil@ejemplo.cl", "password": "admin123", "rol_id": await _rol_comunero(session)})
    assert r.status_code == 422


async def test_me_informa_cuenta_activa(tx):
    c, _ = tx
    me = await c.get("/api/v1/auth/me", headers=await _token(c, EMAIL_ADMIN, CLAVE_SEED))
    assert me.status_code == 200
    assert me.json()["estado"] == "activa"


async def test_cambio_de_clave_por_admin_cierra_las_sesiones_anteriores(tx):
    c, session = tx
    admin = await _token(c, EMAIL_ADMIN, CLAVE_SEED)
    r = await c.post("/api/v1/usuarios/", headers=admin, json={
        "nombre": "Vecino", "email": "sesiones@ejemplo.cl", "password": "clave-inicial-1",
        "rol_id": await _rol_comunero(session)})
    usuario = (await session.execute(select(Usuario).where(Usuario.email == "sesiones@ejemplo.cl"))).scalar_one()
    # La cuenta ya tenía su clave desde hace tiempo (crearla con clave marca clave_cambiada_en ahora)
    usuario.clave_cambiada_en = None
    await session.flush()
    # Token emitido "antes": iat 10 s atrás (el cambio y un login nuevo pueden caer en el mismo segundo)
    ahora = int(time.time())
    viejo = jwt.encode({"sub": str(usuario.id), "rol": "comunero", "condominio_id": usuario.condominio_id,
                        "iat": ahora - 10, "exp": ahora + 600}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    cabecera_vieja = {"Authorization": f"Bearer {viejo}"}
    assert (await c.get("/api/v1/auth/me", headers=cabecera_vieja)).status_code == 200

    r = await c.patch(f"/api/v1/usuarios/{usuario.id}", headers=admin, json={"password": "clave-nueva-123"})
    assert r.status_code == 200, r.text

    assert (await c.get("/api/v1/auth/me", headers=cabecera_vieja)).status_code == 401
    nuevo = await _token(c, "sesiones@ejemplo.cl", "clave-nueva-123")
    assert (await c.get("/api/v1/auth/me", headers=nuevo)).status_code == 200


async def test_arranque_ignora_cuentas_pendientes(db):
    from app.arranque import usuarios_con_clave_conocida
    db.add(Usuario(nombre="Pendiente", email="arranque-pendiente@ejemplo.cl", password_hash=None,
                   rol_id=await _rol_comunero(db)))
    await db.flush()
    expuestos = await usuarios_con_clave_conocida(db)
    assert "arranque-pendiente@ejemplo.cl" not in expuestos
