# control-acceso-multitenant Specification

## Purpose

Garantizar que cada usuario solo pueda ejecutar las acciones que su rol permite y solo sobre los datos de su propio condominio. EnerCheck es una plataforma SaaS multitenant: varios condominios comparten la misma instancia y base de datos, por lo que el aislamiento por `condominio_id` y los guardas de rol son la principal defensa contra la fuga de datos entre comunidades. Incluye también la navegación dinámica derivada del rol.

## Requirements

### Requirement: Jerarquía de roles

El sistema DEBE (SHALL) reconocer exactamente cuatro roles: `super_admin`, `admin_condominio`, `lector` y `parcelero`. El rol se resuelve desde el usuario autenticado en cada petición, no desde datos enviados por el cliente.

#### Scenario: Rol no reconocido

- **WHEN** un usuario cuyo rol no pertenece a la lista intenta acceder a un endpoint protegido
- **THEN** el sistema responde `403`

### Requirement: Guardas de rol por endpoint

Cada endpoint DEBE (SHALL) declarar el conjunto de roles autorizados mediante una dependencia. Los conjuntos disponibles son:

- `SuperAdminRequired`: solo `super_admin`
- `AdminRequired`: `super_admin`, `admin_condominio`
- `LectorRequired`: `super_admin`, `admin_condominio`, `lector`
- `AnyRoleRequired`: cualquier rol autenticado

#### Scenario: Rol insuficiente

- **WHEN** un `parcelero` invoca un endpoint declarado como `AdminRequired`
- **THEN** el sistema responde `403` indicando los roles permitidos y no ejecuta la operación

#### Scenario: Rol suficiente

- **WHEN** un `lector` invoca un endpoint declarado como `LectorRequired`
- **THEN** el sistema ejecuta la operación

### Requirement: Resolución del tenant activo

El sistema DEBE (SHALL) derivar el condominio activo del usuario autenticado. Para `super_admin` el tenant es nulo, lo que representa acceso global; para el resto es su `condominio_id`.

#### Scenario: Usuario no super_admin sin condominio asignado

- **WHEN** un usuario cuyo rol no es `super_admin` tiene `condominio_id` nulo e invoca un endpoint que requiere tenant
- **THEN** el sistema responde `403` con el detalle `"Usuario sin condominio asignado. Contacta al administrador."`

#### Scenario: Super admin sin filtro de tenant

- **WHEN** un `super_admin` lista un recurso multitenant
- **THEN** el sistema no aplica filtro por condominio y devuelve los registros de todos los condominios

### Requirement: Aislamiento de datos por condominio

Toda consulta y toda mutación sobre recursos multitenant (parcelas, boletas, lecturas, liquidaciones, usuarios, logs de auditoría) DEBE (SHALL) filtrarse o validarse contra el tenant activo cuando este no es nulo.

#### Scenario: Listado de recursos

- **WHEN** un usuario con tenant definido lista boletas, parcelas, lecturas o liquidaciones
- **THEN** el sistema devuelve exclusivamente los registros cuyo condominio coincide con su tenant

#### Scenario: Acceso directo a un recurso de otro condominio

- **WHEN** un usuario solicita por identificador una boleta, parcela, lectura o liquidación que pertenece a otro condominio
- **THEN** el sistema responde `403` sin exponer el contenido del recurso

### Requirement: Restricción adicional del parcelero a sus parcelas

Además del filtro por condominio, un usuario con rol `parcelero` DEBE (SHALL) ver únicamente los recursos vinculados a las parcelas que tiene asociadas mediante la relación `usuario_parcelas`.

#### Scenario: Parcelero lista parcelas

- **WHEN** un `parcelero` lista parcelas
- **THEN** el sistema devuelve solo las parcelas asociadas a su usuario

#### Scenario: Parcelero accede a la liquidación de otra parcela

- **WHEN** un `parcelero` solicita una liquidación cuya parcela no le pertenece
- **THEN** el sistema responde `403`

### Requirement: Menú de navegación dependiente del rol

El sistema DEBE (SHALL) exponer `GET /api/v1/menus/me`, que devuelve los ítems de menú raíz activos asociados al rol del usuario autenticado, ordenados por el campo `orden`.

#### Scenario: Usuario consulta su menú

- **WHEN** un usuario autenticado solicita su menú
- **THEN** el sistema devuelve solo los ítems activos, sin padre, cuyo rol coincide con el suyo, ordenados ascendentemente por `orden`

### Requirement: Página de inicio según rol en el cliente

El cliente web DEBE (SHALL) redirigir al usuario, tras iniciar sesión, a la pantalla principal de su rol: `/dashboard` para `super_admin` y `admin_condominio`, `/lecturas` para `lector` y `/liquidaciones` para `parcelero`.

#### Scenario: Lector inicia sesión

- **WHEN** un usuario con rol `lector` inicia sesión y navega a la raíz del sitio
- **THEN** el cliente lo redirige a `/lecturas` y muestra la vista móvil de captura

#### Scenario: Rol sin acceso a la vista de lecturas

- **WHEN** un usuario que no es `lector` abre `/lecturas`
- **THEN** el cliente lo redirige a `/dashboard`
