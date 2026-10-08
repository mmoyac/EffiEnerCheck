# Tasks

## 1. Base de datos y backend

- [x] 1.1 Migración `parcelas.orden_recorrido INTEGER NULL` (con reversa), modelo, `schema.dbml` y `orden_recorrido` en `ParcelaResponse`. Verificar con `alembic upgrade`, `downgrade -1` y de nuevo `upgrade`.
- [x] 1.2 `PUT /parcelas/orden-recorrido` (`AdminRequired`; `condominio_id` para el super admin):
  - posiciones 1..n;
  - las no listadas sin posición;
  - lista vacía quita el recorrido;
  - 422 si hay repetidas;
  - 403 si hay de otro condominio;
  - auditoría `UPDATE_ORDEN_RECORRIDO`.

  Verificar con pytest cada escenario del delta de `gestion-parcelas`.

## 2. Frontend

- [ ] 2.1 `utils/recorrido.ts` (`ordenarRecorrido`: con posición primero, el resto en orden natural), tipos y `parcelasApi.guardarOrdenRecorrido`. La app del lector ordena el recorrido descargado con ese criterio (`LectorDashboard`). Verificar con `npm run build` y en el navegador, con y sin recorrido.
- [ ] 2.2 `Parcelas.tsx`: botón **Orden del recorrido** y un modal con las parcelas activas en el orden actual (arrastrar y flechas ↑ ↓), **Guardar recorrido** y **Quitar recorrido**. Verificar en el navegador que el lector ve el nuevo orden tras **Preparar recorrido**.

## 3. Documentación

- [x] 3.1 `docs/lecturas-sin-conexion.md` (el lector sigue el recorrido; cómo definirlo) y `CLAUDE.md`. Verificar con `openspec validate orden-recorrido --strict`.
