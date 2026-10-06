# Spec Delta

## Purpose

Que cada persona cree y administre su propia clave, sin que nadie más la conozca. Para eso se usan enlaces personales de un solo uso, de invitación o de recuperación, que llegan por correo o que el administrador reenvía por WhatsApp.

## ADDED Requirements

### Requirement: Enlaces de acceso de un solo uso

El sistema DEBE (SHALL) emitir enlaces de acceso de dos tipos: **invitación**, con vigencia de 7 días, y **recuperación**, con vigencia de 1 hora. Cada enlace lleva un token aleatorio de al menos 256 bits.

El sistema DEBE (SHALL) guardar solo el hash del token. Cada enlace DEBE (SHALL) poder usarse una sola vez. Emitir un enlace nuevo para un usuario DEBE (SHALL) anular los enlaces vigentes de ese usuario y del mismo tipo.

#### Scenario: Enlace usado

- **WHEN** un usuario establece su clave con un enlace
- **THEN** el enlace queda marcado como usado y un segundo intento con el mismo enlace responde `410` con el detalle `"El enlace ya fue usado o venció"`

#### Scenario: Enlace vencido

- **WHEN** se intenta usar un enlace de recuperación emitido hace más de una hora
- **THEN** el sistema responde `410` y la clave no cambia

#### Scenario: Reenvío de invitación

- **WHEN** un administrador reenvía la invitación a un usuario que ya tenía una vigente
- **THEN** solo el enlace nuevo sirve y el anterior responde `410`

#### Scenario: Token en la base de datos

- **WHEN** alguien lee la tabla de enlaces
- **THEN** encuentra solo hashes, y con ellos no puede reconstruir ningún enlace utilizable

### Requirement: El token no viaja en la ruta de la URL

El enlace DEBE (SHALL) tener la forma `<portal_url>/crear-clave#<token>` (invitación) o `<portal_url>/restablecer-clave#<token>` (recuperación). El cliente DEBE (SHALL) enviar el token a la API solo en el cuerpo de las peticiones, de modo que no quede registrado en los logs de los servidores web ni se filtre en el encabezado `Referer`.

`portal_url` DEBE (SHALL) ser la URL del portal del condominio del usuario o, si el usuario no tiene condominio o el condominio no la tiene configurada, el valor de `PORTAL_URL_POR_DEFECTO`.

#### Scenario: Enlace de un residente de Santa Laura

- **WHEN** se invita a un parcelero de un condominio cuyo `portal_url` es `https://portal.comunidadsantalaura.cl`
- **THEN** el enlace es `https://portal.comunidadsantalaura.cl/crear-clave#<token>`

### Requirement: Invitación por un administrador

El sistema DEBE (SHALL) permitir que un `super_admin`, o un `admin_condominio` sobre los usuarios de su condominio, invite a un usuario cuya cuenta está **pendiente** (sin clave). La invitación emite un enlace de invitación y, si el administrador lo elige, lo envía por correo al email de la cuenta. Si elige no enviar correo, el enlace se emite igual, sin gastar un envío, para compartirlo por WhatsApp o copiarlo.

El portal DEBE (SHALL) pedir al administrador que elija el canal (correo, o solo WhatsApp y enlace) antes de emitir la invitación, mostrando el correo y el teléfono de la cuenta.

La respuesta DEBE (SHALL) incluir el enlace, para que el administrador pueda reenviarlo por WhatsApp, e indicar si el correo se envió.

#### Scenario: Invitación enviada por correo

- **WHEN** un `admin_condominio` invita a un parcelero pendiente de su condominio y el correo está configurado
- **THEN** el usuario recibe el correo con el enlace, la respuesta indica `correo_enviado: true` e incluye el enlace, y se registra `INVITACION_ENVIADA` sin el token

#### Scenario: Invitación solo por enlace

- **WHEN** el administrador elige «Solo WhatsApp / enlace»
- **THEN** no se envía ningún correo, la respuesta incluye el enlace y se registra `INVITACION_ENVIADA` con el canal `enlace`

#### Scenario: Correo no configurado o rechazado

- **WHEN** el servicio de correo no está configurado o rechaza el envío
- **THEN** la invitación se emite igual, la respuesta indica `correo_enviado: false` con el motivo e incluye el enlace para enviarlo por WhatsApp

#### Scenario: Usuario con clave

- **WHEN** se intenta invitar a un usuario que ya tiene clave
- **THEN** el sistema responde `409` con el detalle `"La cuenta ya está activa: el usuario puede usar «¿Olvidaste tu clave?»"`

#### Scenario: Usuario de otro condominio

- **WHEN** un `admin_condominio` intenta invitar a un usuario de otro condominio
- **THEN** el sistema responde `403` con el detalle `"Sin acceso a este usuario"`

### Requirement: Invitación masiva de pendientes

El sistema DEBE (SHALL) permitir que un administrador invite de una vez a todos los usuarios pendientes de un condominio: el suyo, en el caso del `admin_condominio`, o el que indique el `super_admin`. La respuesta DEBE (SHALL) informar cuántos correos se enviaron y cuántos fallaron, sin incluir enlaces.

#### Scenario: Invitar a todos los pendientes

- **WHEN** el administrador de Santa Laura invita a todos los pendientes y hay 69
- **THEN** se emite y se envía por correo una invitación a cada uno, y la respuesta informa `enviados: 69, fallidos: 0`

#### Scenario: Sin correo configurado

- **WHEN** el servicio de correo no está configurado
- **THEN** el sistema responde `503` con el detalle `"El envío de correos no está configurado"` y no emite ningún enlace

### Requirement: Envío de la invitación por WhatsApp

La pantalla Usuarios DEBE (SHALL) ofrecer, para cada invitación emitida, un botón que abra WhatsApp (`https://wa.me/<telefono>`) con un mensaje que incluya el nombre del condominio y el enlace. El sistema NO DEBE (SHALL NOT) enviar mensajes de WhatsApp por sí mismo.

#### Scenario: Usuario con teléfono

- **WHEN** el administrador invita a un usuario con teléfono `56912345678`
- **THEN** la pantalla muestra el botón WhatsApp, que abre `wa.me/56912345678` con el mensaje y el enlace

#### Scenario: Usuario sin teléfono

- **WHEN** el usuario no tiene teléfono registrado
- **THEN** el botón WhatsApp no se muestra y el administrador puede copiar el enlace

### Requirement: Recuperación de clave

El sistema DEBE (SHALL) exponer `POST /api/v1/auth/recuperar`, sin autenticación, que recibe un email y, si corresponde a una cuenta de un condominio con portal, emite un enlace de recuperación y lo envía por correo.

La respuesta DEBE (SHALL) ser siempre `202` con el mismo cuerpo, exista o no la cuenta. La frecuencia de peticiones por IP DEBE (SHALL) estar limitada.

#### Scenario: Email registrado

- **WHEN** un vecino pide recuperar la clave con su email
- **THEN** recibe un correo con un enlace de restablecimiento, la API responde `202` y se registra `RECUPERACION_SOLICITADA`

#### Scenario: Email no registrado

- **WHEN** se pide recuperar la clave de un email que no existe
- **THEN** la API responde exactamente lo mismo que con un email registrado y no envía nada

#### Scenario: Cuenta pendiente

- **WHEN** pide recuperar la clave un usuario que nunca la creó
- **THEN** recibe igualmente un enlace con el que puede crearla

### Requirement: Verificación y uso del enlace

El sistema DEBE (SHALL) exponer, sin autenticación:
- `POST /api/v1/auth/verificar-enlace`: recibe el token y responde el tipo de enlace y el nombre del usuario si es válido, o `410` si no;
- `POST /api/v1/auth/establecer-clave`: recibe el token y la clave nueva, aplica la política de claves, guarda la clave, marca el enlace como usado, cierra las sesiones abiertas del usuario y registra `CLAVE_ESTABLECIDA`.

Ambos con frecuencia limitada por IP.

#### Scenario: Vecino crea su clave

- **WHEN** un vecino abre su invitación vigente y escribe una clave válida
- **THEN** la cuenta queda activa, el enlace queda usado y el vecino puede iniciar sesión con su email y esa clave

#### Scenario: Clave que no cumple la política

- **WHEN** la clave nueva tiene menos de 10 caracteres o es una clave conocida
- **THEN** el sistema responde `422` con el motivo y el enlace sigue vigente

### Requirement: Cambio de la propia clave

El sistema DEBE (SHALL) exponer `POST /api/v1/auth/cambiar-clave`, para cualquier usuario autenticado, que recibe la clave actual y la nueva. Si la actual es correcta y la nueva cumple la política, la guarda, cierra las demás sesiones del usuario, registra `CLAVE_CAMBIADA` y entrega un token nuevo para la sesión en curso.

#### Scenario: Cambio correcto

- **WHEN** un parcelero escribe su clave actual y una nueva válida
- **THEN** la clave cambia, su sesión sigue abierta con el token nuevo y las sesiones en otros dispositivos se cierran

#### Scenario: Clave actual incorrecta

- **WHEN** la clave actual no coincide
- **THEN** el sistema responde `400` con el detalle `"La clave actual no es correcta"` y nada cambia

### Requirement: Política de claves

Toda clave que se guarde DEBE (SHALL) tener al menos 10 caracteres y NO DEBE (SHALL NOT) ser una de las claves conocidas del sistema (por ejemplo, la de los datos de prueba). Esto vale tanto para la que crea el propio usuario como para la que asigna un administrador.

#### Scenario: Clave de los datos de prueba

- **WHEN** alguien intenta establecer `admin123` como clave
- **THEN** el sistema la rechaza con `422`

### Requirement: Correo transaccional

El sistema DEBE (SHALL) enviar los correos de invitación y recuperación desde la dirección configurada en `EMAIL_REMITENTE`, con el nombre del condominio del usuario como nombre visible y una versión en texto plano. Los correos DEBEN (SHALL) incluir el enlace, su vigencia y una indicación de ignorarlo si no se solicitó. Ni el token ni el contenido del correo DEBEN (SHALL) quedar en los logs ni en la auditoría.

#### Scenario: Correo de invitación

- **WHEN** se invita a un parcelero de Santa Laura
- **THEN** el correo llega de "Santa Laura <EMAIL_REMITENTE>", con el enlace para crear la clave y la vigencia de 7 días
