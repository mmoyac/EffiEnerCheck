# autenticacion Specification

## Purpose

Permitir que los usuarios de EnerCheck se identifiquen mediante email y contraseña, y que cada petición posterior a la API viaje autenticada con un token JWT portador (Bearer). Esta capacidad cubre el login, la emisión y validación del token, la recuperación del perfil propio y el manejo de sesión expirada en el cliente web.

## Requirements

### Requirement: Login con email y contraseña

El sistema DEBE (SHALL) exponer `POST /api/v1/auth/token` que recibe credenciales en formato OAuth2 password flow (campos `username` y `password`, donde `username` es el email) y devuelve un token JWT de tipo Bearer cuando las credenciales son válidas.

#### Scenario: Credenciales válidas

- **WHEN** un usuario registrado envía su email en `username` y su contraseña correcta en `password`
- **THEN** el sistema responde `200` con `access_token` y `token_type: "bearer"`
- **AND** actualiza el campo `ultimo_login` del usuario con la marca de tiempo UTC actual

#### Scenario: Credenciales inválidas

- **WHEN** el email no existe o la contraseña no coincide con el hash almacenado
- **THEN** el sistema responde `401` con el detalle `"Email o contraseña incorrectos"` y la cabecera `WWW-Authenticate: Bearer`
- **AND** no revela si el fallo fue por email inexistente o por contraseña errónea

### Requirement: Almacenamiento seguro de contraseñas

El sistema NO DEBE (SHALL NOT) almacenar contraseñas en texto plano. Las contraseñas se guardan como hash bcrypt en `usuarios.password_hash` y solo se comparan mediante verificación de hash.

#### Scenario: Alta o cambio de contraseña

- **WHEN** se crea un usuario o se actualiza su contraseña
- **THEN** el sistema almacena únicamente el hash bcrypt del valor recibido
- **AND** el valor en texto plano nunca se persiste ni se incluye en las respuestas de la API ni en los registros de auditoría

### Requirement: Contenido y vigencia del token JWT

El token emitido DEBE (SHALL) incluir en su payload el identificador del usuario (`sub`), su rol (`rol`), su condominio (`condominio_id`, nulo para `super_admin`) y una expiración (`exp`) configurable mediante `ACCESS_TOKEN_EXPIRE_MINUTES`.

#### Scenario: Token expirado o manipulado

- **WHEN** una petición presenta un token cuya firma no valida o cuya expiración ya pasó
- **THEN** el sistema responde `401` con el detalle `"Credenciales inválidas o token expirado"`

#### Scenario: Token de usuario inexistente

- **WHEN** el token es válido pero el `sub` no corresponde a ningún usuario en la base de datos
- **THEN** el sistema responde `401` y no procesa la petición

### Requirement: Consulta del perfil propio

El sistema DEBE (SHALL) exponer `GET /api/v1/auth/me`, accesible para cualquier rol autenticado, que devuelve el perfil del usuario del token incluyendo su rol y las parcelas asociadas.

#### Scenario: Usuario autenticado consulta su perfil

- **WHEN** un usuario con token válido llama a `GET /auth/me`
- **THEN** el sistema responde con su nombre, email, rol, `condominio_id` y la lista de parcelas vinculadas

### Requirement: Sesión persistente en el cliente web

El frontend DEBE (SHALL) guardar el token en `localStorage`, adjuntarlo como cabecera `Authorization: Bearer <token>` en cada petición y restaurar la sesión al recargar la página consultando `GET /auth/me`.

#### Scenario: Recarga de página con token vigente

- **WHEN** el usuario recarga la aplicación y existe un token en `localStorage`
- **THEN** el cliente muestra un indicador de carga, consulta el perfil y restaura la sesión sin pedir credenciales nuevamente

#### Scenario: Token rechazado por la API

- **WHEN** cualquier petición del cliente recibe una respuesta `401`
- **THEN** el cliente elimina el token de `localStorage` y redirige a `/login`

### Requirement: Protección de rutas del cliente

Las rutas de la aplicación web, salvo `/login`, DEBEN (SHALL) ser inaccesibles sin sesión iniciada.

#### Scenario: Acceso sin sesión

- **WHEN** un visitante sin token abre cualquier ruta protegida
- **THEN** el cliente lo redirige a `/login`
