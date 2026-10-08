# Spec Delta

## ADDED Requirements

### Requirement: Agradecimiento tras la compra desde el portal

Cuando el sistema registra una compra hecha por el comunero desde su portal, la aplicación DEBE (SHALL) reemplazar la grilla de compra por una pantalla de agradecimiento que muestre:

- un mensaje de agradecimiento por el aporte, que mencione al beneficiario de la rifa;
- el folio, los números comprados, la parcela, el monto total y la forma de pago.

La pantalla DEBE (SHALL) indicar además el paso siguiente según la forma de pago:

- **transferencia:** los datos para transferir de la rifa y el aviso de que la compra queda pendiente hasta que la administración confirme el pago;
- **gasto común:** el aviso de que el monto se cargará en un próximo gasto común de la parcela.

La pantalla DEBE (SHALL) ofrecer acciones para guardar o compartir el comprobante, comprar más números y volver a la rifa. Lo que muestra DEBE (SHALL) provenir de la compra que confirmó el sistema, no de la selección hecha en pantalla. Las ventas de portería y de administración NO DEBEN (SHALL NOT) cambiar por este requisito: siguen mostrando su comprobante de venta.

#### Scenario: Compra con cargo al gasto común

- **WHEN** el comunero confirma la compra de los números 7 y 12 de una rifa con precio 2000, pagando con gasto común, y el sistema la registra con folio `R3-015`
- **THEN** la aplicación muestra el agradecimiento con el folio `R3-015`, los números 7 y 12, su parcela, el total de 4000 y el aviso de que se cargará en un próximo gasto común

#### Scenario: Compra por transferencia

- **WHEN** el comunero confirma una compra pagando por transferencia
- **THEN** la pantalla de agradecimiento muestra los datos para transferir de la rifa e indica que la compra quedará pendiente hasta que la administración confirme el pago

#### Scenario: Rifa sin datos de transferencia

- **WHEN** el comunero paga por transferencia y la rifa no tiene datos para transferir registrados
- **THEN** la pantalla indica que la administración le hará llegar los datos de pago, sin mostrar un bloque vacío

#### Scenario: Comprar más números

- **WHEN** el comunero pulsa comprar más en la pantalla de agradecimiento
- **THEN** la aplicación vuelve a la grilla con la selección vacía y con los números recién comprados marcados como de su parcela

#### Scenario: Compra rechazada

- **WHEN** el sistema rechaza la compra, por ejemplo porque un número ya fue vendido
- **THEN** la aplicación no muestra el agradecimiento: informa el error y conserva la grilla, como antes

#### Scenario: Venta en portería sin cambios

- **WHEN** la portería registra una venta
- **THEN** la aplicación muestra el comprobante de venta de portería y no la pantalla de agradecimiento del comunero
