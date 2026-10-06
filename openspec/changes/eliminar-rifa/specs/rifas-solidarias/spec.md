# Spec Delta

## ADDED Requirements

### Requirement: Eliminación de una rifa

El sistema DEBE (SHALL) permitir que **solo el `super_admin`** elimine una rifa, en cualquier estado, junto con todo lo que depende de ella:
- sus compras, vigentes y anuladas;
- los números vendidos;
- las imputaciones al gasto común;
- los archivos de vouchers de transferencia.

Antes de eliminar, el sistema DEBE (SHALL) ofrecer un resumen con:
- la cantidad de compras vigentes y anuladas;
- los números vendidos y el monto pagado;
- las imputaciones pendientes y cargadas;
- los vouchers.

La eliminación DEBE (SHALL) exigir que se escriba el nombre exacto de la rifa como confirmación.

#### Scenario: Super admin elimina una rifa con ventas

- **WHEN** el super admin elimina una rifa con compras y vouchers, confirmando con su nombre exacto
- **THEN** la rifa, sus compras, sus números, sus imputaciones y los archivos de sus vouchers dejan de existir, y la respuesta es `204`

#### Scenario: Confirmación incorrecta

- **WHEN** la confirmación no coincide con el nombre de la rifa
- **THEN** el sistema responde `422` con el detalle `"Escribe el nombre exacto de la rifa para confirmar"` y no borra nada

#### Scenario: Otro rol intenta eliminar

- **WHEN** un `admin_condominio`, la portería o un parcelero intenta eliminar una rifa o consultar su resumen de eliminación
- **THEN** el sistema responde `403`

#### Scenario: Imputaciones ya cargadas en el gasto común

- **WHEN** la rifa tiene imputaciones marcadas como cargadas en Comunidad Feliz
- **THEN** el resumen lo informa y la pantalla advierte que esos cobros deben revertirse a mano en Comunidad Feliz; la eliminación sigue permitida

### Requirement: Auditoría de la eliminación de una rifa

La eliminación de una rifa DEBE (SHALL) registrarse en la auditoría con el código `ELIMINAR_RIFA`, en la misma transacción, con el nombre de la rifa y el resumen de lo borrado (conteos y montos), sin datos personales de los compradores.

#### Scenario: Eliminación auditada

- **WHEN** el super admin elimina una rifa
- **THEN** se registra `ELIMINAR_RIFA` con el condominio, el nombre de la rifa y el resumen, y ese registro permanece después de la eliminación
