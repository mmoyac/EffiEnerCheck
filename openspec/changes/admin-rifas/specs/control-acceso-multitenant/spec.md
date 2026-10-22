# Spec Delta

## ADDED Requirements

### Requirement: Guarda de administración de rifas

Las operaciones de administración de rifas DEBEN (SHALL) autorizarse con una guarda propia que admite a `super_admin`, a `admin_condominio` y a un `comunero` con el permiso `administra_rifas`. El permiso se DEBE (SHALL) leer de la cuenta en cada petición, no del token, de modo que quitarlo rija de inmediato también en sesiones abiertas. Las guardas generales de administración NO DEBEN (SHALL NOT) admitir el permiso.

#### Scenario: Permiso quitado con la sesión abierta

- **WHEN** la administración quita el permiso a un comunero que tiene la sesión abierta y este intenta cerrar una rifa
- **THEN** el sistema responde `403`

#### Scenario: Endpoint general de administración

- **WHEN** un comunero con el permiso invoca un endpoint declarado para `super_admin` y `admin_condominio`
- **THEN** el sistema responde `403`

### Requirement: Menú del comunero con permiso de administración de rifas

`GET /api/v1/menus/me` DEBE (SHALL) incluir el ítem de menú de Rifas para un comunero con el permiso `administra_rifas`, si su condominio tiene contratado el módulo `rifas`.

#### Scenario: Comunero con el permiso

- **WHEN** un comunero con el permiso, de un condominio con el módulo `rifas`, consulta su menú
- **THEN** recibe sus ítems de comunero más el ítem de Rifas

#### Scenario: Comunero sin el permiso

- **WHEN** un comunero sin el permiso consulta su menú
- **THEN** no recibe el ítem de administración de Rifas
