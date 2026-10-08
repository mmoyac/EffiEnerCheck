# Spec Delta

## Purpose

Capacitar a todas las personas que usan EFFIComunidad: comuneros, portería, lectores, administración del condominio y administradores externos. Para eso, la plataforma ofrece un centro de capacitación público, organizado por módulo y por rol, con recorridos animados que reproducen los flujos reales del portal sin exponer datos de nadie.

## ADDED Requirements

### Requirement: Acceso público sin sesión

El centro de capacitación DEBE (SHALL) estar disponible en la ruta `/capacitacion/` del portal para cualquier visitante, sin iniciar sesión y sin depender de los módulos contratados por un condominio. NO DEBE (SHALL NOT) quedar oculto tras la aplicación instalable del portal: abrir `/capacitacion/` DEBE (SHALL) mostrar la capacitación y no la aplicación del portal.

#### Scenario: Visitante sin cuenta

- **WHEN** una persona sin cuenta abre `/capacitacion/` en el navegador
- **THEN** ve el centro de capacitación sin que se le pida iniciar sesión

#### Scenario: Portal instalado como aplicación

- **WHEN** un usuario que ya instaló el portal en su celular abre el enlace a `/capacitacion/`
- **THEN** ve el centro de capacitación y no la pantalla de inicio del portal

### Requirement: Sin datos reales ni llamadas a la API

El centro de capacitación NO DEBE (SHALL NOT) consultar la API ni mostrar datos reales de condominios, parcelas o personas. Todos los nombres, números, montos y teléfonos de los recorridos DEBEN (SHALL) ser ficticios. NO DEBE (SHALL NOT) cargar scripts, estilos ni fuentes de terceros.

#### Scenario: Revisión de la red

- **WHEN** se abre el centro de capacitación con las herramientas de red del navegador
- **THEN** todas las peticiones son archivos estáticos del mismo origen y ninguna va a `/api/`

### Requirement: Organización por módulo y por rol

El centro de capacitación DEBE (SHALL) presentar la plataforma EFFIComunidad, con sus productos (sitio público y portal) y sus roles, y luego una sección por módulo. Dentro de cada módulo, los recorridos DEBEN (SHALL) agruparse por el rol que los realiza. Una sección cuyo contenido aún no está disponible DEBE (SHALL) mostrarse como «próximamente», no como un enlace roto.

#### Scenario: Navegación por módulo

- **WHEN** el visitante elige el módulo Rifas
- **THEN** ve los recorridos del módulo agrupados por rol: portería, administración y comunero

#### Scenario: Módulo pendiente

- **WHEN** el visitante elige un módulo cuya capacitación aún no se ha escrito
- **THEN** la página lo indica como «próximamente» y le permite volver a los módulos disponibles

### Requirement: Recorridos animados paso a paso

Cada recorrido DEBE (SHALL) reproducir, con pantallas simuladas y animadas, la secuencia de pasos de un flujo real del portal, acompañando cada paso con una explicación breve. El visitante DEBE (SHALL) poder avanzar, retroceder, pausar y reiniciar el recorrido. Cuando el sistema operativo pide reducir el movimiento, los recorridos DEBEN (SHALL) mostrar los pasos sin animación.

#### Scenario: Control del recorrido

- **WHEN** el visitante pausa un recorrido en el tercer paso y luego retrocede
- **THEN** el recorrido muestra el segundo paso con su explicación y espera a que el visitante continúe

#### Scenario: Movimiento reducido

- **WHEN** el visitante tiene activada la preferencia de reducir el movimiento
- **THEN** los pasos se muestran sin transiciones animadas y el contenido sigue completo

#### Scenario: Uso en celular y proyector

- **WHEN** la página se abre en un celular de 360 px de ancho o se proyecta en pantalla completa
- **THEN** los recorridos se leen completos, sin desplazamiento horizontal

### Requirement: Módulo de rifas con los tres caminos de compra

La sección del módulo Rifas DEBE (SHALL) explicar que un número se puede comprar por tres caminos y DEBE (SHALL) incluir un recorrido para cada uno:

1. en la portería, donde la cuenta de portería registra la venta y entrega el comprobante;
2. en la administración, que registra la compra desde su menú de Rifas;
3. por el propio comunero, que entra al portal con su correo y su clave y compra desde su portal.

Cada recorrido DEBE (SHALL) mostrar las formas de pago que ese camino admite y qué pasa después con el pago: efectivo pagado al momento, transferencia pendiente de confirmación, y gasto común cargado en un próximo gasto común.

#### Scenario: Recorrido del comunero

- **WHEN** el visitante reproduce el recorrido del comunero
- **THEN** ve el ingreso con correo y clave, el aviso de rifa abierta, la elección de números, la confirmación y la pantalla de agradecimiento

#### Scenario: Recorrido de la portería

- **WHEN** el visitante reproduce el recorrido de la portería
- **THEN** ve la búsqueda de la parcela, la elección de números, la forma de pago, el registro de la venta y el comprobante con su folio

#### Scenario: Recorrido de la administración

- **WHEN** el visitante reproduce el recorrido de la administración
- **THEN** ve la entrada al menú de Rifas, el registro de la compra a nombre de una parcela y cómo la administración confirma después un pago por transferencia

### Requirement: Capacitación al día con el producto

Todo cambio que altere un flujo visible ya cubierto por un recorrido DEBE (SHALL) actualizar ese recorrido en el mismo cambio. Todo módulo nuevo de la plataforma DEBE (SHALL) agregar su sección, aunque sea como «próximamente».

#### Scenario: Cambio de un flujo cubierto

- **WHEN** un cambio modifica los pasos de la compra de rifas desde el portal
- **THEN** el mismo cambio actualiza el recorrido del comunero en el centro de capacitación

### Requirement: Enlaces de acceso desde el portal

El portal DEBE (SHALL) enlazar el centro de capacitación desde la pantalla de inicio de sesión y desde una opción de ayuda visible para todos los roles una vez dentro.

#### Scenario: Desde el inicio de sesión

- **WHEN** una persona que nunca ha usado el portal está en la pantalla de inicio de sesión
- **THEN** encuentra un enlace para ver cómo funciona la plataforma, que abre `/capacitacion/`

#### Scenario: Desde dentro del portal

- **WHEN** un usuario de cualquier rol con sesión iniciada busca ayuda
- **THEN** encuentra en la navegación una opción que abre el centro de capacitación
