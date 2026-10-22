# Spec Delta

## ADDED Requirements

### Requirement: Permiso de administración de rifas en la cuenta

Las cuentas DEBEN (SHALL) tener el permiso `administra_rifas`, falso por defecto, que `super_admin` y `admin_condominio` pueden fijar al crear o modificar una cuenta de su condominio. Solo una cuenta `comunero` DEBE (SHALL) poder tenerlo. El listado de usuarios y `/auth/me` DEBEN (SHALL) informarlo, y su cambio DEBE (SHALL) quedar en la auditoría de la modificación de la cuenta con su valor anterior y nuevo.

#### Scenario: Activa el permiso a un comunero

- **WHEN** un `admin_condominio` modifica un comunero de su condominio con `administra_rifas = true`
- **THEN** la cuenta queda con el permiso y la auditoría registra el cambio de `false` a `true`

#### Scenario: Permiso en una cuenta que no es comunero

- **WHEN** se crea o modifica una cuenta de rol distinto de `comunero` con `administra_rifas = true`
- **THEN** el sistema responde `422` y no guarda el cambio

#### Scenario: Cambio de rol de un comunero con el permiso

- **WHEN** se cambia el rol de un comunero con el permiso a otro rol
- **THEN** el sistema quita el permiso de la cuenta

#### Scenario: El comunero consulta su sesión

- **WHEN** un comunero con el permiso consulta `/auth/me`
- **THEN** la respuesta incluye `administra_rifas = true`
