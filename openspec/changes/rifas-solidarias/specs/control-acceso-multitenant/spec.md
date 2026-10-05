# Spec Delta

## MODIFIED Requirements

### Requirement: Jerarquía de roles

El sistema DEBE (SHALL) reconocer exactamente cinco roles: `super_admin`, `admin_condominio`, `lector`, `parcelero` y `porteria`. El rol se resuelve desde el usuario autenticado en cada petición, no desde datos enviados por el cliente. El rol `porteria` corresponde a una cuenta de un condominio compartida por los turnos de portería, y su acceso se limita a la venta de rifas.

#### Scenario: Rol no reconocido

- **WHEN** un usuario cuyo rol no pertenece a la lista intenta acceder a un endpoint protegido
- **THEN** el sistema responde `403`

#### Scenario: Portería fuera de su ámbito

- **WHEN** la cuenta de `porteria` invoca un endpoint de boletas, lecturas, liquidaciones, parcelas o usuarios
- **THEN** el sistema responde `403`

### Requirement: Guardas de rol por endpoint

Cada endpoint DEBE (SHALL) declarar el conjunto de roles autorizados mediante una dependencia. Los conjuntos disponibles son:

- `SuperAdminRequired`: solo `super_admin`
- `AdminRequired`: `super_admin`, `admin_condominio`
- `LectorRequired`: `super_admin`, `admin_condominio`, `lector`
- `AnyRoleRequired`: `super_admin`, `admin_condominio`, `lector` y `parcelero`; NO DEBE (SHALL NOT) incluir a `porteria`
- `PorteriaRequired`: `super_admin`, `admin_condominio`, `porteria`
- `RifaAccesoRequired`: los cinco roles; reservado a los endpoints de consulta de rifas

#### Scenario: Rol insuficiente

- **WHEN** un `parcelero` invoca un endpoint declarado como `AdminRequired`
- **THEN** el sistema responde `403` indicando los roles permitidos y no ejecuta la operación

#### Scenario: Rol suficiente

- **WHEN** un `lector` invoca un endpoint declarado como `LectorRequired`
- **THEN** el sistema ejecuta la operación

#### Scenario: Portería en un endpoint para cualquier rol

- **WHEN** la cuenta de `porteria` invoca un endpoint declarado como `AnyRoleRequired`
- **THEN** el sistema responde `403`

### Requirement: Página de inicio según rol en el cliente

El cliente web DEBE (SHALL) redirigir al usuario, tras iniciar sesión, a la pantalla principal de su rol: `/dashboard` para `super_admin` y `admin_condominio`, `/lecturas` para `lector`, `/liquidaciones` para `parcelero` y `/porteria` para `porteria`.

#### Scenario: Lector inicia sesión

- **WHEN** un usuario con rol `lector` inicia sesión y navega a la raíz del sitio
- **THEN** el cliente lo redirige a `/lecturas` y muestra la vista móvil de captura

#### Scenario: Rol sin acceso a la vista de lecturas

- **WHEN** un usuario que no es `lector` abre `/lecturas`
- **THEN** el cliente lo redirige a `/dashboard`

#### Scenario: Portería inicia sesión

- **WHEN** la cuenta de `porteria` inicia sesión
- **THEN** el cliente la lleva a `/porteria`, la pantalla de venta de rifas, sin menú de administración
