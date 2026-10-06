# Spec Delta

## MODIFIED Requirements

### Requirement: Carga inicial de producción sin datos de prueba

La carga inicial de un condominio en producción DEBE (SHALL) incluir solo su configuración (módulos, color, URL del portal y dominios de la landing), sus parcelas y sus residentes con sus asignaciones a parcelas. NO DEBE (SHALL NOT) incluir datos operativos (boletas, lecturas, liquidaciones, rifas, auditoría), cuentas de prueba ni claves.

Todos los residentes cargados DEBEN (SHALL) quedar como cuentas **pendientes**, sin clave: cada uno crea la suya con su invitación. La carga DEBE (SHALL) ser idempotente.

#### Scenario: Carga sobre una base nueva

- **WHEN** el operador carga Santa Laura en la base de producción recién creada
- **THEN** quedan el condominio con su configuración, sus parcelas y sus residentes asignados, todos pendientes, y ningún período, rifa ni cuenta de prueba

#### Scenario: Repetir la carga

- **WHEN** la carga se ejecuta por segunda vez
- **THEN** no duplica registros ni cambia las cuentas que ya existen

#### Scenario: Nadie conoce una clave tras la carga

- **WHEN** termina la carga
- **THEN** ningún residente puede iniciar sesión hasta crear su clave con el enlace de invitación
