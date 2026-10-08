# Proposal

## Why

El lector camina una ruta fija por el condominio (en Santa Laura: 6 → 5 → 4 → 3 → 13 A → 13 B → 23 → 22…), pero la app le muestra las parcelas en orden numérico. En cada parada tiene que buscar en la lista cuál sigue, con el celular en una mano y la linterna en la otra. Si la app sigue su ruta, la próxima parcela pendiente aparece siempre arriba.

## What Changes

- **Orden del recorrido por parcela** (`parcelas.orden_recorrido`, opcional). Lo define la administración **una vez**, en *Parcelas* → **Orden del recorrido**: ordena la lista arrastrando o con flechas, guarda, y puede **quitar el recorrido** para volver al orden numérico.
- **La app del lector usa el recorrido si existe.** Las parcelas con orden van primero, según ese orden; las que no lo tienen, por ejemplo una parcela agregada después, van al final en orden numérico. **Sin recorrido definido, la app se ve exactamente como hoy.** Funciona sin conexión, porque el orden viaja en el recorrido descargado.
- El resto del sistema (consola, liquidaciones, Excel de la lectura inicial, portal del comunero) sigue en orden numérico.
- **Endpoint nuevo:** `PUT /api/v1/parcelas/orden-recorrido` (administración), con la lista ordenada de parcelas. Queda en la auditoría como `UPDATE_ORDEN_RECORRIDO`.

## Capabilities

### New Capabilities

_(ninguna)_

### Modified Capabilities

- `gestion-parcelas`: orden del recorrido, cómo se define, cómo se quita y su auditoría.
- `lecturas-remarcadores`: la vista del lector sigue el orden del recorrido cuando existe.

## Impact

- **Base de datos:** migración con `parcelas.orden_recorrido INTEGER NULL`. `schema.dbml`.
- **Backend:**
  - `endpoints/parcelas.py`: `PUT /orden-recorrido`;
  - `schemas/parcela.py`: `orden_recorrido` en la respuesta.
- **Frontend:**
  - `pages/admin/Parcelas.tsx` y el modal nuevo **Orden del recorrido**: arrastrar en escritorio y flechas en celular;
  - `utils/recorrido.ts`: el criterio de orden, uno solo;
  - `offline/lecturas.ts` y `LectorDashboard.tsx`;
  - `types` y `api/parcelas.ts`.
- **Docs:** `docs/lecturas-sin-conexion.md` (el lector sigue el recorrido) y `CLAUDE.md`.
