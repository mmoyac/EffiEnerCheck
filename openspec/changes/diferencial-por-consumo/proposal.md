# Proposal

## Why

La administración entregó la planilla con que liquida la luz (`MATRIZ_CONSUMO_ELECTRICO`, septiembre 2026) y el sistema debe dar los mismos montos. Hoy no los da: el motor carga el **diferencial** (la energía que la compañía cobró y que ningún remarcador registró) en la **cuota fija**, igual para todas las parcelas. La planilla lo prorratea **según el consumo**, junto con los cargos variables. En septiembre son 3.787 kWh (unos $539.000): con la regla actual una parcela sin consumo pagaría $15.967 en vez de $5.795, y las de mayor consumo pagarían menos de lo que cobra la administración.

## What Changes

- El diferencial se suma a los cargos variables y se prorratea por los kWh de cada parcela. La cuota fija queda solo con los cargos fijos.
- Si nadie registró consumo en el período, no hay a quién prorratear: el diferencial y los cargos variables van a la cuota fija, para que el total siga cuadrando con la emisión.
- Con esto, cada parcela paga `kWh × (emisión − cargos fijos) / Σ kWh + cargos fijos / parcelas activas`, que es el resultado de la planilla.

Verificado en desarrollo con el período de septiembre 2026. La suma cuadra al peso con la emisión ($4.847.112), y cada parcela coincide con la planilla con ±$1 de diferencia. La excepción es la parcela 2, cuya energía la planilla dejó en 0 a mano: el sistema cobra sus 207 kWh. Se considera un error de la planilla y se le avisa a la administración.

## Capabilities

### New Capabilities

_(ninguna)_

### Modified Capabilities

- `motor-liquidaciones`: el diferencial pasa de la cuota fija al prorrateo por consumo.

## Impact

- **Backend:** `services/enercheck.py` y `tests/test_motor.py`.
- **Datos:** ninguno. Las liquidaciones existentes no cambian hasta que se recalcule su período, y los períodos cerrados no se recalculan.
- **Docs:** `CLAUDE.md`, `AGENTS.md`, `README.md`, `docs/flujo-periodo.md` y `.html`, `docs/ayuda-energia.md`, `docs/presentacion-comunidad.md` y el recorrido de Energía del centro de capacitación.
