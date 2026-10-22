# Spec Delta

## ADDED Requirements

### Requirement: Matriz de cálculo por defecto del condominio

El condominio DEBE (SHALL) tener una matriz de cálculo de la luz por defecto, `fijo_y_variable` o `cargo_fijo`, que define solo el `super_admin` junto con el resto de la parametrización comercial (auditada como `UPDATE_CONDOMINIO`). Cambiarla NO DEBE (SHALL NOT) alterar los períodos ya creados: rige para los períodos que se creen después.

#### Scenario: Condominio nuevo

- **WHEN** se crea un condominio sin indicar la matriz
- **THEN** queda con `fijo_y_variable`

#### Scenario: Cambio de la matriz por defecto

- **WHEN** el `super_admin` cambia la matriz por defecto a `cargo_fijo`
- **THEN** el próximo período que se cree usa `cargo_fijo` y los existentes conservan la suya
