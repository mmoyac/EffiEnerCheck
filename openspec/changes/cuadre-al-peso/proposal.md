# Proposal

## Why

La spec y la documentación prometen que **la suma de las liquidaciones es exactamente el total de emisión**. Pero el motor redondea a pesos cada componente de cada parcela por separado, así que el total puede diferir en hasta ±1,5 pesos por parcela: en un condominio de 53 parcelas, unos $80 al mes. Un comunero o la administración que sume las liquidaciones contra la boleta encontraría una diferencia sin explicación. Hay que cerrarlo antes de salir a producción.

## What Changes

- **Cuadre al peso.** El motor reparte el residuo del redondeo con el método del **mayor resto**, de modo que la suma de `total_pagar_mes` sea exactamente el total de emisión: la suma de los montos exactos, redondeada una sola vez.
- **Cómo se componen las cifras de cada parcela:**
  - **cuota fija:** sigue siendo idéntica para todas las parcelas (el valor exacto redondeado);
  - **prorrateo variable:** se reparte por mayor resto, así que suma exactamente el total de ítems variables, redondeado;
  - **energía:** recibe lo que falta para el cuadre, repartido por mayor resto en proporción al consumo, y solo entre parcelas con consumo. Una parcela sin consumo sigue pagando solo la cuota fija.
- La energía de una parcela puede diferir en un peso del redondeo simple de `valor_kwh × kWh`. Es el costo de cuadrar al peso, y queda documentado.

## Capabilities

### New Capabilities

_(ninguna)_

### Modified Capabilities

- `motor-liquidaciones`: la composición por parcela deja de redondear cada componente por separado. El total cuadra al peso con la emisión.

## Impact

- **Backend:** `services/enercheck.py` (reparto por mayor resto) y `tests/test_motor.py` (el cuadre pasa de una tolerancia de ±1,5 por parcela a igualdad exacta, con casos de redondeo adversos).
- **Datos:** ninguno. Las liquidaciones existentes no cambian hasta que se recalcule su período; los períodos cerrados no se recalculan.
- **Docs:** `CLAUDE.md` (Motor EnerCheck) y `docs/flujo-periodo.md` (la invariante).
