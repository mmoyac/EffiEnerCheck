# Proposal

## Why

Hoy la lectura de un remarcador es solo un número que digita el lector. Si un comunero reclama por su consumo, o si el lector se equivoca en un dígito, no hay forma de verificar qué marcaba realmente el medidor: hay que volver a la parcela, y para entonces el contador ya avanzó. Una fotografía del medidor, tomada en el mismo momento que la lectura, resuelve los reclamos con evidencia y permite que la administración corrija errores de digitación sin salir a terreno.

El lector trabaja recorriendo las parcelas, casi siempre **sin señal**. Por eso la foto tiene que funcionar igual que la lectura: se toma y se guarda en el celular, y se sube cuando vuelve la conexión. Este cambio se apoya en el mecanismo del cambio `lecturas-sin-conexion`, que dejó las fotos fuera de su alcance.

## What Changes

- **Foto del medidor al capturar la lectura.** En la pantalla de captura, el lector puede tomar una foto del medidor con la cámara trasera del celular. La foto es **opcional**: no bloquea la captura si la cámara falla o el medidor no se ve bien.
- **Funciona sin conexión.** La foto se reduce y comprime en el celular (JPEG, lado mayor de 1600 px) y se guarda en IndexedDB junto a la lectura pendiente. Se pierde la metadata EXIF, incluida la ubicación GPS.
- **Sincronización en dos pasos.**
  1. Primero se sincroniza el lote de lecturas, igual que hoy.
  2. Luego se sube, una por una, la foto de cada lectura que el servidor dio por **aplicada**.

  Una foto **no se borra del celular hasta que el servidor confirma que la recibió**. Si la lectura quedó en conflicto o fue rechazada, la foto queda en el celular junto a ella, para revisión.
- **La foto queda amarrada a la toma.** El servidor solo acepta la foto si corresponde a la toma vigente de esa lectura (misma `fecha_toma`). Así, una foto de una toma que perdió un conflicto nunca queda pegada a otra lectura.
- **Endpoints nuevos:**
  - `PUT /api/v1/lecturas/{id}/foto` (multipart): sube o reemplaza la foto. Es idempotente: reenviar la misma foto no cambia nada.
  - `GET /api/v1/lecturas/{id}/foto`: entrega la foto con control de acceso. Nunca se sirve como archivo estático.
- **Quién ve la foto:**
  - la administración y el lector del condominio;
  - el **comunero**, solo la de sus parcelas y solo cuando el período ya fue publicado.
- **Consola administrativa:** en la pestaña *Lecturas* del período, un ícono de cámara abre la foto junto al valor digitado. Además, el resumen indica cuántas lecturas no tienen foto.
- **Avance del lector:** el dashboard muestra las parcelas leídas sin foto y las fotos pendientes de subir.

Fuera de alcance:
- foto obligatoria (queda como opción futura por condominio; ver design);
- lectura automática del número desde la foto (OCR del medidor);
- varias fotos por lectura;
- fotos de períodos anteriores en la pantalla de captura.

## Capabilities

### New Capabilities

_(ninguna)_

### Modified Capabilities

- `lecturas-remarcadores`: se agregan los requisitos de captura de la foto del medidor (con y sin conexión), su almacenamiento en el dispositivo, su sincronización amarrada a la toma, el almacenamiento privado en el servidor y el acceso por rol.

## Impact

- **Base de datos:** migración Alembic que agrega a `lecturas_parcelas` las columnas `foto_archivo`, `foto_sha256`, `foto_fecha_toma` y `foto_subida_en`, todas NULL. `schema.dbml`.
- **Backend:**
  - `endpoints/lecturas.py`: `PUT` y `GET /lecturas/{id}/foto`;
  - `schemas/lectura.py`: `tiene_foto` y `foto_fecha_toma` en la respuesta, nunca la ruta del archivo;
  - borrado de los archivos al eliminar una boleta (`boletas.py`), después del commit;
  - auditoría `SUBIR_FOTO_LECTURA`.
- **Almacenamiento:** `/app/privado/lecturas/`, en el volumen `privado`, que ya existe y ya se respalda (`enercheck-ci` empaqueta `uploads` y `privado`). Ningún cambio en Docker ni en Dokploy.
- **Frontend:**
  - `offline/lecturas.ts`: almacén nuevo `fotos` (IndexedDB versión 2) y subida de fotos en `sincronizar()`;
  - `pages/lector/CapturarLectura.tsx`: botón de cámara, vista previa, retomar y quitar;
  - `pages/lector/LectorDashboard.tsx`: contadores de fotos;
  - `pages/admin/BoletaDetalle.tsx`: visor de la foto en la pestaña *Lecturas*;
  - `types/index.ts` y `api/lecturas.ts`.
- **nginx:** el límite de tamaño del cuerpo debe aceptar la subida (≤ 3 MB). Hoy ya admite los vouchers de 10 MB.
- **Datos personales:** la foto muestra solo el medidor, pero sigue siendo de una parcela identificada. Va al volumen privado, nunca al repo, a los logs ni a `/uploads`. `copiar_desde_desarrollo.py` no la copia.
- **Docs:** `docs/lecturas-sin-conexion.md` (cómo tomar la foto), `docs/flujo-periodo.md`, `CLAUDE.md`.
- **Capacitación:** la sección de Energía del centro de capacitación está como «próximamente». Cuando se complete, deberá incluir la foto.
