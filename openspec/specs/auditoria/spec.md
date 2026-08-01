# auditoria Specification

## Purpose

Dejar rastro de quién hizo qué sobre los datos que determinan cuánto paga cada parcela. En una comunidad, la confianza en el prorrateo depende de poder reconstruir el historial: quién cargó la boleta, quién tomó o corrigió una lectura, quién cerró el período y quién lo publicó. Los registros de auditoría son de solo escritura desde la lógica de negocio y guardan el estado anterior y posterior de cada cambio relevante.

## Requirements

### Requirement: Registro de las mutaciones relevantes

Toda operación que altere boletas, ítems de detalle, lecturas, liquidaciones, parcelas o usuarios DEBE (SHALL) dejar un registro de auditoría con el usuario que la ejecutó, el condominio afectado, la acción y sus detalles.

#### Scenario: Acción registrada junto con la operación

- **WHEN** una mutación auditada se confirma en la base de datos
- **THEN** el registro de auditoría se persiste en la misma transacción, de modo que un fallo posterior revierte ambos

#### Scenario: Acción ejecutada por un super admin sin condominio

- **WHEN** la operación la ejecuta un usuario sin condominio asignado
- **THEN** el registro se guarda con el condominio sin informar y conserva el identificador del usuario responsable

### Requirement: Vocabulario de acciones

Cada registro DEBE (SHALL) identificar la acción mediante un código en mayúsculas con guiones bajos. El vocabulario en uso comprende `UPLOAD_BOLETA`, `UPDATE_BOLETA`, `TOGGLE_VISIBILITY`, `UPLOAD_IMAGEN_BOLETA`, `PROCESS_OCR`, `UPDATE_DETALLES_BOLETA`, `DELETE_BOLETA`, `CERRAR_LECTURAS`, `REABRIR_LECTURAS`, `CERRAR_LIQUIDACIONES`, `REABRIR_LIQUIDACIONES`, `CREATE_LECTURA`, `UPDATE_LECTURA`, `CALCULAR_LIQUIDACIONES`, `MARCAR_PAGO`, `CREATE_PARCELA`, `UPDATE_PARCELA`, `CREATE_USER`, `UPDATE_USER` y `DELETE_USER`.

#### Scenario: Distinción entre actualización y publicación

- **WHEN** una actualización de boleta incluye el campo `boleta_visible_usuarios`
- **THEN** la acción se registra como `TOGGLE_VISIBILITY`, y como `UPDATE_BOLETA` en caso contrario

### Requirement: Captura del estado anterior y posterior

En las actualizaciones parciales, los detalles del registro DEBEN (SHALL) incluir el valor previo y el valor nuevo de cada campo modificado.

#### Scenario: Corrección de una lectura

- **WHEN** se corrige la lectura de una parcela
- **THEN** el registro guarda los valores anteriores y nuevos de los campos afectados, incluyendo el autor previo de la lectura, con las fechas serializadas en formato de texto

### Requirement: Exclusión de datos sensibles

Los registros de auditoría NO DEBEN (SHALL NOT) contener contraseñas ni sus hashes.

#### Scenario: Cambio de contraseña de un usuario

- **WHEN** se actualiza la contraseña de una cuenta
- **THEN** el registro de auditoría documenta el cambio sin incluir el valor en texto plano ni el hash almacenado

### Requirement: Trazabilidad del origen de la petición

El registro DEBE (SHALL) poder almacenar la dirección IP del cliente cuando la operación la aporta.

#### Scenario: Carga de boleta desde el navegador

- **WHEN** un administrador crea una boleta maestra
- **THEN** el registro incluye la dirección IP del cliente que originó la petición cuando esta está disponible

### Requirement: Marca temporal de cada registro

Cada registro de auditoría DEBE (SHALL) llevar una marca de tiempo con zona horaria asignada por la base de datos en el momento de la inserción.

#### Scenario: Reconstrucción del historial

- **WHEN** se consultan los registros de un condominio
- **THEN** cada entrada permite ordenar cronológicamente las acciones del período
