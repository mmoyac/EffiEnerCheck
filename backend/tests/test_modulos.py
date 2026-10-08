"""
Plataforma por módulos y parametrización del condominio (specs modulos-plataforma,
gestion-condominios y control-acceso-multitenant). Todo corre dentro de la transacción del fixture
`tx`, que se revierte al final.
"""
import os

from sqlalchemy import func, select

from app.core.security import create_access_token, hash_password
from app.models.boleta import BoletaMaestra
from app.models.condominio import Condominio
from app.models.condominio_modulo import CondominioModulo
from app.models.rol import Rol
from app.models.usuario import Usuario

SANTA_LAURA = 1


async def _usuario(session, rol: str, condominio_id: int | None, clave: str | None = None) -> Usuario:
    rol_id = (await session.execute(select(Rol.id).where(Rol.nombre == rol))).scalar_one()
    u = Usuario(
        nombre=f"Prueba {rol}",
        email=f"prueba-{rol}-{condominio_id}-{os.urandom(3).hex()}@test.cl",
        password_hash=hash_password(clave) if clave else "x",
        rol_id=rol_id,
        condominio_id=condominio_id,
    )
    session.add(u)
    await session.flush()
    return u


def _auth(u: Usuario, rol: str) -> dict[str, str]:
    token = create_access_token(user_id=u.id, rol=rol, condominio_id=u.condominio_id)
    return {"Authorization": f"Bearer {token}"}


async def _condominio(session, modulos: list[str]) -> Condominio:
    c = Condominio(
        nombre="Condominio de prueba",
        rut_comunidad=f"prueba-{os.urandom(4).hex()}",
        plan_suscripcion="basico",
        activo=True,
        modulos=[CondominioModulo(modulo=m) for m in modulos],
    )
    session.add(c)
    await session.flush()
    return c


async def _super(session) -> dict[str, str]:
    return _auth(await _usuario(session, "super_admin", None), "super_admin")


# ---------------------------------------------------------------------------
# Guardas
# ---------------------------------------------------------------------------

async def test_endpoint_de_modulo_no_habilitado(tx):
    client, session = tx
    c = await _condominio(session, ["portal", "rifas"])
    admin = _auth(await _usuario(session, "admin_condominio", c.id), "admin_condominio")

    r = await client.get("/api/v1/boletas/", headers=admin)
    assert r.status_code == 403
    assert r.json()["detail"] == "El módulo energia no está habilitado para este condominio"

    # El núcleo sigue disponible
    assert (await client.get("/api/v1/parcelas/", headers=admin)).status_code == 200


async def test_super_admin_no_es_bloqueado_por_modulos(tx):
    client, session = tx
    assert (await client.get("/api/v1/boletas/", headers=await _super(session))).status_code == 200


async def test_porteria_sin_rifas(tx):
    client, session = tx
    c = await _condominio(session, ["portal", "energia"])
    porteria = _auth(await _usuario(session, "porteria", c.id), "porteria")
    r = await client.get("/api/v1/rifas/", headers=porteria)
    assert r.status_code == 403
    assert r.json()["detail"] == "El módulo rifas no está habilitado para este condominio"


async def test_sin_portal_no_inicia_sesion(tx):
    client, session = tx
    c = await _condominio(session, ["sitio"])
    u = await _usuario(session, "admin_condominio", c.id, clave="clave-de-prueba-123")

    r = await client.post("/api/v1/auth/token", data={"username": u.email, "password": "clave-de-prueba-123"})
    assert r.status_code == 403
    assert r.json()["detail"] == "Tu condominio no tiene contratado el portal de administración"


async def test_quitar_portal_corta_sesion_abierta(tx):
    client, session = tx
    c = await _condominio(session, ["portal", "energia"])
    admin = _auth(await _usuario(session, "admin_condominio", c.id), "admin_condominio")
    assert (await client.get("/api/v1/auth/me", headers=admin)).status_code == 200

    r = await client.patch(f"/api/v1/condominios/{c.id}", json={"modulos": ["sitio"]}, headers=await _super(session))
    assert r.status_code == 200
    assert (await client.get("/api/v1/auth/me", headers=admin)).status_code == 403


# ---------------------------------------------------------------------------
# Menú y sesión
# ---------------------------------------------------------------------------

async def test_menu_sin_modulo_rifas(tx):
    client, session = tx
    c = await _condominio(session, ["portal", "energia"])
    admin = _auth(await _usuario(session, "admin_condominio", c.id), "admin_condominio")

    menu = (await client.get("/api/v1/menus/me", headers=admin)).json()
    paths = {m["path"] for m in menu}
    assert "/rifas" not in paths
    assert {"/usuarios", "/boletas"} <= paths
    assert next(m for m in menu if m["path"] == "/boletas")["modulo"] == "energia"


async def test_auth_me_informa_modulos_y_marca(tx):
    client, session = tx
    c = await _condominio(session, ["portal", "energia", "rifas"])
    c.color_primario = "#1E5AA8"
    comunero = _auth(await _usuario(session, "comunero", c.id), "comunero")

    me = (await client.get("/api/v1/auth/me", headers=comunero)).json()
    assert me["modulos"] == ["portal", "energia", "rifas"]
    assert me["condominio"] == {"id": c.id, "nombre": c.nombre, "logo_url": None, "color_primario": "#1E5AA8"}

    me_super = (await client.get("/api/v1/auth/me", headers=await _super(session))).json()
    assert me_super["modulos"] == ["sitio", "portal", "energia", "rifas"]
    assert me_super["condominio"] is None


# ---------------------------------------------------------------------------
# Parametrización del condominio
# ---------------------------------------------------------------------------

def _alta(**extra):
    return {"nombre": "Nuevo", "rut_comunidad": f"alta-{os.urandom(4).hex()}", "plan_suscripcion": "pro", **extra}


async def test_alta_solo_administracion(tx):
    client, session = tx
    r = await client.post(
        "/api/v1/condominios/",
        json=_alta(modulos=["energia", "portal"], portal_url="https://portal.ejemplo.cl"),
        headers=await _super(session),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["modulos"] == ["portal", "energia"]
    assert body["portal_url"] == "https://portal.ejemplo.cl"
    assert body["dominios_sitio"] == []


async def test_alta_sin_modulos_los_habilita_todos(tx):
    client, session = tx
    r = await client.post("/api/v1/condominios/", json=_alta(), headers=await _super(session))
    assert r.json()["modulos"] == ["sitio", "portal", "energia", "rifas"]


async def test_validaciones_de_parametrizacion(tx):
    client, session = tx
    sa = await _super(session)
    casos = [
        {"modulos": ["energia"]},              # energia sin portal
        {"modulos": ["portal", "helipuerto"]},  # módulo desconocido
        {"portal_url": "http://portal.ejemplo.cl"},
        {"color_primario": "azul"},
        {"color_primario": "#12345"},
        {"dominios_sitio": ["no es un dominio"]},
    ]
    for caso in casos:
        r = await client.patch(f"/api/v1/condominios/{SANTA_LAURA}", json=caso, headers=sa)
        assert r.status_code == 422, caso
    r = await client.patch(f"/api/v1/condominios/{SANTA_LAURA}", json={"modulos": ["energia"]}, headers=sa)
    assert "Los módulos energia y rifas requieren el módulo portal" in r.text


async def test_patch_parcial_no_toca_parametrizacion(tx):
    client, session = tx
    sa = await _super(session)
    antes = (await client.get(f"/api/v1/condominios/{SANTA_LAURA}", headers=sa)).json()
    r = await client.patch(f"/api/v1/condominios/{SANTA_LAURA}", json={"direccion": "Camino de prueba 123"}, headers=sa)
    despues = r.json()
    assert despues["direccion"] == "Camino de prueba 123"
    for campo in ("modulos", "portal_url", "dominios_sitio", "color_primario", "logo_url"):
        assert despues[campo] == antes[campo]


async def test_color_se_normaliza_y_se_puede_quitar(tx):
    client, session = tx
    sa = await _super(session)
    r = await client.patch(f"/api/v1/condominios/{SANTA_LAURA}", json={"color_primario": "#1e5aa8"}, headers=sa)
    assert r.json()["color_primario"] == "#1E5AA8"
    r = await client.patch(f"/api/v1/condominios/{SANTA_LAURA}", json={"color_primario": None}, headers=sa)
    assert r.json()["color_primario"] is None


async def test_dominio_repetido_entre_condominios(tx):
    client, session = tx
    sa = await _super(session)
    otro = await _condominio(session, ["sitio"])
    r = await client.patch(
        f"/api/v1/condominios/{SANTA_LAURA}", json={"dominios_sitio": ["WWW.Ejemplo-Prueba.cl"]}, headers=sa
    )
    assert r.json()["dominios_sitio"] == ["ejemplo-prueba.cl"]
    r = await client.patch(f"/api/v1/condominios/{otro.id}", json={"dominios_sitio": ["ejemplo-prueba.cl"]}, headers=sa)
    assert r.status_code == 409
    assert r.json()["detail"] == "El dominio ya está asignado a otro condominio"


async def test_quitar_y_poner_energia_conserva_boletas(tx):
    client, session = tx
    sa = await _super(session)
    contar = select(func.count()).select_from(BoletaMaestra).where(BoletaMaestra.condominio_id == SANTA_LAURA)
    antes = (await session.execute(contar)).scalar_one()

    await client.patch(f"/api/v1/condominios/{SANTA_LAURA}", json={"modulos": ["sitio", "portal", "rifas"]}, headers=sa)
    r = await client.patch(
        f"/api/v1/condominios/{SANTA_LAURA}", json={"modulos": ["sitio", "portal", "energia", "rifas"]}, headers=sa
    )
    assert r.json()["modulos"] == ["sitio", "portal", "energia", "rifas"]
    assert (await session.execute(contar)).scalar_one() == antes


async def test_cambio_de_modulos_queda_en_auditoria(tx):
    from app.models.auditoria import AuditoriaLog

    client, session = tx
    await client.patch(f"/api/v1/condominios/{SANTA_LAURA}", json={"modulos": ["sitio", "portal", "energia"]},
                       headers=await _super(session))
    log = (await session.execute(
        select(AuditoriaLog).where(AuditoriaLog.accion == "UPDATE_CONDOMINIO").order_by(AuditoriaLog.id.desc())
    )).scalars().first()
    assert log.detalles["antes"]["modulos"] == ["sitio", "portal", "energia", "rifas"]
    assert log.detalles["despues"]["modulos"] == ["sitio", "portal", "energia"]


async def test_admin_no_modifica_parametrizacion(tx):
    client, session = tx
    admin = _auth(await _usuario(session, "admin_condominio", SANTA_LAURA), "admin_condominio")
    r = await client.patch(f"/api/v1/condominios/{SANTA_LAURA}", json={"modulos": ["portal"]}, headers=admin)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Logo
# ---------------------------------------------------------------------------

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 200


def _ruta(url: str) -> str:
    return os.path.join("/app/uploads", url.removeprefix("/uploads/"))


async def test_logo_subir_reemplazar_y_quitar(tx):
    client, session = tx
    sa = await _super(session)
    c = await _condominio(session, ["sitio", "portal"])

    r = await client.post(f"/api/v1/condominios/{c.id}/logo", files={"archivo": ("logo.png", PNG, "image/png")}, headers=sa)
    assert r.status_code == 200
    primero = r.json()["logo_url"]
    assert primero.startswith(f"/uploads/condominios/{c.id}/logo-") and primero.endswith(".png")
    assert os.path.isfile(_ruta(primero))

    r = await client.post(f"/api/v1/condominios/{c.id}/logo", files={"archivo": ("x.bin", WEBP, "application/octet-stream")}, headers=sa)
    segundo = r.json()["logo_url"]
    assert segundo != primero and segundo.endswith(".webp")
    assert not os.path.exists(_ruta(primero))

    r = await client.delete(f"/api/v1/condominios/{c.id}/logo", headers=sa)
    assert r.json()["logo_url"] is None
    assert not os.path.exists(_ruta(segundo))


async def test_logo_rechaza_formatos_y_tamano(tx):
    client, session = tx
    sa = await _super(session)
    c = await _condominio(session, ["sitio"])
    url = f"/api/v1/condominios/{c.id}/logo"

    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    assert (await client.post(url, files={"archivo": ("l.svg", svg, "image/svg+xml")}, headers=sa)).status_code == 422
    falso = b"no soy un png" * 10
    assert (await client.post(url, files={"archivo": ("l.png", falso, "image/png")}, headers=sa)).status_code == 422
    grande = PNG + b"\x00" * (1024 * 1024)
    assert (await client.post(url, files={"archivo": ("l.png", grande, "image/png")}, headers=sa)).status_code == 413

    admin = _auth(await _usuario(session, "admin_condominio", c.id), "admin_condominio")
    assert (await client.post(url, files={"archivo": ("l.png", PNG, "image/png")}, headers=admin)).status_code == 403
