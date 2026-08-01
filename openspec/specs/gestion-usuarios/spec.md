# gestion-usuarios Specification

## Purpose

Administrar las cuentas de acceso a EnerCheck y su vinculación con roles y parcelas. Un `admin_condominio` gestiona las cuentas de su propia comunidad; el `super_admin` gestiona las de cualquier condominio y es el único que puede eliminar cuentas. Un usuario con rol `parcelero` puede estar vinculado a una o varias parcelas mediante una relación muchos a muchos.

## Requirements

### Requirement: Listado de usuarios acotado al condominio

El sistema DEBE (SHALL) exponer `GET /api/v1/usuarios/`, restringido a roles administrativos, devolviendo al `super_admin` todos los usuarios y al `admin_condominio` solo los de su condominio, incluyendo en cada uno su rol y sus parcelas asociadas.

#### Scenario: Administrador lista usuarios

- **WHEN** un `admin_condominio` lista usuarios
- **THEN** el sistema devuelve solo los usuarios cuyo `condominio_id` coincide con el suyo

#### Scenario: Lector intenta listar usuarios

- **WHEN** un `lector` invoca el listado de usuarios
- **THEN** el sistema responde `403`

### Requirement: Alta de usuario

El sistema DEBE (SHALL) exponer `POST /api/v1/usuarios/`, restringido a roles administrativos, que crea una cuenta con nombre, email, contraseña, rol, condominio y, opcionalmente, la lista de parcelas a vincular.

#### Scenario: Administrador crea usuario en su condominio

- **WHEN** un `admin_condominio` crea un usuario sin indicar condominio o indicando el suyo
- **THEN** el sistema fuerza el `condominio_id` del administrador, guarda la contraseña como hash, responde `201` y registra la acción `CREATE_USER`

#### Scenario: Administrador intenta crear usuario en otro condominio

- **WHEN** un `admin_condominio` envía un `condominio_id` distinto al suyo
- **THEN** el sistema responde `403` con el detalle `"No puede crear usuarios en otro condominio"`

#### Scenario: Email ya registrado

- **WHEN** el email enviado ya pertenece a otra cuenta
- **THEN** el sistema responde `409` con el detalle `"El email ya está registrado"` y no crea la cuenta

#### Scenario: Alta con parcelas vinculadas

- **WHEN** se crea un usuario indicando una lista de identificadores de parcela
- **THEN** el sistema registra los vínculos en `usuario_parcelas` y los devuelve en la respuesta

### Requirement: Modificación de usuario

El sistema DEBE (SHALL) exponer `PATCH /api/v1/usuarios/{usuario_id}`, restringido a roles administrativos, que aplica actualizaciones parciales sobre los datos de la cuenta y sobre sus parcelas vinculadas.

#### Scenario: Cambio de contraseña

- **WHEN** la petición incluye el campo `password`
- **THEN** el sistema almacena su hash bcrypt y excluye el valor en texto plano del registro de auditoría

#### Scenario: Reemplazo de parcelas vinculadas

- **WHEN** la petición incluye `parcela_ids`
- **THEN** el sistema elimina todos los vínculos previos del usuario y crea únicamente los indicados en la lista

#### Scenario: Administrador modifica usuario de otro condominio

- **WHEN** un `admin_condominio` intenta modificar un usuario de otro condominio
- **THEN** el sistema responde `403` con el detalle `"Sin acceso a este usuario"`

### Requirement: Eliminación de usuario reservada al super admin

El sistema DEBE (SHALL) exponer `DELETE /api/v1/usuarios/{usuario_id}` restringido exclusivamente a `super_admin`.

#### Scenario: Super admin elimina una cuenta

- **WHEN** un `super_admin` elimina un usuario existente
- **THEN** el sistema registra la acción `DELETE_USER` con el email de la cuenta y responde `204`

#### Scenario: Administrador de condominio intenta eliminar

- **WHEN** un `admin_condominio` invoca la eliminación de un usuario
- **THEN** el sistema responde `403` y la cuenta permanece intacta
