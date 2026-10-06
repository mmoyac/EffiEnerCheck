# Tasks

## 1. Backend

- [x] 1.1 Schemas `SincronizarLecturasRequest`/`Response` (items con `lectura_id`, `lectura_actual`, `fecha_toma` y `base`; resultados con estado, motivo y lectura vigente), con un máximo de 200 items. Verificar que un lote de 201 items responde 422.
- [x] 1.2 `POST /lecturas/sincronizar` (`LectorRequired`): un *savepoint* por item; idempotencia; conflicto contra la base; rechazo por período cerrado, contador regresivo u otro tenant; auditoría `UPDATE_LECTURA` con `origen: sin_conexion`. Verificar con pruebas pytest de cada escenario de la spec.

## 2. Almacenamiento local

- [x] 2.1 Agregar `idb` y crear `offline/lecturas.ts` con:
  - `prepararRecorrido()`;
  - `leerRecorrido()`;
  - `guardarPendiente()`;
  - `pendientes()`;
  - `sincronizar()` (candado, manejo de 401 y de condominio);
  - `descartar()`.

  Verificar con `npm audit` sin vulnerabilidades altas y con `npm run build`.

## 3. Pantallas del lector

- [ ] 3.1 `LectorDashboard`: modo con y sin conexión, barra de estado, botones **Preparar recorrido** y **Sincronizar**, avance con los pendientes y lista **Revisar** para conflictos y rechazos. Verificar en el navegador con DevTools en modo *Offline*.
- [ ] 3.2 `CapturarLectura`: guarda en IndexedDB y luego sincroniza si hay red; mantiene las validaciones de hoy. Verificar en el navegador: con red se sincroniza al instante; sin red queda pendiente y se sincroniza al volver la red.
- [ ] 3.3 Sincronización automática con el evento `online` y al abrir la app; tras un 401, login y luego sincronización. Verificar en el navegador cortando la red, capturando, dejando vencer el token (o borrándolo) y recuperando la red.

## 4. Documentación

- [x] 4.1 `docs/` (guía corta para el lector: preparar recorrido, trabajar sin señal, sincronizar, instalar la app) y `CLAUDE.md` (patrón offline). Verificar con `openspec validate lecturas-sin-conexion --strict`.
