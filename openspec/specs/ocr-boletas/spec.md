# ocr-boletas Specification

## Purpose

Evitar la digitación manual de la boleta eléctrica. El administrador sube una foto o PDF del documento y el sistema extrae, mediante Gemini Vision, los totales de cabecera y el desglose de cargos. Como las descripciones que imprime la compañía varían de mes a mes, los cargos extraídos se emparejan por similitud contra los ítems que ya existen en el período (arrastrados del mes anterior), de modo que la comunidad conserva su propia nomenclatura y clasificación `fijo` / `variable` / `informativo`.

## Requirements

### Requirement: Extracción de datos mediante Gemini Vision

El sistema DEBE (SHALL) enviar la imagen o PDF de la boleta al modelo `gemini-2.5-flash` con un prompt que solicita exclusivamente un objeto JSON con los campos `periodo_mes`, `total_kwh_compania`, `monto_neto_electricidad_consumida`, `monto_total_emision`, `monto_saldo_anterior` e `items_detalle`.

#### Scenario: Extracción exitosa

- **WHEN** el modelo devuelve un JSON válido para una boleta legible
- **THEN** el sistema entrega los campos extraídos, usando valor nulo para los que no aparecen en el documento

#### Scenario: Respuesta envuelta en marcado

- **WHEN** el modelo devuelve el JSON dentro de un bloque de código markdown
- **THEN** el sistema retira los delimitadores antes de interpretar el contenido

#### Scenario: Respuesta no interpretable

- **WHEN** el modelo devuelve texto que no es JSON válido
- **THEN** el sistema responde `422` incluyendo un extracto de la respuesta recibida para facilitar el diagnóstico

### Requirement: Manejo de fallos del proveedor de OCR

El sistema DEBE (SHALL) traducir los fallos de la llamada a Gemini en errores de negocio legibles, distinguiendo el agotamiento de cuota de los demás errores.

#### Scenario: Clave de API no configurada

- **WHEN** la variable de entorno `GEMINI_API_KEY` está vacía y se solicita un OCR
- **THEN** el sistema responde `422` indicando que la clave no está configurada en el servidor

#### Scenario: Cuota agotada

- **WHEN** la llamada al modelo falla por límite de uso
- **THEN** el sistema responde `422` con un mensaje que indica cuota agotada y apunta a la revisión del plan de facturación

### Requirement: OCR exploratorio sobre archivo subido

El sistema DEBE (SHALL) exponer `POST /api/v1/boletas/ocr`, restringido a roles administrativos, que recibe un archivo, lo almacena y devuelve los datos extraídos junto con la URL del archivo guardado, sin asociarlo todavía a ninguna boleta.

#### Scenario: Limpieza tras fallo de extracción

- **WHEN** el archivo se almacena correctamente pero la extracción falla
- **THEN** el sistema elimina el archivo del servidor antes de responder el error

### Requirement: Procesamiento del OCR sobre una boleta existente

El sistema DEBE (SHALL) exponer `POST /api/v1/boletas/{boleta_id}/procesar-ocr`, restringido a roles administrativos, que lee la imagen ya asociada a la boleta, la procesa y vuelca los datos extraídos sobre el registro.

#### Scenario: Boleta sin imagen

- **WHEN** se solicita procesar una boleta cuyo `url_imagen_boleta` no está informado
- **THEN** el sistema responde `400` indicando que debe subirse la imagen primero

#### Scenario: Archivo ausente en el servidor

- **WHEN** la boleta tiene URL de imagen pero el archivo no existe en disco
- **THEN** el sistema responde `404` indicando que no se encontró el archivo físico

#### Scenario: Procesamiento sobre período cerrado

- **WHEN** se solicita procesar el OCR de una boleta con `liquidaciones_cerradas` en verdadero
- **THEN** el sistema responde `409` y no modifica ningún dato

#### Scenario: Volcado de totales

- **WHEN** la extracción devuelve valores no nulos para los totales
- **THEN** el sistema actualiza `total_kwh_compania`, `monto_neto_electricidad_consumida`, `monto_total_emision` y `monto_saldo_anterior`, dejando sin tocar aquellos campos cuyo valor extraído sea nulo

### Requirement: Aplicación de IVA a los cargos extraídos

Los montos de los ítems que devuelve el OCR corresponden a valores netos de la boleta, mientras que el motor de cálculo opera con montos con IVA incluido. El sistema DEBE (SHALL) multiplicar cada monto de ítem extraído por 1,19 y redondearlo al entero más cercano antes de persistirlo.

#### Scenario: Cargo neto convertido a bruto

- **WHEN** el OCR extrae un cargo con monto neto de 10.000 pesos
- **THEN** el sistema persiste 11.900 pesos en el ítem correspondiente

### Requirement: Emparejamiento difuso contra los ítems existentes

El sistema DEBE (SHALL) asociar cada cargo extraído al ítem del período con la descripción más parecida, en lugar de crear ítems nuevos. La comparación DEBE (SHALL) normalizar los textos eliminando acentos, pasando a minúsculas, descartando las palabras vacías (`de`, `del`, `la`, `el`, `los`, `las`, `por`, `en`, `y`) y removiendo todo carácter que no sea alfanumérico.

#### Scenario: Coincidencia por similitud

- **WHEN** el OCR extrae un cargo cuya descripción normalizada alcanza una similitud superior a 0,6 con la de un ítem existente
- **THEN** el sistema actualiza el monto de ese ítem con el valor extraído más IVA

#### Scenario: Sin coincidencia suficiente

- **WHEN** ningún ítem existente supera el umbral de similitud
- **THEN** el sistema descarta el cargo extraído y no crea ítems nuevos, preservando la nomenclatura definida por la comunidad

#### Scenario: Descripción vacía tras normalizar

- **WHEN** la descripción extraída queda vacía después de la normalización
- **THEN** el sistema omite ese cargo sin interrumpir el procesamiento del resto
