"""Enlaces de acceso: invitación, recuperación, uso único, vencimiento y correo (spec acceso-por-enlace)."""
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.auditoria import AuditoriaLog
from app.models.enlace_acceso import EnlaceAcceso
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.services import correo

EMAIL_ADMIN = "hhernandez@santalaura.cl"     # admin_condominio de Santa Laura (seed)
EMAIL_SUPER = "mmoyainfo@gmail.com"
CLAVE_SEED = "admin123"


@pytest.fixture
def buzon(monkeypatch):
    """Resend falso: guarda cada correo enviado. Devuelve la lista."""
    enviados: list[dict] = []

    def responder(request: httpx.Request) -> httpx.Response:
        enviados.append(json.loads(request.content))
        return httpx.Response(200, json={"id": f"falso-{len(enviados)}"})

    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_prueba")
    monkeypatch.setattr(settings, "EMAIL_REMITENTE", "no-responder@ejemplo.cl")
    monkeypatch.setattr(correo, "transporte", httpx.MockTransport(responder))
    monkeypatch.setattr("app.api.v1.endpoints.usuarios.PAUSA_ENTRE_CORREOS", 0)
    return enviados


@pytest.fixture
def sin_correo(monkeypatch):
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")


async def _cabecera(c, email, clave=CLAVE_SEED):
    r = await c.post("/api/v1/auth/token", data={"username": email, "password": clave})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _pendiente(session, email="vecina@ejemplo.cl", condominio_id=None, telefono=None) -> Usuario:
    admin = (await session.execute(select(Usuario).where(Usuario.email == EMAIL_ADMIN))).scalar_one()
    rol = (await session.execute(select(Rol.id).where(Rol.nombre == "comunero"))).scalar_one()
    u = Usuario(nombre="Vecina Prueba", email=email, password_hash=None, rol_id=rol, telefono=telefono,
                condominio_id=condominio_id or admin.condominio_id)
    session.add(u)
    await session.flush()
    return u


async def _sin_otros_pendientes(session) -> None:
    """Las pruebas masivas no deben depender de las cuentas pendientes que haya en la base de desarrollo."""
    from sqlalchemy import update
    await session.execute(update(Usuario).where(Usuario.password_hash.is_(None)).values(password_hash="x"))
    await session.flush()


def _token(url: str) -> str:
    assert "#" in url
    return url.split("#", 1)[1]


async def test_invitacion_por_correo_y_creacion_de_clave(tx, buzon):
    c, session = tx
    u = await _pendiente(session)
    r = await c.post(f"/api/v1/usuarios/{u.id}/invitacion", headers=await _cabecera(c, EMAIL_ADMIN))
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["correo_enviado"] is True
    assert "/crear-clave#" in cuerpo["enlace"]
    assert len(buzon) == 1 and buzon[0]["to"] == ["vecina@ejemplo.cl"]
    assert cuerpo["enlace"] in buzon[0]["text"]
    assert buzon[0]["from"].startswith('"Santa Laura"') or buzon[0]["from"].startswith("Santa Laura")

    token = _token(cuerpo["enlace"])
    info = await c.post("/api/v1/auth/verificar-enlace", json={"token": token})
    assert info.json() == {"tipo": "invitacion", "nombre": "Vecina Prueba"}

    ok = await c.post("/api/v1/auth/establecer-clave", json={"token": token, "password": "mi-clave-propia"})
    assert ok.status_code == 204
    await _cabecera(c, "vecina@ejemplo.cl", "mi-clave-propia")

    otra = await c.post("/api/v1/auth/establecer-clave", json={"token": token, "password": "otra-clave-123"})
    assert otra.status_code == 410
    assert otra.json()["detail"] == "El enlace ya fue usado o venció"


async def test_invitacion_sin_correo_entrega_el_enlace(tx, sin_correo):
    c, session = tx
    u = await _pendiente(session)
    r = await c.post(f"/api/v1/usuarios/{u.id}/invitacion", headers=await _cabecera(c, EMAIL_ADMIN))
    assert r.status_code == 200
    assert r.json()["correo_enviado"] is False
    assert r.json()["motivo"] == "El envío de correos no está configurado"
    assert "/crear-clave#" in r.json()["enlace"]


async def test_invitacion_solo_enlace_no_envia_correo(tx, buzon):
    c, session = tx
    u = await _pendiente(session)
    r = await c.post(f"/api/v1/usuarios/{u.id}/invitacion", headers=await _cabecera(c, EMAIL_ADMIN),
                     params={"correo_electronico": "false"})
    assert r.status_code == 200
    assert r.json()["correo_enviado"] is False
    assert "/crear-clave#" in r.json()["enlace"]
    assert buzon == []   # no gasta envíos
    token = _token(r.json()["enlace"])
    assert (await c.post("/api/v1/auth/verificar-enlace", json={"token": token})).status_code == 200


async def test_reenviar_anula_la_invitacion_anterior(tx, buzon):
    c, session = tx
    u = await _pendiente(session)
    cab = await _cabecera(c, EMAIL_ADMIN)
    primera = _token((await c.post(f"/api/v1/usuarios/{u.id}/invitacion", headers=cab)).json()["enlace"])
    segunda = _token((await c.post(f"/api/v1/usuarios/{u.id}/invitacion", headers=cab)).json()["enlace"])
    assert (await c.post("/api/v1/auth/verificar-enlace", json={"token": primera})).status_code == 410
    assert (await c.post("/api/v1/auth/verificar-enlace", json={"token": segunda})).status_code == 200


async def test_no_se_invita_a_una_cuenta_activa_ni_de_otro_condominio(tx, buzon):
    c, session = tx
    cab = await _cabecera(c, EMAIL_ADMIN)
    activo = (await session.execute(select(Usuario).where(Usuario.email == EMAIL_SUPER))).scalar_one()
    r = await c.post(f"/api/v1/usuarios/{activo.id}/invitacion", headers=cab)
    assert r.status_code in (403, 409)   # el super admin no es del condominio: 403 antes que 409

    from app.models.condominio import Condominio
    otro = Condominio(nombre="Otro Condominio", rut_comunidad="55555555-5", plan_suscripcion="basico", activo=True)
    session.add(otro)
    await session.flush()
    ajeno = await _pendiente(session, email="ajeno@ejemplo.cl", condominio_id=otro.id)
    assert (await c.post(f"/api/v1/usuarios/{ajeno.id}/invitacion", headers=cab)).status_code == 403

    propio_activo = (await session.execute(select(Usuario).where(Usuario.email == EMAIL_ADMIN))).scalar_one()
    r = await c.post(f"/api/v1/usuarios/{propio_activo.id}/invitacion", headers=cab)
    assert r.status_code == 409
    assert "ya está activa" in r.json()["detail"]


async def test_invitacion_masiva(tx, buzon):
    c, session = tx
    await _sin_otros_pendientes(session)
    cab = await _cabecera(c, EMAIL_ADMIN)
    for i in range(3):
        await _pendiente(session, email=f"masiva{i}@ejemplo.cl")
    r = await c.post("/api/v1/usuarios/invitaciones", headers=cab, json={})
    assert r.status_code == 200, r.text
    assert r.json() == {"enviados": 3, "fallidos": 0, "pendientes": 0, "limite_alcanzado": False}
    assert sorted(m["to"][0] for m in buzon) == [f"masiva{i}@ejemplo.cl" for i in range(3)]
    assert "enlace" not in r.text


async def test_invitacion_masiva_sin_correo_no_emite_nada(tx, sin_correo):
    c, session = tx
    u = await _pendiente(session)
    r = await c.post("/api/v1/usuarios/invitaciones", headers=await _cabecera(c, EMAIL_ADMIN), json={})
    assert r.status_code == 503
    emitidos = (await session.execute(select(EnlaceAcceso).where(EnlaceAcceso.usuario_id == u.id))).scalars().all()
    assert emitidos == []


async def test_recuperar_responde_igual_exista_o_no_la_cuenta(tx, buzon):
    c, _ = tx
    existe = await c.post("/api/v1/auth/recuperar", json={"email": EMAIL_ADMIN.upper()})
    no_existe = await c.post("/api/v1/auth/recuperar", json={"email": "nadie@ejemplo.cl"})
    assert existe.status_code == no_existe.status_code == 202
    assert existe.json() == no_existe.json()
    assert [m["to"] for m in buzon] == [[EMAIL_ADMIN]]
    assert "/restablecer-clave#" in buzon[0]["text"]


async def test_recuperacion_vencida_no_sirve(tx, buzon):
    c, session = tx
    await c.post("/api/v1/auth/recuperar", json={"email": EMAIL_ADMIN})
    token = buzon[0]["text"].split("#", 1)[1].split()[0]
    enlace = (await session.execute(select(EnlaceAcceso).order_by(EnlaceAcceso.id.desc()))).scalars().first()
    enlace.expira_en = datetime.now(timezone.utc) - timedelta(minutes=1)
    await session.flush()
    r = await c.post("/api/v1/auth/establecer-clave", json={"token": token, "password": "clave-nueva-123"})
    assert r.status_code == 410


async def test_clave_debil_no_consume_el_enlace(tx, buzon):
    c, session = tx
    u = await _pendiente(session)
    token = _token((await c.post(f"/api/v1/usuarios/{u.id}/invitacion",
                                 headers=await _cabecera(c, EMAIL_ADMIN))).json()["enlace"])
    debil = await c.post("/api/v1/auth/establecer-clave", json={"token": token, "password": "admin123"})
    assert debil.status_code == 422
    assert (await c.post("/api/v1/auth/verificar-enlace", json={"token": token})).status_code == 200


async def test_cambiar_mi_clave(tx):
    c, _ = tx
    cab = await _cabecera(c, EMAIL_ADMIN)
    mal = await c.post("/api/v1/auth/cambiar-clave", headers=cab, json={"actual": "otra", "nueva": "clave-nueva-123"})
    assert mal.status_code == 400
    assert mal.json()["detail"] == "La clave actual no es correcta"

    r = await c.post("/api/v1/auth/cambiar-clave", headers=cab, json={"actual": CLAVE_SEED, "nueva": "clave-nueva-123"})
    assert r.status_code == 200
    nuevo = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert (await c.get("/api/v1/auth/me", headers=nuevo)).status_code == 200
    await _cabecera(c, EMAIL_ADMIN, "clave-nueva-123")


async def test_ni_el_token_ni_la_clave_quedan_en_la_auditoria(tx, buzon):
    c, session = tx
    u = await _pendiente(session)
    enlace = (await c.post(f"/api/v1/usuarios/{u.id}/invitacion", headers=await _cabecera(c, EMAIL_ADMIN))).json()["enlace"]
    token = _token(enlace)
    await c.post("/api/v1/auth/establecer-clave", json={"token": token, "password": "clave-secreta-123"})
    detalles = json.dumps([a.detalles for a in (await session.execute(select(AuditoriaLog))).scalars()])
    assert token not in detalles
    assert "clave-secreta-123" not in detalles
    hashes = [e.token_hash for e in (await session.execute(select(EnlaceAcceso))).scalars()]
    assert token not in hashes and all(len(h) == 64 for h in hashes)


async def test_correo_rechazado_por_resend(monkeypatch):
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_prueba")
    monkeypatch.setattr(settings, "EMAIL_REMITENTE", "no-responder@ejemplo.cl")
    monkeypatch.setattr(correo, "transporte", httpx.MockTransport(lambda req: httpx.Response(422, json={})))
    r = await correo.enviar("a@b.cl", "x", "x", "<p>x</p>", "Santa Laura")
    assert r.ok is False and "rechazó la dirección" in r.motivo


async def test_invitacion_masiva_se_detiene_en_el_limite(tx, buzon, monkeypatch):
    c, session = tx
    await _sin_otros_pendientes(session)
    for i in range(4):
        await _pendiente(session, email=f"limite{i}@ejemplo.cl")
    llamadas = []

    def responder(request):
        llamadas.append(1)
        return httpx.Response(200 if len(llamadas) <= 2 else 429, json={"id": "x"})

    monkeypatch.setattr(correo, "transporte", httpx.MockTransport(responder))
    r = await c.post("/api/v1/usuarios/invitaciones", headers=await _cabecera(c, EMAIL_ADMIN), json={})
    assert r.json() == {"enviados": 2, "fallidos": 1, "pendientes": 1, "limite_alcanzado": True}
    assert len(llamadas) == 3   # no sigue intentando después del 429


def test_plantilla_escapa_el_nombre():
    _, texto, html = correo.invitacion("<b>Ana</b>", "Santa Laura", "https://p.cl/crear-clave#abc")
    assert "<b>Ana</b>" not in html and "&lt;b&gt;Ana&lt;/b&gt;" in html
    assert "https://p.cl/crear-clave#abc" in texto
