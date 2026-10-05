# Spec Delta

## MODIFIED Requirements

### Requirement: Alta de condominio

El sistema DEBE (SHALL) exponer `POST /api/v1/condominios/`, restringido a `super_admin`, que crea un condominio con nombre, RUT de comunidad, dirección opcional y plan de suscripción, más su parametrización comercial opcional:

- `modulos`: los productos y módulos contratados (ver la capacidad `modulos-plataforma`). Si no se envían, el condominio queda con todos los módulos del catálogo.
- `portal_url`: la dirección pública del portal de administración del condominio, con `https://` (se admite `http://localhost` solo para desarrollo).
- `dominios_sitio`: los dominios en que se publica su landing.

La respuesta DEBE (SHALL) incluir esta parametrización. Un dominio NO DEBE (SHALL NOT) estar asignado a más de un condominio.

#### Scenario: Creación con RUT nuevo

- **WHEN** un `super_admin` envía los datos de un condominio cuyo RUT no está registrado
- **THEN** el sistema crea el condominio con `activo` en verdadero y responde `201` con el registro creado

#### Scenario: Alta de un condominio solo con administración

- **WHEN** un `super_admin` crea un condominio con los módulos `portal` y `energia` y una `portal_url`
- **THEN** el condominio queda sin landing y la respuesta informa sus módulos y su `portal_url`

#### Scenario: Dominio ya asignado

- **WHEN** un `super_admin` asigna a un condominio un dominio que ya pertenece a otro
- **THEN** el sistema responde `409` con el detalle `"El dominio ya está asignado a otro condominio"` y no guarda cambios

#### Scenario: URL del portal inválida

- **WHEN** un `super_admin` envía una `portal_url` que no comienza con `https://`
- **THEN** el sistema responde `422`

#### Scenario: RUT duplicado

- **WHEN** un `super_admin` intenta crear un condominio con un `rut_comunidad` ya existente
- **THEN** el sistema responde `409` con el detalle `"RUT de comunidad ya registrado"` y no crea el registro

#### Scenario: Rol sin permiso

- **WHEN** un `admin_condominio` intenta crear un condominio
- **THEN** el sistema responde `403`

### Requirement: Modificación de condominio

El sistema DEBE (SHALL) exponer `PATCH /api/v1/condominios/{condominio_id}`, restringido a `super_admin`, que aplica actualizaciones parciales sobre los campos enviados. Si se envían `modulos` o `dominios_sitio`, cada lista reemplaza por completo a la anterior. Todo cambio en `modulos`, `portal_url` o `dominios_sitio` DEBE (SHALL) quedar en auditoría con el valor anterior y el nuevo. Deshabilitar un módulo NO DEBE (SHALL NOT) borrar sus datos: al volver a habilitarlo, la información sigue disponible.

#### Scenario: Actualización parcial

- **WHEN** un `super_admin` envía solo el campo `direccion`
- **THEN** el sistema actualiza únicamente ese campo y conserva el resto sin cambios, incluidos los módulos, la `portal_url` y los dominios

#### Scenario: Deshabilitar y volver a habilitar un módulo

- **WHEN** un `super_admin` quita el módulo `energia` de un condominio con boletas y luego lo vuelve a habilitar
- **THEN** las boletas, lecturas y liquidaciones del condominio siguen intactas y vuelven a estar accesibles

#### Scenario: Pasar de solo landing a ambos productos

- **WHEN** un `super_admin` agrega `portal` y una `portal_url` a un condominio que solo tenía `sitio`
- **THEN** sus usuarios pueden iniciar sesión y la landing pasa a mostrar "Acceso propietarios"

#### Scenario: Condominio inexistente

- **WHEN** se intenta modificar un identificador que no existe
- **THEN** el sistema responde `404` con el detalle `"Condominio no encontrado"`

## ADDED Requirements

### Requirement: Logo del condominio

Cada condominio DEBE (SHALL) poder tener una imagen de logo, guardada como un campo del condominio (`logo_url`) e incluida en sus respuestas. El sistema DEBE (SHALL) exponer `POST /api/v1/condominios/{condominio_id}/logo` (multipart) para subirlo o reemplazarlo y `DELETE /api/v1/condominios/{condominio_id}/logo` para quitarlo, ambos restringidos a `super_admin`. Solo DEBE (SHALL) aceptar PNG, JPEG o WEBP de hasta 1 MB, verificando el contenido real del archivo y no solo su tipo declarado; SVG NO DEBE (SHALL NOT) aceptarse. Cada reemplazo DEBE (SHALL) generar una URL nueva, para que los navegadores no muestren el logo anterior desde su caché, y DEBE (SHALL) eliminar el archivo previo. Subir o quitar el logo DEBE (SHALL) quedar en auditoría. El logo es público: se muestra en la landing y en el portal.

#### Scenario: Subida de un logo válido

- **WHEN** un `super_admin` sube un PNG de 200 KB como logo de un condominio
- **THEN** el sistema lo guarda, responde con el condominio y su `logo_url`, y la imagen queda accesible en esa URL

#### Scenario: Reemplazo del logo

- **WHEN** un `super_admin` sube un logo nuevo a un condominio que ya tenía uno
- **THEN** la `logo_url` cambia y el archivo anterior deja de existir

#### Scenario: Formato no permitido

- **WHEN** se sube un SVG, un PDF o un archivo renombrado como `.png` que no es una imagen PNG
- **THEN** el sistema responde `422` y no modifica el logo actual

#### Scenario: Archivo demasiado grande

- **WHEN** se sube una imagen de más de 1 MB
- **THEN** el sistema responde `413` y no modifica el logo actual

#### Scenario: Rol sin permiso

- **WHEN** un `admin_condominio` intenta subir el logo de su condominio
- **THEN** el sistema responde `403`

#### Scenario: Quitar el logo

- **WHEN** un `super_admin` quita el logo de un condominio
- **THEN** `logo_url` queda vacío, el archivo se elimina y la landing y el portal muestran el nombre del condominio en su lugar

### Requirement: Color institucional del condominio

Cada condominio DEBE (SHALL) poder tener un color institucional (`color_primario`), que define el `super_admin` en el alta o la modificación del condominio. El valor DEBE (SHALL) ser hexadecimal de seis dígitos (`#RRGGBB`), se guarda en mayúsculas y se incluye en las respuestas del condominio. Sin color definido, la landing y el portal DEBEN (SHALL) usar el color por defecto de la plataforma. El cambio de color DEBE (SHALL) quedar en auditoría como cualquier otra modificación del condominio.

#### Scenario: Color válido

- **WHEN** un `super_admin` define `color_primario` como `#1e5aa8` para un condominio
- **THEN** el sistema lo guarda como `#1E5AA8` y lo devuelve en la respuesta del condominio

#### Scenario: Color inválido

- **WHEN** un `super_admin` envía `color_primario` como `azul` o `#12345`
- **THEN** el sistema responde `422` y no modifica el condominio

#### Scenario: Quitar el color

- **WHEN** un `super_admin` envía `color_primario` en nulo
- **THEN** el condominio vuelve a usar el color por defecto de la plataforma
