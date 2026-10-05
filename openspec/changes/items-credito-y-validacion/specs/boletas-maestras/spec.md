## ADDED Requirements

### Requirement: Clasificación pendiente de los ítems

El sistema DEBE (SHALL) admitir el valor `pendiente` en `tipo_calculo`, reservado a los ítems que el OCR creó y que el administrador todavía no ha juzgado. Un ítem `pendiente` es visible en el desglose pero NO DEBE (SHALL NOT) participar de ningún cálculo hasta que reciba una clasificación definitiva.

#### Scenario: Valores admitidos

- **WHEN** se crea o actualiza un ítem de detalle
- **THEN** el sistema acepta `fijo`, `variable`, `informativo` o `pendiente` y rechaza cualquier otro valor con `422`

#### Scenario: Ítem pendiente en el desglose

- **WHEN** una boleta contiene un ítem con `tipo_calculo` igual a `pendiente`
- **THEN** el ítem aparece en el desglose de la boleta, señalado como no clasificado

### Requirement: Ítems con monto negativo

El sistema DEBE (SHALL) aceptar montos negativos en `monto_neto_clp` para representar descuentos, notas de crédito, abonos y devoluciones de la compañía.

#### Scenario: Persistencia de un crédito

- **WHEN** se guarda un ítem con `monto_neto_clp` negativo
- **THEN** el sistema lo persiste con su signo, sin convertirlo a valor absoluto ni rechazarlo

#### Scenario: Clasificación de un crédito

- **WHEN** un ítem de monto negativo se clasifica como `fijo` o `variable`
- **THEN** el crédito se reparte entre las parcelas según ese mismo criterio, reduciendo la cuota correspondiente

## MODIFIED Requirements

### Requirement: Arrastre de ítems de detalle del período anterior

Al crear una boleta maestra sin ítems explícitos, el sistema DEBE (SHALL) copiar las descripciones y el `tipo_calculo` de los ítems de la boleta anterior del condominio, dejando todos los montos en cero para que sean completados por OCR o manualmente. La clasificación arrastrada constituye una **propuesta** para el período nuevo, no una decisión tomada: el administrador la corrobora o la cambia antes de calcular.

#### Scenario: Copia desde el mes anterior

- **WHEN** se crea una boleta sin enviar `items_detalle` y la boleta anterior tiene cargos registrados
- **THEN** el sistema crea los mismos cargos con idéntica descripción y tipo, con `monto_neto_clp` en cero

#### Scenario: Ítems enviados explícitamente

- **WHEN** la petición incluye `items_detalle`
- **THEN** el sistema crea esos ítems tal como fueron enviados y no copia los del período anterior

#### Scenario: La clasificación arrastrada no exime de corroborar

- **WHEN** una boleta nueva hereda los ítems del período anterior con su clasificación
- **THEN** la boleta nace en estado `borrador` y requiere la corroboración del administrador antes de poder calcular, aunque ningún ítem quede en `pendiente`

### Requirement: Estados de la boleta

Cada boleta maestra DEBE (SHALL) tener un campo `estado` con valor inicial `borrador`. Pasa a `validada` cuando el administrador corrobora el desglose del período, y a `publicada` automáticamente cuando se activa `boleta_visible_usuarios`.

#### Scenario: Corroboración del desglose

- **WHEN** un administrador corrobora los ítems de una boleta en `borrador`
- **THEN** el sistema fija `estado` en `validada`

#### Scenario: Publicación de la boleta

- **WHEN** un administrador actualiza `boleta_visible_usuarios` a verdadero
- **THEN** el sistema fija además `estado` en `publicada` y registra la acción `TOGGLE_VISIBILITY`

### Requirement: Edición manual de totales e ítems

El sistema DEBE (SHALL) exponer `PUT /api/v1/boletas/{boleta_id}/detalles`, restringido a roles administrativos, que reemplaza los totales de la boleta y la totalidad de sus ítems de detalle. Como la edición altera las cifras sobre las que se emitió el juicio, el sistema DEBE (SHALL) devolver la boleta al estado `borrador` cuando estaba `validada`.

#### Scenario: Reemplazo del desglose

- **WHEN** un administrador envía los totales y la lista completa de ítems
- **THEN** el sistema elimina los ítems previos, crea los enviados y registra la acción `UPDATE_DETALLES_BOLETA`

#### Scenario: Edición sobre período cerrado

- **WHEN** se intenta editar los detalles de una boleta con `liquidaciones_cerradas` en verdadero
- **THEN** el sistema responde `409` con el detalle `"El período está cerrado. No se puede modificar."`

#### Scenario: Edición sobre boleta ya corroborada

- **WHEN** un administrador edita los detalles de una boleta en estado `validada`
- **THEN** el sistema aplica los cambios y devuelve la boleta a `borrador`, obligando a corroborar de nuevo antes de calcular
