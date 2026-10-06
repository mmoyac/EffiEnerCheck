# Spec Delta

## MODIFIED Requirements

### Requirement: Login con email y contraseña

El sistema DEBE (SHALL) exponer `POST /api/v1/auth/token` que recibe credenciales en formato OAuth2 password flow (campos `username` y `password`, donde `username` es el email) y devuelve un token JWT de tipo Bearer cuando las credenciales son válidas. Una cuenta **pendiente** (sin clave) NO DEBE (SHALL NOT) poder iniciar sesión.

#### Scenario: Credenciales válidas

- **WHEN** un usuario registrado envía su email en `username` y su contraseña correcta en `password`
- **THEN** el sistema responde `200` con `access_token` y `token_type: "bearer"`
- **AND** actualiza el campo `ultimo_login` del usuario con la marca de tiempo UTC actual

#### Scenario: Credenciales inválidas

- **WHEN** el email no existe o la contraseña no coincide con el hash almacenado
- **THEN** el sistema responde `401` con el detalle `"Email o contraseña incorrectos"` y la cabecera `WWW-Authenticate: Bearer`
- **AND** no revela si el fallo fue por email inexistente o por contraseña errónea

#### Scenario: Cuenta pendiente

- **WHEN** alguien intenta iniciar sesión con el email de una cuenta que todavía no tiene clave
- **THEN** el sistema responde exactamente igual que ante credenciales inválidas

### Requirement: Contenido y vigencia del token JWT

El token emitido DEBE (SHALL) incluir en su payload:
- el identificador del usuario (`sub`);
- su rol (`rol`);
- su condominio (`condominio_id`, nulo para `super_admin`);
- su hora de emisión (`iat`);
- una expiración (`exp`) configurable mediante `ACCESS_TOKEN_EXPIRE_MINUTES`.

El sistema DEBE (SHALL) rechazar los tokens emitidos antes del último establecimiento o cambio de clave del usuario.

#### Scenario: Token expirado o manipulado

- **WHEN** una petición presenta un token cuya firma no valida o cuya expiración ya pasó
- **THEN** el sistema responde `401` con el detalle `"Credenciales inválidas o token expirado"`

#### Scenario: Token de usuario inexistente

- **WHEN** el token es válido pero el `sub` no corresponde a ningún usuario en la base de datos
- **THEN** el sistema responde `401` y no procesa la petición

#### Scenario: Token anterior al cambio de clave

- **WHEN** un usuario cambia su clave y otra sesión suya presenta un token emitido antes del cambio
- **THEN** el sistema responde `401` y esa sesión vuelve al login

### Requirement: Protección de rutas del cliente

Las rutas de la aplicación web DEBEN (SHALL) ser inaccesibles sin sesión iniciada, salvo `/login`, `/crear-clave` y `/restablecer-clave`.

#### Scenario: Acceso sin sesión

- **WHEN** un visitante sin token abre cualquier ruta protegida
- **THEN** el cliente lo redirige a `/login`

#### Scenario: Enlace de invitación sin sesión

- **WHEN** un vecino sin sesión abre `/crear-clave#<token>`
- **THEN** el cliente muestra el formulario para crear la clave, sin redirigir a `/login`

## ADDED Requirements

### Requirement: Accesos a la gestión de la clave en el cliente

El cliente web DEBE (SHALL) ofrecer tres accesos:
- en el login, un enlace "¿Olvidaste tu clave?" que pide el email y muestra siempre el mismo mensaje de confirmación;
- en las páginas `/crear-clave` y `/restablecer-clave`, un formulario de clave nueva con confirmación. Al terminar, lleva al login con un aviso de éxito;
- en el menú del usuario con sesión, "Cambiar mi clave".

#### Scenario: Enlace vencido en el cliente

- **WHEN** un vecino abre un enlace vencido o ya usado
- **THEN** el cliente le explica que el enlace no es válido y le ofrece pedir uno nuevo con "¿Olvidaste tu clave?"

#### Scenario: Olvidé mi clave

- **WHEN** un vecino escribe su email en "¿Olvidaste tu clave?"
- **THEN** el cliente muestra "Si el correo está registrado, te enviamos un enlace", haya o no cuenta
