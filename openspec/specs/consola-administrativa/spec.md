# consola-administrativa Specification

## Purpose

Ofrecer al administrador del condominio un único lugar desde el cual conducir el período completo: ver el estado general, crear la boleta, cargar y corregir sus datos, revisar el avance de lecturas, ejecutar el cálculo y consolidar el resultado. La consola prioriza escritorio y organiza el trabajo alrededor de la pantalla de detalle de boleta, que reúne en pestañas todo lo que ocurre en un período.

## Requirements

### Requirement: Panel de indicadores del período

La consola DEBE (SHALL) presentar un panel inicial con la cantidad de períodos registrados, la cantidad de liquidaciones del período más reciente, cuántas de ellas están pagadas y el total a recaudar, junto con las boletas más recientes y su estado.

#### Scenario: Condominio sin boletas

- **WHEN** el condominio no tiene ningún período registrado
- **THEN** el panel muestra los indicadores sin período activo y la tabla de boletas informa que no hay registros

#### Scenario: Total a recaudar

- **WHEN** el período más reciente tiene liquidaciones calculadas
- **THEN** el panel muestra la suma de los totales a pagar de esas liquidaciones expresada en pesos chilenos

### Requirement: Etiqueta de estado del período

La consola DEBE (SHALL) traducir los tres candados del período en una única etiqueta legible, con la precedencia: publicada, período cerrado, lecturas cerradas y, en ausencia de todas, borrador.

#### Scenario: Período con lecturas cerradas y liquidaciones abiertas

- **WHEN** una boleta tiene `lecturas_cerradas` en verdadero y `liquidaciones_cerradas` en falso
- **THEN** la consola la etiqueta como lecturas cerradas

### Requirement: Creación de boleta desde la consola

La consola DEBE (SHALL) permitir crear el período con un mínimo de datos, delegando en el backend la determinación del mes, el arrastre de ítems y la generación de lecturas, y llevar al administrador directamente a la pantalla de carga de la boleta recién creada.

#### Scenario: Creación por un super admin

- **WHEN** el usuario es `super_admin`
- **THEN** la consola exige seleccionar el condominio destino antes de crear la boleta

#### Scenario: Navegación tras crear

- **WHEN** la boleta se crea correctamente
- **THEN** la consola navega al detalle del nuevo período con la pestaña de carga de boleta abierta

### Requirement: Detalle del período organizado en pestañas

La pantalla de detalle DEBE (SHALL) organizar el trabajo en cuatro pestañas —resumen, lecturas, liquidaciones y boleta— y DEBE (SHALL) poder abrirse directamente en una pestaña concreta mediante el parámetro `tab` de la URL.

#### Scenario: Apertura directa en una pestaña

- **WHEN** se abre el detalle con `?tab=liquidaciones`
- **THEN** la consola muestra la pestaña de liquidaciones desde el primer render

#### Scenario: Cambio de pestaña tras una acción

- **WHEN** el administrador ejecuta el cálculo desde el listado de boletas
- **THEN** la consola navega al detalle de ese período con la pestaña de liquidaciones abierta

### Requirement: Filtro por condominio para el super admin

Cuando el usuario es `super_admin`, el listado de boletas DEBE (SHALL) ofrecer un filtro por condominio e identificar a qué comunidad pertenece cada período.

#### Scenario: Filtro aplicado

- **WHEN** un `super_admin` selecciona un condominio en el filtro
- **THEN** la consola muestra solo las boletas de ese condominio e indica cuántas de cuántas se están viendo

### Requirement: Comunicación de los errores del backend

Toda acción de la consola DEBE (SHALL) mostrar el mensaje de error que devuelve la API en lugar de fallar en silencio, incluyendo los errores de validación que llegan como lista de campos.

#### Scenario: Conflicto de estado

- **WHEN** una acción es rechazada con `409` por una transición inválida del período
- **THEN** la consola muestra el detalle recibido del backend

#### Scenario: Error de validación con múltiples campos

- **WHEN** la API responde con una lista de errores de validación
- **THEN** la consola compone un mensaje legible indicando el campo y la causa de cada uno

### Requirement: Consistencia de la caché tras cada mutación

Tras cada acción que modifica el período, la consola DEBE (SHALL) invalidar las consultas afectadas para que la información mostrada refleje el estado real del servidor.

#### Scenario: Cálculo de liquidaciones

- **WHEN** el administrador ejecuta el cálculo
- **THEN** la consola invalida las liquidaciones y la boleta del período, de modo que las cifras y la botonera se actualizan sin recargar la página

### Requirement: Administración de parcelas y usuarios desde la consola

La consola DEBE (SHALL) incluir pantallas de mantenimiento para el padrón de parcelas y para las cuentas de usuario del condominio, y una pantalla adicional de condominios disponible para el `super_admin`.

#### Scenario: Orden del padrón tras editar

- **WHEN** el administrador edita una parcela y la lista se vuelve a consultar
- **THEN** la consola conserva el orden natural por número de parcela en lugar del orden de inserción de la base de datos
