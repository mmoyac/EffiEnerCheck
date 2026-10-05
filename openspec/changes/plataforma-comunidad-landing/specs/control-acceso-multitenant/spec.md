# Spec Delta

## MODIFIED Requirements

### Requirement: Menú de navegación dependiente del rol

El sistema DEBE (SHALL) exponer `GET /api/v1/menus/me`, que devuelve los ítems de menú raíz activos asociados al rol del usuario autenticado, ordenados por el campo `orden`. Cada ítem DEBE (SHALL) indicar el módulo al que pertenece, o ninguno si es del núcleo, y el sistema NO DEBE (SHALL NOT) devolver ítems de módulos que no estén habilitados en el condominio del usuario. Para el `super_admin` no se aplica el filtro por módulo.

#### Scenario: Usuario consulta su menú

- **WHEN** un usuario autenticado solicita su menú
- **THEN** el sistema devuelve solo los ítems activos, sin padre, cuyo rol coincide con el suyo y cuyo módulo está habilitado en su condominio o es del núcleo, ordenados ascendentemente por `orden`

#### Scenario: Menú de un módulo no habilitado

- **WHEN** un `admin_condominio` de un condominio sin el módulo `rifas` solicita su menú
- **THEN** la respuesta no incluye el ítem "Rifas"
