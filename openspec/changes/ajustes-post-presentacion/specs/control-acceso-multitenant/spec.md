# Spec Delta

## MODIFIED Requirements

### Requirement: Jerarquía de roles

El sistema DEBE (SHALL) reconocer exactamente cinco roles: `super_admin`, `admin_condominio`, `lector`, `comunero` y `porteria`. El rol se resuelve desde el usuario autenticado en cada petición, no desde datos enviados por el cliente. El rol `comunero` corresponde al vecino vinculado a una o más parcelas. El rol `porteria` corresponde a una cuenta de un condominio compartida por los turnos de portería, y su acceso se limita a la venta de rifas. El sistema NO DEBE (SHALL NOT) reconocer el nombre `parcelero` como rol.

#### Scenario: Rol no reconocido

- **WHEN** un usuario cuyo rol no pertenece a la lista intenta acceder a un endpoint protegido
- **THEN** el sistema responde `403`

#### Scenario: Portería fuera de su ámbito

- **WHEN** la cuenta de `porteria` invoca un endpoint de boletas, lecturas, liquidaciones, parcelas o usuarios
- **THEN** el sistema responde `403`

#### Scenario: Usuarios existentes tras el cambio de nombre

- **WHEN** se aplica la migración que renombra el rol `parcelero` a `comunero` sobre una base con usuarios de ese rol
- **THEN** esos usuarios quedan con el rol `comunero`, conservan sus parcelas asociadas y sus sesiones abiertas siguen siendo válidas

#### Scenario: Reversa de la migración

- **WHEN** se revierte la migración
- **THEN** el rol vuelve a llamarse `parcelero` y los usuarios conservan su rol y sus parcelas

### Requirement: Guardas de rol por endpoint

Cada endpoint DEBE (SHALL) declarar el conjunto de roles autorizados mediante una dependencia. Los conjuntos disponibles son:

- `SuperAdminRequired`: solo `super_admin`
- `AdminRequired`: `super_admin`, `admin_condominio`
- `LectorRequired`: `super_admin`, `admin_condominio`, `lector`
- `AnyRoleRequired`: `super_admin`, `admin_condominio`, `lector` y `comunero`; NO DEBE (SHALL NOT) incluir a `porteria`
- `PorteriaRequired`: `super_admin`, `admin_condominio`, `porteria`
- `RifaAccesoRequired`: los cinco roles; reservado a los endpoints de consulta de rifas

#### Scenario: Rol insuficiente

- **WHEN** un `comunero` invoca un endpoint declarado como `AdminRequired`
- **THEN** el sistema responde `403` indicando los roles permitidos y no ejecuta la operación

#### Scenario: Rol suficiente

- **WHEN** un `lector` invoca un endpoint declarado como `LectorRequired`
- **THEN** el sistema ejecuta la operación

#### Scenario: Portería en un endpoint para cualquier rol

- **WHEN** la cuenta de `porteria` invoca un endpoint declarado como `AnyRoleRequired`
- **THEN** el sistema responde `403`

#### Scenario: Comunero restringido a sus parcelas

- **WHEN** un `comunero` lista parcelas, boletas, lecturas o liquidaciones
- **THEN** el sistema le entrega solo lo vinculado a sus parcelas, igual que antes del cambio de nombre

### Requirement: Página de inicio según rol en el cliente

El cliente web DEBE (SHALL) redirigir al usuario, tras iniciar sesión, a la pantalla principal de su rol: `/dashboard` para `super_admin` y `admin_condominio`, `/lecturas` para `lector`, `/liquidaciones` para `comunero` y `/porteria` para `porteria`. En toda la interfaz el rol DEBE (SHALL) mostrarse como «Comunero».

#### Scenario: Lector inicia sesión

- **WHEN** un usuario con rol `lector` inicia sesión y navega a la raíz del sitio
- **THEN** el cliente lo redirige a `/lecturas` y muestra la vista móvil de captura

#### Scenario: Rol sin acceso a la vista de lecturas

- **WHEN** un usuario que no es `lector` abre `/lecturas`
- **THEN** el cliente lo redirige a `/dashboard`

#### Scenario: Portería inicia sesión

- **WHEN** la cuenta de `porteria` inicia sesión
- **THEN** el cliente la lleva a `/porteria`, la pantalla de venta de rifas, sin menú de administración

#### Scenario: Comunero inicia sesión

- **WHEN** un usuario con rol `comunero` inicia sesión
- **THEN** el cliente lo lleva a `/liquidaciones` y la cabecera identifica su rol como «Comunero»
