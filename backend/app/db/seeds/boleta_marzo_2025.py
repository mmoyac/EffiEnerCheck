"""
Seed de datos reales — Período Marzo 2025
Condominio Santa Laura (id=1)
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.boleta import BoletaItemDetalle, BoletaMaestra

BOLETA = {
    "id": 1,
    "condominio_id": 1,
    "periodo_mes": date(2025, 3, 1),
    "boleta_visible_usuarios": False,
    "estado": "borrador",
    "lecturas_cerradas": False,
    "liquidaciones_cerradas": False,
    # Totales de la boleta de la compañía eléctrica
    "total_kwh_compania": 24000.0,
    "monto_neto_electricidad_consumida": 2792352.0,
    "monto_total_emision": 3322899.0,
    "monto_saldo_anterior": 12498000,
    "creado_por": 2,  # Henry Hernández — admin_condominio
}

# valor_kwh = (2.792.352 × 1,19) / 24.000 = $138,45 CLP/kWh
ITEMS = [
    {"boleta_id": 1, "descripcion": "TRANSPORTE ELECTRICIDAD",           "monto_neto_clp": 383132.4,    "tipo_calculo": "variable"},
    {"boleta_id": 1, "descripcion": "RECARGA POR LECTURA ALTA TENSIÓN",  "monto_neto_clp": 161215.25,   "tipo_calculo": "variable"},
    {"boleta_id": 1, "descripcion": "CARGO POR POTENCIA PRESENTE PUNTA", "monto_neto_clp": 1283266.25,  "tipo_calculo": "variable"},
    {"boleta_id": 1, "descripcion": "ADMINISTRACION DE SERVICIO",        "monto_neto_clp": 1036.49,     "tipo_calculo": "fijo"},
    {"boleta_id": 1, "descripcion": "CARGO POR SERVICIO PUBLICO",        "monto_neto_clp": 20520.0,     "tipo_calculo": "fijo"},
    {"boleta_id": 1, "descripcion": "Interés",                           "monto_neto_clp": 259801.99,   "tipo_calculo": "fijo"},
    {"boleta_id": 1, "descripcion": "Cargo Fondo estabilización ley 21472", "monto_neto_clp": 77496.0,  "tipo_calculo": "fijo"},
    {"boleta_id": 1, "descripcion": "Diferencial KW",                    "monto_neto_clp": 250186.595,  "tipo_calculo": "informativo"},
]


async def seed_boleta_marzo_2025(db: AsyncSession) -> None:
    existe = await db.execute(select(BoletaMaestra).where(BoletaMaestra.id == 1))
    if existe.scalar_one_or_none():
        print("  ✓ boleta marzo 2025: ya existe, omitiendo")
        return

    db.add(BoletaMaestra(**BOLETA))
    await db.flush()

    for item in ITEMS:
        db.add(BoletaItemDetalle(**item))

    await db.commit()
    print(f"  ✓ boleta marzo 2025: 1 boleta + {len(ITEMS)} ítems cargados")
