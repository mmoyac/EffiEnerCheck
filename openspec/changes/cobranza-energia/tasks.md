# Tasks

## 1. Base de datos y backend

- [x] 1.1 Migración: tabla `movimientos_luz` (saldo inicial y abonos, con anulación) y `liquidaciones_parcelas.monto_abonado`; los pagos ya marcados se convierten en abonos. Verificado con `alembic upgrade`, `downgrade -1` y de nuevo `upgrade`.
- [x] 1.2 `services/cuenta_luz.py`: cuenta (cargos del saldo inicial y de los períodos publicados; abonos vigentes), imputación a la deuda más antigua y `recalcular()` de las liquidaciones. Recálculo al publicar (`boletas.py`).
- [x] 1.3 `endpoints/cuenta_luz.py`:
  - `GET /resumen` y `GET /parcelas/{id}` (comunero, solo las suyas);
  - `POST /abonos` (todo o nada, sin fechas futuras ni repetidas, auditoría con saldo antes y después);
  - `POST /abonos/{id}/anular` (motivo obligatorio, sin borrar).

  Se quita `PATCH /liquidaciones/{id}/pago`.
- [x] 1.4 Saldo inicial en la planilla de la lectura inicial: plantilla, vista previa y aplicar; el vigente se anula, no se pisa. Al eliminar la lectura inicial, sus saldos se anulan.
- [x] 1.5 Verificado con `tests/test_cobranza.py`:
  - imputación y estados;
  - auditoría y anulación sin borrado;
  - resumen;
  - saldo a favor al publicar;
  - validaciones;
  - acceso del comunero;
  - saldo inicial desde la planilla;
  - la suite completa en verde.

## 2. Frontend

- [ ] 2.1 `api/cuentaLuz.ts`, tipos y `pages/admin/Cobranza.tsx`:
  - indicadores;
  - por período;
  - deudores con abono individual y masivo (fecha y nota);
  - cuenta de la parcela con anulación;
  - exportar CSV.

  `/cobranza` para la administración (menú «Cobranza», migración `menu_cobranza`) y `/liquidaciones` para el comunero, cada una redirigiendo a la otra si entra el rol equivocado. Verificar en el navegador.
- [ ] 2.2 `BoletaDetalle.tsx` (estado de pago de solo lectura: pagado, parcial o pendiente), `MiLiquidacion.tsx` (saldo y cuenta del comunero) e `ImportarLecturasIniciales.tsx` (saldos en la vista previa). Verificar con `npm run build` y en el navegador.

## 3. Documentación

- [x] 3.1 `docs/flujo-periodo.md`, `docs/ayuda-energia.md`, `CLAUDE.md` y `schema.dbml`. Verificar con `openspec validate cobranza-energia --strict`.
