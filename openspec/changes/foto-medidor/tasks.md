# Tasks

## 1. Base de datos

- [x] 1.1 Migración Alembic: `foto_archivo`, `foto_sha256`, `foto_fecha_toma` y `foto_subida_en` en `lecturas_parcelas` (todas NULL), con su `downgrade`. Actualizar el modelo `LecturaParcela` y `schema.dbml`. Verificar con `alembic upgrade head` y `alembic downgrade -1`.

## 2. Backend

- [x] 2.1 `schemas/lectura.py`: `tiene_foto` y `foto_fecha_toma` en `LecturaParcelaResponse` (sin `foto_archivo`). Verificar que `GET /lecturas` no expone la ruta.
- [x] 2.2 `PUT /lecturas/{id}/foto` (`LectorRequired`, multipart con `foto` y `fecha_toma`; el `sha256` lo calcula el servidor):
  - tenant;
  - período abierto (409);
  - `foto_desfasada` (409);
  - idempotencia por `sha256` y toma;
  - validación por bytes JPEG/WEBP y ≤ 3 MB (422);
  - archivo en `/app/privado/lecturas/<uuid>`;
  - auditoría `SUBIR_FOTO_LECTURA`;
  - borrado del archivo anterior después del commit.

  Verificar con pytest cada escenario de la spec.
- [x] 2.3 `GET /lecturas/{id}/foto`:
  - staff del tenant;
  - comunero solo de sus parcelas y con período publicado;
  - portería nunca;
  - 404 sin foto;
  - `Cache-Control: private, no-store`.

  Verificar con pytest.
- [x] 2.4 `DELETE /boletas/{id}`: borrar los archivos de las fotos después del commit. Verificar con pytest que el archivo desaparece del disco y que nada se borra si la eliminación falla.
- [x] 2.5 `PATCH /lecturas/{id}` y `POST /lecturas/sincronizar` no tocan la foto. Verificar con pytest: tras corregir el valor, `tiene_foto` sigue en verdadero y `foto_fecha_toma` mantiene su valor.
- [x] 2.6 Confirmar que `copiar_desde_desarrollo.py` no copia `foto_*` ni archivos, y que el límite de cuerpo de nginx (`frontend/nginx*.conf`) admite 3 MB en `/api/v1/lecturas/`.

## 3. Almacenamiento local

- [ ] 3.1 `offline/lecturas.ts`:
  - IndexedDB versión 2 con el almacén `fotos`;
  - `procesarFoto(archivo)` (bitmap con orientación, canvas de 1600 px, JPEG 0,7);
  - `guardarPendiente(lectura, valor, foto)` y `guardarFotoDeLectura()`;
  - `listarFotos()`, `leerFoto()` y `descartarFoto()`;
  - `descartar()` también borra la foto;
  - `navigator.storage.persist()` en `prepararRecorrido()`.

  Verificar que una base versión 1 con pendientes migra sin perderlos.
- [x] 3.2 `sincronizar()`: tras el lote de lecturas, subir una a una las fotos cuya lectura no está en `pendientes`, con manejo de 200, 409, 401 y error de red, bajo el mismo candado. Verificar con `npm run build` y `npm audit --omit=dev --audit-level=high`.

## 4. Pantallas

- [ ] 4.1 `CapturarLectura`:
  - botón «Tomar foto del medidor» (`capture="environment"`);
  - vista previa;
  - retomar y quitar;
  - aviso si no se pudo procesar.

  Guarda la foto con la misma `fecha_toma` que la lectura, y permite agregar una foto a una lectura ya sincronizada. Verificar en un celular real (Android e iPhone), con y sin señal.
- [ ] 4.2 `LectorDashboard`: «N fotos por subir», parcelas leídas «sin foto» y fotos rechazadas en la lista **Revisar**. Verificar en el navegador con DevTools en modo *Offline*.
- [ ] 4.3 `BoletaDetalle`, pestaña *Lecturas*:
  - ícono de cámara en las lecturas con foto;
  - visor descargado con el token;
  - aviso «Foto de la toma del …» cuando `foto_fecha_toma ≠ fecha_toma`;
  - al inicio de la pestaña, el conteo de lecturas tomadas sin foto.

  Verificar en el navegador.
- [ ] 4.4 Portal del comunero (`MiLiquidacion`): enlace «Ver foto del medidor» en el detalle de un período publicado, cuando la lectura tiene foto. Verificar en el navegador con el usuario comunero del seed.

## 5. Documentación

- [x] 5.1 Documentación:
  - `docs/lecturas-sin-conexion.md`: tomar la foto y qué pasa sin señal;
  - `docs/flujo-periodo.md`;
  - `CLAUDE.md`: almacén `fotos` y `/app/privado/lecturas`, nunca en `/uploads`.

  Verificar con `openspec validate foto-medidor --strict`.
