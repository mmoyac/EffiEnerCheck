"""
Seed de lecturas — Período Marzo 2025
Parcelas en orden: 2,3,4,5,6,7,8,9,10,11,12,13A,13B,14A,14B,15..52
lector_id=3 → Claudio Portero

Nota: el "." en los valores originales de la boleta es separador de miles
chileno (77.569 = 77 569 kWh), no decimal. Todos los valores se almacenan
como enteros en float.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lectura import LecturaParcela

BOLETA_ID = 1
LECTOR_ID = 3
FECHA_TOMA = datetime(2025, 3, 31, tzinfo=timezone.utc)

# parcela_id : lectura_anterior (kWh acumulados al cierre del período anterior)
LECTURAS_ANTERIORES: dict[int, float] = {
    1:  77569.0,   # parcela "2"
    2:  99953.0,   # parcela "3"
    3:  63655.0,   # parcela "4"
    4:   6150.0,   # parcela "5"
    5:  35171.0,   # parcela "6"
    6:      0.0,   # parcela "7"
    7:  62178.0,   # parcela "8"
    8:  41976.0,   # parcela "9"
    9:  58483.0,   # parcela "10"
    10:  3467.0,   # parcela "11"
    11: 39636.0,   # parcela "12"
    12: 38181.0,   # parcela "13 A"
    13: 18274.0,   # parcela "13 B"
    14: 32764.0,   # parcela "14 A"
    15: 11040.0,   # parcela "14 B"
    16: 81067.0,   # parcela "15"
    17: 20036.0,   # parcela "16"
    18: 71786.0,   # parcela "17"
    19: 46590.0,   # parcela "18"
    20: 37834.0,   # parcela "19"
    21: 41904.0,   # parcela "20"
    22: 27609.0,   # parcela "21"
    23: 80482.0,   # parcela "22"
    24: 50954.0,   # parcela "23"
    25: 32427.0,   # parcela "24"
    26: 51304.0,   # parcela "25"
    27: 86181.0,   # parcela "26"
    28:  8164.0,   # parcela "27"
    29: 42814.0,   # parcela "28"
    30: 15421.0,   # parcela "29"
    31: 59866.0,   # parcela "30"
    32: 57286.0,   # parcela "31"
    33:     0.0,   # parcela "32"
    34: 94029.0,   # parcela "33"
    35:  3495.0,   # parcela "34"
    36: 95268.0,   # parcela "35"
    37: 92486.0,   # parcela "36"
    38: 46584.0,   # parcela "37"
    39: 100315.0,  # parcela "38"
    40: 73972.0,   # parcela "39"
    41: 23204.0,   # parcela "40"
    42: 16097.0,   # parcela "41"
    43: 59896.0,   # parcela "42"
    44: 83313.0,   # parcela "43"
    45: 25988.0,   # parcela "44"
    46: 35217.0,   # parcela "45"
    47: 18652.0,   # parcela "46"
    48: 25509.0,   # parcela "47"
    49: 12100.0,   # parcela "48"
    50: 33321.0,   # parcela "49"
    51: 50665.0,   # parcela "50"
    52:  9369.0,   # parcela "51"
    53: 87798.0,   # parcela "52"
}

# Lecturas tomadas por Claudio Portero el 31-03-2025
LECTURAS_ACTUALES: dict[int, float] = {
    1:  77844.0,   # parcela "2"   → 275 kWh
    2: 100916.0,   # parcela "3"   → 963 kWh
    3:  63844.0,   # parcela "4"   → 189 kWh
    4:   6350.0,   # parcela "5"   → 200 kWh
    5:  35656.0,   # parcela "6"   → 485 kWh
    6:      0.0,   # parcela "7"   →   0 kWh (sin consumo)
    7:  62606.0,   # parcela "8"   → 428 kWh
    8:  42597.0,   # parcela "9"   → 621 kWh
    9:  58675.0,   # parcela "10"  → 192 kWh
    10:  4754.0,   # parcela "11"  →1287 kWh
    11: 39867.0,   # parcela "12"  → 231 kWh
    12: 38302.0,   # parcela "13 A"→ 121 kWh
    13: 18407.0,   # parcela "13 B"→ 133 kWh
    14: 33219.0,   # parcela "14 A"→ 455 kWh
    15: 11717.0,   # parcela "14 B"→ 677 kWh
    16: 81668.0,   # parcela "15"  → 601 kWh
    17: 20493.0,   # parcela "16"  → 457 kWh
    18: 72182.0,   # parcela "17"  → 396 kWh
    19: 47397.0,   # parcela "18"  → 807 kWh
    20: 37834.0,   # parcela "19"  →   0 kWh (sin consumo)
    21: 42391.0,   # parcela "20"  → 487 kWh
    22: 27727.0,   # parcela "21"  → 118 kWh
    23: 80933.0,   # parcela "22"  → 451 kWh
    24: 51647.0,   # parcela "23"  → 693 kWh
    25: 32742.0,   # parcela "24"  → 315 kWh
    26: 51647.0,   # parcela "25"  → 343 kWh
    27: 86587.0,   # parcela "26"  → 406 kWh
    28:  8164.0,   # parcela "27"  →   0 kWh (sin consumo)
    29: 43428.0,   # parcela "28"  → 614 kWh
    30: 15955.0,   # parcela "29"  → 534 kWh
    31: 60094.0,   # parcela "30"  → 228 kWh
    32: 57872.0,   # parcela "31"  → 586 kWh
    33:     0.0,   # parcela "32"  →   0 kWh (sin consumo)
    34: 94747.0,   # parcela "33"  → 718 kWh
    35:  3495.0,   # parcela "34"  →   0 kWh (sin consumo)
    36: 95544.0,   # parcela "35"  → 276 kWh
    37: 93566.0,   # parcela "36"  →1080 kWh
    38: 46840.0,   # parcela "37"  → 256 kWh
    39: 100670.0,  # parcela "38"  → 355 kWh
    40: 74279.0,   # parcela "39"  → 307 kWh
    41: 23876.0,   # parcela "40"  → 672 kWh
    42: 16408.0,   # parcela "41"  → 311 kWh
    43: 60216.0,   # parcela "42"  → 320 kWh
    44: 84114.0,   # parcela "43"  → 801 kWh
    45: 26211.0,   # parcela "44"  → 223 kWh
    46: 36047.0,   # parcela "45"  → 830 kWh
    47: 19274.0,   # parcela "46"  → 622 kWh
    48: 25938.0,   # parcela "47"  → 429 kWh
    49: 12550.0,   # parcela "48"  → 450 kWh
    50: 33546.0,   # parcela "49"  → 225 kWh
    51: 50665.0,   # parcela "50"  →   0 kWh (sin consumo)
    52:  9570.0,   # parcela "51"  → 201 kWh
    53: 88622.0,   # parcela "52"  → 824 kWh
    # Σ remarcadores = 21.724 kWh  |  boleta compañía = 24.000 kWh  |  diferencial = 2.276 kWh
}


async def seed_lecturas_marzo_2025(db: AsyncSession) -> None:
    if not LECTURAS_ACTUALES:
        print("  ⚠  lecturas marzo 2025: faltan lecturas_actuales, omitiendo")
        return

    count = 0
    for parcela_id, lectura_anterior in LECTURAS_ANTERIORES.items():
        existe = await db.execute(
            select(LecturaParcela).where(
                LecturaParcela.parcela_id == parcela_id,
                LecturaParcela.boleta_id == BOLETA_ID,
            )
        )
        if existe.scalar_one_or_none():
            continue

        lectura_actual = LECTURAS_ACTUALES.get(parcela_id, lectura_anterior)
        kwh = lectura_actual - lectura_anterior

        db.add(LecturaParcela(
            parcela_id=parcela_id,
            boleta_id=BOLETA_ID,
            lectura_anterior=lectura_anterior,
            lectura_actual=lectura_actual,
            kwh_consumidos=kwh,
            lector_id=LECTOR_ID,
            fecha_toma=FECHA_TOMA,
        ))
        count += 1

    await db.commit()
    print(f"  ✓ lecturas marzo 2025: {count} registros cargados")
