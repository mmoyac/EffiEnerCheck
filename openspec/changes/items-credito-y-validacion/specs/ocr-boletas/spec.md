## ADDED Requirements

### Requirement: Exclusión de totales y saldo anterior del desglose

El prompt del OCR DEBE (SHALL) instruir al modelo para que `items_detalle` contenga únicamente los cargos y abonos individuales del período, excluyendo los totales y subtotales (`Total exento`, `Total neto`, `19% IVA`, `Total Emisión`, `Otros`, `Total a pagar`) y las líneas de saldo anterior, que ya se capturan en los campos de cabecera.

Esta exclusión es indispensable desde que las líneas sin coincidencia se crean como ítems en lugar de descartarse: un saldo anterior clasificado como `fijo` o `variable` puede superar el total de emisión y producir un `valor_kwh` negativo.

#### Scenario: Totales no aparecen como ítems

- **WHEN** el OCR procesa una boleta con líneas de `Total neto`, `19% IVA` y `Total Emisión`
- **THEN** esas líneas no se devuelven en `items_detalle` y sus valores se reflejan solo en los campos de cabecera

#### Scenario: Saldo anterior no aparece como ítem

- **WHEN** la boleta contiene `Saldo Anterior Servicio Eléctrico` u `Otro Saldo Anterior`
- **THEN** esas líneas no se devuelven en `items_detalle` y su valor se refleja en `monto_saldo_anterior`

#### Scenario: Cargos del período sí aparecen

- **WHEN** la boleta contiene cargos como transporte, administración o potencia contratada
- **THEN** cada uno se devuelve como un ítem independiente en `items_detalle`

### Requirement: Reconocimiento de montos negativos

El prompt del OCR DEBE (SHALL) instruir explícitamente al modelo para que devuelva con signo negativo los conceptos que restan del total —descuentos, notas de crédito, abonos, devoluciones, bonificaciones y reliquidaciones a favor— en lugar de su valor absoluto.

#### Scenario: Descuento extraído con signo

- **WHEN** la boleta contiene una línea de descuento por 50.000 pesos netos
- **THEN** el OCR devuelve `-50000` en el `monto_neto_clp` de ese ítem

#### Scenario: Nota de crédito

- **WHEN** la boleta contiene una nota de crédito o una devolución
- **THEN** el OCR la devuelve como monto negativo y no como cargo positivo

#### Scenario: Cargo normal

- **WHEN** la línea es un cargo ordinario de la compañía
- **THEN** el OCR la devuelve con monto positivo, sin cambio respecto del comportamiento previo

## MODIFIED Requirements

### Requirement: Aplicación de IVA a los cargos extraídos

Los montos de los ítems que devuelve el OCR corresponden a valores netos de la boleta, mientras que el motor de cálculo opera con montos con IVA incluido. El sistema DEBE (SHALL) multiplicar cada monto de ítem extraído por 1,19 y redondearlo al entero más cercano antes de persistirlo, preservando el signo del valor extraído.

#### Scenario: Cargo neto convertido a bruto

- **WHEN** el OCR extrae un cargo con monto neto de 10.000 pesos
- **THEN** el sistema persiste 11.900 pesos en el ítem correspondiente

#### Scenario: Crédito neto convertido a bruto

- **WHEN** el OCR extrae un crédito con monto neto de −50.000 pesos
- **THEN** el sistema persiste −59.500 pesos, conservando el signo negativo

### Requirement: Emparejamiento difuso contra los ítems existentes

El sistema DEBE (SHALL) asociar cada cargo extraído al ítem del período con la descripción más parecida. La comparación DEBE (SHALL) normalizar los textos eliminando acentos, pasando a minúsculas, descartando las palabras vacías (`de`, `del`, `la`, `el`, `los`, `las`, `por`, `en`, `y`) y removiendo todo carácter que no sea alfanumérico. Las líneas sin coincidencia suficiente NO DEBEN (SHALL NOT) descartarse: el sistema las crea como ítems nuevos con `tipo_calculo` igual a `pendiente`, para que el administrador decida si entran o no al reparto.

#### Scenario: Coincidencia por similitud

- **WHEN** el OCR extrae un cargo cuya descripción normalizada alcanza una similitud superior a 0,6 con la de un ítem existente
- **THEN** el sistema actualiza el monto de ese ítem con el valor extraído más IVA, conservando su `tipo_calculo` actual

#### Scenario: Sin coincidencia suficiente

- **WHEN** ningún ítem existente supera el umbral de similitud
- **THEN** el sistema crea un ítem nuevo con la descripción extraída, su monto con IVA y `tipo_calculo` igual a `pendiente`, sin descartar la línea

#### Scenario: Crédito no reconocido

- **WHEN** la boleta trae una nota de crédito que no existía en el período anterior
- **THEN** el sistema la crea como ítem `pendiente` con monto negativo, de modo que quede visible para el administrador en lugar de diluirse en el componente de energía

#### Scenario: Descripción vacía tras normalizar

- **WHEN** la descripción extraída queda vacía después de la normalización
- **THEN** el sistema omite ese cargo sin interrumpir el procesamiento del resto

### Requirement: Procesamiento del OCR sobre una boleta existente

El sistema DEBE (SHALL) exponer `POST /api/v1/boletas/{boleta_id}/procesar-ocr`, restringido a roles administrativos, que lee la imagen ya asociada a la boleta, la procesa y vuelca los datos extraídos sobre el registro. Como el procesamiento altera las cifras sobre las que el administrador emite su juicio, el sistema DEBE (SHALL) devolver la boleta al estado `borrador` cuando estaba `validada`.

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

#### Scenario: Reproceso sobre boleta ya corroborada

- **WHEN** se reprocesa el OCR de una boleta en estado `validada`
- **THEN** el sistema devuelve la boleta a `borrador`, obligando a una nueva corroboración del desglose antes de poder calcular
