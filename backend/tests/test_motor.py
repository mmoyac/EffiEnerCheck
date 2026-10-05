"""Motor EnerCheck: el total liquidado debe cuadrar con el Total Emisión de la boleta."""
from datetime import date

import pytest
from sqlalchemy import select

from app.models.boleta import BoletaItemDetalle, BoletaMaestra
from app.models.condominio import Condominio
from app.models.lectura import LecturaParcela
from app.models.parcela import Parcela
from app.models.usuario import Usuario
from app.services.enercheck import calcular_liquidaciones_boleta


async def _escenario(db, items, kwh_por_parcela, emision=1_000_000, kwh_compania=1_000.0):
    condominio = Condominio(nombre="Prueba motor", rut_comunidad="99999999-9", plan_suscripcion="basico")
    db.add(condominio)
    await db.flush()
    usuario = (await db.execute(select(Usuario).order_by(Usuario.id).limit(1))).scalar_one()

    boleta = BoletaMaestra(
        condominio_id=condominio.id, periodo_mes=date(2030, 1, 1), estado="validada",
        total_kwh_compania=kwh_compania, monto_neto_electricidad_consumida=500_000.0,
        monto_total_emision=emision, creado_por=usuario.id,
    )
    db.add(boleta)
    await db.flush()
    for descripcion, monto, tipo in items:
        db.add(BoletaItemDetalle(boleta_id=boleta.id, descripcion=descripcion, monto_neto_clp=monto, tipo_calculo=tipo))

    for n, kwh in enumerate(kwh_por_parcela, start=1):
        parcela = Parcela(condominio_id=condominio.id, numero_parcela=str(n), activa=True)
        db.add(parcela)
        await db.flush()
        db.add(LecturaParcela(parcela_id=parcela.id, boleta_id=boleta.id, lectura_anterior=0.0,
                              lectura_actual=kwh, kwh_consumidos=kwh, lector_id=usuario.id))
    await db.flush()
    return boleta, usuario


@pytest.mark.parametrize("items", [
    [("Transporte", 120_000.0, "variable"), ("Administración", 30_000.0, "fijo")],
    # Un descuento (monto negativo) reduce su cuota sin romper el cuadre
    [("Transporte", 120_000.0, "variable"), ("Administración", 30_000.0, "fijo"), ("Descuento", -40_000.0, "fijo")],
    # Los informativos quedan fuera del reparto
    [("Transporte", 120_000.0, "variable"), ("Diferencial KW", 0.0, "informativo")],
])
async def test_total_liquidado_cuadra_con_la_emision(db, items):
    kwh = [300.0, 250.0, 200.0, 150.0]   # Σ 900 de 1.000 kWh: hay diferencial
    boleta, usuario = await _escenario(db, items, kwh)

    liquidaciones = await calcular_liquidaciones_boleta(boleta.id, None, usuario, db)

    assert len(liquidaciones) == len(kwh)
    total = sum(l.total_pagar_mes for l in liquidaciones)
    # Cada componente se redondea a pesos por parcela: a lo más 1,5 pesos de diferencia por parcela
    assert abs(total - boleta.monto_total_emision) <= 1.5 * len(kwh)


async def test_recalcular_no_duplica(db):
    boleta, usuario = await _escenario(db, [("Administración", 30_000.0, "fijo")], [100.0, 200.0])
    await calcular_liquidaciones_boleta(boleta.id, None, usuario, db)
    segunda = await calcular_liquidaciones_boleta(boleta.id, None, usuario, db)
    assert len(segunda) == 2
