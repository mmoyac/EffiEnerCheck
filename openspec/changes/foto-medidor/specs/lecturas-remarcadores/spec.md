# Spec Delta

## ADDED Requirements

### Requirement: Foto del medidor en la captura

La pantalla de captura DEBE (SHALL) permitir al lector tomar una fotografía del medidor con la cámara del dispositivo, con o sin conexión. La foto DEBE (SHALL) ser opcional: su ausencia no impide guardar la lectura. Antes de guardarla, el dispositivo DEBE (SHALL) reducirla (lado mayor de 1600 px como máximo), comprimirla en JPEG y descartar su metadata EXIF, incluida la ubicación. Además DEBE (SHALL) agregar debajo de la imagen, sin tapar el medidor, una franja con el número de parcela y la fecha y hora en que se sacó la foto (la del archivo o, si no la trae, la de la captura).

#### Scenario: Lectura con foto

- **WHEN** el lector toma la foto del medidor, ingresa el valor y guarda
- **THEN** la lectura y su foto quedan guardadas en el dispositivo con la misma `fecha_toma`, y la pantalla muestra la vista previa de la foto

#### Scenario: Foto con fecha y hora

- **WHEN** el lector toma la foto del medidor de la parcela 23
- **THEN** la foto guardada lleva debajo una franja con «Parcela 23» y la fecha y hora en que se sacó, en hora de Chile

#### Scenario: Lectura sin foto

- **WHEN** el lector guarda una lectura sin tomar foto
- **THEN** la lectura se guarda igual y la parcela cuenta como leída, marcada «sin foto» en el avance

#### Scenario: Retomar la foto antes de sincronizar

- **WHEN** el lector vuelve a una parcela con foto pendiente y toma otra foto
- **THEN** la nueva foto reemplaza a la anterior en el dispositivo y solo se sube la última

#### Scenario: Foto que el dispositivo no puede procesar

- **WHEN** la foto tomada no se puede procesar en el dispositivo
- **THEN** la app avisa «No se pudo procesar la foto, intenta de nuevo» y permite guardar la lectura sin foto

#### Scenario: Foto para una lectura ya sincronizada

- **WHEN** el lector agrega una foto a una lectura que ya está sincronizada y no tenía foto
- **THEN** la foto queda pendiente en el dispositivo, amarrada a la `fecha_toma` vigente de esa lectura

### Requirement: Fotos pendientes en el dispositivo

Las fotos tomadas DEBEN (SHALL) guardarse en el dispositivo y sobrevivir a recargas de la app, a la falta de conexión y al vencimiento o cierre de la sesión. Una foto NO DEBE (SHALL NOT) borrarse del dispositivo hasta que el servidor confirme que la recibió. La vista del lector DEBE (SHALL) mostrar cuántas fotos faltan por subir y cuántas parcelas leídas no tienen foto. Al descartar una lectura pendiente, su foto DEBE (SHALL) descartarse con ella.

#### Scenario: Avance con fotos pendientes

- **WHEN** el lector tiene 5 fotos tomadas sin conexión
- **THEN** la vista del lector muestra «5 fotos por subir»

#### Scenario: Descartar una lectura en conflicto

- **WHEN** el lector descarta una lectura en conflicto que tenía foto
- **THEN** se borran del dispositivo la lectura pendiente y su foto

### Requirement: Sincronización de fotos

Al sincronizar, la aplicación DEBE (SHALL) enviar primero las lecturas pendientes y después, una por una, las fotos cuya lectura ya no esté pendiente en el dispositivo. La foto de una lectura pendiente, en conflicto o rechazada DEBE (SHALL) esperar en el dispositivo. El sistema DEBE (SHALL) exponer `PUT /api/v1/lecturas/{id}/foto` (multipart, para el rol lector y los administrativos), que recibe la foto y la `fecha_toma` de la toma a la que pertenece. El servidor DEBE (SHALL) aceptar la foto solo si esa `fecha_toma` coincide con la vigente de la lectura, y DEBE (SHALL) validar por su contenido que el archivo sea JPEG o WEBP de hasta 3 MB.

#### Scenario: Foto de una lectura aplicada

- **WHEN** vuelve la conexión, la lectura se aplica y luego se sube su foto
- **THEN** el servidor guarda la foto asociada a esa lectura, la registra en la auditoría como `SUBIR_FOTO_LECTURA` y el dispositivo la borra

#### Scenario: Foto de una lectura en conflicto

- **WHEN** la lectura de la foto queda en conflicto al sincronizar
- **THEN** la foto no se envía y queda en el dispositivo junto a la lectura, para revisión

#### Scenario: Foto de una toma que ya no está vigente

- **WHEN** se sube una foto cuya `fecha_toma` no coincide con la vigente de la lectura
- **THEN** el servidor responde 409 sin modificar nada, y el dispositivo muestra la foto como rechazada, con el motivo

#### Scenario: Reenvío de la misma foto

- **WHEN** el dispositivo reenvía una foto que el servidor ya guardó para esa misma toma (por ejemplo, porque se cortó la conexión antes de la respuesta)
- **THEN** el servidor responde éxito sin modificar nada ni duplicar la auditoría, y el dispositivo borra la foto

#### Scenario: Período cerrado

- **WHEN** se sube una foto para una lectura de un período con lecturas cerradas
- **THEN** el servidor responde 409 «Las lecturas del período ya están cerradas» y no guarda la foto

#### Scenario: Archivo que no es una imagen válida

- **WHEN** el archivo recibido no es JPEG ni WEBP por su contenido, o supera 3 MB
- **THEN** el servidor responde 422 y no guarda nada

#### Scenario: Sesión vencida con fotos pendientes

- **WHEN** al subir fotos la sesión está vencida
- **THEN** las fotos se conservan en el dispositivo y se suben después de que el lector vuelva a ingresar

### Requirement: Almacenamiento privado de la foto

El servidor DEBE (SHALL) guardar las fotos fuera de todo directorio servido como estático, en el almacenamiento privado, con un nombre que no revele la parcela ni el período. La respuesta de una lectura DEBE (SHALL) informar si tiene foto y de qué toma es (`tiene_foto`, `foto_fecha_toma`), y NO DEBE (SHALL NOT) exponer la ruta del archivo. Una corrección posterior del valor de la lectura NO DEBE (SHALL NOT) borrar la foto. Al reemplazar una foto o eliminar la boleta del período, los archivos que dejan de usarse DEBEN (SHALL) borrarse del disco después de confirmada la transacción.

#### Scenario: Corrección del valor con la foto como evidencia

- **WHEN** la administración corrige el valor de una lectura que tiene foto
- **THEN** la foto se conserva y la consola indica de qué toma es

#### Scenario: Eliminación del período

- **WHEN** se elimina una boleta cuyas lecturas tienen fotos
- **THEN** los archivos de esas fotos se borran del disco después de confirmada la eliminación

### Requirement: Acceso a la foto del medidor

El sistema DEBE (SHALL) exponer `GET /api/v1/lecturas/{id}/foto`, que entrega la foto sin caché compartida. La administración y el lector DEBEN (SHALL) poder ver las fotos de su condominio. El comunero DEBE (SHALL) poder ver solo las fotos de sus parcelas, y solo cuando el período fue publicado. La portería NO DEBE (SHALL NOT) acceder a las fotos.

#### Scenario: Administración revisa una lectura

- **WHEN** el administrador abre la foto de una lectura en la pestaña Lecturas del período
- **THEN** ve la foto junto al valor digitado

#### Scenario: Lector revisa la foto guardada, con señal

- **WHEN** el lector abre una parcela cuya lectura ya tiene foto en el servidor
- **THEN** con conexión puede ver esa foto a pedido, sin guardarla en el dispositivo; sin conexión, la aplicación le indica que necesita señal para verla

#### Scenario: Comunero ve la foto de su medidor

- **WHEN** un comunero pide la foto de la lectura de su parcela en un período publicado
- **THEN** recibe la foto

#### Scenario: Comunero antes de la publicación

- **WHEN** un comunero pide la foto de su parcela en un período aún no publicado
- **THEN** el servidor responde 404

#### Scenario: Comunero pide la foto de otra parcela

- **WHEN** un comunero pide la foto de una lectura de una parcela que no es suya
- **THEN** el servidor responde 404

#### Scenario: Lectura de otro condominio

- **WHEN** un usuario pide la foto de una lectura de otro condominio
- **THEN** el servidor responde 404

#### Scenario: Lectura sin foto

- **WHEN** se pide la foto de una lectura que no tiene
- **THEN** el servidor responde 404
