"""Eliminación de una rifa con todo lo que depende de ella (solo super admin; cambio eliminar-rifa)."""
import os

from sqlalchemy import func, select

from app.api.v1.endpoints import rifas as rifas_endpoint
from app.models.auditoria import AuditoriaLog
from app.models.parcela import Parcela
from app.models.rifa import CompraRifa, ImputacionRifa, Rifa, RifaNumero
from app.models.usuario import Usuario

EMAIL_SUPER = "mmoyainfo@gmail.com"
EMAIL_ADMIN = "hhernandez@santalaura.cl"
CLAVE_SEED = "admin123"


async def _cabecera(c, email, session=None):
    """Token del usuario. El super admin de desarrollo puede haber cambiado su clave: se emite directo."""
    if email == EMAIL_SUPER:
        from app.core.security import create_access_token
        u = (await session.execute(select(Usuario).where(Usuario.email == email))).scalar_one()
        return {"Authorization": f"Bearer {create_access_token(user_id=u.id, rol='super_admin')}"}
    r = await c.post("/api/v1/auth/token", data={"username": email, "password": CLAVE_SEED})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _rifa_con_ventas(session, tmp_path, monkeypatch) -> tuple[Rifa, str]:
    """Rifa cerrada con una compra pagada con voucher, una anulada y una imputación cargada."""
    monkeypatch.setattr(rifas_endpoint, "VOUCHERS_DIR", str(tmp_path))
    admin = (await session.execute(select(Usuario).where(Usuario.email == EMAIL_ADMIN))).scalar_one()
    parcela = (await session.execute(
        select(Parcela).where(Parcela.condominio_id == admin.condominio_id).order_by(Parcela.id)
    )).scalars().first()
    rifa = Rifa(condominio_id=admin.condominio_id, nombre="Rifa de Prueba Eliminar", beneficiario="Alguien",
                precio_numero=1000, cantidad_numeros=100, estado="cerrada", creado_por_id=admin.id)
    session.add(rifa)
    await session.flush()
    voucher = "voucher-prueba.jpg"
    (tmp_path / voucher).write_bytes(b"jpg")
    pagada = CompraRifa(rifa_id=rifa.id, folio=1, parcela_id=parcela.id, usuario_id=admin.id, canal="administracion",
                        numeros=[1, 2], monto=2000, medio_pago="transferencia", pagada=True,
                        voucher_archivo=voucher, voucher_mime="image/jpeg")
    anulada = CompraRifa(rifa_id=rifa.id, folio=2, parcela_id=parcela.id, usuario_id=admin.id, canal="administracion",
                         numeros=[3], monto=1000, medio_pago="efectivo", pagada=True, anulada=True)
    session.add_all([pagada, anulada])
    await session.flush()
    session.add_all([RifaNumero(compra_id=pagada.id, rifa_id=rifa.id, numero=n) for n in (1, 2)])
    session.add(ImputacionRifa(rifa_id=rifa.id, parcela_id=parcela.id, cantidad_numeros=2, monto=2000, cargada=True))
    await session.flush()
    return rifa, voucher


async def test_resumen_y_eliminacion_completa(tx, tmp_path, monkeypatch):
    c, session = tx
    rifa, voucher = await _rifa_con_ventas(session, tmp_path, monkeypatch)
    cab = await _cabecera(c, EMAIL_SUPER, session)

    r = await c.get(f"/api/v1/rifas/{rifa.id}/eliminacion", headers=cab)
    assert r.status_code == 200, r.text
    assert r.json() == {
        "nombre": "Rifa de Prueba Eliminar", "estado": "cerrada",
        "compras_vigentes": 1, "compras_anuladas": 1, "numeros_vendidos": 2, "monto_pagado": 2000,
        "imputaciones_pendientes": 0, "imputaciones_cargadas": 1, "vouchers": 1,
    }

    r = await c.delete(f"/api/v1/rifas/{rifa.id}", headers=cab, params={"confirmacion": " Rifa de Prueba Eliminar "})
    assert r.status_code == 204, r.text

    for modelo in (Rifa, CompraRifa, RifaNumero, ImputacionRifa):
        columna = modelo.id if modelo is Rifa else modelo.rifa_id
        assert (await session.execute(select(func.count()).where(columna == rifa.id))).scalar() == 0
    assert not os.path.exists(tmp_path / voucher)

    auditoria = (await session.execute(
        select(AuditoriaLog).where(AuditoriaLog.accion == "ELIMINAR_RIFA").order_by(AuditoriaLog.id.desc())
    )).scalars().first()
    assert auditoria.detalles["rifa_id"] == rifa.id
    assert auditoria.detalles["compras_vigentes"] == 1


async def test_confirmacion_incorrecta_no_borra_nada(tx, tmp_path, monkeypatch):
    c, session = tx
    rifa, voucher = await _rifa_con_ventas(session, tmp_path, monkeypatch)
    r = await c.delete(f"/api/v1/rifas/{rifa.id}", headers=await _cabecera(c, EMAIL_SUPER, session),
                       params={"confirmacion": "otra rifa"})
    assert r.status_code == 422
    assert r.json()["detail"] == "Escribe el nombre exacto de la rifa para confirmar"
    assert (await session.execute(select(func.count()).where(CompraRifa.rifa_id == rifa.id))).scalar() == 2
    assert os.path.exists(tmp_path / voucher)


async def test_solo_el_super_admin_puede_eliminar(tx, tmp_path, monkeypatch):
    c, session = tx
    rifa, _ = await _rifa_con_ventas(session, tmp_path, monkeypatch)
    admin = await _cabecera(c, EMAIL_ADMIN)
    assert (await c.get(f"/api/v1/rifas/{rifa.id}/eliminacion", headers=admin)).status_code == 403
    r = await c.delete(f"/api/v1/rifas/{rifa.id}", headers=admin, params={"confirmacion": rifa.nombre})
    assert r.status_code == 403
    assert (await session.execute(select(func.count()).where(Rifa.id == rifa.id))).scalar() == 1
