"""
Aceptación de punta a punta del módulo de Energía (spec proceso-energia, escenario «Recorrido completo»).

Un condominio sin boletas recorre: lectura inicial por Excel → primera boleta (totales a mano, sin imagen)
→ toma del lector (sincronización sin conexión, con foto) → cálculo cuadrado al peso → cierre →
publicación → consulta del comunero → segundo período. Todo dentro de la transacción del fixture `tx`.
"""
import io
import os
from datetime import date, datetime, timezone

import pytest
from openpyxl import Workbook
from sqlalchemy import insert, select

from app.core.security import create_access_token
from app.models.condominio import Condominio
from app.models.condominio_modulo import CondominioModulo
from app.models.parcela import Parcela
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.models.usuario_parcela import usuario_parcelas
from app.services import fotos_lectura

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200
EMISION = 119_000


@pytest.fixture(autouse=True)
def fotos_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(fotos_lectura, "FOTOS_DIR", str(tmp_path))


async def _usuario(session, rol: str, condominio_id: int) -> tuple[Usuario, dict]:
    rol_id = (await session.execute(select(Rol.id).where(Rol.nombre == rol))).scalar_one()
    u = Usuario(nombre=f"Prueba {rol}", email=f"proceso-{rol}-{os.urandom(3).hex()}@test.cl", password_hash="x",
                rol_id=rol_id, condominio_id=condominio_id)
    session.add(u)
    await session.flush()
    token = create_access_token(user_id=u.id, rol=rol, condominio_id=condominio_id)
    return u, {"Authorization": f"Bearer {token}"}


def _planilla(filas) -> bytes:
    libro = Workbook()
    libro.active.append(["Parcela", "Propietario", "Lectura inicial"])
    for fila in filas:
        libro.active.append(list(fila))
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


async def test_recorrido_completo(tx):
    c, session = tx
    # Condominio nuevo, con portal y energía, tres parcelas activas
    condominio = Condominio(nombre="Condominio Proceso", rut_comunidad=f"proceso-{os.urandom(4).hex()}",
                            plan_suscripcion="basico", activo=True,
                            modulos=[CondominioModulo(modulo="portal"), CondominioModulo(modulo="energia")])
    session.add(condominio)
    await session.flush()
    parcelas = [Parcela(condominio_id=condominio.id, numero_parcela=n, activa=True) for n in ("1", "2", "3")]
    session.add_all(parcelas)
    await session.flush()
    _, admin = await _usuario(session, "admin_condominio", condominio.id)
    _, lector = await _usuario(session, "lector", condominio.id)
    comunero, cab_comunero = await _usuario(session, "comunero", condominio.id)
    await session.execute(insert(usuario_parcelas).values(usuario_id=comunero.id, parcela_id=parcelas[1].id))
    await session.flush()

    # ---- Etapa 0: lectura inicial por Excel (onboarding) ---------------------------------------------
    r = await c.post("/api/v1/boletas/lectura-inicial", headers=admin, json={"periodo_mes": "2099-09-01"})
    assert r.status_code == 201, r.text
    inicial = r.json()
    r = await c.post(f"/api/v1/boletas/{inicial['id']}/lecturas-iniciales/importar", headers=admin,
                     params={"aplicar": "true"},
                     files={"archivo": ("inicial.xlsx", _planilla([("1", "", 1000), ("2", "", 2000), ("3", "", 3000)]),
                                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert r.status_code == 200, r.text
    assert r.json()["aplicadas"] == 3
    assert (await c.post(f"/api/v1/boletas/{inicial['id']}/cerrar-lecturas", headers=admin)).status_code == 200

    # ---- Etapa 1: primera boleta, hereda la lectura inicial; totales a mano, sin imagen -----------------
    r = await c.post("/api/v1/boletas/", headers=admin, json={})
    assert r.status_code == 201, r.text
    octubre = r.json()
    assert octubre["periodo_mes"] == "2099-10-01" and octubre["url_imagen_boleta"] is None
    lecturas = {l["parcela_id"]: l for l in
                (await c.get("/api/v1/lecturas/", headers=admin, params={"boleta_id": octubre["id"]})).json()}
    assert [lecturas[p.id]["lectura_anterior"] for p in parcelas] == [1000, 2000, 3000]

    r = await c.put(f"/api/v1/boletas/{octubre['id']}/detalles", headers=admin, json={
        "total_kwh_compania": 800, "monto_neto_electricidad_consumida": 100_000, "monto_total_emision": EMISION,
        "items_detalle": [
            {"descripcion": "Cargo fijo", "monto_neto_clp": 3_000, "tipo_calculo": "fijo"},
            {"descripcion": "Transporte de electricidad", "monto_neto_clp": 6_000, "tipo_calculo": "variable"},
            {"descripcion": "Interés por mora", "monto_neto_clp": 100, "tipo_calculo": "informativo"},
        ]})
    assert r.status_code == 200, r.text
    # La planilla es solo para el onboarding
    r = await c.post(f"/api/v1/boletas/{octubre['id']}/lecturas-iniciales/importar", headers=admin,
                     files={"archivo": ("x.xlsx", _planilla([("1", "", 5)]), "application/octet-stream")})
    assert r.status_code == 409

    # ---- Etapa 3: desglose corroborado (sin él no se calcula) ----------------------------------------
    assert (await c.post(f"/api/v1/liquidaciones/calcular/{octubre['id']}", headers=admin)).status_code == 409
    assert (await c.post(f"/api/v1/boletas/{octubre['id']}/validar-items", headers=admin)).status_code == 200

    # ---- Etapa 2: el lector sincroniza lo tomado sin conexión, con foto -------------------------------
    cuando = datetime(2099, 10, 30, 9, 15, tzinfo=timezone.utc)
    actuales = {parcelas[0].id: 1100.0, parcelas[1].id: 2250.0, parcelas[2].id: 3400.0}
    r = await c.post("/api/v1/lecturas/sincronizar", headers=lector, json={"items": [
        {"lectura_id": lecturas[pid]["id"], "lectura_actual": valor, "fecha_toma": cuando.isoformat(),
         "base": {"lectura_actual": 0, "fecha_toma": None}} for pid, valor in actuales.items()]})
    assert r.status_code == 200, r.text
    assert {x["estado"] for x in r.json()["resultados"]} == {"aplicada"}
    lectura_comunero = lecturas[parcelas[1].id]["id"]
    r = await c.put(f"/api/v1/lecturas/{lectura_comunero}/foto", headers=lector,
                    files={"foto": ("m.jpg", JPEG, "image/jpeg")}, data={"fecha_toma": cuando.isoformat()})
    assert r.status_code == 200, r.text
    assert (await c.post(f"/api/v1/boletas/{octubre['id']}/cerrar-lecturas", headers=lector)).status_code == 200

    # ---- Etapa 4: cálculo cuadrado al peso -----------------------------------------------------------
    r = await c.post(f"/api/v1/liquidaciones/calcular/{octubre['id']}", headers=admin)
    assert r.status_code == 200, r.text
    liquidaciones = r.json()
    assert len(liquidaciones) == 3
    assert sum(l["total_pagar_mes"] for l in liquidaciones) == EMISION
    consumos = {l["parcela_id"]: l["kwh_consumidos"] for l in
                (await c.get("/api/v1/lecturas/", headers=admin, params={"boleta_id": octubre["id"]})).json()}
    assert [consumos[p.id] for p in parcelas] == [100, 250, 400]   # lectura del mes − lectura inicial

    # PDF de las liquidaciones: solo la administración
    r = await c.get(f"/api/v1/liquidaciones/pdf/{octubre['id']}", headers=admin)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF") and "liquidaciones-2099-10.pdf" in r.headers["content-disposition"]
    assert (await c.get(f"/api/v1/liquidaciones/pdf/{octubre['id']}", headers=cab_comunero)).status_code == 403

    # ---- Etapa 5: cierre; el comunero aún no ve nada -------------------------------------------------
    assert (await c.post(f"/api/v1/boletas/{octubre['id']}/cerrar-liquidaciones", headers=admin)).status_code == 200
    r = await c.get("/api/v1/liquidaciones/", headers=cab_comunero, params={"boleta_id": octubre["id"]})
    assert r.status_code == 200 and r.json() == []
    propia = next(l for l in liquidaciones if l["parcela_id"] == parcelas[1].id)
    assert (await c.get(f"/api/v1/liquidaciones/{propia['id']}", headers=cab_comunero)).status_code == 403
    assert (await c.get(f"/api/v1/lecturas/{lectura_comunero}/foto", headers=cab_comunero)).status_code == 404

    r = await c.patch(f"/api/v1/boletas/{octubre['id']}", headers=admin, json={"boleta_visible_usuarios": True})
    assert r.status_code == 200, r.text
    assert (await c.post(f"/api/v1/boletas/{octubre['id']}/reabrir-liquidaciones", headers=admin)).status_code == 409

    # ---- Etapa 6: el comunero ve solo lo suyo, publicado, con la foto de su medidor --------------------
    r = await c.get("/api/v1/liquidaciones/", headers=cab_comunero, params={"boleta_id": octubre["id"]})
    assert [l["parcela_id"] for l in r.json()] == [parcelas[1].id]
    assert r.json()[0]["total_pagar_mes"] == propia["total_pagar_mes"]
    assert (await c.get(f"/api/v1/liquidaciones/{propia['id']}", headers=cab_comunero)).status_code == 200
    ajena = next(l for l in liquidaciones if l["parcela_id"] == parcelas[0].id)
    assert (await c.get(f"/api/v1/liquidaciones/{ajena['id']}", headers=cab_comunero)).status_code == 403
    assert (await c.get(f"/api/v1/lecturas/{lectura_comunero}/foto", headers=cab_comunero)).status_code == 200
    periodos = (await c.get("/api/v1/boletas/", headers=cab_comunero)).json()
    assert [b["id"] for b in periodos] == [octubre["id"]]   # la lectura inicial nunca se publica

    # ---- Meses siguientes: hereda la lectura del mes y propone los cargos en cero ---------------------
    r = await c.post("/api/v1/boletas/", headers=admin, json={})
    assert r.status_code == 201, r.text
    noviembre = r.json()
    assert noviembre["periodo_mes"] == "2099-11-01"
    assert {(i["descripcion"], i["tipo_calculo"], i["monto_neto_clp"]) for i in noviembre["items_detalle"]} == {
        ("Cargo fijo", "fijo", 0), ("Transporte de electricidad", "variable", 0), ("Interés por mora", "informativo", 0)}
    anteriores = {l["parcela_id"]: l["lectura_anterior"] for l in
                  (await c.get("/api/v1/lecturas/", headers=admin, params={"boleta_id": noviembre["id"]})).json()}
    assert anteriores == actuales
