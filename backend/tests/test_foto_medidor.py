"""Foto del medidor asociada a la lectura (cambio foto-medidor)."""
import os
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import insert, select

from app.models.auditoria import AuditoriaLog
from app.models.boleta import BoletaMaestra
from app.models.condominio import Condominio
from app.models.lectura import LecturaParcela
from app.models.parcela import Parcela
from app.models.usuario import Usuario
from app.models.usuario_parcela import usuario_parcelas
from app.services import fotos_lectura

EMAIL_LECTOR = "cportero@santalaura.cl"
EMAIL_ADMIN = "hhernandez@santalaura.cl"
EMAIL_COMUNERO = "mmoyainfo+parcela@gmail.com"
EMAIL_PORTERIA = "porteria@santalaura.cl"
CLAVE_SEED = "admin123"
TOMA = datetime(2099, 1, 15, 10, 30, 12, 345000, tzinfo=timezone.utc)
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 200


@pytest.fixture(autouse=True)
def fotos_dir(tmp_path, monkeypatch):
    """Las fotos de las pruebas van a un directorio temporal, no al volumen privado."""
    monkeypatch.setattr(fotos_lectura, "FOTOS_DIR", str(tmp_path))
    return tmp_path


async def _cabecera(c, email=EMAIL_LECTOR):
    r = await c.post("/api/v1/auth/token", data={"username": email, "password": CLAVE_SEED})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _lectura(session, *, condominio_id=None, cerrada=False, publicada=False, fecha_toma=TOMA) -> LecturaParcela:
    admin = (await session.execute(select(Usuario).where(Usuario.email == EMAIL_ADMIN))).scalar_one()
    condominio_id = condominio_id or admin.condominio_id
    parcela = Parcela(condominio_id=condominio_id, numero_parcela="T-1", activa=True)
    boleta = BoletaMaestra(condominio_id=condominio_id, periodo_mes=date(2099, 1, 1), creado_por=admin.id,
                           lecturas_cerradas=cerrada, boleta_visible_usuarios=publicada)
    session.add_all([parcela, boleta])
    await session.flush()
    lectura = LecturaParcela(parcela_id=parcela.id, boleta_id=boleta.id, lectura_anterior=100.0,
                             lectura_actual=150.0, kwh_consumidos=50.0, lector_id=admin.id, fecha_toma=fecha_toma)
    session.add(lectura)
    await session.flush()
    return lectura


async def _subir(c, cab, lectura_id, contenido=JPEG, fecha_toma=TOMA, mime="image/jpeg"):
    return await c.put(f"/api/v1/lecturas/{lectura_id}/foto", headers=cab,
                       files={"foto": ("foto.jpg", contenido, mime)},
                       data={"fecha_toma": fecha_toma.isoformat()})


async def _auditorias(session):
    return (await session.execute(
        select(AuditoriaLog).where(AuditoriaLog.accion == "SUBIR_FOTO_LECTURA"))).scalars().all()


async def test_sube_foto_y_es_idempotente(tx, fotos_dir):
    c, session = tx
    lectura = await _lectura(session)
    cab = await _cabecera(c)

    r = await _subir(c, cab, lectura.id)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["tiene_foto"] is True
    assert "foto_archivo" not in cuerpo
    await session.refresh(lectura)
    assert lectura.foto_fecha_toma == TOMA
    assert os.listdir(fotos_dir) == [lectura.foto_archivo]
    auditadas = len(await _auditorias(session))

    # Reintento (se cortó la red antes de la respuesta): ni archivo nuevo ni auditoría
    r = await _subir(c, cab, lectura.id)
    assert r.status_code == 200
    assert os.listdir(fotos_dir) == [lectura.foto_archivo]
    assert len(await _auditorias(session)) == auditadas


async def test_reemplazo_borra_el_archivo_anterior(tx, fotos_dir):
    c, session = tx
    lectura = await _lectura(session)
    cab = await _cabecera(c)
    await _subir(c, cab, lectura.id)
    r = await _subir(c, cab, lectura.id, contenido=WEBP, mime="image/webp")
    assert r.status_code == 200, r.text
    await session.refresh(lectura)
    assert os.listdir(fotos_dir) == [lectura.foto_archivo]
    assert lectura.foto_archivo.endswith(".webp")


async def test_foto_de_toma_no_vigente(tx, fotos_dir):
    c, session = tx
    lectura = await _lectura(session)
    r = await _subir(c, await _cabecera(c), lectura.id, fecha_toma=datetime(2099, 1, 14, tzinfo=timezone.utc))
    assert r.status_code == 409
    assert "ya no está vigente" in r.json()["detail"]
    assert os.listdir(fotos_dir) == []


async def test_periodo_cerrado(tx, fotos_dir):
    c, session = tx
    lectura = await _lectura(session, cerrada=True)
    r = await _subir(c, await _cabecera(c), lectura.id)
    assert r.status_code == 409
    assert r.json()["detail"] == "Las lecturas del período ya están cerradas"
    assert os.listdir(fotos_dir) == []


@pytest.mark.parametrize("contenido", [b"%PDF-1.4 no es una foto", b"\xff\xd8\xff" + b"\x00" * (3 * 1024 * 1024)])
async def test_archivo_invalido(tx, fotos_dir, contenido):
    c, session = tx
    lectura = await _lectura(session)
    r = await _subir(c, await _cabecera(c), lectura.id, contenido=contenido)
    assert r.status_code == 422
    assert os.listdir(fotos_dir) == []


async def test_otro_condominio(tx):
    c, session = tx
    otro = Condominio(nombre="Otro Condominio", rut_comunidad="55555555-5", plan_suscripcion="basico", activo=True)
    session.add(otro)
    await session.flush()
    lectura = await _lectura(session, condominio_id=otro.id)
    r = await _subir(c, await _cabecera(c), lectura.id)
    assert r.status_code == 403
    lectura.foto_archivo = "x.jpg"
    await session.flush()
    r = await c.get(f"/api/v1/lecturas/{lectura.id}/foto", headers=await _cabecera(c))
    assert r.status_code == 404


async def test_correccion_del_valor_conserva_la_foto(tx):
    c, session = tx
    lectura = await _lectura(session)
    cab_admin = await _cabecera(c, EMAIL_ADMIN)
    await _subir(c, await _cabecera(c), lectura.id)
    corregida = datetime(2099, 1, 16, tzinfo=timezone.utc)
    r = await c.patch(f"/api/v1/lecturas/{lectura.id}", headers=cab_admin,
                      json={"lectura_actual": 151.0, "fecha_toma": corregida.isoformat()})
    assert r.status_code == 200, r.text
    assert r.json()["tiene_foto"] is True
    assert datetime.fromisoformat(r.json()["foto_fecha_toma"]) == TOMA


async def test_acceso_a_la_foto(tx):
    c, session = tx
    lectura = await _lectura(session)
    await _subir(c, await _cabecera(c), lectura.id)
    url = f"/api/v1/lecturas/{lectura.id}/foto"

    for email in (EMAIL_LECTOR, EMAIL_ADMIN):
        r = await c.get(url, headers=await _cabecera(c, email))
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/jpeg"
        assert r.headers["cache-control"] == "private, no-store"
        assert r.content == JPEG

    r = await c.get(url, headers=await _cabecera(c, EMAIL_PORTERIA))
    assert r.status_code == 403   # la portería queda fuera por la guarda

    # Comunero: no es su parcela
    cab_comunero = await _cabecera(c, EMAIL_COMUNERO)
    assert (await c.get(url, headers=cab_comunero)).status_code == 404
    # Es su parcela pero el período no está publicado
    comunero = (await session.execute(select(Usuario).where(Usuario.email == EMAIL_COMUNERO))).scalar_one()
    await session.execute(insert(usuario_parcelas).values(usuario_id=comunero.id, parcela_id=lectura.parcela_id))
    session.expire(comunero, ["parcelas"])   # la sesión compartida guardaba sus parcelas de antes
    assert (await c.get(url, headers=cab_comunero)).status_code == 404
    # Publicado: la ve
    boleta = await session.get(BoletaMaestra, lectura.boleta_id)
    boleta.boleta_visible_usuarios = True
    await session.flush()
    assert (await c.get(url, headers=cab_comunero)).status_code == 200


async def test_lectura_sin_foto(tx):
    c, session = tx
    lectura = await _lectura(session)
    r = await c.get(f"/api/v1/lecturas/{lectura.id}/foto", headers=await _cabecera(c))
    assert r.status_code == 404


async def test_eliminar_boleta_borra_las_fotos(tx, fotos_dir):
    c, session = tx
    lectura = await _lectura(session)
    await _subir(c, await _cabecera(c), lectura.id)
    assert len(os.listdir(fotos_dir)) == 1
    r = await c.delete(f"/api/v1/boletas/{lectura.boleta_id}", headers=await _cabecera(c, EMAIL_ADMIN))
    assert r.status_code == 204, r.text
    assert os.listdir(fotos_dir) == []
