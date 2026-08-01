# gestion-condominios Specification

## Purpose

Administrar las comunidades (condominios) que operan sobre la plataforma. Cada condominio es el tenant raíz del que cuelgan parcelas, usuarios, boletas, lecturas y liquidaciones. Solo el `super_admin` da de alta y modifica condominios; los demás roles únicamente pueden consultar el suyo.

## Requirements

### Requirement: Alta de condominio

El sistema DEBE (SHALL) exponer `POST /api/v1/condominios/`, restringido a `super_admin`, que crea un condominio con nombre, RUT de comunidad, dirección opcional y plan de suscripción.

#### Scenario: Creación con RUT nuevo

- **WHEN** un `super_admin` envía los datos de un condominio cuyo RUT no está registrado
- **THEN** el sistema crea el condominio con `activo` en verdadero y responde `201` con el registro creado

#### Scenario: RUT duplicado

- **WHEN** un `super_admin` intenta crear un condominio con un `rut_comunidad` ya existente
- **THEN** el sistema responde `409` con el detalle `"RUT de comunidad ya registrado"` y no crea el registro

#### Scenario: Rol sin permiso

- **WHEN** un `admin_condominio` intenta crear un condominio
- **THEN** el sistema responde `403`

### Requirement: Consulta de condominios acotada al propio

El sistema DEBE (SHALL) exponer `GET /api/v1/condominios/` para cualquier rol autenticado, devolviendo todos los condominios al `super_admin` y únicamente el condominio propio al resto.

#### Scenario: Administrador de condominio lista condominios

- **WHEN** un `admin_condominio` lista condominios
- **THEN** el sistema devuelve una lista con un solo elemento: su propio condominio

#### Scenario: Usuario sin condominio asignado

- **WHEN** un usuario no `super_admin` con `condominio_id` nulo lista condominios
- **THEN** el sistema devuelve una lista vacía

#### Scenario: Consulta directa de un condominio ajeno

- **WHEN** un usuario no `super_admin` solicita por identificador un condominio distinto al suyo
- **THEN** el sistema responde `403` con el detalle `"Sin acceso a este condominio"`

### Requirement: Modificación de condominio

El sistema DEBE (SHALL) exponer `PATCH /api/v1/condominios/{condominio_id}`, restringido a `super_admin`, que aplica actualizaciones parciales sobre los campos enviados.

#### Scenario: Actualización parcial

- **WHEN** un `super_admin` envía solo el campo `direccion`
- **THEN** el sistema actualiza únicamente ese campo y conserva el resto sin cambios

#### Scenario: Condominio inexistente

- **WHEN** se intenta modificar un identificador que no existe
- **THEN** el sistema responde `404` con el detalle `"Condominio no encontrado"`

### Requirement: Desactivación en lugar de borrado

El sistema DEBE (SHALL) exponer `DELETE /api/v1/condominios/{condominio_id}`, restringido a `super_admin`, que realiza un borrado lógico marcando `activo` en falso. Los datos históricos del condominio se conservan.

#### Scenario: Desactivación de un condominio

- **WHEN** un `super_admin` invoca el borrado de un condominio existente
- **THEN** el sistema marca `activo` en falso, responde `204` y conserva en la base de datos sus parcelas, boletas, lecturas y liquidaciones
