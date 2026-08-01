# boletas-maestras Specification

## Purpose

Registrar la boleta eléctrica colectiva que la compañía distribuidora emite mensualmente al condominio. La boleta maestra es el contenedor del período: guarda los totales de la emisión, el desglose de cargos (ítems de detalle) y la imagen del documento original. Al crearla, el sistema prepara automáticamente el trabajo del período: genera las lecturas en blanco de todas las parcelas y arrastra los ítems de cargo del mes anterior.

## Requirements

### Requirement: Un solo período abierto por condominio

El sistema NO DEBE (SHALL NOT) permitir crear una nueva boleta maestra mientras exista otra del mismo condominio cuyas liquidaciones no estén cerradas.

#### Scenario: Período anterior sin cerrar

- **WHEN** un administrador intenta crear una boleta y ya existe una con `liquidaciones_cerradas` en falso
- **THEN** el sistema responde `409` indicando la etiqueta del período pendiente y que debe cerrarse antes de cargar una nueva boleta

### Requirement: Determinación automática del período

El sistema DEBE (SHALL) usar el `periodo_mes` enviado en la petición si viene informado. Si no viene, DEBE (SHALL) calcular el mes siguiente al de la última boleta del condominio; si el condominio no tiene boletas previas, DEBE (SHALL) usar el primer día del mes en curso.

#### Scenario: Encadenamiento de meses

- **WHEN** se crea una boleta sin `periodo_mes` y la última boleta del condominio corresponde a diciembre
- **THEN** el sistema asigna el primer día de enero del año siguiente

#### Scenario: Primera boleta del condominio

- **WHEN** se crea la primera boleta de un condominio sin `periodo_mes`
- **THEN** el sistema asigna el primer día del mes actual

### Requirement: Generación automática de lecturas del período

Al crear una boleta maestra, el sistema DEBE (SHALL) generar una lectura en blanco por cada parcela del condominio, arrastrando como `lectura_anterior` el valor de `lectura_actual` de la última lectura registrada para esa parcela.

#### Scenario: Parcela con historial previo

- **WHEN** se crea una boleta y una parcela ya tiene lecturas de períodos anteriores
- **THEN** el sistema crea su lectura del nuevo período con `lectura_anterior` igual a la `lectura_actual` más reciente, `lectura_actual` en cero, `kwh_consumidos` en cero y `fecha_toma` sin informar

#### Scenario: Parcela sin historial

- **WHEN** una parcela no tiene ninguna lectura previa
- **THEN** el sistema crea su lectura del período con `lectura_anterior` en cero

### Requirement: Arrastre de ítems de detalle del período anterior

Al crear una boleta maestra sin ítems explícitos, el sistema DEBE (SHALL) copiar las descripciones y el `tipo_calculo` de los ítems de la boleta anterior del condominio, dejando todos los montos en cero para que sean completados por OCR o manualmente.

#### Scenario: Copia desde el mes anterior

- **WHEN** se crea una boleta sin enviar `items_detalle` y la boleta anterior tiene cargos registrados
- **THEN** el sistema crea los mismos cargos con idéntica descripción y tipo, con `monto_neto_clp` en cero

#### Scenario: Ítems enviados explícitamente

- **WHEN** la petición incluye `items_detalle`
- **THEN** el sistema crea esos ítems tal como fueron enviados y no copia los del período anterior

### Requirement: Estados de la boleta

Cada boleta maestra DEBE (SHALL) tener un campo `estado` con valor inicial `borrador`, que pasa a `publicada` automáticamente cuando se activa `boleta_visible_usuarios`.

#### Scenario: Publicación de la boleta

- **WHEN** un administrador actualiza `boleta_visible_usuarios` a verdadero
- **THEN** el sistema fija además `estado` en `publicada` y registra la acción `TOGGLE_VISIBILITY`

### Requirement: Listado de boletas

El sistema DEBE (SHALL) exponer `GET /api/v1/boletas/` para cualquier rol autenticado, devolviendo las boletas del tenant activo ordenadas por período de forma descendente, y restringiendo al rol `parcelero` a las boletas en estado `publicada`.

#### Scenario: Parcelero lista boletas

- **WHEN** un `parcelero` lista boletas
- **THEN** el sistema devuelve únicamente las boletas de su condominio cuyo estado es `publicada`

### Requirement: Vista reducida de la boleta para el parcelero

Al consultar una boleta por identificador, el sistema DEBE (SHALL) devolver al rol `parcelero` una representación reducida que incluye el período y el estado, y que expone la URL de la imagen solo cuando `boleta_visible_usuarios` está activo.

#### Scenario: Boleta no publicada

- **WHEN** un `parcelero` solicita una boleta cuyo estado no es `publicada`
- **THEN** el sistema responde `403` con el detalle `"Boleta no disponible"`

#### Scenario: Boleta publicada sin visibilidad de imagen

- **WHEN** un `parcelero` consulta una boleta publicada cuyo `boleta_visible_usuarios` es falso
- **THEN** el sistema devuelve la boleta con la URL de la imagen sin informar

### Requirement: Edición manual de totales e ítems

El sistema DEBE (SHALL) exponer `PUT /api/v1/boletas/{boleta_id}/detalles`, restringido a roles administrativos, que reemplaza los totales de la boleta y la totalidad de sus ítems de detalle.

#### Scenario: Reemplazo del desglose

- **WHEN** un administrador envía los totales y la lista completa de ítems
- **THEN** el sistema elimina los ítems previos, crea los enviados y registra la acción `UPDATE_DETALLES_BOLETA`

#### Scenario: Edición sobre período cerrado

- **WHEN** se intenta editar los detalles de una boleta con `liquidaciones_cerradas` en verdadero
- **THEN** el sistema responde `409` con el detalle `"El período está cerrado. No se puede modificar."`

### Requirement: Carga y reemplazo de la imagen de la boleta

El sistema DEBE (SHALL) exponer `POST /api/v1/boletas/{boleta_id}/imagen`, restringido a roles administrativos, que acepta archivos JPEG, PNG, WEBP, HEIC o PDF, los almacena con un nombre generado aleatoriamente y actualiza la URL de la boleta. Esta operación DEBE (SHALL) permitirse incluso con el período cerrado.

#### Scenario: Tipo de archivo no soportado

- **WHEN** se sube un archivo cuyo tipo MIME no está en la lista permitida
- **THEN** el sistema responde `422` indicando los formatos aceptados y no almacena el archivo

#### Scenario: Reemplazo de imagen en período cerrado

- **WHEN** un administrador sube una imagen a una boleta con las liquidaciones ya cerradas
- **THEN** el sistema acepta la carga, actualiza la URL y registra la acción `UPLOAD_IMAGEN_BOLETA`

### Requirement: Eliminación de boleta no consolidada

El sistema DEBE (SHALL) exponer `DELETE /api/v1/boletas/{boleta_id}`, restringido a roles administrativos, que elimina la boleta junto con sus liquidaciones, lecturas e ítems de detalle, únicamente mientras las lecturas del período no estén cerradas.

#### Scenario: Eliminación permitida

- **WHEN** un administrador elimina una boleta con `lecturas_cerradas` en falso
- **THEN** el sistema borra sus liquidaciones, lecturas e ítems, registra la acción `DELETE_BOLETA` y responde `204`

#### Scenario: Eliminación bloqueada por lecturas cerradas

- **WHEN** se intenta eliminar una boleta con `lecturas_cerradas` en verdadero
- **THEN** el sistema responde `409` indicando que primero deben reabrirse las lecturas
