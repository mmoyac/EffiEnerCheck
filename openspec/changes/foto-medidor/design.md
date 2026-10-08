# Design

## Context

- **Lecturas sin conexión ya existe** (cambio `lecturas-sin-conexion`). `offline/lecturas.ts` tiene dos almacenes en IndexedDB:
  - `recorrido`: la base descargada;
  - `pendientes`: lecturas tomadas en el celular, con clave `lectura_id`.

  `sincronizar()` envía el lote a `POST /lecturas/sincronizar`, que responde `aplicada`, `conflicto` o `rechazada` por lectura. Una pendiente no se borra hasta que el servidor responde `aplicada`.
- **Cada toma tiene una `fecha_toma` única.** Es lo que usa el servidor para detectar conflictos, y sirve también para amarrar la foto a la toma.
- **Ya existe un patrón de archivos privados:** los vouchers de rifas viven en `/app/privado/vouchers` (volumen `privado`, respaldado), se validan por bytes y solo se entregan por un endpoint con control de acceso. `/app/uploads` se sirve como estático público y **no** sirve para esto.
- **El lector usa celulares de gama media**, con señal débil o nula, a veces iPhone con la app instalada en la pantalla de inicio.

## Goals / Non-Goals

**Goals**
- Ninguna foto tomada en terreno se pierde por falta de red, por la sesión o por recargar la app. Es la misma garantía que ya tienen las lecturas.
- Una foto siempre corresponde a la toma que documenta. Nunca queda una foto de un valor con el número de otro.
- La foto no estorba la captura: es opcional y no frena el recorrido.

**Non-Goals**
- Foto obligatoria.
- OCR del medidor.
- Varias fotos por lectura.
- Background Sync API (no existe en iOS Safari; igual que en `lecturas-sin-conexion`).

## Decisions

### 1. Cámara con `<input type="file" accept="image/*" capture="environment">`

Abre la cámara nativa del celular, funciona sin conexión, no pide permisos de la página y se comporta igual en Android e iOS.

*Alternativa descartada:* `getUserMedia` con un visor propio. Exige permisos de cámara, manejar orientación y enfoque, y falla de formas más variadas en iOS. No aporta nada a una foto fija.

### 2. Reducción y compresión en el celular, antes de guardar

`createImageBitmap(archivo, { imageOrientation: 'from-image' })` y luego un `canvas` con el lado mayor en 1600 px y `toBlob('image/jpeg', 0.7)`. Una foto queda en ~200–400 KB, y un recorrido de 60 parcelas en ~25 MB.

- Reencodear en el canvas **descarta el EXIF**, incluida la ubicación GPS. Es lo correcto: la ubicación no aporta y es un dato personal.
- 1600 px alcanza para leer los dígitos de un medidor con holgura.
- Si `createImageBitmap` falla (formato no soportado, como HEIC en algunos navegadores), se muestra «No se pudo procesar la foto, intenta de nuevo» y la lectura se puede guardar igual.

### 3. Almacén `fotos` separado en IndexedDB (versión 2 de la base)

`fotos` tiene clave `lectura_id` y guarda `{lectura_id, fecha_toma, blob, sha256, estado: 'pendiente'|'rechazada', motivo?}`.

- **Va aparte de `pendientes`** para que listar pendientes, calcular el avance y armar el lote JSON no carguen blobs.
- **`fecha_toma` es la de la toma a la que pertenece la foto.** Al guardar una lectura con foto, ambas reciben la misma `fecha_toma`.
- **Retomar la foto** antes de sincronizar reemplaza el registro.
- **Una foto sin lectura nueva:** el lector puede agregar una foto a una lectura ya sincronizada que no la tenía. En ese caso se amarra a la `fecha_toma` vigente de esa lectura en el recorrido.
- **`descartar()` de una pendiente borra también su foto.** Si se descarta el valor local, su evidencia también deja de servir.
- **La migración de versión 1 a 2 solo crea el almacén.** Los pendientes existentes no se tocan.
- **Espacio:** se pide `navigator.storage.persist()` al preparar el recorrido. En Android reduce el riesgo de que el navegador purgue los datos; en iOS sigue valiendo la recomendación de instalar la app.

### 4. Sincronización: primero lecturas, después fotos, una a una

`sincronizar()` mantiene el lote de lecturas tal como está. Al terminar, recorre `fotos` con estado `pendiente` y sube cada una cuya lectura **ya no está pendiente en el celular**:
- la lectura se aplicó en esta pasada o en una anterior;
- o la foto era de una lectura ya sincronizada.

Una foto cuya lectura sigue en `pendientes` (sin enviar, en conflicto o rechazada) **espera**.

- **Una foto por petición**, con `PUT /lecturas/{id}/foto` multipart: `foto` (archivo) + `fecha_toma`. Con mala señal, una petición de 300 KB que falla se reintenta sola sin arrastrar a las demás. Un lote multipart de 25 MB fallaría entero.
- **Con 200**, la foto se borra del celular.
- **Con 409 `foto_desfasada`**, la foto queda `rechazada` con el motivo, para revisión: el servidor tiene otra toma vigente.
- **Con 401**, se aplica el mismo tratamiento de sesión vencida que hoy. La foto se conserva.
- **Con un error de red**, la foto queda `pendiente` y se reintenta en la próxima sincronización.
- **El mismo candado en memoria** cubre lecturas y fotos: una sola sincronización a la vez.

*Alternativa descartada:* meter la foto en base64 dentro del lote JSON. Infla un 33 %, hace el lote enorme y mezcla el destino de la foto con el de la lectura.

### 5. El servidor amarra la foto a la toma vigente

`PUT /lecturas/{id}/foto` (`LectorRequired`):

| Caso | Respuesta |
|---|---|
| Lectura de otro tenant | 403 |
| Período con lecturas cerradas | 409 «Las lecturas del período ya están cerradas» |
| `fecha_toma` enviada ≠ `fecha_toma` vigente de la lectura | 409 `foto_desfasada` |
| La lectura ya tiene una foto con el mismo `sha256` y la misma `foto_fecha_toma` | 200 sin cambios ni auditoría (idempotencia por reintento) |
| Archivo que no es JPEG/WEBP por bytes, o > 3 MB | 422 |
| Caso normal | Guarda el archivo, actualiza `foto_archivo`, `foto_sha256`, `foto_fecha_toma = fecha_toma` y `foto_subida_en`, audita `SUBIR_FOTO_LECTURA` y, **después del commit**, borra el archivo anterior si lo había |

- **Archivo:** `/app/privado/lecturas/<uuid>.jpg|webp`. El nombre no deja adivinar la parcela ni el período.
- **Auditoría:** `{lectura_id, parcela_id, sha256, bytes, reemplaza: bool}`. Nunca el contenido.
- **El `sha256` lo calcula el servidor** sobre los bytes recibidos. El cliente no lo envía: `crypto.subtle` no existe fuera de HTTPS, y la idempotencia no lo necesita.

### 6. Una corrección posterior no borra la foto

Si la administración corrige el valor con `PATCH` (por ejemplo, porque la foto muestra un error de digitación), la `fecha_toma` de la lectura puede cambiar, pero la foto **se conserva**: es justamente la evidencia de la corrección. Como `foto_fecha_toma` queda distinta de `fecha_toma`, la consola muestra «Foto de la toma del dd/mm hh:mm».

Se descartó borrar la foto al cambiar la toma: destruiría la evidencia en el caso que más la necesita.

### 7. Acceso a la foto

`GET /lecturas/{id}/foto` entrega el archivo con `Cache-Control: private, no-store`.

| Rol | Acceso |
|---|---|
| `super_admin`, `admin_condominio`, `lector` | Todas las del condominio (tenant) |
| `comunero` | Solo de sus parcelas, y solo si la boleta tiene `boleta_visible_usuarios = true` |
| `porteria` | Nunca |

Para el comunero, la regla es la misma que para ver su liquidación: antes de publicar, el período todavía se puede corregir.

- **La respuesta de la lectura** expone `tiene_foto` y `foto_fecha_toma`, nunca `foto_archivo`.
- **El frontend descarga la foto con el token**, como el voucher (`rifasApi`), y la muestra con un `URL.createObjectURL`.

### 8. Borrado

Al eliminar una boleta, se recogen los `foto_archivo` de sus lecturas antes del `DELETE` y se borran del disco **después** del commit. Es el mismo patrón que `ELIMINAR_RIFA`: si el commit falla, no se pierde nada.

## Risks / Trade-offs

- **[Almacenamiento del celular]** Un recorrido completo con fotos ocupa ~25 MB. Es bastante menos que la cuota habitual (cientos de MB en Android, ≥ 1 GB en iOS instalado). Mitigación: las fotos se borran del celular apenas el servidor confirma.
- **[Subida lenta con mala señal]** Mitigación: una foto por petición, reintentos naturales en cada sincronización y un contador visible «N fotos por subir».
- **[El usuario borra los datos del navegador con fotos pendientes]** Se pierden, igual que las lecturas. Lo mitiga el mismo aviso visible y la sincronización automática.
- **[Disco del servidor]** 60 fotos × 12 meses × ~300 KB ≈ 220 MB/año por condominio. Es aceptable. Una política de retención queda para un cambio futuro si hace falta.
- **[HEIC o formatos raros]** El canvas siempre entrega JPEG. Si el navegador no puede decodificar la foto, se avisa y la lectura sigue sin foto.

## Open Questions

- **¿Foto obligatoria?** Se propone opcional. Si la comunidad la quiere obligatoria, conviene un parámetro por condominio (`foto_lectura_obligatoria`) en un cambio aparte. Así no se traba el recorrido cuando la cámara falla o el medidor está en un nicho oscuro.
