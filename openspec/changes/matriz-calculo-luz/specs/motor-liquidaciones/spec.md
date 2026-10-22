# Spec Delta

## ADDED Requirements

### Requirement: Matriz de cálculo del período

Cada período regular DEBE (SHALL) tener una matriz de cálculo, `fijo_y_variable` o `cargo_fijo`, copiada al crearlo desde la matriz por defecto del condominio. Solo el `super_admin` DEBE (SHALL) poder cambiarla, y solo mientras las liquidaciones del período no estén cerradas; el cambio DEBE (SHALL) descartar las liquidaciones calculadas y quedar auditado como `CAMBIAR_MATRIZ_CALCULO`. Con cualquiera de las dos matrices, la suma de las liquidaciones DEBE (SHALL) cuadrar al peso con el total de emisión.

#### Scenario: Matriz fijo y variable

- **WHEN** el motor calcula un período con matriz `fijo_y_variable`
- **THEN** los ítems `fijo` van en partes iguales y los `variable`, junto con el diferencial, según el consumo de cada parcela

#### Scenario: Matriz cargo fijo

- **WHEN** el motor calcula un período con matriz `cargo_fijo`
- **THEN** el cargo fijo de cada parcela es `(Σ ítems fijo + Σ ítems variable) / total_parcelas_activas`, el consumo es `kwh_parcela × (emisión − cargo fijo total) / Σ kwh_remarcadores` y el prorrateo variable es cero

#### Scenario: Cambio de matriz con el período abierto

- **WHEN** el `super_admin` cambia la matriz de un período con liquidaciones calculadas y no cerradas
- **THEN** la matriz cambia, las liquidaciones se descartan y hay que volver a calcular

#### Scenario: Cambio de matriz con el período cerrado

- **WHEN** alguien intenta cambiar la matriz de un período con las liquidaciones cerradas
- **THEN** el sistema responde 409 y la matriz no cambia

#### Scenario: Cambio de matriz sin ser super_admin

- **WHEN** un `admin_condominio` intenta cambiar la matriz de un período
- **THEN** el sistema responde 403
