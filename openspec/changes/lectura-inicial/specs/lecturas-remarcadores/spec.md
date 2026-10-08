# Spec Delta

## ADDED Requirements

### Requirement: Captura de la lectura inicial

En un período de lectura inicial, la aplicación del lector DEBE (SHALL) identificarlo como «Lectura inicial». La pantalla de captura DEBE (SHALL) pedir la lectura del medidor sin mostrar lectura anterior ni consumo. La captura DEBE (SHALL) funcionar con las mismas garantías que un período regular: sin conexión, con foto del medidor, sincronización y detección de conflictos.

#### Scenario: Captura de la lectura de partida

- **WHEN** el lector abre una parcela de un período de lectura inicial
- **THEN** la pantalla se titula «Lectura inicial» y pide el valor del medidor, sin lectura anterior ni consumo

#### Scenario: Lectura inicial sin señal

- **WHEN** el lector toma una lectura inicial sin conexión
- **THEN** la lectura y su foto quedan guardadas en el dispositivo y se sincronizan al volver la señal, igual que en un período regular

### Requirement: Lectura anterior editable solo sin historial

El listado de lecturas de un período DEBE (SHALL) informar, por cada lectura, si su lectura anterior es editable (`lectura_anterior_editable`). Es editable cuando la parcela no tiene ninguna lectura en un período anterior del condominio y el período es regular. La consola administrativa DEBE (SHALL) permitir ingresar la lectura anterior solo en esas lecturas.

#### Scenario: Parcela agregada después

- **WHEN** el administrador abre las lecturas de un período en el que una parcela nueva no tiene historial
- **THEN** la lectura anterior de esa parcela aparece editable y las demás no

## MODIFIED Requirements

### Requirement: Corrección de una lectura

El sistema DEBE (SHALL) exponer `PATCH /api/v1/lecturas/{lectura_id}`, restringido a `lector` y roles administrativos, que aplica actualizaciones parciales y recalcula el consumo cuando cambia alguno de los dos valores del medidor. El sistema NO DEBE (SHALL NOT) aceptar un cambio de `lectura_anterior` cuando la parcela tiene una lectura en un período anterior del condominio, porque ese valor viene del período anterior.

#### Scenario: Recálculo del consumo

- **WHEN** se modifica `lectura_actual`, o `lectura_anterior` en una parcela sin historial
- **THEN** el sistema recalcula `kwh_consumidos` como la diferencia entre la lectura actual y la anterior

#### Scenario: Lectura anterior con historial

- **WHEN** se intenta cambiar `lectura_anterior` de una parcela que tiene una lectura en un período anterior
- **THEN** el sistema responde `409` indicando que la lectura anterior viene del período anterior, y no modifica nada

#### Scenario: Reasignación de autoría

- **WHEN** un usuario corrige una lectura tomada por otra persona
- **THEN** el sistema reemplaza `lector_id` por el usuario que realiza la corrección y deja constancia del autor previo en el registro de auditoría

#### Scenario: Lectura inexistente

- **WHEN** el identificador de lectura no existe
- **THEN** el sistema responde `404` con el detalle `"Lectura no encontrada"`
