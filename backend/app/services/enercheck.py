"""
Motor EnerCheck — Cálculo de liquidaciones por período.

El valor del kWh se despeja a la inversa desde el Total Emisión para garantizar
que la suma de todas las liquidaciones cuadre exactamente con lo que la compañía
cobró al condominio. Los ítems de detalle vienen con IVA incluido.

Fórmulas (fuente: AGENTS.md §8):
  monto_total_energia = monto_total_emision − (Σ ítems_fijo + Σ ítems_variable)
  valor_kwh           = monto_total_energia / total_kwh_compania
  diferencial         = (total_kwh_compania − Σ kwh_remarcadores) × valor_kwh
  cuota_fija          = Σ ítems_fijo / total_parcelas_activas
  prorrateo_var       = (Σ ítems_variable + diferencial) × (kwh_parcela / Σ kwh_remarcadores)
  monto_energia       = valor_kwh × kwh_parcela
  total_pagar         = monto_energia + prorrateo_var + cuota_fija

El diferencial (energía que la compañía cobró y ningún remarcador registró) se
prorratea según el consumo, igual que los ítems variables: es el criterio de la
planilla con que la administración liquidaba (cambio diferencial-por-consumo).
Si nadie registró consumo, el diferencial y los variables van a la cuota fija, para que el total cuadre.

Clasificación de los ítems:
  fijo        → se reparte en partes iguales entre las parcelas activas
  variable    → se prorratea según los kWh de cada parcela
  informativo → visible en el desglose pero FUERA del reparto
  pendiente   → creado por el OCR, sin clasificar. Tampoco entra al reparto,
                pero no puede llegar hasta acá: el cálculo exige estado
                'validada' y la corroboración exige cero pendientes.

MONTOS NEGATIVOS (descuentos, notas de crédito, abonos)
Se reparten con el mismo criterio de su tipo_calculo, reduciendo la cuota
correspondiente. Las fórmulas NO necesitan caso especial.

No distorsionan el valor_kwh, aunque a primera vista lo parezca. Cuando hay un
descuento, monto_total_emision YA viene rebajado por la compañía; al restar el
ítem negativo de la suma se devuelve esa misma plata al lado de energía, y ambos
efectos se cancelan. Comprobación con un descuento fijo de -40.000:

  sin descuento                    con descuento
    emision   = 1.000.000            emision   =   960.000  (ya rebajada)
    Σ items   =   300.000            Σ items   =   260.000
    energia   =   700.000            energia   =   700.000  ← idéntica
    valor_kwh =        70            valor_kwh =        70  ← idéntico
    cuota_fija=    42.500            cuota_fija=    32.500  ← baja 40.000/4

El descuento aterriza íntegro en la cuota fija, que es donde corresponde, y el
total sigue cuadrando con la emisión.
"""

import math

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.boleta import BoletaMaestra
from app.models.lectura import LecturaParcela
from app.models.liquidacion import LiquidacionParcela
from app.models.parcela import Parcela
from app.models.usuario import Usuario


def repartir_al_peso(montos: list[float], total: int) -> list[int]:
    """
    Reparto por mayor resto: redondea cada monto hacia abajo y entrega los pesos que faltan para llegar a
    `total` a los de mayor fracción. La suma del resultado es exactamente `total` y ningún monto se aleja
    más de un peso de su valor exacto (si `total` es el redondeo de la suma exacta). Funciona con negativos.
    """
    if not montos:
        return []
    pisos = [math.floor(m) for m in montos]
    faltan = total - sum(pisos)
    orden = sorted(range(len(montos)), key=lambda i: montos[i] - pisos[i], reverse=True)
    for k in range(faltan):
        pisos[orden[k % len(montos)]] += 1
    return pisos


class EnerCheckError(ValueError):
    """Error de negocio del Motor EnerCheck."""


async def calcular_liquidaciones_boleta(
    boleta_id: int,
    tenant_id: int | None,
    current_user: Usuario,
    db: AsyncSession,
) -> list[LiquidacionParcela]:
    """
    Calcula y persiste las liquidaciones de todas las parcelas activas
    para el período de la boleta indicada.

    Elimina liquidaciones previas del mismo boleta_id antes de recalcular
    para garantizar idempotencia (se puede volver a correr si hubo un error).
    """
    # ------------------------------------------------------------------ #
    # 1. Cargar boleta con sus ítems de detalle
    # ------------------------------------------------------------------ #
    result = await db.execute(
        select(BoletaMaestra)
        .options(selectinload(BoletaMaestra.items_detalle))
        .where(BoletaMaestra.id == boleta_id)
    )
    boleta = result.scalar_one_or_none()
    if not boleta:
        raise EnerCheckError(f"Boleta {boleta_id} no encontrada")

    if tenant_id is not None and boleta.condominio_id != tenant_id:
        raise EnerCheckError("Sin acceso a esta boleta")

    # Validar que los campos base requeridos estén cargados.
    # total_kwh_compania es el divisor del valor_kwh.
    # monto_neto_electricidad_consumida no entra en las fórmulas, pero se exige
    # como señal de que la boleta fue efectivamente cargada (OCR o manual) antes
    # de liquidar; sin él lo más probable es que monto_total_emision venga en 0.
    if not boleta.total_kwh_compania:
        raise EnerCheckError("La boleta no tiene 'total_kwh_compania' definido")
    if not boleta.monto_neto_electricidad_consumida:
        raise EnerCheckError("La boleta no tiene 'monto_neto_electricidad_consumida' definido")
    # monto_total_emision es lo que se reparte (valor_kwh se despeja desde él): sin él no hay cálculo posible
    if not boleta.monto_total_emision:
        raise EnerCheckError("La boleta no tiene 'monto_total_emision' definido")

    # ------------------------------------------------------------------ #
    # 2. Lecturas del período (indexadas por parcela_id para O(1) lookup)
    # ------------------------------------------------------------------ #
    lecturas_result = await db.execute(
        select(LecturaParcela).where(LecturaParcela.boleta_id == boleta_id)
    )
    lecturas_por_parcela: dict[int, LecturaParcela] = {
        l.parcela_id: l for l in lecturas_result.scalars().all()
    }

    # ------------------------------------------------------------------ #
    # 3. Parcelas activas del condominio
    # ------------------------------------------------------------------ #
    parcelas_result = await db.execute(
        select(Parcela).where(
            Parcela.condominio_id == boleta.condominio_id,
            Parcela.activa == True,  # noqa: E712
        )
    )
    parcelas_activas = parcelas_result.scalars().all()
    total_parcelas_activas = len(parcelas_activas)

    if total_parcelas_activas == 0:
        raise EnerCheckError("No hay parcelas activas en este condominio")

    # ------------------------------------------------------------------ #
    # 4. Valores base compartidos por todas las parcelas
    # ------------------------------------------------------------------ #
    # Clasificar ítems por tipo. Solo 'fijo' y 'variable' entran al reparto:
    # 'informativo' y 'pendiente' quedan fuera por no coincidir con el filtro.
    suma_items_fijo: float = sum(
        i.monto_neto_clp for i in boleta.items_detalle if i.tipo_calculo == "fijo"
    )
    suma_items_variable: float = sum(
        i.monto_neto_clp for i in boleta.items_detalle if i.tipo_calculo == "variable"
    )

    # El valor del kWh se calcula a la inversa para garantizar que el total recaudado 
    # cuadre exactamente con el Total Emisión de la boleta.
    monto_total_energia = boleta.monto_total_emision - (suma_items_fijo + suma_items_variable)
    valor_kwh: float = monto_total_energia / boleta.total_kwh_compania

    suma_kwh_remarcadores: float = sum(
        l.kwh_consumidos for l in lecturas_por_parcela.values()
    )

    # Energía que los remarcadores no capturaron (diferencia boleta vs lecturas)
    diferencial_kwh: float = boleta.total_kwh_compania - suma_kwh_remarcadores
    monto_diferencial: float = diferencial_kwh * valor_kwh

    # Actualizar el ítem informativo del Diferencial si existe
    for item in boleta.items_detalle:
        if "diferencial" in item.descripcion.lower():
            item.monto_neto_clp = round(monto_diferencial)
            db.add(item)

    # El diferencial se prorratea por consumo junto con los ítems variables (cambio
    # diferencial-por-consumo). Sin consumo registrado no hay a quién prorratear: todo va a la cuota fija.
    if suma_kwh_remarcadores > 0:
        monto_a_prorratear = suma_items_variable + monto_diferencial
        fijo_a_repartir = suma_items_fijo
    else:
        monto_a_prorratear = 0.0
        fijo_a_repartir = suma_items_fijo + suma_items_variable + monto_diferencial

    # Cuota fija idéntica para cada parcela activa
    cuota_fija_por_parcela: float = fijo_a_repartir / total_parcelas_activas

    # ------------------------------------------------------------------ #
    # 5. Limpiar liquidaciones previas (recálculo idempotente)
    # ------------------------------------------------------------------ #
    await db.execute(
        delete(LiquidacionParcela).where(LiquidacionParcela.boleta_id == boleta_id)
    )

    # ------------------------------------------------------------------ #
    # 6. Montos por parcela cuadrados al peso (cambio cuadre-al-peso)
    # ------------------------------------------------------------------ #
    # Exactos (sin redondear) por parcela activa
    kwh = [
        (lecturas_por_parcela[p.id].kwh_consumidos if p.id in lecturas_por_parcela else 0.0)
        for p in parcelas_activas
    ]
    energia_exacta = [valor_kwh * k for k in kwh]
    variable_exacta = [
        monto_a_prorratear * (k / suma_kwh_remarcadores) if suma_kwh_remarcadores > 0 else 0.0
        for k in kwh
    ]
    total_exacto = sum(energia_exacta) + sum(variable_exacta) + cuota_fija_por_parcela * total_parcelas_activas

    # La suma de las liquidaciones es el total exacto redondeado UNA vez (= la emisión si todo el consumo
    # es de parcelas activas). Fija igual para todas; variable por mayor resto; la energía completa el cuadre.
    monto_fijo = round(cuota_fija_por_parcela)
    variables = repartir_al_peso(variable_exacta, round(sum(variable_exacta)))
    energia_total = round(total_exacto) - monto_fijo * total_parcelas_activas - sum(variables)
    con_consumo = [i for i, k in enumerate(kwh) if k > 0]
    energias = [0] * total_parcelas_activas
    if con_consumo:
        suma_energia = sum(energia_exacta[i] for i in con_consumo)
        base = ([energia_exacta[i] * energia_total / suma_energia for i in con_consumo] if suma_energia
                else [energia_total / len(con_consumo)] * len(con_consumo))
        for i, monto in zip(con_consumo, repartir_al_peso(base, energia_total)):
            energias[i] = monto
    elif energia_total:
        # Nadie consumió: el residuo del redondeo de la cuota fija se reparte entre todas
        energias = repartir_al_peso([energia_total / total_parcelas_activas] * total_parcelas_activas, energia_total)

    # ------------------------------------------------------------------ #
    # 7. Persistir una liquidación por parcela activa
    # ------------------------------------------------------------------ #
    liquidaciones: list[LiquidacionParcela] = []

    for i, parcela in enumerate(parcelas_activas):
        monto_energia = energias[i]
        monto_variable = variables[i]

        liq = LiquidacionParcela(
            parcela_id=parcela.id,
            boleta_id=boleta_id,
            monto_energia_kwh=monto_energia,
            monto_prorrateo_variable=monto_variable,
            monto_cuota_fija=monto_fijo,
            total_pagar_mes=monto_energia + monto_variable + monto_fijo,
        )
        db.add(liq)
        liquidaciones.append(liq)

    await db.flush()
    return liquidaciones
