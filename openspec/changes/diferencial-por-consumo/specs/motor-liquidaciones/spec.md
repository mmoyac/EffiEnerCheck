# Spec Delta

## MODIFIED Requirements

### Requirement: Diferencial de energía no registrada

El sistema DEBE (SHALL) calcular el diferencial como la energía de la boleta que los remarcadores no capturaron, valorizada al mismo valor del kWh, y prorratearlo según el consumo de cada parcela junto con los cargos variables. La cuota fija DEBE (SHALL) componerse solo de los cargos fijos. Cuando ninguna parcela registró consumo, el diferencial y los cargos variables DEBEN (SHALL) sumarse a la cuota fija, para que el total siga cuadrando con la emisión.

#### Scenario: Fórmula del diferencial y la cuota fija

- **WHEN** el motor se ejecuta y la suma de kWh de los remarcadores es mayor que cero
- **THEN** calcula `diferencial = (total_kwh_compania − Σ kwh_remarcadores) × valor_kwh`, `prorrateo_variable = (Σ cargos variables + diferencial) × (kwh_parcela / Σ kwh_remarcadores)` y `cuota_fija = Σ cargos fijos / total_parcelas_activas`

#### Scenario: Parcela sin consumo

- **WHEN** una parcela activa no registró consumo en un período en que otras sí lo hicieron
- **THEN** paga solo la cuota fija, sin parte del diferencial

#### Scenario: Nadie registró consumo

- **WHEN** la suma de kWh de todos los remarcadores es cero
- **THEN** la cuota fija es `(Σ cargos fijos + Σ cargos variables + diferencial) / total_parcelas_activas` y el prorrateo variable es cero para todas

#### Scenario: Ítem informativo de diferencial

- **WHEN** la boleta contiene un ítem cuya descripción incluye la palabra `diferencial`
- **THEN** el motor actualiza su monto con el diferencial calculado redondeado, dejándolo visible en el desglose de la boleta
