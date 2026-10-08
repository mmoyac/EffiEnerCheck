# Toma de lecturas sin señal

La app de lecturas funciona **sin conexión**: el lector recorre las parcelas sin señal y sincroniza al volver. El resto del portal (rifas, administración, liquidaciones) sigue requiriendo conexión.

## Para el lector

1. **Instala la app** en el celular, una vez: en Chrome, menú ⋮ → *Agregar a pantalla de inicio*; en iPhone (Safari), botón Compartir → *Agregar a inicio*. En iPhone es importante: si no se instala, Safari puede borrar los datos de sitios que no se usan en 7 días.
2. **Antes de salir, con señal:** abre la app. Si es la primera vez, presiona **Preparar recorrido**. Arriba verás "Recorrido de las hh:mm".
3. **En terreno:** toma las lecturas como siempre. Sin señal aparece la barra amarilla *"Sin conexión: las lecturas se guardan en el celular · N sin sincronizar"*, y cada parcela muestra "en el celular, sin sincronizar".
4. **Foto del medidor (opcional, recomendada):** en la pantalla de la parcela, presiona **Tomar foto del medidor** antes de confirmar. Se abre la cámara del celular; procura que se lean bien los dígitos. Funciona sin señal: la foto queda en el celular junto a la lectura. Puedes **Retomar** o **Quitar** la foto antes de confirmar. Si una parcela ya leída no tiene foto, entra de nuevo, toma la foto y confirma sin cambiar el número: solo se agrega la foto.
5. **Al volver la señal:** se sincroniza sola. También puedes presionar **Sincronizar**. Primero se envían las lecturas y después las fotos, una por una; la barra muestra "N fotos por subir".
6. Si aparece la pestaña **Revisar** ⚠️, alguna lectura o foto no se aplicó. El motivo aparece en la parcela:
   - *"cambió en el servidor después de preparar el recorrido"*: alguien la registró o corrigió mientras tanto. Entra a la parcela y vuelve a capturarla si corresponde, o presiona **Descartar** para quedarte con la del servidor (se descarta también su foto).
   - *"las lecturas del período ya están cerradas"*: avisa a la administración.
   - *"La foto no se subió: … ya no está vigente"*: la lectura cambió en el servidor y la foto era de la toma anterior. Vuelve a tomar la foto o presiona **Descartar foto**.

**Lectura inicial:** antes de la primera boleta, la administración abre la *lectura inicial*. En la app aparece como «Lectura inicial · mes» y cada parcela pide solo el valor del medidor (sin lectura anterior ni consumo). Se toma igual que una lectura mensual, con o sin señal y con foto. Tómala **el mismo día en que la compañía lee el medidor general**: es el punto de partida del primer consumo de cada comunero.

**Orden del recorrido:** si la administración definió el recorrido (*Parcelas* → **Orden del recorrido**, arrastrando o con flechas), la app muestra las parcelas en ese orden: la próxima pendiente siempre arriba. Las parcelas sin ubicar van al final en orden numérico, y sin recorrido definido se usa el orden numérico de siempre. Tras cambiar el recorrido, el lector debe abrir la app con señal (o presionar **Preparar recorrido**) para recibir el orden nuevo.

Las lecturas y las fotos **no se pierden** si se cierra la app, se apaga el celular o vence la sesión. Si la sesión venció, la app pide la clave y sincroniza después. **No borres los datos del navegador** mientras haya lecturas o fotos sin sincronizar.

## Cómo funciona (técnico)

- **IndexedDB** (`efficomunidad-lecturas`), en `frontend/src/offline/lecturas.ts`:
  - `recorrido`: período, parcelas y lecturas como **base**;
  - `pendientes`: lecturas tomadas que el servidor aún no confirma;
  - `fotos` (versión 2 de la base): foto del medidor por `lectura_id`, amarrada a la `fecha_toma` de la toma que documenta. Se reduce en el celular (lado mayor 1600 px, JPEG 0,7, sin EXIF ni GPS) con `procesarFoto()`.
- **`POST /api/v1/lecturas/sincronizar`** (rol lector y administrativos): lote de hasta 200 lecturas `{lectura_id, lectura_actual, fecha_toma, base}`. Cada una responde `aplicada`, `conflicto` (la del servidor ya no coincide con la base; no se pisa) o `rechazada` (período cerrado, contador regresivo u otro condominio). Es idempotente: reenviar lo ya aplicado responde `aplicada` sin auditar de nuevo.
- **Fotos del medidor** (cambio `foto-medidor`): `sincronizar()` sube después del lote, una por petición, las fotos cuya lectura ya no está en `pendientes`, con `PUT /api/v1/lecturas/{id}/foto` (multipart `foto` + `fecha_toma`). El servidor solo la acepta si `fecha_toma` es la vigente de la lectura (si no, 409 y la foto queda *rechazada*); reenviar la misma foto responde 200 sin auditar de nuevo. Se guardan en `/app/privado/lecturas` (nunca en `/uploads`) y se ven con `GET /api/v1/lecturas/{id}/foto`: staff y lector del condominio; el comunero solo las de sus parcelas y con el período publicado; la portería nunca. Una corrección posterior del valor no borra la foto (`foto_fecha_toma` indica de qué toma es).
- **Sesión sin señal:** `AuthContext` guarda la última sesión (`localStorage.sesion`). Si `/auth/me` falla **por red**, la usa; si el servidor responde 401, la sesión se cierra como siempre.
- **Probar en desarrollo:** Chrome DevTools → *Application → Service Workers* (debe estar activo) y *Network → Offline*.
