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
    # Cuadre al peso (cambio cuadre-al-peso): igualdad exacta, sin tolerancia
    assert sum(l.total_pagar_mes for l in liquidaciones) == boleta.monto_total_emision
    for l in liquidaciones:
        assert l.total_pagar_mes == l.monto_energia_kwh + l.monto_prorrateo_variable + l.monto_cuota_fija


async def test_recalcular_no_duplica(db):
    boleta, usuario = await _escenario(db, [("Administración", 30_000.0, "fijo")], [100.0, 200.0])
    await calcular_liquidaciones_boleta(boleta.id, None, usuario, db)
    segunda = await calcular_liquidaciones_boleta(boleta.id, None, usuario, db)
    assert len(segunda) == 2


@pytest.mark.parametrize("kwh, items, emision", [
    # Tres parcelas iguales: un tercio nunca da pesos enteros
    ([100.0, 100.0, 100.0], [("Administración", 10_000.0, "fijo"), ("Transporte", 1_000.0, "variable")], 100_000),
    # Consumos con decimales y una emisión "fea"
    ([123.4, 56.7, 89.1, 10.9, 0.3], [("Transporte", 7_777.0, "variable")], 99_999),
    # Descuento que deja los fijos en negativo
    ([300.0, 200.0, 100.0], [("Cargo fijo", 1_000.0, "fijo"), ("Nota de crédito", -5_000.5, "fijo")], 50_001),
])
async def test_cuadre_al_peso_con_fracciones_adversas(db, kwh, items, emision):
    boleta, usuario = await _escenario(db, items, kwh, emision=emision, kwh_compania=sum(kwh) + 33.3)
    liquidaciones = await calcular_liquidaciones_boleta(boleta.id, None, usuario, db)
    assert sum(l.total_pagar_mes for l in liquidaciones) == emision
    # La cuota fija es idéntica para todas
    assert len({l.monto_cuota_fija for l in liquidaciones}) == 1


async def test_parcela_sin_consumo_solo_paga_cuota_fija(db):
    boleta, usuario = await _escenario(db, [("Transporte", 12_345.0, "variable"), ("Adm.", 9_999.0, "fijo")],
                                       [250.0, 0.0, 333.3], emision=200_001)
    liquidaciones = await calcular_liquidaciones_boleta(boleta.id, None, usuario, db)
    sin_consumo = liquidaciones[1]
    assert sin_consumo.monto_energia_kwh == 0 and sin_consumo.monto_prorrateo_variable == 0
    assert sin_consumo.total_pagar_mes == sin_consumo.monto_cuota_fija
    assert sum(l.total_pagar_mes for l in liquidaciones) == 200_001


async def test_diferencial_se_prorratea_por_consumo(db):
    """Cambio diferencial-por-consumo: como la planilla de la administración, el diferencial va con los
    variables. Cada parcela paga sus kWh × (emisión − fijos) / Σ kWh, más su parte de los fijos."""
    kwh = [782.0, 156.0, 0.0, 317.0, 0.0, 1.0]
    items = [("Potencia punta", 50_000.0, "variable"), ("Administración", 6_000.0, "fijo")]
    boleta, usuario = await _escenario(db, items, kwh, emision=300_000, kwh_compania=1_500.0)   # 244 kWh sin medir

    liquidaciones = await calcular_liquidaciones_boleta(boleta.id, None, usuario, db)

    por_kwh = (300_000 - 6_000) / sum(kwh)
    for l, k in zip(liquidaciones, kwh):
        assert abs(l.total_pagar_mes - (k * por_kwh + 6_000 / len(kwh))) <= 1
    # Sin consumo: solo la cuota fija, sin parte del diferencial
    assert liquidaciones[2].total_pagar_mes == liquidaciones[2].monto_cuota_fija == 1_000
    assert sum(l.total_pagar_mes for l in liquidaciones) == 300_000


async def test_sin_consumo_el_diferencial_va_a_la_cuota_fija(db):
    boleta, usuario = await _escenario(db, [("Potencia punta", 10_000.0, "variable"), ("Adm.", 3_000.0, "fijo")],
                                       [0.0, 0.0, 0.0], emision=100_000)
    liquidaciones = await calcular_liquidaciones_boleta(boleta.id, None, usuario, db)
    assert sum(l.total_pagar_mes for l in liquidaciones) == 100_000
    assert all(l.monto_prorrateo_variable == 0 for l in liquidaciones)
