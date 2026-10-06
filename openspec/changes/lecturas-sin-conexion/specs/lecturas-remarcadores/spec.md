# Spec Delta

## ADDED Requirements

### Requirement: Preparación del recorrido sin conexión

La aplicación del lector DEBE (SHALL) permitir, con conexión, descargar al dispositivo el período con lecturas abiertas, sus parcelas activas y la lectura vigente de cada parcela (lectura anterior, lectura actual y `fecha_toma`). Desde ese momento, la vista del lector DEBE (SHALL) poder abrirse y usarse sin conexión.

#### Scenario: Recorrido preparado

- **WHEN** el lector prepara el recorrido con conexión
- **THEN** el dispositivo guarda el período, las parcelas y sus lecturas, y la pantalla muestra la hora de la última descarga

#### Scenario: Abrir la app sin señal

- **WHEN** el lector abre la app de lecturas sin conexión y con un recorrido preparado
- **THEN** ve el listado de parcelas y su avance desde los datos del dispositivo

#### Scenario: Sin recorrido preparado y sin señal

- **WHEN** el lector abre la app sin conexión y nunca preparó un recorrido
- **THEN** la app indica que necesita conexión una vez para preparar el recorrido

### Requirement: Captura de lecturas sin conexión

Sin conexión, la pantalla de captura DEBE (SHALL) guardar la lectura en el dispositivo con la fecha y hora reales de la toma, aplicar las mismas validaciones visibles que con conexión (contador no regresivo) y contarla en el avance. Cada lectura guardada en el dispositivo DEBE (SHALL) mostrarse como **pendiente de sincronizar** hasta que el servidor la confirme.

#### Scenario: Lectura tomada sin señal

- **WHEN** el lector ingresa la lectura de una parcela sin conexión
- **THEN** la lectura queda guardada en el dispositivo, la parcela cuenta como leída en el avance y aparece como pendiente de sincronizar

#### Scenario: Corrección antes de sincronizar

- **WHEN** el lector vuelve a una parcela con una lectura pendiente y la corrige
- **THEN** se reemplaza la lectura pendiente del dispositivo y se sincroniza solo la última

### Requirement: Sincronización por lotes

El sistema DEBE (SHALL) exponer `POST /api/v1/lecturas/sincronizar`, para el rol lector y los administrativos. Recibe un lote de lecturas tomadas en el dispositivo, cada una con:
- el identificador de la lectura;
- el valor tomado y su `fecha_toma`;
- el valor y la `fecha_toma` que el dispositivo descargó como base.

Responde, por cada lectura, si fue **aplicada**, si quedó en **conflicto** o si fue **rechazada**, con el motivo. La aplicación DEBE (SHALL) sincronizar automáticamente al recuperar la conexión y también a pedido. Una lectura NO DEBE (SHALL NOT) borrarse del dispositivo hasta que el servidor la informe como aplicada.

#### Scenario: Sincronización exitosa

- **WHEN** vuelve la conexión y hay lecturas pendientes cuya base coincide con el servidor
- **THEN** el servidor las aplica como capturas del lector que sincroniza (con su `fecha_toma` original), las registra en la auditoría y el dispositivo las marca como sincronizadas

#### Scenario: Lectura corregida en el servidor mientras tanto

- **WHEN** la lectura del servidor ya no coincide con la base que descargó el dispositivo
- **THEN** el servidor no la modifica y responde `conflicto` con el valor vigente, y el dispositivo la muestra con advertencia para revisión

#### Scenario: Período cerrado mientras tanto

- **WHEN** las lecturas del período se cerraron antes de sincronizar
- **THEN** el servidor responde `rechazada` con el motivo "Las lecturas del período ya están cerradas" y no modifica nada

#### Scenario: Contador regresivo

- **WHEN** el valor tomado es menor que la lectura anterior
- **THEN** el servidor responde `rechazada` con el motivo y no modifica la lectura

#### Scenario: Reenvío del mismo lote

- **WHEN** el dispositivo reenvía una lectura que el servidor ya aplicó (por ejemplo, porque se cortó la conexión antes de recibir la respuesta)
- **THEN** el servidor responde `aplicada` sin modificar nada ni duplicar la auditoría

#### Scenario: Lectura de otro condominio

- **WHEN** el lote incluye una lectura de un condominio distinto al del usuario
- **THEN** esa lectura se responde `rechazada` y no se modifica

### Requirement: Lecturas pendientes independientes de la sesión

Las lecturas pendientes del dispositivo NO DEBEN (SHALL NOT) perderse cuando vence la sesión ni al cerrarla. Si al sincronizar la sesión venció, la aplicación DEBE (SHALL) pedir ingresar de nuevo y sincronizar a continuación. Las lecturas pendientes solo se envían con la sesión de un usuario del mismo condominio.

#### Scenario: Sesión vencida con lecturas pendientes

- **WHEN** el lector vuelve a tener señal con la sesión vencida y lecturas pendientes
- **THEN** la app le pide ingresar, conserva las pendientes y las sincroniza apenas ingresa
