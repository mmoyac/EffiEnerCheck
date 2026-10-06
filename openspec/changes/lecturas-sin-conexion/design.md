# Design

## Context

- **Las lecturas ya existen antes de capturarlas:** al crear la boleta se crea una `LecturaParcela` por parcela activa (`fecha_toma` NULL). Capturar es actualizar `lectura_actual` y `fecha_toma` con `PATCH /lecturas/{id}`.
- **Validaciones vigentes:** tenant, período abierto (409) y contador no regresivo (422). La auditoría usa `UPDATE_LECTURA`.
- **La PWA ya existe:** el service worker cachea la app (precache, `navigateFallback` a `index.html`) y excluye `/api/`. La app abre sin red; hoy faltan los datos.
- **El JWT dura 60 minutos.** El lector puede pasar más tiempo sin señal.

## Goals / Non-Goals

**Goals**
- Ninguna lectura tomada en terreno se pierde: ni por falta de red, ni por la sesión, ni por recargar la app.
- Lo que se cambió en el servidor nunca se pisa en silencio.

**Non-Goals**
- Fotos.
- Funcionamiento sin conexión del resto del portal.
- Background Sync API: no existe en iOS Safari. Se sincroniza con la app abierta.

## Decisions

### 1. IndexedDB con `idb` y dos almacenes

- `recorrido`: un registro por dispositivo con el período (boleta), las parcelas y las lecturas descargadas como **base**, más la hora de descarga y el `condominio_id`.
- `pendientes`: clave `lectura_id`, con `{lectura_actual, fecha_toma, base: {lectura_actual, fecha_toma}, estado: 'pendiente'|'conflicto'|'rechazada', motivo}`. Volver a capturar la misma parcela reemplaza el registro.

`idb` (~1 KB, sin dependencias) evita el boilerplate de la API nativa de IndexedDB. Alternativa descartada: `localStorage`, que es síncrono, tiene un límite de ~5 MB y solo admite texto.

### 2. Conflictos por comparación con la base descargada

Para cada item, el servidor compara la lectura vigente (`lectura_actual` y `fecha_toma`) con la `base` que envía el dispositivo:

| Caso | Respuesta |
|---|---|
| El servidor ya tiene exactamente el valor y la `fecha_toma` enviados | `aplicada`, sin cambios (idempotencia por reintento) |
| Coincide con la base | Se aplica, como el `PATCH` actual, y se registra en la auditoría con `{"origen": "sin_conexion"}` |
| No coincide con la base ni con lo enviado | `conflicto`, con el valor vigente |
| Período cerrado | `rechazada` |
| Contador regresivo | `rechazada` |
| Otro tenant | `rechazada` |

No hace falta columna de versión: `fecha_toma` cambia en cada captura. Alternativa descartada: *last write wins*, que pisaría correcciones del administrador.

### 3. Un endpoint por lote, con transacción por item

`POST /lecturas/sincronizar` recibe `{items: [...]}`, como máximo 200. Cada item se procesa en su propio *savepoint* (`begin_nested`): un rechazo no revierte los demás. La respuesta es `{resultados: [{lectura_id, estado, motivo, lectura}]}`.

Alternativa descartada: N llamadas a `PATCH`. Son más viajes con mala señal y no tienen idempotencia ni detección de conflicto.

### 4. Sincronización

- Se dispara con el evento `online`, al abrir la app con pendientes y con el botón **Sincronizar**.
- Un solo envío a la vez (candado en memoria).
- Si la respuesta es 401, los pendientes se conservan. La app redirige al login con un aviso y, al volver, sincroniza.
- Antes de enviar, se verifica que el `condominio_id` del recorrido coincida con el del usuario con sesión.

### 5. Pantallas

- `LectorDashboard`:
  - si hay conexión, refresca el recorrido; si no, usa IndexedDB;
  - muestra una barra de estado: "Sin conexión · N pendientes" o "Sincronizado hh:mm";
  - botones **Preparar recorrido** y **Sincronizar**;
  - el avance cuenta como leídas las parcelas con `fecha_toma` en la base **o** con un pendiente.
- `CapturarLectura` guarda siempre primero en IndexedDB y luego intenta sincronizar si hay red. Un solo camino, con o sin señal: con señal la experiencia es la de hoy, y sin señal no se nota diferencia al capturar.
- Pendientes en conflicto o rechazados: lista "Revisar" con el motivo, y opción de descartar el valor local o volver a capturar.

### 6. Cuándo se descarga de nuevo el recorrido

Se descarga al abrir el dashboard con conexión **y sin pendientes**. Si hay pendientes, primero se sincroniza; descargar antes cambiaría la base y ocultaría conflictos.

## Risks / Trade-offs

- **[El usuario borra los datos del navegador con lecturas pendientes]** → Se pierden. Mitigación: el aviso "N lecturas sin sincronizar" visible en todo momento, y la sincronización automática apenas hay red.
- **[Dos lectores en la misma parcela]** → Gana el primero en sincronizar; el segundo queda en conflicto para revisión.
- **[Recarga automática por una versión nueva durante la captura]** → Solo ocurre con red y al haber un deploy. Lo ya guardado vive en IndexedDB; solo se perdería lo que se esté escribiendo en ese momento.
- **[iOS puede borrar el almacenamiento de sitios no usados en 7 días]** → Se mitiga sincronizando apenas hay red. Se documenta que conviene **instalar la app** en la pantalla de inicio, porque así iOS no la purga.
