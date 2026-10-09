# Proposal

## Why

La administración necesita un respaldo de cada período que pueda guardar, imprimir o compartir con la comunidad: cuánto paga cada parcela y la prueba de que la suma coincide con la boleta. Hoy eso solo se ve en pantalla.

## What Changes

- `GET /api/v1/liquidaciones/pdf/{boleta_id}` (solo administración) devuelve un PDF con:
  - los datos de la boleta (total emisión, kWh de la compañía y de las parcelas, diferencial, valor del kWh);
  - el desglose de cargos;
  - una fila por parcela, en orden natural (lecturas, kWh, energía, variable, fijo y total);
  - el cuadre de la suma contra el total emisión.
- El PDF dice si el período está publicado, cerrado o en borrador.
- Botón **PDF** en la pestaña Liquidaciones del período.

## Capabilities

### New Capabilities

_(ninguna)_

### Modified Capabilities

- `motor-liquidaciones`: se agrega la descarga del PDF del período.

## Impact

- **Backend:** `services/reporte_liquidaciones.py`, `endpoints/liquidaciones.py` y la dependencia `fpdf2` (Python puro, sin vulnerabilidades conocidas).
- **Frontend:** `api/liquidaciones.ts` (`descargarPdf`) y `BoletaDetalle.tsx`.
- **Tests:** `test_proceso_energia.py` descarga el PDF como administración y verifica que un comunero recibe 403.
