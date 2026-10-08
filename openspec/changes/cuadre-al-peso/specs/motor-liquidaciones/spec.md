# Spec Delta

## ADDED Requirements

### Requirement: Cuadre al peso con el total de emisión

La suma de `total_pagar_mes` de todas las liquidaciones de un período DEBE (SHALL) ser exactamente la suma de los montos sin redondear de todas las parcelas, redondeada una sola vez al peso. Cuando todo el consumo registrado es de parcelas activas, esa suma es el total de emisión. El residuo del redondeo DEBE (SHALL) repartirse con el método del mayor resto, sin que ninguna parcela reciba más de un peso de ajuste por componente.

#### Scenario: Redondeos que no cuadran por separado

- **WHEN** los montos exactos de varias parcelas tienen fracciones que, redondeadas una a una, sumarían un peso de más o de menos
- **THEN** el motor asigna los pesos del residuo a las parcelas con mayor fracción, y la suma de las liquidaciones es exactamente el total de emisión

## MODIFIED Requirements

### Requirement: Composición de la liquidación de cada parcela

Para cada parcela activa el sistema DEBE (SHALL) calcular tres componentes en pesos enteros y su total como la suma de los tres:
- la **cuota fija**, idéntica para todas las parcelas (el valor exacto redondeado);
- el **prorrateo variable**, repartido por mayor resto para que sume exactamente el total de cargos variables, redondeado;
- la **energía**, que completa el cuadre con la emisión, repartida por mayor resto en proporción al consumo y solo entre parcelas con consumo.

#### Scenario: Fórmula por parcela

- **WHEN** el motor procesa una parcela activa con un consumo registrado
- **THEN** calcula `monto_energia ≈ valor_kwh × kwh_parcela`, `prorrateo_variable ≈ Σ cargos variables × (kwh_parcela / Σ kwh_remarcadores)` y `cuota_fija` igual para todas, cada uno en pesos enteros con a lo más un peso de ajuste por el reparto del residuo, y fija `total_pagar_mes` como la suma de los tres

#### Scenario: Parcela activa sin lectura

- **WHEN** una parcela activa no tiene lectura registrada en el período
- **THEN** el motor la trata con consumo cero, por lo que solo se le imputa la cuota fija

#### Scenario: Sin consumo registrado en el condominio

- **WHEN** la suma de kWh de todos los remarcadores es cero
- **THEN** el motor asigna prorrateo variable cero a todas las parcelas y evita la división por cero
