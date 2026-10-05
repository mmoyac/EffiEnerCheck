"""Landing pública: contrato, resolución por dominio y contenido (spec sitio-publico)."""
import json

import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.sitio import ArchivoSitio, SitioPublico
from app.services.sitio import CONTENIDO_DIR, cargar_contenidos
from tests.test_modulos import SANTA_LAURA, _condominio, _super

MINIMO = {
    "condominio": {"nombre": "X", "descripcion_corta": "Y"},
    "portada": {"titulo": "Hola"},
    "contacto": {},
}


# ---------------------------------------------------------------------------
# Contrato
# ---------------------------------------------------------------------------

def test_contrato_minimo_es_valido():
    assert SitioPublico.model_validate(MINIMO).portada.cta_texto == "Acceso propietarios"


@pytest.mark.parametrize("cambio", [
    {"portada": None},                                                         # sin portada
    {"espacios": [{"nombre": "A", "descripcion": "B", "icono": "helipuerto"}]},  # ícono fuera de la lista
    {"portada": {"titulo": "<b>Hola</b>"}},                                     # HTML
    {"portada": {"titulo": "Hola", "imagen_url": "http://inseguro.cl/a.jpg"}},  # URL sin https
    {"campo_inventado": 1},                                                     # campo desconocido
])
def test_contrato_rechaza(cambio):
    with pytest.raises(ValidationError):
        SitioPublico.model_validate({**MINIMO, **cambio})


def test_archivos_de_contenido_cumplen_el_esquema():
    # extra="forbid": una clave del JSON que no exista en el schema hace fallar la carga
    for ruta in CONTENIDO_DIR.glob("*.json"):
        ArchivoSitio.model_validate(json.loads(ruta.read_text(encoding="utf-8")))
    assert cargar_contenidos()


def _marcadores(valor, ruta=""):
    if isinstance(valor, dict):
        for k, v in valor.items():
            yield from _marcadores(v, f"{ruta}.{k}")
    elif isinstance(valor, list):
        for i, v in enumerate(valor):
            yield from _marcadores(v, f"{ruta}[{i}]")
    elif isinstance(valor, str) and "[POR CONFIRMAR]" in valor:
        yield ruta


@pytest.mark.parametrize("ruta", sorted(CONTENIDO_DIR.glob("*.json")), ids=lambda r: r.name)
def test_contenido_sin_marcadores_pendientes(ruta):
    """Informativo: lista lo que falta confirmar con la administración (pytest -rx)."""
    pendientes = list(_marcadores(json.loads(ruta.read_text(encoding="utf-8"))))
    if pendientes:
        pytest.xfail(f"{len(pendientes)} dato(s) [POR CONFIRMAR]: {', '.join(pendientes)}")


# ---------------------------------------------------------------------------
# Endpoint y resolución por dominio
# ---------------------------------------------------------------------------

async def _registrar_dominio(client, session, dominio: str, condominio_id: int = SANTA_LAURA):
    r = await client.patch(
        f"/api/v1/condominios/{condominio_id}", json={"dominios_sitio": [dominio]}, headers=await _super(session)
    )
    assert r.status_code == 200


async def test_dominio_con_y_sin_www(tx, monkeypatch):
    client, session = tx
    monkeypatch.setattr(settings, "SITIO_POR_DEFECTO", "")
    await _registrar_dominio(client, session, "condominio-prueba.cl")

    for host in ("condominio-prueba.cl", "WWW.condominio-prueba.cl:443"):
        r = await client.get("/api/v1/sitio", headers={"Host": host})
        assert r.status_code == 200, host
        assert r.json()["condominio"]["nombre"] == "Condominio Santa Laura"
    assert r.headers["cache-control"] == "public, max-age=300"


async def test_host_reenviado_por_el_proxy(tx, monkeypatch):
    client, session = tx
    monkeypatch.setattr(settings, "SITIO_POR_DEFECTO", "")
    await _registrar_dominio(client, session, "condominio-prueba.cl")
    r = await client.get("/api/v1/sitio", headers={"Host": "backend:8000", "X-Forwarded-Host": "www.condominio-prueba.cl"})
    assert r.status_code == 200


async def test_dominio_desconocido_sin_defecto(tx, monkeypatch):
    client, _ = tx
    monkeypatch.setattr(settings, "SITIO_POR_DEFECTO", "")
    r = await client.get("/api/v1/sitio", headers={"Host": "desconocido.cl"})
    assert r.status_code == 404
    assert r.json()["detail"] == "Sitio no encontrado"


async def test_sitio_por_defecto(tx, monkeypatch):
    client, _ = tx
    monkeypatch.setattr(settings, "SITIO_POR_DEFECTO", "1-9")
    assert (await client.get("/api/v1/sitio", headers={"Host": "localhost:3001"})).status_code == 200


async def test_condominio_sin_modulo_sitio(tx, monkeypatch):
    client, session = tx
    monkeypatch.setattr(settings, "SITIO_POR_DEFECTO", "")
    await _registrar_dominio(client, session, "condominio-prueba.cl")
    await client.patch(f"/api/v1/condominios/{SANTA_LAURA}", json={"modulos": ["portal", "energia", "rifas"]},
                       headers=await _super(session))
    assert (await client.get("/api/v1/sitio", headers={"Host": "condominio-prueba.cl"})).status_code == 404


async def test_portal_url_solo_con_portal(tx, monkeypatch):
    client, session = tx
    monkeypatch.setattr(settings, "SITIO_POR_DEFECTO", "")
    sa = await _super(session)
    await _registrar_dominio(client, session, "condominio-prueba.cl")
    await client.patch(f"/api/v1/condominios/{SANTA_LAURA}",
                       json={"portal_url": "https://portal.condominio-prueba.cl", "color_primario": "#1E5AA8"}, headers=sa)

    body = (await client.get("/api/v1/sitio", headers={"Host": "condominio-prueba.cl"})).json()
    assert body["portal_url"] == "https://portal.condominio-prueba.cl"
    assert body["condominio"]["color_primario"] == "#1E5AA8"
    # Nunca expone la configuración interna
    assert "rut_comunidad" not in json.dumps(body) and "dominios" not in json.dumps(body)

    await client.patch(f"/api/v1/condominios/{SANTA_LAURA}", json={"modulos": ["sitio"]}, headers=sa)
    body = (await client.get("/api/v1/sitio", headers={"Host": "condominio-prueba.cl"})).json()
    assert "portal_url" not in body


async def test_condominio_con_sitio_sin_archivo(tx, monkeypatch):
    client, session = tx
    monkeypatch.setattr(settings, "SITIO_POR_DEFECTO", "")
    c = await _condominio(session, ["sitio"])
    await _registrar_dominio(client, session, "sin-contenido.cl", c.id)
    assert (await client.get("/api/v1/sitio", headers={"Host": "sin-contenido.cl"})).status_code == 404
