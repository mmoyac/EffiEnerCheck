"""Carga inicial de producción copiada desde desarrollo: sin claves, sin cuentas del seed, idempotente."""
import json

import pytest
from sqlalchemy import insert, select
from sqlalchemy.orm import selectinload

from app.db import cargar_residentes
from app.db.copiar_desde_desarrollo import exportar, importar
from app.models.condominio import Condominio
from app.models.condominio_modulo import CondominioModulo
from app.models.parcela import Parcela
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.models.usuario_parcela import usuario_parcelas


async def _condominio_de_desarrollo(db) -> None:
    """Condominio ficticio con un parcelero real, uno del seed y un lector."""
    c = Condominio(nombre="Copia Origen", rut_comunidad="77777777-7", direccion="Camino 1",
                   plan_suscripcion="premium", color_primario="#22C55E", activo=True,
                   modulos=[CondominioModulo(modulo="portal"), CondominioModulo(modulo="rifas")])
    db.add(c)
    await db.flush()
    p1 = Parcela(condominio_id=c.id, numero_parcela="10", propietario_nombre="Eva Luna", activa=True)
    p2 = Parcela(condominio_id=c.id, numero_parcela="2", propietario_nombre=None, activa=False)
    db.add_all([p1, p2])
    await db.flush()
    roles = {r.nombre: r.id for r in (await db.execute(select(Rol))).scalars()}
    eva = Usuario(nombre="Eva Luna", email="Eva@Ejemplo.cl", password_hash="hash-dev", telefono="56911112222",
                  rol_id=roles["parcelero"], condominio_id=c.id)
    seed = Usuario(nombre="Seed", email="gchacon@santalaura.cl.copia", password_hash="hash-dev",
                   rol_id=roles["parcelero"], condominio_id=c.id)
    lector = Usuario(nombre="Lector", email="lector@ejemplo.cl", password_hash="hash-dev",
                     rol_id=roles["lector"], condominio_id=c.id)
    db.add_all([eva, seed, lector])
    await db.flush()
    await db.execute(insert(usuario_parcelas).values(
        [{"usuario_id": eva.id, "parcela_id": p1.id}, {"usuario_id": eva.id, "parcela_id": p2.id}]))


def _como_otro_condominio(datos: dict) -> dict:
    """La exportación, pero para un condominio que aún no existe en la base (como producción vacía)."""
    datos = json.loads(json.dumps(datos))
    datos["condominio"].update(nombre="Copia Destino", rut_comunidad="66666666-6")
    for r in datos["residentes"]:
        r["email"] = r["email"].replace("@", "+destino@")
    return datos


async def test_exportar_no_lleva_claves_ni_cuentas_de_prueba(db, monkeypatch):
    monkeypatch.setattr("app.db.copiar_desde_desarrollo.emails_del_seed",
                        lambda: {"gchacon@santalaura.cl.copia"})
    await _condominio_de_desarrollo(db)

    datos = await exportar(db, "Copia Origen")

    assert datos["condominio"]["modulos"] == ["portal", "rifas"]
    assert [p["numero_parcela"] for p in datos["parcelas"]] == ["2", "10"]
    assert [r["email"] for r in datos["residentes"]] == ["eva@ejemplo.cl"]   # ni el seed ni el lector
    assert datos["residentes"][0]["parcelas"] == ["2", "10"]
    assert "password_hash" not in json.dumps(datos) and "hash-dev" not in json.dumps(datos)


async def test_importar_crea_todo_y_es_idempotente(db, monkeypatch):
    monkeypatch.setattr("app.db.copiar_desde_desarrollo.emails_del_seed", lambda: set())
    await _condominio_de_desarrollo(db)
    datos = _como_otro_condominio(await exportar(db, "Copia Origen"))
    kwargs = dict(portal_url="https://portal.destino.cl", dominios=["WWW.Destino.cl", "destino.cl"],
                  clave_hash="hash-inicial")

    primera = await importar(db, datos, **kwargs)
    assert (primera.condominio_creado, primera.modulos_agregados, primera.dominios_agregados,
            primera.parcelas_creadas, primera.usuarios_creados, primera.asignaciones_creadas) == \
           (True, 2, 1, 2, 2, 2)   # www.destino.cl y destino.cl son el mismo dominio
    assert primera.avisos == []

    segunda = await importar(db, datos, **kwargs)
    assert (segunda.condominio_creado, segunda.modulos_agregados, segunda.dominios_agregados,
            segunda.parcelas_creadas, segunda.usuarios_creados, segunda.asignaciones_creadas) == \
           (False, 0, 0, 0, 0, 0)

    destino = (await db.execute(
        select(Condominio).options(selectinload(Condominio.dominios_sitio))
        .where(Condominio.rut_comunidad == "66666666-6")
    )).scalar_one()
    assert destino.portal_url == "https://portal.destino.cl"
    assert destino.color_primario == "#22C55E"
    assert [d.dominio for d in destino.dominios_sitio] == ["destino.cl"]
    eva = (await db.execute(
        select(Usuario).options(selectinload(Usuario.parcelas)).where(Usuario.email == "eva+destino@ejemplo.cl")
    )).scalar_one()
    assert eva.password_hash == "hash-inicial"          # nunca la clave de desarrollo
    assert sorted(p.numero_parcela for p in eva.parcelas) == ["10", "2"]
    assert (await db.execute(select(Parcela).where(
        Parcela.condominio_id == destino.id, Parcela.numero_parcela == "2"))).scalar_one().activa is False


async def test_importar_omite_cuentas_del_seed(db, monkeypatch):
    monkeypatch.setattr("app.db.copiar_desde_desarrollo.emails_del_seed", lambda: set())
    await _condominio_de_desarrollo(db)
    datos = _como_otro_condominio(await exportar(db, "Copia Origen"))
    monkeypatch.setattr("app.db.copiar_desde_desarrollo.emails_del_seed",
                        lambda: {"gchacon+destino@santalaura.cl.copia"})

    resumen = await importar(db, datos, portal_url=None, dominios=[], clave_hash="hash-inicial")

    assert resumen.usuarios_creados == 1
    assert any("cuenta de prueba del seed" in a for a in resumen.avisos)
    assert (await db.execute(
        select(Usuario).where(Usuario.email == "gchacon+destino@santalaura.cl.copia"))).scalar_one_or_none() is None


@pytest.mark.parametrize("clave", ["corta", "admin123"])
def test_clave_inicial_debil_se_rechaza(monkeypatch, clave):
    monkeypatch.setattr(cargar_residentes.getpass, "getpass", lambda _: clave)
    with pytest.raises(ValueError):
        cargar_residentes.pedir_clave_inicial()
