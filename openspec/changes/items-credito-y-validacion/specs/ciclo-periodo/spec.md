## ADDED Requirements

### Requirement: Corroboración del desglose por el administrador

Cada mes el administrador es el juez de qué cargos de la boleta entran y cuáles no entran al reparto de gastos comunes. El sistema DEBE (SHALL) exponer `POST /api/v1/boletas/{boleta_id}/validar-items`, restringido a roles administrativos, que registra ese juicio y lleva la boleta del estado `borrador` al estado `validada`.

#### Scenario: Corroboración válida

- **WHEN** un administrador corrobora el desglose de una boleta en `borrador` sin ítems `pendiente`
- **THEN** el sistema fija `estado` en `validada` y registra la acción `VALIDAR_ITEMS`

#### Scenario: Corroboración con ítems sin clasificar

- **WHEN** la boleta contiene al menos un ítem con `tipo_calculo` igual a `pendiente`
- **THEN** el sistema responde `409` indicando cuántos ítems faltan por clasificar y la boleta permanece en `borrador`

#### Scenario: Boleta ya corroborada

- **WHEN** se intenta corroborar una boleta que ya está en estado `validada`
- **THEN** el sistema responde `409` indicando que el desglose ya fue corroborado

#### Scenario: Corroboración sobre período cerrado

- **WHEN** se intenta corroborar una boleta con `liquidaciones_cerradas` en verdadero
- **THEN** el sistema responde `409` y no modifica el estado

### Requirement: Reversión de la corroboración

Toda operación que altere las cifras o el desglose sobre los que el administrador emitió su juicio DEBE (SHALL) devolver la boleta al estado `borrador`, de modo que el juicio nunca quede desacoplado de los datos que lo sustentan.

#### Scenario: Reproceso del OCR

- **WHEN** se reprocesa el OCR de una boleta en estado `validada`
- **THEN** el sistema la devuelve a `borrador`

#### Scenario: Edición de detalles

- **WHEN** se editan los totales o los ítems de una boleta en estado `validada`
- **THEN** el sistema la devuelve a `borrador`

#### Scenario: Liquidaciones existentes tras la reversión

- **WHEN** una boleta vuelve a `borrador` y ya tenía liquidaciones calculadas
- **THEN** las liquidaciones existentes se conservan, pero el período no puede cerrarse sin recalcular tras una nueva corroboración

### Requirement: Trazabilidad del juicio del administrador

El registro de auditoría de la corroboración DEBE (SHALL) incluir una instantánea del desglose completo en el momento de validar: descripción, monto y `tipo_calculo` de cada ítem, más los totales de la boleta.

#### Scenario: Reconstrucción de la decisión

- **WHEN** se consulta el registro `VALIDAR_ITEMS` de un período
- **THEN** permite reconstruir exactamente qué ítems entraron al reparto, cuáles quedaron fuera, con qué montos y quién lo decidió

## MODIFIED Requirements

### Requirement: Botonera del ciclo en la interfaz administrativa

La pantalla de detalle de boleta DEBE (SHALL) ofrecer únicamente las acciones válidas para el estado actual del período, evitando que el administrador intente transiciones que el backend rechazaría.

#### Scenario: Visibilidad de las acciones

- **WHEN** el administrador abre el detalle de una boleta
- **THEN** corroborar el desglose se ofrece con la boleta en `borrador` y el período abierto; la acción de calcular se ofrece con la boleta en `validada` y las liquidaciones no cerradas; cerrar el período se ofrece con las lecturas cerradas y liquidaciones existentes; reabrir lecturas se ofrece con las lecturas cerradas y el período abierto; y reabrir liquidaciones y publicar se ofrecen con el período cerrado y la boleta aún no publicada

#### Scenario: Cálculo no disponible sin corroborar

- **WHEN** la boleta está en estado `borrador`
- **THEN** la consola no ofrece la acción de calcular y señala que primero debe corroborarse el desglose
