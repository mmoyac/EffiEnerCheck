# Spec Delta

## MODIFIED Requirements

### Requirement: Listado de usuarios acotado al condominio

El sistema DEBE (SHALL) exponer `GET /api/v1/usuarios/`, restringido a roles administrativos, devolviendo al `super_admin` todos los usuarios y al `admin_condominio` solo los de su condominio. Cada usuario DEBE (SHALL) incluir su rol, sus parcelas asociadas y el **estado de su cuenta**: `pendiente` si no tiene clave o `activa` si la tiene.

#### Scenario: Administrador lista usuarios

- **WHEN** un `admin_condominio` lista usuarios
- **THEN** el sistema devuelve solo los usuarios cuyo `condominio_id` coincide con el suyo

#### Scenario: Lector intenta listar usuarios

- **WHEN** un `lector` invoca el listado de usuarios
- **THEN** el sistema responde `403`

#### Scenario: Estado de la cuenta

- **WHEN** el listado incluye a un parcelero que todavía no crea su clave
- **THEN** ese usuario aparece con estado `pendiente`, y pasa a `activa` cuando la crea

### Requirement: Alta de usuario

El sistema DEBE (SHALL) exponer `POST /api/v1/usuarios/`, restringido a roles administrativos, que crea una cuenta con nombre, email, rol, condominio y, opcionalmente, una contraseña y la lista de parcelas a vincular. Sin contraseña, la cuenta queda **pendiente** hasta que el usuario la cree con una invitación. Si se indica, la contraseña DEBE (SHALL) cumplir la política de claves.

#### Scenario: Administrador crea usuario en su condominio

- **WHEN** un `admin_condominio` crea un usuario sin indicar condominio o indicando el suyo
- **THEN** el sistema fuerza el `condominio_id` del administrador, guarda la contraseña como hash si se indicó, responde `201` y registra la acción `CREATE_USER`

#### Scenario: Alta sin contraseña

- **WHEN** un administrador crea un usuario sin contraseña
- **THEN** la cuenta queda con estado `pendiente` y no puede iniciar sesión hasta crear su clave

#### Scenario: Contraseña débil

- **WHEN** la contraseña indicada tiene menos de 10 caracteres o es una clave conocida
- **THEN** el sistema responde `422` y no crea la cuenta

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

- **WHEN** la petición incluye el campo `password` con una clave que cumple la política
- **THEN** el sistema almacena su hash bcrypt, cierra las sesiones abiertas del usuario y excluye el valor en texto plano del registro de auditoría

#### Scenario: Reemplazo de parcelas vinculadas

- **WHEN** la petición incluye `parcela_ids`
- **THEN** el sistema elimina todos los vínculos previos del usuario y crea únicamente los indicados en la lista

#### Scenario: Administrador modifica usuario de otro condominio

- **WHEN** un `admin_condominio` intenta modificar un usuario de otro condominio
- **THEN** el sistema responde `403` con el detalle `"Sin acceso a este usuario"`
