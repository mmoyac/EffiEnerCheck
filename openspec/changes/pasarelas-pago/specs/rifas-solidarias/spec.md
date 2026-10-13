# Spec Delta

## ADDED Requirements

### Requirement: Formas de pago según el canal

Una rifa DEBE (SHALL) poder aceptar la forma de pago `en_linea` además de `efectivo`, `transferencia` y `gasto_comun`. Dentro de las formas que acepta la rifa, el canal DEBE (SHALL) determinar las disponibles:

- Comunero desde el portal: `en_linea` y `gasto_comun`.
- Portería y administración: las mismas de antes, es decir, las que acepta la rifa salvo `en_linea`. En portería la `transferencia` exige voucher.

Cuando el comunero no puede pagar en línea (la rifa no acepta `en_linea`, o el condominio no tiene una pasarela disponible para el monto) y la rifa acepta `en_linea` o `transferencia`, el comunero DEBE (SHALL) poder usar la `transferencia` manual, con los datos bancarios de la rifa y el voucher obligatorio, igual que en portería. El servidor DEBE (SHALL) rechazar con `422` una forma de pago no disponible para el canal. La aplicación DEBE (SHALL) indicar que el pago en línea tiene un costo adicional para el comunero.

#### Scenario: Comunero elige pago en línea

- **WHEN** el comunero selecciona números de una rifa que acepta `en_linea` y elige "Pago en línea"
- **THEN** la aplicación pasa directamente a la elección de pasarela, o al total de la única pasarela disponible

#### Scenario: Portería intenta cobrar en línea

- **WHEN** la portería envía una compra con forma de pago `en_linea`
- **THEN** el sistema responde `422` y no la registra

#### Scenario: Comunero con pasarela disponible intenta transferencia manual

- **WHEN** el condominio tiene una pasarela disponible y el comunero envía una compra por `transferencia`
- **THEN** el sistema responde `422` y no la registra

#### Scenario: Sin pasarelas disponibles

- **WHEN** la rifa acepta `en_linea` pero el condominio no tiene pasarelas disponibles
- **THEN** el comunero ve "Transferencia" con los datos bancarios de la rifa y debe adjuntar el voucher para registrar la compra, que queda pendiente hasta que la administración confirme el pago

#### Scenario: Comunero sin voucher en el respaldo manual

- **WHEN** el comunero envía una compra por `transferencia` sin voucher porque no hay pasarelas disponibles
- **THEN** el sistema responde `422` con "Adjunta la foto del voucher de la transferencia"

### Requirement: Reserva de números durante el pago en línea

Al iniciar un pago en línea, el sistema DEBE (SHALL) registrar la compra pendiente con su folio y reservar sus números mientras la intención esté `INICIADO`. La compra NO DEBE (SHALL NOT) confirmarse a mano ni anularla el comunero mientras su pago está en curso. Cuando la intención se confirma, la compra DEBE (SHALL) quedar pagada con la fecha de confirmación. Cuando la intención se rechaza o vence, la compra DEBE (SHALL) anularse automáticamente y sus números quedar libres.

#### Scenario: Pago confirmado

- **WHEN** se confirma la intención de una compra en línea
- **THEN** la compra queda pagada y sus números siguen asignados a la parcela

#### Scenario: Pago rechazado

- **WHEN** la intención de una compra en línea queda rechazada
- **THEN** la compra queda anulada y sus números vuelven a estar disponibles

#### Scenario: Número reservado

- **WHEN** otro comunero intenta comprar un número reservado por un pago en línea en curso
- **THEN** el sistema responde `409` indicando que el número no está disponible

#### Scenario: Confirmar a mano una compra en línea

- **WHEN** la administración intenta confirmar a mano el pago de una compra `en_linea`
- **THEN** el sistema responde `409`

### Requirement: Pago en línea aprobado tarde

Si el pago de una compra en línea se aprueba después de anulada la compra, el sistema DEBE (SHALL) reactivarla con sus mismos números y folio cuando todos siguen libres y la rifa sigue abierta. En otro caso, la intención DEBE (SHALL) quedar `EN_REVISION` con el motivo ("números ya vendidos" o "rifa cerrada"), para que la administración resuelva con el comunero.

#### Scenario: Números todavía libres

- **WHEN** llega aprobado el pago de una compra anulada por vencimiento y sus números siguen libres
- **THEN** la compra se reactiva pagada con sus números

#### Scenario: Números ya vendidos

- **WHEN** llega aprobado el pago de una compra anulada y uno de sus números ya se vendió a otra parcela
- **THEN** la compra sigue anulada y la intención queda `EN_REVISION` con el motivo "números ya vendidos"

### Requirement: Cierre de rifa con pagos en curso

El sistema NO DEBE (SHALL NOT) cerrar una rifa mientras tenga intenciones de pago `INICIADO` vigentes; DEBE (SHALL) responder `409` indicando cuántos pagos están en curso. Las compras `en_linea` pagadas NO DEBEN (SHALL NOT) generar imputaciones al gasto común.

#### Scenario: Cerrar con un pago en curso

- **WHEN** la administración cierra una rifa con un pago en línea en curso
- **THEN** el sistema responde `409` con "Hay 1 pago en línea en curso; espera a que termine"

### Requirement: Anulación de una compra pagada en línea

La administración DEBE (SHALL) poder anular una compra `en_linea` ya pagada mientras la rifa esté abierta. Antes de confirmar, la aplicación DEBE (SHALL) advertir que anular no devuelve el dinero, con el total cobrado, la pasarela y el número de operación. Al anularla, el sistema DEBE (SHALL) liberar sus números y dejar su intención de pago `EN_REVISION` con el motivo de devolución, para que aparezca en los pagos por revisar hasta que la administración la marque resuelta. El sistema NO DEBE (SHALL NOT) devolver el dinero por sí mismo: la devolución se hace en la pasarela.

#### Scenario: Anular una compra pagada en línea

- **WHEN** la administración anula la compra R4-009, pagada en línea por $1.009 en Khipu con la operación vrlhqjzgqrmv
- **THEN** los números quedan libres, la compra se muestra «Anulada · devolución pendiente» y el pago aparece en los pagos por revisar con el motivo «Compra R4-009 anulada después de pagada: devolver $1.009 en Khipu (operación vrlhqjzgqrmv)»

#### Scenario: Devolución resuelta

- **WHEN** la administración marca resuelto ese pago con una nota
- **THEN** la compra se muestra «Anulada · devolución resuelta» y el pago deja de aparecer en los pagos por revisar
