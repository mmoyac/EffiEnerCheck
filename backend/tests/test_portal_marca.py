"""Marca y manifiesto de la app por dominio del portal (cambio app-instalable-por-condominio)."""
from sqlalchemy import select

from app.models.condominio import Condominio


async def _santa_laura(session) -> Condominio:
    c = (await session.execute(select(Condominio).where(Condominio.rut_comunidad == "1-9"))).scalar_one()
    c.portal_url = "https://portal.prueba-marca.cl"
    c.color_primario = "#22C55E"
    await session.flush()
    return c


async def test_marca_y_manifiesto_del_condominio(tx):
    c, session = tx
    cond = await _santa_laura(session)
    r = await c.get("/api/v1/portal/marca", headers={"X-Forwarded-Host": "portal.prueba-marca.cl"})
    assert r.json() == {"nombre": cond.nombre, "nombre_completo": f"{cond.nombre} · EFFIComunidad",
                        "color": "#22C55E", "condominio": True}

    m = await c.get("/api/v1/portal/manifest", headers={"X-Forwarded-Host": "portal.prueba-marca.cl"})
    assert m.headers["content-type"].startswith("application/manifest+json")
    datos = m.json()
    assert datos["short_name"] == cond.nombre
    assert datos["theme_color"] == "#22C55E"
    assert {i["sizes"] for i in datos["icons"]} == {"192x192", "512x512"}
    assert any(i["purpose"] == "maskable" for i in datos["icons"])
    assert "rut" not in m.text.lower() and "dominio" not in m.text.lower()


async def test_cambio_de_nombre_se_ve_sin_desplegar(tx):
    c, session = tx
    cond = await _santa_laura(session)
    cond.nombre = "SL Nuevo Nombre"
    await session.flush()
    r = await c.get("/api/v1/portal/marca", headers={"X-Forwarded-Host": "portal.prueba-marca.cl"})
    assert r.json()["nombre"] == "SL Nuevo Nombre"


async def test_dominio_desconocido_usa_la_plataforma(tx):
    c, _ = tx
    r = await c.get("/api/v1/portal/marca", headers={"X-Forwarded-Host": "otro.ejemplo.cl"})
    assert r.json()["nombre"] == "EFFIComunidad" and r.json()["condominio"] is False
