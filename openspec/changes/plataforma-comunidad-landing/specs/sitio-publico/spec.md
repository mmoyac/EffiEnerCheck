# Spec Delta

## Purpose

Dar a cada condominio que lo contrate un sitio web público, independiente del portal de administración, que presente a la comunidad y lleve a los propietarios al portal cuando el condominio lo tenga. El contenido lo configura hoy el equipo de la plataforma y mañana lo administrará el propio condominio, sin cambiar el sitio.

## ADDED Requirements

### Requirement: Landing independiente del portal

La landing DEBE (SHALL) ser una aplicación web distinta del portal de administración: se construye, se empaqueta y se despliega por separado, se sirve en su propio dominio y NO DEBE (SHALL NOT) incluir código, rutas ni pantallas del portal. Su única dependencia del resto de la plataforma DEBE (SHALL) ser el endpoint público de contenido. El portal NO DEBE (SHALL NOT) depender de la landing para funcionar.

#### Scenario: Condominio solo con administración

- **WHEN** un condominio tiene el módulo `portal` pero no el módulo `sitio`
- **THEN** el portal funciona completo en su dominio y el condominio puede enlazarlo desde su propio sitio web con su `portal_url`

#### Scenario: Condominio solo con landing

- **WHEN** un condominio tiene el módulo `sitio` pero no el módulo `portal`
- **THEN** la landing se muestra completa y no ofrece el botón "Acceso propietarios"

### Requirement: Acceso al portal desde la landing

La landing DEBE (SHALL) mostrar el botón "Acceso propietarios" en la portada y en la navegación solo si el condominio tiene habilitado el módulo `portal` y una `portal_url` definida por el `super_admin`, y el botón DEBE (SHALL) llevar a esa URL. Ambos datos salen de la parametrización del condominio, no del contenido editorial del sitio.

#### Scenario: Portal habilitado sin URL

- **WHEN** un condominio tiene `portal` y `sitio`, pero no tiene `portal_url`
- **THEN** la landing no muestra el botón "Acceso propietarios"

#### Scenario: Visitante pulsa el acceso

- **WHEN** un visitante de `www.condominiosantalaura.cl` pulsa "Acceso propietarios"
- **THEN** llega al login del portal del condominio

### Requirement: Secciones del sitio

El sitio DEBE (SHALL) componerse de secciones con estructura fija: portada (nombre, lema, imagen y llamado a la acción), presentación de la comunidad, avisos, espacios y servicios, administración y directiva, documentos públicos, contacto (teléfonos, correo, WhatsApp y horarios de atención), ubicación y pie de página. Toda sección, salvo la portada, el contacto y el pie, DEBE (SHALL) ser opcional: si su contenido viene vacío o ausente, la sección no se muestra y no deja espacio en blanco ni enlaces rotos en la navegación.

#### Scenario: Sección sin contenido

- **WHEN** el contenido del condominio no trae avisos
- **THEN** la landing no muestra la sección de avisos ni su enlace en la navegación

#### Scenario: Contacto por WhatsApp

- **WHEN** el contenido trae un número de WhatsApp de contacto
- **THEN** la landing ofrece un enlace que abre una conversación con ese número

### Requirement: Contrato del contenido

El sistema DEBE (SHALL) exponer `GET /api/v1/sitio`, sin autenticación, que devuelve el contenido del sitio del condominio con un esquema fijo y versionado (campo `version_esquema`). La landing DEBE (SHALL) construirse únicamente a partir de esta respuesta, de modo que cambiar el origen del contenido no exija cambios en la landing. La respuesta DEBE (SHALL) incluir el logo del condominio (`logo_url`) cuando el `super_admin` lo haya cargado, y la landing DEBE (SHALL) mostrarlo en la cabecera y en la portada, o el nombre del condominio si no hay logo. La respuesta DEBE (SHALL) poder cachearse por un tiempo breve y NO DEBE (SHALL NOT) incluir datos internos de configuración, como el RUT de la comunidad o la lista de dominios.

#### Scenario: Consulta del contenido

- **WHEN** un visitante anónimo solicita `GET /api/v1/sitio` desde el dominio de un condominio con sitio configurado
- **THEN** el sistema responde `200` con el contenido del condominio conforme al esquema

#### Scenario: Color del condominio

- **WHEN** el condominio tiene `color_primario` definido
- **THEN** la respuesta incluye `condominio.color_primario` y la landing lo usa en la cabecera, los botones (incluido "Acceso propietarios"), los enlaces y los acentos de las secciones, con un color de texto legible sobre él

#### Scenario: Condominio sin logo

- **WHEN** el condominio no tiene logo cargado
- **THEN** la respuesta no incluye `logo_url` y la landing muestra el nombre del condominio en la cabecera

#### Scenario: Contenido inválido

- **WHEN** el contenido configurado de un condominio no cumple el esquema
- **THEN** el sistema no lo publica a medias: lo rechaza al cargarlo y lo informa en el registro del servidor

### Requirement: Resolución del condominio por dominio

El sistema DEBE (SHALL) identificar el condominio del sitio comparando el dominio de la petición con los dominios que el `super_admin` asignó al condominio, sin distinguir mayúsculas e ignorando el prefijo `www.` y el puerto. Si el dominio no corresponde a ningún condominio, DEBE (SHALL) usar el sitio por defecto configurado para la instalación y, si no lo hay, DEBE (SHALL) responder `404`. Solo los condominios activos con el módulo `sitio` habilitado DEBEN (SHALL) tener sitio público.

#### Scenario: Dominio propio con y sin www

- **WHEN** se solicita el sitio desde `condominiosantalaura.cl` o desde `www.condominiosantalaura.cl`
- **THEN** el sistema devuelve el sitio de Santa Laura en ambos casos

#### Scenario: Dominio desconocido sin sitio por defecto

- **WHEN** se solicita el sitio desde un dominio no asociado y la instalación no define sitio por defecto
- **THEN** el sistema responde `404` con el detalle `"Sitio no encontrado"`

#### Scenario: Condominio sin el módulo sitio

- **WHEN** el dominio corresponde a un condominio que no tiene habilitado el módulo `sitio`
- **THEN** el sistema responde `404` con el detalle `"Sitio no encontrado"`

### Requirement: Origen del contenido

La parametrización del sitio (si está contratado, sus dominios y la URL del portal) DEBE (SHALL) guardarse en la base de datos y administrarla el `super_admin`. En esta versión el contenido editorial de cada condominio (textos, imágenes, contacto y secciones) DEBE (SHALL) provenir de un archivo de configuración versionado en el repositorio y validado contra el esquema al arrancar. El origen DEBE (SHALL) quedar aislado detrás del endpoint, de modo que pueda reemplazarse por contenido guardado en la base de datos y editado por el `admin_condominio` desde el portal sin cambiar el contrato de la respuesta.

#### Scenario: Nuevo dominio sin despliegue

- **WHEN** el `super_admin` asigna un dominio nuevo a un condominio con sitio
- **THEN** `GET /api/v1/sitio` responde con el sitio de ese condominio para ese dominio, sin desplegar nada

#### Scenario: Cambio del contenido

- **WHEN** se modifica el archivo de contenido de un condominio y se despliega el backend
- **THEN** la landing muestra el contenido nuevo sin reconstruir su imagen

### Requirement: Datos personales en el sitio

El sitio público NO DEBE (SHALL NOT) exponer datos del padrón (parcelas, residentes, ni teléfonos o correos de propietarios), liquidaciones, rifas ni ningún dato que requiera sesión. Los únicos datos de personas que se pueden publicar son los de contacto institucional (portería y administración) y los nombres y cargos de la directiva que la comunidad haya aprobado publicar, y DEBEN (SHALL) venir explícitamente en el contenido del sitio.

#### Scenario: Sitio sin consultas privadas

- **WHEN** un visitante anónimo carga la landing
- **THEN** la landing solo consulta `GET /api/v1/sitio` y ningún endpoint que requiera autenticación

### Requirement: Presentación adaptable y liviana

La landing DEBE (SHALL) verse correctamente en teléfonos y en escritorio, y DEBE (SHALL) declarar el título y la descripción del condominio para los buscadores y para las vistas previas al compartir el enlace.

#### Scenario: Visita desde un teléfono

- **WHEN** un visitante abre la landing en una pantalla de 360 px de ancho
- **THEN** el contenido se lee sin desplazamiento horizontal y el botón de acceso queda visible en la portada
