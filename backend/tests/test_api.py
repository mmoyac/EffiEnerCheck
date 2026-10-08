"""Humo de la API: salud, login JWT y rechazo de tokens inválidos."""
import jwt

from app.core.config import settings

# Usuario de prueba del seed de desarrollo (app/db/seeds/usuarios.py)
EMAIL_ADMIN = "hhernandez@santalaura.cl"
CLAVE_SEED = "admin123"


async def test_health_consulta_la_base(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_login_y_me(client):
    r = await client.post("/api/v1/auth/token", data={"username": EMAIL_ADMIN, "password": CLAVE_SEED})
    assert r.status_code == 200
    token = r.json()["access_token"]

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL_ADMIN


async def test_login_con_clave_incorrecta(client):
    r = await client.post("/api/v1/auth/token", data={"username": EMAIL_ADMIN, "password": "otra-clave"})
    assert r.status_code == 401


async def test_token_firmado_con_otra_clave_es_rechazado(client):
    falso = jwt.encode({"sub": "1", "rol": "super_admin", "condominio_id": None}, "otra-clave-" * 4,
                       algorithm=settings.ALGORITHM)
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {falso}"})
    assert r.status_code == 401


async def test_comunero_ve_solo_sus_parcelas(client):
    """El rol 4 se llama `comunero` (antes `parcelero`) y conserva su restricción a sus parcelas."""
    r = await client.post("/api/v1/auth/token", data={"username": "mmoyainfo+parcela@gmail.com", "password": CLAVE_SEED})
    assert r.status_code == 200
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}

    me = (await client.get("/api/v1/auth/me", headers=h)).json()
    assert me["rol"]["nombre"] == "comunero"
    propias = {p["id"] for p in me["parcelas"]}
    assert propias

    parcelas = await client.get("/api/v1/parcelas/", headers=h)
    assert parcelas.status_code == 200
    assert {p["id"] for p in parcelas.json()} <= propias

    assert (await client.get("/api/v1/usuarios/", headers=h)).status_code == 403
