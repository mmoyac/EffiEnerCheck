"""Orden del recorrido del lector (cambio orden-recorrido)."""
import os

from sqlalchemy import select

from app.core.security import create_access_token
from app.models.auditoria import AuditoriaLog
from app.models.condominio import Condominio
from app.models.condominio_modulo import CondominioModulo
from app.models.parcela import Parcela
from app.models.rol import Rol
from app.models.usuario import Usuario

URL = "/api/v1/parcelas/orden-recorrido"


async def _condominio(session, numeros=("3", "4", "5", "6", "13 A", "13 B")):
    c = Condominio(nombre="Condominio Recorrido", rut_comunidad=f"recorrido-{os.urandom(4).hex()}",
                   plan_suscripcion="basico", activo=True,
                   modulos=[CondominioModulo(modulo="portal"), CondominioModulo(modulo="energia")])
    session.add(c)
    await session.flush()
    parcelas = {n: Parcela(condominio_id=c.id, numero_parcela=n, activa=True) for n in numeros}
    session.add_all(parcelas.values())
    await session.flush()
    return c, parcelas


async def _cabecera(session, rol, condominio_id):
    rol_id = (await session.execute(select(Rol.id).where(Rol.nombre == rol))).scalar_one()
    u = Usuario(nombre=f"Prueba {rol}", email=f"recorrido-{rol}-{os.urandom(3).hex()}@test.cl", password_hash="x",
                rol_id=rol_id, condominio_id=condominio_id)
    session.add(u)
    await session.flush()
    return {"Authorization": f"Bearer {create_access_token(user_id=u.id, rol=rol, condominio_id=condominio_id)}"}


async def _orden(c, cab):
    return {p["numero_parcela"]: p["orden_recorrido"] for p in (await c.get("/api/v1/parcelas/", headers=cab)).json()}


async def test_definir_y_quitar_el_recorrido(tx):
    c, session = tx
    condominio, p = await _condominio(session)
    admin = await _cabecera(session, "admin_condominio", condominio.id)

    ruta = ["6", "5", "4", "3", "13 A", "13 B"]
    r = await c.put(URL, headers=admin, json={"parcela_ids": [p[n].id for n in ruta[:4]]})
    assert r.status_code == 200, r.text
    assert await _orden(c, admin) == {"3": 4, "4": 3, "5": 2, "6": 1, "13 A": None, "13 B": None}
    auditoria = (await session.execute(select(AuditoriaLog).where(
        AuditoriaLog.accion == "UPDATE_ORDEN_RECORRIDO", AuditoriaLog.condominio_id == condominio.id))).scalars().all()
    assert len(auditoria) == 1

    # Redefinir: las que salen de la lista quedan sin posición
    await c.put(URL, headers=admin, json={"parcela_ids": [p["13 B"].id, p["6"].id]})
    assert await _orden(c, admin) == {"3": None, "4": None, "5": None, "6": 2, "13 A": None, "13 B": 1}

    # Quitar el recorrido
    await c.put(URL, headers=admin, json={"parcela_ids": []})
    assert set((await _orden(c, admin)).values()) == {None}


async def test_rechaza_repetidas_y_ajenas(tx):
    c, session = tx
    condominio, p = await _condominio(session)
    otro, q = await _condominio(session, numeros=("1",))
    admin = await _cabecera(session, "admin_condominio", condominio.id)

    r = await c.put(URL, headers=admin, json={"parcela_ids": [p["3"].id, p["3"].id]})
    assert r.status_code == 422
    r = await c.put(URL, headers=admin, json={"parcela_ids": [p["3"].id, q["1"].id]})
    assert r.status_code == 403
    r = await c.put(URL, headers=admin, json={"parcela_ids": [p["3"].id, 999_999_999]})
    assert r.status_code == 403
    assert set((await _orden(c, admin)).values()) == {None}


async def test_solo_administracion(tx):
    c, session = tx
    condominio, p = await _condominio(session)
    lector = await _cabecera(session, "lector", condominio.id)
    r = await c.put(URL, headers=lector, json={"parcela_ids": [p["3"].id]})
    assert r.status_code == 403
