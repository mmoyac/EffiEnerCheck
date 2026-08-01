# ciclo-periodo Specification

## Purpose

Gobernar el avance ordenado del período mensual mediante candados explícitos. El ciclo protege la integridad del prorrateo: impide que las lecturas cambien después de haber sido certificadas, que las liquidaciones se recalculen después de haber sido cerradas, y que un período publicado a la comunidad se altere. Cada transición es reversible solo mientras el paso siguiente no se haya consumado, y toda transición queda registrada en auditoría.

## Requirements

### Requirement: Candados del período

Cada boleta maestra DEBE (SHALL) mantener tres indicadores booleanos que representan el avance del ciclo: `lecturas_cerradas`, `liquidaciones_cerradas` y `boleta_visible_usuarios`. Los tres nacen en falso al crear la boleta y avanzan en ese orden.

#### Scenario: Estado inicial

- **WHEN** se crea una boleta maestra
- **THEN** los tres indicadores quedan en falso y el período admite captura de lecturas y recálculo de liquidaciones

### Requirement: Cierre de lecturas

El sistema DEBE (SHALL) exponer `POST /api/v1/boletas/{boleta_id}/cerrar-lecturas`, accesible a `lector` y roles administrativos, que certifica que la captura en terreno terminó.

#### Scenario: Cierre con lecturas pendientes

- **WHEN** existe al menos una lectura del período sin `fecha_toma` informada
- **THEN** el sistema responde `409` indicando que faltan lecturas por ingresar y mantiene el período abierto

#### Scenario: Cierre válido

- **WHEN** todas las lecturas del período tienen `fecha_toma` informada
- **THEN** el sistema marca `lecturas_cerradas` en verdadero y registra la acción `CERRAR_LECTURAS`

#### Scenario: Cierre repetido

- **WHEN** se intenta cerrar lecturas ya cerradas
- **THEN** el sistema responde `409` con el detalle `"Las lecturas de este período ya están cerradas"`

### Requirement: Reapertura de lecturas

El sistema DEBE (SHALL) exponer `POST /api/v1/boletas/{boleta_id}/reabrir-lecturas`, restringido a roles administrativos, que devuelve el período a captura de lecturas siempre que las liquidaciones no estén cerradas.

#### Scenario: Reapertura permitida

- **WHEN** un administrador reabre las lecturas de un período con `liquidaciones_cerradas` en falso
- **THEN** el sistema marca `lecturas_cerradas` en falso y registra la acción `REABRIR_LECTURAS`

#### Scenario: Reapertura bloqueada por período cerrado

- **WHEN** se intenta reabrir las lecturas de un período con las liquidaciones ya cerradas
- **THEN** el sistema responde `409` con el detalle `"El período ya está cerrado y no se puede reabrir"`

#### Scenario: Lecturas ya abiertas

- **WHEN** se intenta reabrir lecturas que no están cerradas
- **THEN** el sistema responde `409` con el detalle `"Las lecturas ya están abiertas"`

### Requirement: Cierre de liquidaciones

El sistema DEBE (SHALL) exponer `POST /api/v1/boletas/{boleta_id}/cerrar-liquidaciones`, restringido a roles administrativos, que consolida el período. El cierre exige que las lecturas estén cerradas y que exista al menos una liquidación calculada.

#### Scenario: Cierre sin lecturas cerradas

- **WHEN** se intenta cerrar las liquidaciones de un período con `lecturas_cerradas` en falso
- **THEN** el sistema responde `409` indicando que primero deben cerrarse las lecturas

#### Scenario: Cierre sin liquidaciones calculadas

- **WHEN** el período no tiene ninguna liquidación registrada
- **THEN** el sistema responde `409` indicando que debe ejecutarse el cálculo antes de cerrar

#### Scenario: Cierre válido

- **WHEN** las lecturas están cerradas y existen liquidaciones calculadas
- **THEN** el sistema marca `liquidaciones_cerradas` en verdadero y registra la acción `CERRAR_LIQUIDACIONES`

### Requirement: Reapertura de liquidaciones

El sistema DEBE (SHALL) exponer `POST /api/v1/boletas/{boleta_id}/reabrir-liquidaciones`, restringido a roles administrativos, que revierte el cierre del período únicamente mientras la boleta no haya sido publicada a los parceleros.

#### Scenario: Reapertura bloqueada por publicación

- **WHEN** se intenta reabrir las liquidaciones de una boleta con `boleta_visible_usuarios` en verdadero
- **THEN** el sistema responde `409` indicando que la boleta ya fue publicada y no se puede reabrir

#### Scenario: Período no cerrado

- **WHEN** se intenta reabrir las liquidaciones de un período que no está cerrado
- **THEN** el sistema responde `409` con el detalle `"El período no está cerrado"`

### Requirement: Inmutabilidad del período cerrado

Con `liquidaciones_cerradas` en verdadero, el sistema DEBE (SHALL) rechazar toda modificación de la boleta, de sus ítems, de sus lecturas y del estado de pago de sus liquidaciones. La única actualización admitida sobre la boleta es la de su visibilidad para los usuarios.

#### Scenario: Modificación de campos de la boleta

- **WHEN** se intenta actualizar cualquier campo distinto de `boleta_visible_usuarios` en una boleta con período cerrado
- **THEN** el sistema responde `409` con el detalle `"El período está cerrado y no permite modificaciones"`

#### Scenario: Publicación sobre período cerrado

- **WHEN** la actualización solicitada afecta exclusivamente a `boleta_visible_usuarios`
- **THEN** el sistema la acepta pese al cierre del período

### Requirement: Publicación a los parceleros

La publicación DEBE (SHALL) realizarse activando `boleta_visible_usuarios` mediante `PATCH /api/v1/boletas/{boleta_id}`, operación restringida a roles administrativos. La publicación es el paso final del ciclo y bloquea la reapertura del período.

#### Scenario: Publicación del período

- **WHEN** un administrador activa la visibilidad de una boleta con las liquidaciones cerradas
- **THEN** el sistema fija el estado en `publicada`, registra la acción `TOGGLE_VISIBILITY` y los parceleros pasan a ver su liquidación y la imagen de la boleta

### Requirement: Botonera del ciclo en la interfaz administrativa

La pantalla de detalle de boleta DEBE (SHALL) ofrecer únicamente las acciones válidas para el estado actual del período, evitando que el administrador intente transiciones que el backend rechazaría.

#### Scenario: Visibilidad de las acciones

- **WHEN** el administrador abre el detalle de una boleta
- **THEN** la acción de calcular se ofrece mientras las liquidaciones no estén cerradas; cerrar el período se ofrece con las lecturas cerradas y liquidaciones existentes; reabrir lecturas se ofrece con las lecturas cerradas y el período abierto; y reabrir liquidaciones y publicar se ofrecen con el período cerrado y la boleta aún no publicada
