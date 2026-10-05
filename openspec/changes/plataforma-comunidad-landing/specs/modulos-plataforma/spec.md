# Spec Delta

## Purpose

Permitir que el `super_admin` defina, para cada condominio cliente, qué productos tiene contratados (landing, administración o ambos) y qué módulos usa dentro de la administración (energía, rifas), y que esa parametrización se respete en la navegación y en la API.

## ADDED Requirements

### Requirement: Catálogo de módulos

El sistema DEBE (SHALL) reconocer un catálogo fijo de módulos:

- `sitio`: la landing pública del condominio, un producto aparte (ver la capacidad `sitio-publico`).
- `portal`: el portal de administración, que da a los usuarios del condominio acceso con login y a las funciones del núcleo (usuarios, parcelas, panel inicial y auditoría).
- `energia`: boletas, lecturas, liquidaciones y el Motor EnerCheck, dentro del portal.
- `rifas`: rifas solidarias, venta en portería y sus exportaciones, dentro del portal.

Los módulos `energia` y `rifas` DEBEN (SHALL) exigir el módulo `portal`.

#### Scenario: Módulo desconocido

- **WHEN** un `super_admin` intenta habilitar en un condominio un módulo que no pertenece al catálogo
- **THEN** el sistema responde `422` y no modifica los módulos del condominio

#### Scenario: Módulo del portal sin portal

- **WHEN** un `super_admin` intenta dejar un condominio con `energia` habilitado y sin `portal`
- **THEN** el sistema responde `422` con el detalle `"Los módulos energia y rifas requieren el módulo portal"`

### Requirement: Productos contratados por condominio

Cada condominio DEBE (SHALL) tener un conjunto de módulos habilitados, sin repetidos, que define su contratación: **solo administración** (`portal` sin `sitio`), **solo landing** (`sitio` sin `portal`) o **ambos**. Solo el `super_admin` DEBE (SHALL) poder modificarlo. Los condominios existentes antes de este cambio DEBEN (SHALL) quedar con los cuatro módulos habilitados.

#### Scenario: Condominio existente tras la migración

- **WHEN** se aplica la migración en una base con condominios ya registrados
- **THEN** cada condominio queda con `sitio`, `portal`, `energia` y `rifas` habilitados

#### Scenario: Condominio solo con administración

- **WHEN** un condominio tiene `portal` y `energia`, pero no `sitio`
- **THEN** sus usuarios usan el portal con normalidad y `GET /api/v1/sitio` no devuelve un sitio para sus dominios

### Requirement: Acceso al portal según contratación

Si el condominio de un usuario no tiene habilitado el módulo `portal`, el sistema DEBE (SHALL) rechazar su inicio de sesión y toda petición autenticada con `403` y el detalle `"Tu condominio no tiene contratado el portal de administración"`. El `super_admin` NO DEBE (SHALL NOT) verse afectado.

#### Scenario: Usuario de un condominio solo con landing

- **WHEN** un `admin_condominio` de un condominio que solo tiene `sitio` intenta iniciar sesión
- **THEN** el sistema responde `403` con el detalle `"Tu condominio no tiene contratado el portal de administración"`

#### Scenario: Portal deshabilitado con una sesión abierta

- **WHEN** el `super_admin` quita `portal` a un condominio mientras un usuario suyo tiene sesión
- **THEN** la siguiente petición de ese usuario responde `403`

### Requirement: Guarda de módulo en la API

Los endpoints de boletas, lecturas y liquidaciones DEBEN (SHALL) exigir el módulo `energia`, y los endpoints de rifas el módulo `rifas`, además de su guarda de rol. Si el condominio del usuario no tiene habilitado el módulo, el sistema DEBE (SHALL) responder `403` con el detalle `"El módulo <nombre> no está habilitado para este condominio"` sin ejecutar la operación. El `super_admin` NO DEBE (SHALL NOT) ser bloqueado por esta guarda.

#### Scenario: Endpoint de un módulo no habilitado

- **WHEN** un `admin_condominio` de un condominio sin el módulo `energia` lista boletas
- **THEN** el sistema responde `403` con el detalle `"El módulo energia no está habilitado para este condominio"`

#### Scenario: Endpoint de un módulo habilitado

- **WHEN** un `parcelero` de un condominio con `rifas` habilitado consulta la rifa abierta
- **THEN** el sistema aplica solo las reglas de rol y tenant habituales

#### Scenario: Super admin

- **WHEN** un `super_admin` invoca un endpoint de cualquier módulo
- **THEN** la guarda de módulo no lo bloquea

#### Scenario: Rol autorizado no basta

- **WHEN** la cuenta de `porteria` de un condominio sin `rifas` intenta registrar una venta
- **THEN** el sistema responde `403`, aunque el rol `porteria` esté autorizado en ese endpoint

#### Scenario: Núcleo sin módulos de negocio

- **WHEN** un `admin_condominio` de un condominio con `portal` pero sin `energia` ni `rifas` consulta parcelas o usuarios
- **THEN** el sistema ejecuta la operación con las reglas habituales de rol y tenant

### Requirement: Módulos informados al cliente

`GET /api/v1/auth/me` DEBE (SHALL) incluir el campo `modulos` con la lista de módulos habilitados del condominio del usuario. Para el `super_admin` DEBE (SHALL) incluir el catálogo completo.

#### Scenario: Usuario de un condominio con módulos

- **WHEN** un `parcelero` de un condominio con `portal`, `energia` y `rifas` consulta su sesión
- **THEN** la respuesta incluye `modulos` con exactamente `portal`, `energia` y `rifas`

### Requirement: Cliente respeta los módulos habilitados

El portal NO DEBE (SHALL NOT) mostrar menús, accesos ni avisos de un módulo no habilitado, y DEBE (SHALL) redirigir a la pantalla de inicio cuando se abre directamente una ruta de un módulo no habilitado. Cuando la pantalla principal de un rol pertenece a un módulo no habilitado, la pantalla de inicio DEBE (SHALL) usar una alternativa habilitada: para `parcelero`, sus rifas si no tiene `energia`; para `admin_condominio`, el panel inicial sin los indicadores de energía.

#### Scenario: Ruta de un módulo no habilitado

- **WHEN** un `admin_condominio` de un condominio sin `rifas` abre `/rifas`
- **THEN** el portal lo redirige a su pantalla de inicio

#### Scenario: Parcelero sin módulo de energía

- **WHEN** un `parcelero` de un condominio que tiene `portal` y `rifas`, pero no `energia`, inicia sesión
- **THEN** el portal lo lleva a `/mis-rifas`

#### Scenario: Panel sin energía

- **WHEN** un `admin_condominio` de un condominio sin `energia` abre el panel inicial
- **THEN** el panel no muestra indicadores ni boletas del período y no consulta endpoints de energía

### Requirement: Menú agrupado por módulo

El menú lateral del portal DEBE (SHALL) agrupar los ítems bajo encabezados según su módulo: "Energía" para `energia`, "Comunidad" para `rifas` y "Administración" para el núcleo. DEBE (SHALL) mostrar el logo y el nombre del condominio del usuario como identidad del portal, o solo el nombre si no tiene logo. Los acentos del portal (botones, menú activo, enlaces e indicadores) DEBEN (SHALL) tomar el color institucional del condominio del usuario y conservar un contraste legible sobre el fondo del portal; el `super_admin` ve el color por defecto de la plataforma. "EnerCheck" DEBE (SHALL) identificar al módulo de energía y no a la plataforma completa.

#### Scenario: Administrador con todos los módulos

- **WHEN** un `admin_condominio` con `energia` y `rifas` habilitados abre el portal
- **THEN** el menú muestra las boletas bajo "Energía", las rifas bajo "Comunidad", y usuarios y parcelas bajo "Administración"
