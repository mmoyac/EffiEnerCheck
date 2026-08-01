# lecturas-remarcadores Specification

## Purpose

Capturar el consumo individual de cada parcela a partir del remarcador instalado en terreno. El lector recorre el condominio con el teléfono y anota la lectura actual de cada medidor; el sistema calcula el consumo del período como la diferencia con la lectura anterior. Estas lecturas son la entrada principal del motor de liquidaciones, por lo que su integridad y su trazabilidad son críticas.

## Requirements

### Requirement: Registro de una lectura

El sistema DEBE (SHALL) exponer `POST /api/v1/lecturas/`, restringido a `lector` y roles administrativos, que crea una lectura asociada a una parcela y a una boleta, registrando como autor al usuario autenticado.

#### Scenario: Parcela de otro condominio

- **WHEN** el usuario intenta registrar una lectura sobre una parcela que no pertenece a su condominio
- **THEN** el sistema responde `403` con el detalle `"Parcela no pertenece a su condominio"`

#### Scenario: Parcela inexistente

- **WHEN** el identificador de parcela no existe
- **THEN** el sistema responde `404` con el detalle `"Parcela no encontrada"`

#### Scenario: Registro exitoso

- **WHEN** se crea una lectura válida
- **THEN** el sistema la persiste con el usuario autenticado como `lector_id`, responde `201` y registra la acción `CREATE_LECTURA` con los kWh consumidos

### Requirement: Corrección de una lectura

El sistema DEBE (SHALL) exponer `PATCH /api/v1/lecturas/{lectura_id}`, restringido a `lector` y roles administrativos, que aplica actualizaciones parciales y recalcula el consumo cuando cambia alguno de los dos valores del medidor.

#### Scenario: Recálculo del consumo

- **WHEN** se modifica `lectura_actual` o `lectura_anterior`
- **THEN** el sistema recalcula `kwh_consumidos` como la diferencia entre la lectura actual y la anterior

#### Scenario: Reasignación de autoría

- **WHEN** un usuario corrige una lectura tomada por otra persona
- **THEN** el sistema reemplaza `lector_id` por el usuario que realiza la corrección y deja constancia del autor previo en el registro de auditoría

#### Scenario: Lectura inexistente

- **WHEN** el identificador de lectura no existe
- **THEN** el sistema responde `404` con el detalle `"Lectura no encontrada"`

### Requirement: Coherencia del contador

El sistema NO DEBE (SHALL NOT) aceptar una lectura actual menor que la lectura anterior, ya que el remarcador es un contador acumulativo.

#### Scenario: Lectura actual regresiva

- **WHEN** se intenta guardar una corrección donde la lectura actual resulta menor que la anterior
- **THEN** el sistema responde `422` indicando ambos valores y no persiste el cambio

### Requirement: Bloqueo de lecturas por cierre de período

Toda creación o modificación de lecturas DEBE (SHALL) rechazarse cuando la boleta del período tiene `lecturas_cerradas` en verdadero.

#### Scenario: Período con lecturas cerradas

- **WHEN** se intenta crear o corregir una lectura de una boleta con las lecturas cerradas
- **THEN** el sistema responde `409` con el detalle `"Las lecturas de este período están cerradas y no se pueden modificar"`

#### Scenario: Boleta inexistente

- **WHEN** la lectura referencia una boleta que no existe
- **THEN** el sistema responde `404` con el detalle `"Boleta no encontrada"`

### Requirement: Consulta de lecturas del período

El sistema DEBE (SHALL) exponer `GET /api/v1/lecturas/` para cualquier rol autenticado, con filtro opcional por boleta, acotado al tenant activo y, para el rol `parcelero`, a las parcelas asociadas a su usuario.

#### Scenario: Filtro por boleta

- **WHEN** se consultan las lecturas indicando un `boleta_id`
- **THEN** el sistema devuelve solo las lecturas de ese período

#### Scenario: Parcelero consulta lecturas

- **WHEN** un `parcelero` consulta lecturas
- **THEN** el sistema devuelve únicamente las de sus propias parcelas

### Requirement: Marca de lectura efectivamente tomada

El campo `fecha_toma` DEBE (SHALL) distinguir una lectura realmente capturada en terreno de una fila generada automáticamente al crear la boleta. Las filas autogeneradas nacen sin `fecha_toma`.

#### Scenario: Captura desde la aplicación del lector

- **WHEN** el lector confirma una lectura desde la aplicación móvil
- **THEN** el cliente envía la marca de tiempo actual en `fecha_toma`, con lo que la parcela pasa a contar como leída

### Requirement: Vista móvil de avance del lector

La aplicación web DEBE (SHALL) ofrecer al rol `lector` una pantalla optimizada para móvil que liste las parcelas activas del período abierto, muestre el avance como parcelas leídas sobre el total y permita filtrar entre pendientes y todas.

#### Scenario: Cálculo del avance

- **WHEN** el lector abre su pantalla principal
- **THEN** la aplicación cuenta como completadas las parcelas activas que ya tienen una lectura con `fecha_toma` en el período abierto

#### Scenario: Sin período activo

- **WHEN** el condominio no tiene ninguna boleta cargada
- **THEN** la aplicación muestra el mensaje de que no hay período activo e indica que el administrador debe crear una boleta

#### Scenario: Todas las lecturas completadas

- **WHEN** no quedan parcelas pendientes bajo el filtro seleccionado
- **THEN** la aplicación muestra una confirmación de que todas las lecturas fueron completadas

#### Scenario: Período con lecturas cerradas

- **WHEN** la boleta activa ya tiene las lecturas cerradas
- **THEN** la aplicación deshabilita la navegación a la pantalla de captura

### Requirement: Pantalla de captura de lectura

La aplicación web DEBE (SHALL) ofrecer una pantalla de captura por parcela que muestre la lectura anterior, permita ingresar la lectura actual con teclado numérico, presente el consumo calculado en tiempo real y confirme el guardado antes de volver al listado.

#### Scenario: Consumo negativo en pantalla

- **WHEN** el valor ingresado es menor que la lectura anterior
- **THEN** la aplicación destaca el consumo en rojo, advierte que la lectura actual no puede ser menor que la anterior y deshabilita el botón de confirmación

#### Scenario: Edición de una lectura ya capturada

- **WHEN** el lector abre una parcela que ya tiene lectura registrada
- **THEN** la aplicación precarga el valor existente e identifica la pantalla como edición en lugar de alta
