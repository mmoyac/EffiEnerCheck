# Spec Delta

## Purpose

Cobro en línea común a toda la plataforma: cada condominio configura sus pasarelas de pago (Flow, Khipu u otras) y cualquier módulo puede cobrar a través de ellas, con el resultado decidido siempre por el backend consultando al proveedor y un solo pago registrado por intención.

## ADDED Requirements

### Requirement: Pasarelas de pago por condominio

Cada condominio DEBE (SHALL) poder tener varias pasarelas de pago, cada una con proveedor (`flow`, `khipu` u otro registrado), nombre visible para el comunero, ambiente (`integracion` o `produccion`), credenciales, comisión (porcentaje con IVA incluido y monto fijo en pesos), orden, estado activo, fecha y resultado de la última prueba de conexión y fecha del último cambio de credenciales. Solo el `super_admin` DEBE (SHALL) poder crear, modificar, probar, activar, desactivar y eliminar pasarelas, en cualquier condominio. El `admin_condominio` DEBE (SHALL) poder ver las pasarelas de su condominio (proveedor, nombre visible, ambiente, comisión, estado y última prueba), sin modificarlas. Los demás roles reciben `403`. Una pasarela NO DEBE (SHALL NOT) ser visible ni usable desde otro condominio.

#### Scenario: Super admin crea una pasarela

- **WHEN** el `super_admin` crea para un condominio una pasarela Flow de integración con sus credenciales y una comisión de 3,8 %
- **THEN** la pasarela queda registrada en ese condominio, inactiva, y la respuesta indica que las credenciales están cargadas sin incluir sus valores

#### Scenario: Administrador del condominio ve sus pasarelas

- **WHEN** un `admin_condominio` consulta las pasarelas de su condominio
- **THEN** ve su proveedor, nombre, ambiente, comisión, estado y última prueba, sin acciones para modificarlas

#### Scenario: Administrador del condominio intenta modificar

- **WHEN** un `admin_condominio` intenta crear, modificar, probar, activar o eliminar una pasarela
- **THEN** el sistema responde `403`

#### Scenario: Comunero intenta ver las pasarelas

- **WHEN** un `comunero` consulta la lista de pasarelas
- **THEN** el sistema responde `403`

#### Scenario: Pasarela de otro condominio

- **WHEN** un `admin_condominio` intenta ver una pasarela de otro condominio
- **THEN** el sistema responde `404`

### Requirement: Credenciales cifradas y nunca expuestas

Las credenciales de una pasarela DEBEN (SHALL) guardarse cifradas con AES-256-GCM, con una clave maestra de entorno y un dato asociado que las amarra a su condominio y su pasarela. La API NO DEBE (SHALL NOT) devolver nunca los valores de las credenciales: solo informa si están cargadas, y se pueden reemplazar enteras. La auditoría NO DEBE (SHALL NOT) registrar los valores. Sin clave maestra, el sistema NO DEBE (SHALL NOT) guardar credenciales (los pagos en línea son opcionales y el resto del sistema funciona); con una clave maestra mal formada, el arranque en producción DEBE (SHALL) fallar. DEBE (SHALL) existir un comando para rotar la clave maestra que recifra todas las credenciales.

#### Scenario: Credenciales en la respuesta

- **WHEN** se lista o se consulta una pasarela con credenciales cargadas
- **THEN** la respuesta indica `credenciales_cargadas: true` y no incluye ninguna clave ni secreto

#### Scenario: Credenciales copiadas a otra pasarela

- **WHEN** el texto cifrado de las credenciales de una pasarela se copia en la base a otra pasarela
- **THEN** el sistema no logra descifrarlas y trata la pasarela como sin credenciales válidas

#### Scenario: Sin clave maestra

- **WHEN** el servidor no tiene la clave maestra de pagos y el `super_admin` intenta crear una pasarela
- **THEN** el sistema responde `422` nombrando la variable faltante y no guarda la pasarela ni sus credenciales

#### Scenario: Clave maestra mal formada en producción

- **WHEN** el backend arranca en producción con una clave maestra que no son 32 bytes en base64
- **THEN** el arranque falla con un mensaje que nombra la variable

#### Scenario: Auditoría del cambio de credenciales

- **WHEN** el `super_admin` reemplaza las credenciales de una pasarela
- **THEN** la auditoría registra la acción, la pasarela y los nombres de los campos cambiados, pero no sus valores

### Requirement: Prueba de conexión y activación

El `super_admin` DEBE (SHALL) poder probar la conexión de una pasarela sin crear cobros; el sistema DEBE (SHALL) guardar la fecha y el resultado, y distinguir el error de credenciales de un error de comunicación. Activar una pasarela de ambiente `produccion` DEBE (SHALL) exigir una prueba exitosa posterior al último cambio de credenciales. Cambiar el ambiente o las credenciales de una pasarela DEBE (SHALL) desactivarla. Una pasarela solo DEBE (SHALL) poder eliminarse si no tiene intenciones de pago.

#### Scenario: Prueba con credenciales válidas

- **WHEN** el `super_admin` prueba una pasarela con credenciales válidas
- **THEN** el sistema informa conexión correcta, guarda la fecha y no crea ningún cobro en el proveedor

#### Scenario: Prueba con credenciales inválidas

- **WHEN** el proveedor rechaza las credenciales en la prueba
- **THEN** el sistema informa "Credenciales rechazadas por el proveedor" y guarda el resultado fallido

#### Scenario: Activar producción sin prueba vigente

- **WHEN** se intenta activar una pasarela de producción cuya última prueba exitosa es anterior al último cambio de credenciales
- **THEN** el sistema responde `409` pidiendo probar la conexión primero

#### Scenario: Eliminar una pasarela con pagos

- **WHEN** se intenta eliminar una pasarela que tiene intenciones de pago
- **THEN** el sistema responde `409` y ofrece desactivarla en su lugar

### Requirement: Pasarelas ofrecidas al comunero

Al pagar en línea, el sistema DEBE (SHALL) ofrecer al comunero solo las pasarelas activas de su condominio, en su orden. En el entorno de producción NO DEBE (SHALL NOT) ofrecer pasarelas de ambiente `integracion`. Una pasarela cuyo monto mínimo de proveedor supera el total a cobrar NO DEBE (SHALL NOT) ofrecerse, y la aplicación DEBE (SHALL) explicar por qué. Por cada pasarela, la aplicación DEBE (SHALL) mostrar el nombre visible, la comisión y el total a pagar antes de iniciar el pago. Si queda una sola pasarela disponible, la aplicación DEBE (SHALL) omitir la elección y mostrar directamente su total.

#### Scenario: Una sola pasarela

- **WHEN** el condominio tiene solo Khipu activa y el comunero elige pagar en línea
- **THEN** la aplicación muestra el total con la comisión de Khipu y el botón para pagar, sin pedir elegir pasarela

#### Scenario: Varias pasarelas

- **WHEN** el condominio tiene Flow y Khipu activas
- **THEN** la aplicación lista ambas con su nombre visible, su comisión y el total de cada una, y el comunero elige una

#### Scenario: Pasarela de integración en producción

- **WHEN** en producción hay una pasarela activa de ambiente `integracion`
- **THEN** no se ofrece al comunero y el servidor rechaza con `422` un pago que la indique

#### Scenario: Monto bajo el mínimo del proveedor

- **WHEN** el total a cobrar es menor que el mínimo de Flow
- **THEN** Flow no se ofrece y la aplicación indica el monto mínimo que exige

### Requirement: Comisión a cargo del pagador

El total cobrado por la pasarela DEBE (SHALL) ser el monto adeudado más la comisión, calculado de modo que, descontada la comisión configurada de la pasarela, quede al menos el monto adeudado: `total = ⌈(monto + comisión_fija) / (1 − porcentaje/100)⌉`. La intención DEBE (SHALL) registrar el monto adeudado, la comisión y el total. Lo que se aplica al concepto pagado (por ejemplo, la compra de la rifa) DEBE (SHALL) ser el monto adeudado, no el total.

#### Scenario: Cálculo del recargo

- **WHEN** se paga una deuda de $6.000 con una pasarela de comisión 3,8 % y $0 fijo
- **THEN** el total a cobrar es $6.238 y la comisión registrada es $238

#### Scenario: Pasarela sin comisión configurada

- **WHEN** la pasarela tiene comisión 0 % y $0 fijo
- **THEN** el total a cobrar es igual al monto adeudado

### Requirement: Intención de pago

Iniciar un pago en línea DEBE (SHALL) crear una intención con identificador UUID, pasarela, usuario, concepto pagado, montos, estado `INICIADO` y vencimiento a los 15 minutos, y una orden del comercio única derivada del UUID (base32 sin relleno, 26 caracteres). Mientras una intención está `INICIADO` y vigente, lo que cubre NO DEBE (SHALL NOT) poder pagarse ni anularse por otro camino. La llamada al proveedor NO DEBE (SHALL NOT) hacerse dentro de una transacción de base de datos que mantenga bloqueos: la intención se guarda primero, luego se llama al proveedor y su respuesta se guarda en otra transacción. Si el proveedor falla al crear el cobro, la intención DEBE (SHALL) quedar `RECHAZADO` y liberar lo que cubría.

#### Scenario: Inicio exitoso

- **WHEN** el comunero inicia un pago con Flow
- **THEN** el sistema crea la intención `INICIADO`, obtiene del proveedor la dirección de pago y la aplicación redirige al comunero a ella

#### Scenario: El proveedor falla al crear el cobro

- **WHEN** el proveedor responde con error o no responde al crear el cobro
- **THEN** la intención queda `RECHAZADO`, lo que cubría queda liberado y la aplicación informa que no se pudo iniciar el pago

### Requirement: El backend decide el resultado consultando al proveedor

El resultado de un pago DEBE (SHALL) decidirlo siempre el backend con una consulta directa al proveedor. Los datos que llegan por el navegador del comunero o por la notificación del proveedor solo DEBEN (SHALL) servir para identificar la intención. El sistema DEBE (SHALL) buscar la intención localmente antes de llamar al proveedor: un identificador desconocido NO DEBE (SHALL NOT) provocar llamadas al proveedor. Solo un estado definitivamente pagado según el proveedor cuenta como aprobado; un estado desconocido DEBE (SHALL) tratarse como pendiente.

#### Scenario: Retorno con un token inventado

- **WHEN** llega al retorno o al webhook un token que no corresponde a ninguna intención
- **THEN** el sistema no llama al proveedor; el retorno redirige a una pantalla de pago no encontrado y el webhook responde `404`

#### Scenario: Retorno que dice pagado sin serlo

- **WHEN** el navegador vuelve al retorno pero el proveedor informa el pago como pendiente
- **THEN** la intención sigue `INICIADO` y la pantalla de resultado muestra "Pago en proceso"

#### Scenario: Khipu en verificación

- **WHEN** Khipu informa un pago en estado `verifying`
- **THEN** la intención sigue pendiente hasta que Khipu informe `done` con detalle `normal`

### Requirement: Confirmación idempotente

El retorno, el webhook, la conciliación y la consulta a pedido DEBEN (SHALL) confirmar por un mismo camino que bloquea la intención, de modo que una intención aprobada registre un solo pago aunque varios lleguen a la vez. Si el monto confirmado por el proveedor difiere del total de la intención, la intención DEBE (SHALL) quedar `EN_REVISION` sin aplicar el pago. Una intención `RECHAZADO` NO DEBE (SHALL NOT) aceptar un aprobado posterior, por lo que solo DEBE (SHALL) rechazarse con una respuesta definitiva del proveedor o tras anular con éxito la transacción en el proveedor.

#### Scenario: Retorno y webhook a la vez

- **WHEN** el retorno y el webhook de un mismo pago aprobado se procesan al mismo tiempo
- **THEN** la intención queda `CONFIRMADO` y el pago se aplica una sola vez

#### Scenario: Monto distinto

- **WHEN** el proveedor confirma un monto distinto del total de la intención
- **THEN** la intención queda `EN_REVISION` con el motivo, y el pago no se aplica

#### Scenario: Rechazo definitivo

- **WHEN** el proveedor informa el pago como rechazado o anulado
- **THEN** la intención queda `RECHAZADO` con el motivo y lo que cubría queda liberado

### Requirement: Pago aprobado después del vencimiento

Si una intención vence sin confirmación, DEBE (SHALL) quedar `EXPIRADO` y liberar lo que cubría. Si después el proveedor la informa aprobada, el pago NO DEBE (SHALL NOT) perderse: el sistema DEBE (SHALL) aplicarlo si lo que cubría sigue disponible, y si no, dejar la intención `EN_REVISION` con el motivo para que la administración lo resuelva.

#### Scenario: Aprobado tarde y aplicable

- **WHEN** una intención `EXPIRADO` resulta aprobada y lo que cubría sigue disponible
- **THEN** el pago se aplica y la intención queda `CONFIRMADO`

#### Scenario: Aprobado tarde y no aplicable

- **WHEN** una intención `EXPIRADO` resulta aprobada pero lo que cubría ya no está disponible
- **THEN** la intención queda `EN_REVISION` con el motivo y el `admin_condominio` la ve en su lista de pagos por revisar, donde la marca resuelta con una nota

### Requirement: Retorno y notificación públicos

El sistema DEBE (SHALL) exponer `/pagos/retorno/{proveedor}` (GET y POST) y `/pagos/webhook/{proveedor}` (POST) sin sesión, aceptando cuerpo de formulario y JSON, con límite de solicitudes por IP. El retorno DEBE (SHALL) responder con `303` a la pantalla de resultado del portal del condominio. El webhook DEBE (SHALL) responder `200` si la intención existe y `404` si no. Cuando el proveedor no envía datos en el retorno, la intención DEBE (SHALL) identificarse por su id en la URL, que solo vale para el proveedor de esa intención, y el retorno DEBE (SHALL) redirigir al portal de su condominio. Si el proveedor acepta la notificación como opcional (Khipu), DEBE (SHALL) enviársele solo cuando su URL es https.

#### Scenario: Retorno de Khipu

- **WHEN** el comunero vuelve desde Khipu a la URL de retorno con el id de su intención
- **THEN** el sistema consulta a Khipu con el identificador de pago guardado y redirige con `303` a la pantalla de resultado

#### Scenario: Cancelación en Khipu

- **WHEN** el comunero cancela en Khipu y vuelve por la URL de cancelación
- **THEN** el sistema intenta anular el cobro en Khipu; si lo logra, la intención queda `RECHAZADO`, y si no (porque ya se pagó), consulta el estado y lo aplica

#### Scenario: Desarrollo sin https

- **WHEN** la URL de notificación de un cobro de Khipu no es https
- **THEN** el cobro se crea sin URL de notificación y el pago se confirma por el retorno o la conciliación

#### Scenario: Id de intención con otro proveedor

- **WHEN** llega al retorno de Flow el id de una intención de Khipu
- **THEN** el sistema no la procesa ni llama a ningún proveedor, y redirige a la pantalla de pago no encontrado

### Requirement: Conciliación automática

El sistema DEBE (SHALL) revisar en segundo plano, cada 2 minutos, las intenciones `INICIADO` de más de 5 minutos y las `EXPIRADO` de las últimas 24 horas, consultando al proveedor por el mismo camino de confirmación. La revisión DEBE (SHALL) ejecutarse una sola vez a la vez aunque haya varios procesos del backend. Las intenciones `INICIADO` vencidas y sin pago DEBEN (SHALL) pasar a `EXPIRADO`.

#### Scenario: Aviso perdido

- **WHEN** el comunero pagó, cerró el navegador y el webhook nunca llegó
- **THEN** la conciliación consulta al proveedor, confirma la intención y aplica el pago

#### Scenario: Varios procesos del backend

- **WHEN** dos procesos del backend intentan conciliar al mismo tiempo
- **THEN** solo uno ejecuta la revisión en esa vuelta

### Requirement: Pantalla de resultado del pago

La aplicación DEBE (SHALL) mostrar el resultado de una intención: "Pago aprobado" (número de operación, monto y medio), "El pago no se realizó" (con el motivo), "En revisión", "Expiró" o "Pago en proceso". Mientras siga en proceso, DEBE (SHALL) actualizar el estado cada 3 segundos y pedir al backend una consulta al proveedor cada 15 segundos durante 5 minutos, con un botón "Consultar de nuevo". El backend DEBE (SHALL) limitar esa consulta a una vez cada 10 segundos por intención. Solo el usuario que inició la intención y la administración de su condominio DEBEN (SHALL) poder verla.

#### Scenario: Pago aprobado

- **WHEN** el comunero vuelve de la pasarela y el pago está confirmado
- **THEN** ve "Pago aprobado" con el número de operación, el total pagado y el medio de pago

#### Scenario: Pago que tarda

- **WHEN** el pago sigue pendiente en el proveedor
- **THEN** la pantalla muestra "Pago en proceso" y se actualiza sola hasta obtener un resultado o cumplir 5 minutos

#### Scenario: Intención de otro usuario

- **WHEN** un comunero abre el resultado de una intención que inició otro usuario
- **THEN** el sistema responde `404`

### Requirement: Datos del pagador y auditoría de pagos

El sistema NO DEBE (SHALL NOT) guardar del pagador su RUT, su nombre ni su cuenta bancaria. De la respuesta del proveedor solo DEBE (SHALL) conservar los datos del pago (estado, montos, número de operación, autorización, últimos dígitos, medio y motivo). La auditoría DEBE (SHALL) registrar la creación, edición, prueba, activación y eliminación de pasarelas y la confirmación, rechazo, vencimiento y revisión de intenciones.

#### Scenario: Respuesta del proveedor con datos personales

- **WHEN** el proveedor devuelve el nombre y el RUT del pagador junto al resultado
- **THEN** la intención guarda el resultado sin esos datos
