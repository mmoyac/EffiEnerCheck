# Spec Delta

## Purpose

Permitir que un condominio organice rifas solidarias cuyos números se venden en la portería o se compran desde el portal, con registro verificable de quién compró qué, cómo pagó y a qué parcela corresponde, y que lo que se imputa al gasto común se informe por parcela, sin alterar la distribución de la boleta eléctrica.

## ADDED Requirements

### Requirement: Creación y configuración de una rifa

El sistema DEBE (SHALL) permitir a los roles administrativos crear una rifa en su condominio con nombre, beneficiario, descripción opcional, una lista ordenada de premios (al menos uno), datos para transferir opcionales (texto libre con banco, cuenta y titular), precio por número (entero positivo, en pesos) y cantidad de números (entero positivo). Los números de una rifa son los enteros del 1 a la cantidad configurada. Toda rifa nueva queda en estado `abierta`.

#### Scenario: Creación válida

- **WHEN** un `admin_condominio` crea una rifa con precio 2000, 100 números y los premios "Notebook e impresora reacondicionadas", "Juego de loza" y "Hervidor eléctrico"
- **THEN** el sistema la registra en su condominio en estado `abierta`, con los números del 1 al 100 disponibles y los premios en ese orden

#### Scenario: Sin premios

- **WHEN** se intenta crear una rifa sin premios
- **THEN** el sistema responde `422` y no la crea

#### Scenario: Valores no positivos

- **WHEN** se intenta crear o editar una rifa con precio o cantidad de números menor o igual a cero
- **THEN** el sistema responde `422` y no guarda cambios

#### Scenario: Rol no administrativo

- **WHEN** un `parcelero`, un `lector` o la `porteria` intenta crear o editar una rifa
- **THEN** el sistema responde `403`

### Requirement: Edición restringida de una rifa abierta

Mientras la rifa está `abierta`, el sistema DEBE (SHALL) permitir editar nombre, beneficiario, descripción, premios y datos para transferir. El precio por número NO DEBE (SHALL NOT) cambiar si la rifa tiene compras vigentes, y la cantidad de números NO DEBE (SHALL NOT) bajar del mayor número vendido. Una rifa `cerrada` NO DEBE (SHALL NOT) editarse.

#### Scenario: Cambio de precio con compras

- **WHEN** el administrador intenta cambiar el precio de una rifa que tiene al menos una compra vigente
- **THEN** el sistema responde `409` indicando que el precio no puede cambiar porque ya hay números vendidos

#### Scenario: Reducción por debajo de un número vendido

- **WHEN** el número 80 está vendido y el administrador intenta reducir la cantidad a 50
- **THEN** el sistema responde `409` y conserva la cantidad anterior

#### Scenario: Ampliación de números

- **WHEN** el administrador aumenta la cantidad de números de una rifa abierta
- **THEN** los nuevos números quedan disponibles para la compra

### Requirement: Formas de pago de una compra

Cada compra DEBE (SHALL) registrar una forma de pago: `efectivo`, `transferencia` o `gasto_comun`. Una compra en `efectivo` queda pagada en el momento de registrarse. Una compra por `transferencia` queda pendiente hasta que un rol administrativo confirma el pago. Una compra con `gasto_comun` NO DEBE (SHALL NOT) marcarse como pagada en EnerCheck: se informa como imputación al cerrar la rifa. Solo la `porteria` y los roles administrativos DEBEN (SHALL) poder registrar compras en `efectivo`.

#### Scenario: Venta en efectivo en portería

- **WHEN** la portería registra una compra en efectivo
- **THEN** la compra queda pagada, con la fecha y la cuenta que recibió el dinero

#### Scenario: Parcelero intenta registrar efectivo

- **WHEN** un `parcelero` envía una compra con forma de pago `efectivo`
- **THEN** el sistema responde `422` y no la registra

#### Scenario: Confirmación de una transferencia

- **WHEN** el administrador confirma el pago de una compra por transferencia
- **THEN** la compra queda pagada con su fecha, y los usuarios de la parcela la ven como pagada

#### Scenario: Confirmar una compra que no es por transferencia

- **WHEN** se intenta confirmar el pago de una compra en efectivo o con gasto común
- **THEN** el sistema responde `409`

### Requirement: Compra de números por un usuario vinculado a la parcela

El sistema DEBE (SHALL) permitir a un usuario autenticado vinculado a parcelas comprar uno o más números de una rifa `abierta` de su condominio, a nombre de una parcela que tenga asociada mediante `usuario_parcelas`, con forma de pago `transferencia` o `gasto_comun`. Cada compra DEBE (SHALL) registrar la parcela, el usuario comprador, los números, la forma de pago y la fecha y hora. No hay límite de números por parcela.

#### Scenario: Compra de varios números

- **WHEN** un parcelero asociado a la parcela 12 compra los números 7, 8 y 15 con imputación al gasto común
- **THEN** el sistema registra una compra a nombre de la parcela 12 con esos tres números, el usuario comprador y la forma de pago, y esos números dejan de estar disponibles

#### Scenario: Parcela no asociada al usuario

- **WHEN** un usuario intenta comprar a nombre de una parcela que no tiene asociada
- **THEN** el sistema responde `403` y no registra la compra

#### Scenario: Número ya vendido

- **WHEN** una compra incluye al menos un número que ya está vendido, incluso si se vendió un instante antes por otra petición
- **THEN** el sistema responde `409` indicando los números no disponibles y no registra ninguno de los números de esa compra

#### Scenario: Número fuera de rango o repetido

- **WHEN** una compra incluye un número menor que 1, mayor que la cantidad de la rifa, o el mismo número dos veces
- **THEN** el sistema responde `422` y no registra la compra

#### Scenario: Rifa cerrada

- **WHEN** un usuario intenta comprar números de una rifa `cerrada`
- **THEN** el sistema responde `409`

### Requirement: Venta en portería y por la administración

El sistema DEBE (SHALL) permitir a la `porteria` y a los roles administrativos registrar una venta a nombre de cualquier parcela activa del condominio de la rifa, con cualquiera de las formas de pago. La venta DEBE (SHALL) admitir el nombre del comprador como texto libre opcional, porque el comprador puede no ser residente, y DEBE (SHALL) dejar constancia del canal (`porteria` o `administracion`) y de la cuenta que la registró.

#### Scenario: Venta a una persona externa

- **WHEN** la portería vende los números 30 y 31 a "Ana Pérez", amiga de la parcela 5, pagados en efectivo
- **THEN** la compra queda a nombre de la parcela 5, con "Ana Pérez" como comprador, canal `porteria` y pagada, y los usuarios de la parcela 5 la ven identificada como venta de portería

#### Scenario: Parcela de otro condominio

- **WHEN** la portería o un `admin_condominio` intenta registrar una venta a nombre de una parcela de otro condominio
- **THEN** el sistema responde `403`

#### Scenario: Parcela inactiva

- **WHEN** se intenta registrar una venta a nombre de una parcela inactiva
- **THEN** el sistema responde `409`

### Requirement: Foto del voucher de transferencia

Una venta por `transferencia` registrada por la `porteria` DEBE (SHALL) incluir una imagen del voucher de la transferencia, tomada con la cámara del equipo o elegida desde sus archivos. En las compras por transferencia hechas desde el portal o por la administración, el voucher DEBE (SHALL) ser opcional y DEBE (SHALL) poder adjuntarse después, mientras el pago no esté confirmado. Los formatos admitidos son JPG, PNG, WEBP, HEIC y PDF, hasta 10 MB. El voucher NO DEBE (SHALL NOT) ser accesible sin sesión: solo pueden verlo los roles administrativos, la `porteria` y los usuarios vinculados a la parcela de la compra.

#### Scenario: Transferencia en portería sin voucher

- **WHEN** la portería registra una venta por transferencia sin adjuntar el voucher
- **THEN** el sistema responde `422` y no registra la venta ni reserva los números

#### Scenario: Transferencia en portería con voucher

- **WHEN** la portería registra una venta por transferencia adjuntando la foto del voucher
- **THEN** la venta queda registrada, pendiente de confirmación, con el voucher asociado

#### Scenario: El administrador revisa antes de confirmar

- **WHEN** el administrador abre una compra por transferencia pendiente que tiene voucher
- **THEN** la aplicación le muestra el voucher junto a la opción de confirmar el pago

#### Scenario: Parcelero adjunta el voucher después

- **WHEN** un parcelero que compró por transferencia desde el portal adjunta su voucher antes de que el pago se confirme
- **THEN** el voucher queda asociado a su compra

#### Scenario: Acceso sin permiso

- **WHEN** alguien sin sesión, o un usuario que no pertenece a la parcela de la compra, solicita el voucher
- **THEN** el sistema responde `401` o `403` según corresponda y no entrega el archivo

#### Scenario: Archivo no admitido

- **WHEN** se adjunta un archivo de otro tipo o de más de 10 MB
- **THEN** el sistema responde `422` y no registra la venta ni el adjunto

### Requirement: Teléfono propuesto y comprobante por WhatsApp

Al registrar una venta en portería o por la administración, la aplicación DEBE (SHALL) proponer los teléfonos registrados de los usuarios vinculados a la parcela elegida y permitir elegir uno, editarlo o ingresar otro. El teléfono usado DEBE (SHALL) guardarse en la compra. Tras confirmar una compra con teléfono, la aplicación DEBE (SHALL) ofrecer abrir WhatsApp dirigido a ese teléfono con un mensaje ya redactado que incluya el nombre de la rifa, los números, la parcela, el monto, la forma de pago, los premios y, si el pago es por transferencia, los datos para transferir. El sistema NO DEBE (SHALL NOT) enviar mensajes por sí mismo.

#### Scenario: Parcela con teléfono registrado

- **WHEN** la portería elige la parcela 23 y uno de sus residentes tiene teléfono registrado
- **THEN** la aplicación propone ese teléfono, que puede usarse tal cual o modificarse

#### Scenario: Envío del comprobante

- **WHEN** la portería confirma una venta con teléfono y pulsa enviar comprobante
- **THEN** la aplicación abre WhatsApp con ese número de destino y el mensaje redactado, listo para que la portería lo envíe

#### Scenario: Teléfono con formato local

- **WHEN** el teléfono ingresado tiene formato local, como `9 9332 7142`
- **THEN** la aplicación lo normaliza al formato internacional chileno `56993327142` antes de abrir WhatsApp

#### Scenario: Venta sin teléfono

- **WHEN** la parcela no tiene teléfonos registrados y la portería no ingresa ninguno
- **THEN** la venta se registra igual, la aplicación no ofrece enviar comprobante por WhatsApp y muestra el folio para entregarlo por escrito

### Requirement: Folio y comprobante sin teléfono

Cada compra DEBE (SHALL) tener un folio corto y único dentro de su rifa, con el formato `R<id de la rifa>-<correlativo de tres dígitos o más>` (por ejemplo `R3-042`), que identifica la compra en el comprobante, la lista del sorteo y las búsquedas. Tras confirmar una venta, la aplicación DEBE (SHALL) mostrar de forma destacada el folio, los números, la parcela y el monto, para que la portería pueda anotarlos en papel, y DEBE (SHALL) ofrecer imprimir un comprobante con esos datos y los premios. La portería DEBE (SHALL) poder buscar las compras vigentes de una parcela o por folio.

#### Scenario: Comprador en efectivo sin teléfono

- **WHEN** la portería vende en efectivo los números 12 y 13 a una persona sin teléfono
- **THEN** la aplicación muestra el folio, los números, la parcela y el monto en grande, y ofrece imprimir el comprobante

#### Scenario: Comprobante extraviado

- **WHEN** un comprador sin comprobante pregunta en la portería por sus números
- **THEN** la portería busca por parcela o por folio y le informa sus números y su folio

#### Scenario: Correlativo por rifa

- **WHEN** se registran tres compras en la rifa 3 y la segunda se anula
- **THEN** sus folios son `R3-001`, `R3-002` y `R3-003`, y el folio de la compra anulada no se reutiliza

### Requirement: Anulación de compras mientras la rifa está abierta

Mientras la rifa está `abierta`, el sistema DEBE (SHALL) permitir a los roles administrativos anular cualquier compra, y al usuario que la hizo anular su propia compra si fue hecha desde el portal y no está pagada. Al anularla, sus números DEBEN (SHALL) volver a quedar disponibles, y la compra DEBE (SHALL) conservarse en el historial marcada como anulada, con quién la anuló y cuándo. La `porteria` NO DEBE (SHALL NOT) anular compras, y otros usuarios de la misma parcela NO DEBEN (SHALL NOT) anular una compra ajena.

#### Scenario: El comprador se arrepiente

- **WHEN** el usuario que compró desde el portal los números 7 y 8, aún sin pagar, anula su compra con la rifa abierta
- **THEN** los números 7 y 8 quedan disponibles y la compra aparece como anulada en el historial de la parcela

#### Scenario: Compra ya pagada

- **WHEN** un parcelero intenta anular su compra por transferencia que el administrador ya confirmó
- **THEN** el sistema responde `403`, y la anulación debe pedirse al administrador

#### Scenario: La portería intenta anular

- **WHEN** la portería intenta anular una venta
- **THEN** el sistema responde `403`

#### Scenario: Anulación de una venta en efectivo

- **WHEN** el administrador anula una venta pagada en efectivo
- **THEN** la compra queda anulada y deja de sumar en la caja de portería, y el registro de auditoría indica que había sido pagada en efectivo

#### Scenario: Rifa cerrada

- **WHEN** se intenta anular una compra de una rifa `cerrada`
- **THEN** el sistema responde `409`

### Requirement: Visibilidad de las compras por parcela

El sistema DEBE (SHALL) mostrar a cada usuario las compras, vigentes y anuladas, de todas las parcelas que tiene asociadas, indicando para cada una los números, quién la hizo (el usuario, o el canal y el nombre del comprador), la fecha y hora, el monto, la forma de pago y si está pagada. Un usuario sin rol administrativo ni de portería NO DEBE (SHALL NOT) ver quién compró los números de otras parcelas: para esas solo ve que el número no está disponible.

#### Scenario: Compra hecha por otro integrante de la parcela

- **WHEN** un usuario de la parcela 12 abre la rifa y otro usuario de esa parcela compró los números 20 y 21
- **THEN** la aplicación le muestra esa compra con el nombre del comprador, los números, la fecha y hora, el monto y la forma de pago

#### Scenario: Número vendido a otra parcela

- **WHEN** un parcelero ve la grilla y el número 40 está vendido a otra parcela
- **THEN** la aplicación lo muestra como no disponible sin revelar la parcela ni el comprador

#### Scenario: La portería ve las ventas

- **WHEN** la portería abre una rifa
- **THEN** la aplicación le muestra todas las compras de la rifa, para poder responder consultas de los vecinos

### Requirement: Compra simple desde el portal

La aplicación DEBE (SHALL) ofrecer al parcelero los premios de la rifa y una grilla de sus números que distinga los disponibles, los no disponibles y los de su parcela, y permitir seleccionar varios números disponibles, elegir la forma de pago (`transferencia` o `gasto_comun`) y confirmar la compra en un paso que muestre la cantidad y el monto total. Si el usuario tiene varias parcelas asociadas, la aplicación DEBE (SHALL) pedirle que elija a nombre de cuál compra. Cuando el condominio tiene una rifa abierta, la pantalla principal del parcelero DEBE (SHALL) mostrar un aviso con acceso directo a la compra.

#### Scenario: Confirmación de la compra

- **WHEN** el usuario selecciona tres números de una rifa con precio 2000, elige gasto común y pulsa confirmar
- **THEN** la aplicación muestra una confirmación con los tres números, el total de 6000 y la forma de pago antes de registrar la compra

#### Scenario: Pago por transferencia

- **WHEN** el usuario elige pagar por transferencia
- **THEN** la aplicación le muestra los datos para transferir de la rifa y le indica que la compra quedará pendiente hasta que la administración confirme el pago

#### Scenario: Número tomado mientras se elegía

- **WHEN** al confirmar, el sistema rechaza la compra porque un número ya fue vendido
- **THEN** la aplicación informa qué números ya no están disponibles, refresca la grilla y conserva seleccionados los que siguen libres

#### Scenario: Aviso de rifa abierta

- **WHEN** un parcelero entra a su pantalla principal y existe una rifa abierta en su condominio
- **THEN** la aplicación muestra un aviso con el nombre de la rifa y el beneficiario, con acceso a la compra

### Requirement: Pantalla de venta de la portería

La aplicación DEBE (SHALL) ofrecer a la `porteria` una pantalla de venta optimizada para tablet o teléfono que, para la rifa abierta elegida, permita buscar la parcela por número o por nombre del propietario, elegir los números en la grilla, ingresar el nombre del comprador, elegir la forma de pago con `efectivo` como opción predeterminada, tomar la foto del voucher si el pago es por transferencia, elegir o editar el teléfono y confirmar; y que, tras la venta, ofrezca enviar el comprobante y comenzar una venta nueva sin salir de la pantalla.

#### Scenario: Venta completa

- **WHEN** la portería busca "23", elige la parcela, marca los números 12 y 13 y confirma en efectivo
- **THEN** la aplicación registra la venta, muestra el resumen con la opción de enviar el comprobante por WhatsApp y deja la pantalla lista para la siguiente venta

#### Scenario: Sin rifas abiertas

- **WHEN** la portería entra y el condominio no tiene rifas abiertas
- **THEN** la aplicación informa que no hay rifas a la venta

### Requirement: Caja de portería

El sistema DEBE (SHALL) entregar a los roles administrativos y a la `porteria` un resumen del efectivo recibido en una rifa, agrupado por día y por cuenta que registró la venta, con la cantidad de números y el monto, considerando solo compras vigentes.

#### Scenario: Cuadre del día

- **WHEN** el administrador consulta la caja de una rifa en la que la portería vendió hoy 5 números en efectivo a 2000 y se anuló una de esas ventas de 1 número
- **THEN** el resumen de hoy para la portería muestra 4 números y 8000

### Requirement: Cierre de la rifa e imputaciones al gasto común

El sistema DEBE (SHALL) permitir a los roles administrativos cerrar una rifa `abierta`. Al cerrarla, las compras vigentes quedan firmes y el sistema DEBE (SHALL) generar una imputación por cada parcela con al menos un número vigente comprado con `gasto_comun`, cuyo monto es la cantidad de esos números por el precio por número. Las imputaciones NO DEBEN (SHALL NOT) incorporarse a las liquidaciones eléctricas ni afectar el cálculo del Motor EnerCheck. Las compras por transferencia pendientes al cierre DEBEN (SHALL) poder confirmarse después.

#### Scenario: Cierre con formas de pago mixtas

- **WHEN** el administrador cierra una rifa de precio 2000 en la que la parcela 12 tiene 3 números con gasto común y 1 en efectivo, y la parcela 5 tiene 2 por transferencia
- **THEN** la rifa queda `cerrada` y se genera una sola imputación, de 6000, para la parcela 12

#### Scenario: Compras anuladas

- **WHEN** una parcela solo tiene compras anuladas con gasto común al momento del cierre
- **THEN** no se le genera imputación

#### Scenario: Liquidación eléctrica intacta

- **WHEN** se cierra una rifa y luego se calculan las liquidaciones de un período
- **THEN** los totales de las liquidaciones no incluyen montos de la rifa

### Requirement: Exportación de imputaciones para Comunidad Feliz

El sistema DEBE (SHALL) permitir a los roles administrativos descargar en CSV las imputaciones de una rifa cerrada, con una fila por parcela que indique la unidad, el propietario, la cantidad de números, el monto y un concepto con el nombre de la rifa, y marcar cada imputación como cargada en el sistema de gasto común o revertir esa marca. Cada usuario DEBE (SHALL) ver el monto y el estado de las imputaciones de sus parcelas.

#### Scenario: Descarga de imputaciones

- **WHEN** el administrador descarga las imputaciones de una rifa cerrada
- **THEN** recibe un CSV con una fila por parcela imputada, ordenado por unidad, con el concepto "Rifa <nombre>"

#### Scenario: Imputación cargada

- **WHEN** el administrador marca como cargada la imputación de la parcela 12
- **THEN** la imputación queda cargada con su fecha, y los usuarios de la parcela 12 la ven como incluida en su gasto común

### Requirement: Reapertura de una rifa cerrada

El sistema DEBE (SHALL) permitir a los roles administrativos reabrir una rifa `cerrada` solo si ninguna de sus imputaciones está marcada como cargada. Al reabrirla, sus imputaciones DEBEN (SHALL) eliminarse y las compras vuelven a poder anularse.

#### Scenario: Reapertura sin imputaciones cargadas

- **WHEN** el administrador reabre una rifa cerrada sin imputaciones cargadas
- **THEN** la rifa vuelve a `abierta` y sus imputaciones se eliminan

#### Scenario: Reapertura con una imputación cargada

- **WHEN** el administrador intenta reabrir una rifa con al menos una imputación cargada
- **THEN** el sistema responde `409` y la rifa sigue cerrada

### Requirement: Lista de compradores para el sorteo

El sistema DEBE (SHALL) entregar a los roles administrativos la lista de números vigentes de una rifa, ordenada por número, con el folio, la parcela, el comprador, el canal, la forma de pago y la fecha de compra, y permitir descargarla en CSV. El sistema NO DEBE (SHALL NOT) realizar el sorteo.

#### Scenario: Exportación

- **WHEN** el administrador descarga la lista de una rifa
- **THEN** recibe un archivo CSV con una fila por número vigente, ordenada por número, sin las compras anuladas

### Requirement: Aislamiento por condominio de las rifas

Toda consulta y mutación sobre rifas, compras e imputaciones DEBE (SHALL) filtrarse o validarse contra el tenant activo cuando este no es nulo. El `super_admin` accede a las rifas de todos los condominios.

#### Scenario: Rifa de otro condominio

- **WHEN** un usuario o la portería solicita por identificador una rifa, compra o imputación de otro condominio
- **THEN** el sistema responde `403` sin exponer su contenido

#### Scenario: Listado de rifas

- **WHEN** un usuario con tenant definido lista rifas
- **THEN** el sistema devuelve solo las rifas de su condominio

### Requirement: Auditoría de las operaciones de rifa

Toda mutación de rifas DEBE (SHALL) registrarse en la auditoría en la misma transacción, con estos códigos de acción: `CREATE_RIFA`, `UPDATE_RIFA`, `COMPRAR_RIFA`, `ANULAR_COMPRA_RIFA`, `CONFIRMAR_PAGO_RIFA`, `CERRAR_RIFA`, `REABRIR_RIFA` y `MARCAR_IMPUTACION_RIFA`. Los detalles DEBEN (SHALL) incluir la rifa, la parcela, los números, la forma de pago y el canal cuando corresponda.

#### Scenario: Venta auditada

- **WHEN** la portería registra una venta
- **THEN** se registra `COMPRAR_RIFA` con la cuenta de portería, el condominio, la rifa, la parcela, los números, el monto, la forma de pago, el canal y el nombre del comprador

#### Scenario: Edición auditada

- **WHEN** el administrador edita una rifa
- **THEN** se registra `UPDATE_RIFA` con el valor anterior y el nuevo de cada campo modificado
