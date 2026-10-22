# Proposal

## Why

Santa Laura recibió una nueva forma de liquidar la luz (`docs/planillas/MATRIZ CONSUMO ELECTRICO junio_nuevo_calculo.xlsx`): todos los cargos de la boleta, salvo la electricidad consumida, se dividen en partes iguales entre las parcelas (**cargo fijo**), y cada parcela paga además sus kWh a un precio por kWh (**consumo**). La administración quiere poder elegir, período a período, entre esa matriz y la actual (cargos fijos parejos, cargos variables y diferencial según consumo).

La planilla trae dos problemas que el sistema no repite:
- la fila «Cargo Fondo de Estabilización» divide por la fila anterior (`=F6/G5`) en vez de por las parcelas: da $193 en vez de $1.122;
- usa montos sin IVA y un precio por kWh fijo de $138, así que lo cobrado no llega al total de emisión. El sistema despeja el precio por kWh desde la boleta para que la suma cuadre al peso con la emisión, como en la matriz actual.

## What Changes

- Nueva **matriz de cálculo** con dos valores: `fijo_y_variable` (la actual) y `cargo_fijo` (la nueva).
- El condominio tiene su matriz por defecto (`condominios.matriz_calculo_luz`) y cada período la copia al crearse (`boletas_maestras.matriz_calculo`). Los dos los define solo el `super_admin`; la del período se puede cambiar mientras no esté cerrado, y al cambiarla se descartan las liquidaciones calculadas.
- Con `cargo_fijo`, el motor reparte en partes iguales **todos** los ítems que entran al reparto (`fijo` y `variable`); la energía y el diferencial se cobran por kWh a `(emisión − cargo fijo total) / Σ kWh remarcadores`. La liquidación queda en dos componentes (cargo fijo y consumo); el prorrateo variable es 0.
- El detalle del período, el PDF y la vista del comunero muestran la matriz aplicada y el precio por kWh.

## Capabilities

### New Capabilities

_(ninguna)_

### Modified Capabilities

- `motor-liquidaciones`: matriz de cálculo por período.
- `gestion-condominios`: matriz de cálculo por defecto del condominio.

## Impact

- **Backend:** modelos `Condominio` y `BoletaMaestra`, migración, `services/enercheck.py`, `endpoints/boletas.py` (`PUT /boletas/{id}/matriz-calculo`, auditoría `CAMBIAR_MATRIZ_CALCULO`), `endpoints/condominios.py`, `services/reporte_liquidaciones.py`, `db/copiar_desde_desarrollo.py`, tests.
- **Frontend:** `Condominios.tsx`, `BoletaDetalle.tsx`, `MiLiquidacion.tsx`, tipos.
- **Datos:** todo lo existente queda en `fijo_y_variable`; septiembre 2026 (publicado) no cambia.
