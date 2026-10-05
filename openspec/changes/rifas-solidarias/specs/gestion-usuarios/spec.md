# Spec Delta

## ADDED Requirements

### Requirement: Teléfono de contacto

Las cuentas de usuario DEBEN (SHALL) admitir un teléfono de contacto opcional, que se puede indicar al crear la cuenta y modificar después, y que se devuelve en el listado y el detalle de usuarios. El sistema DEBE (SHALL) guardarlo normalizado en formato internacional chileno, solo con dígitos (por ejemplo `56993327142`).

#### Scenario: Alta con teléfono en formato local

- **WHEN** un administrador crea un usuario con teléfono `9 9332 7142`
- **THEN** el sistema lo guarda como `56993327142`

#### Scenario: Teléfono inválido

- **WHEN** se envía un teléfono que, quitando espacios y signos, no tiene entre 8 y 11 dígitos
- **THEN** el sistema responde `422` y no guarda el cambio

#### Scenario: Cuenta sin teléfono

- **WHEN** se crea un usuario sin teléfono
- **THEN** la cuenta queda con el teléfono sin informar
