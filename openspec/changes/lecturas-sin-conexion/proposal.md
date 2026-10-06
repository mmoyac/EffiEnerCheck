# Proposal

## Why

El lector toma las lecturas recorriendo las parcelas, donde la señal es débil o no existe. Hoy cada lectura se guarda directamente en el servidor, así que sin conexión no se puede trabajar: el lector anota en papel y después transcribe. Eso duplica el trabajo y abre la puerta a errores.

## What Changes

- **La app de lecturas funciona sin conexión** (PWA). Solo la app de lecturas: el resto del portal (rifas, administración, liquidaciones) sigue requiriendo conexión.
- **"Preparar recorrido"**: con señal, el celular descarga el período abierto, las parcelas activas y la lectura vigente de cada una, y las guarda en **IndexedDB**.
- **Captura sin señal**: la lectura queda guardada en el celular con su fecha y hora real de toma. El avance ("31 de 53") se calcula con lo guardado en el celular.
- **Sincronización**:
  - se hace sola cuando vuelve la conexión, y también con un botón **"Sincronizar (N pendientes)"**;
  - cada lectura queda ✅ sincronizada o ⚠️ con problema, con su motivo;
  - una lectura **no se borra del celular hasta que el servidor la confirma**.
- **Sin pisar cambios ajenos**: si mientras el lector estaba sin señal alguien corrigió esa lectura en el servidor, o se cerraron las lecturas del período, la lectura del celular **no se aplica**. Queda ⚠️ en conflicto, para revisión.
- **Las lecturas pendientes no dependen de la sesión**: si al sincronizar la sesión venció, la app pide ingresar de nuevo y luego sincroniza, sin perder nada.
- **Endpoint nuevo** `POST /api/v1/lecturas/sincronizar`: recibe un lote de lecturas tomadas sin conexión y responde el resultado de cada una. Es idempotente: reenviar el mismo lote no duplica ni cambia nada.

Fuera de alcance:
- foto del medidor;
- venta de rifas sin conexión;
- edición sin conexión por el administrador;
- varios lectores sobre el mismo recorrido a la vez (se cubre con la detección de conflictos, pero sin herramientas de coordinación).

## Capabilities

### New Capabilities

_(ninguna)_

### Modified Capabilities

- `lecturas-remarcadores`: se agregan los requisitos de preparación del recorrido, captura y avance sin conexión, sincronización por lotes con detección de conflictos, e independencia de la sesión.

## Impact

- **Backend:** `endpoints/lecturas.py` (`POST /lecturas/sincronizar`) y `schemas/lectura.py`, con las mismas validaciones de hoy: tenant, período abierto y contador no regresivo.
- **Frontend:**
  - `pages/lector/LectorDashboard.tsx` y `CapturarLectura.tsx` leen y escriben en IndexedDB;
  - módulo nuevo `offline/lecturas.ts` (almacén y cola);
  - indicador de conexión y de pendientes;
  - la dependencia `idb` (envoltorio mínimo de IndexedDB).
- **PWA:** la vista del lector abre sin conexión. La app ya está en caché del service worker; la API sigue fuera de esa caché.
- **Sin cambios en la base de datos:** la detección de conflictos usa el valor y la `fecha_toma` que el celular descargó.
