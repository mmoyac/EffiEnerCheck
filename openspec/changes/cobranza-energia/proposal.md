# Proposal

## Why

El cargo de luz de cada parcela se cobra **dentro del gasto común**, y el comunero puede ir **abonando** a lo que debe. La administración necesita saber cuánto debe cada uno por luz, con trazabilidad para auditorías. Hoy el portal no lo permite:
- el pago solo se marca como «pagado o pendiente» por mes, y únicamente **antes de cerrar** el período, cuando todavía no se le cobró a nadie;
- recalcular borra lo marcado;
- no existe la deuda anterior a la plataforma, ni una vista de deudores.

## What Changes

- **Cuenta corriente de luz por parcela:**
  - **cargos:** el **saldo inicial** (la deuda anterior a la plataforma, cargada en el onboarding) y la liquidación de cada período **publicado**;
  - **abonos:** pagos de **cualquier monto**, con fecha y nota, que registra la administración;
  - **saldo** = cargos − abonos; si es negativo, es saldo a favor.
- **Imputación a la deuda más antigua.** Cada abono cubre primero el saldo inicial y después los meses en orden. Así cada mes queda **Pagado**, **Parcial** o **Pendiente** de forma automática; `pagado`, `fecha_pago` y el nuevo `monto_abonado` de cada liquidación se derivan y **no se marcan a mano**.
- **Trazabilidad para auditorías:**
  - un abono **nunca se borra**; se **anula** con motivo obligatorio, y quedan registrados quién y cuándo;
  - la auditoría registra `REGISTRAR_ABONO_LUZ` y `ANULAR_ABONO_LUZ`, con el saldo antes y después;
  - un saldo inicial corregido anula al anterior, no lo pisa.
- **Saldo inicial en el onboarding:** columna opcional **«Saldo luz»** en la planilla de la lectura inicial, en la plantilla, la vista previa y el aplicar todo o nada.
- **Endpoints `/api/v1/cuenta-luz`:**

  | Endpoint | Qué hace |
  |---|---|
  | `GET /resumen` | Totales, cobranza por período y deudores |
  | `GET /parcelas/{id}` | Movimientos y saldo; para el comunero, solo de sus parcelas |
  | `POST /abonos` | Uno o varios abonos, todo o nada |
  | `POST /abonos/{id}/anular` | Anula un abono |

- **Al publicar** un período, sus liquidaciones pasan a ser cargos y los abonos se vuelven a imputar (el saldo a favor se aplica solo).
- **BREAKING:** se eliminan `PATCH /liquidaciones/{id}/pago` y el marcado manual. Los pagos marcados antes se convierten en abonos durante la migración.
- **Pantalla «Liquidaciones y cobranza»** para la administración, en **`/cobranza`**: la opción «Liquidaciones» del menú pasa a llamarse «Cobranza», por migración. `/liquidaciones` queda solo para el comunero, y cada ruta redirige a la otra si entra el rol equivocado:
  - indicadores;
  - cobranza por período;
  - deudores, con abono individual o masivo;
  - cuenta de cada parcela, con anulación;
  - exportación CSV.
- **Comunero:** su saldo por luz y su cuenta (cargos, abonos y estado de cada mes).

Fuera de alcance: importación del informe de Comunidad Feliz e intereses por mora.

## Capabilities

### New Capabilities

- `cobranza-energia`: cuenta corriente de luz, saldo inicial, abonos con imputación y anulación auditada, resumen de cobranza, deudores y exportación.

### Modified Capabilities

- `motor-liquidaciones`: el estado de pago de una liquidación deja de marcarse a mano y se deriva de la cuenta corriente.
- `portal-parcelero`: el comunero ve su saldo y su cuenta de luz.

## Impact

- **Base de datos:** tabla `movimientos_luz` y `liquidaciones_parcelas.monto_abonado`; migración que convierte los pagos ya marcados en abonos. `schema.dbml`.
- **Backend:**
  - `services/cuenta_luz.py`, con la cuenta y la imputación;
  - `endpoints/cuenta_luz.py`;
  - `boletas.py`: recálculo al publicar, saldo inicial en la planilla y anulación de saldos al eliminar la lectura inicial;
  - `services/lecturas_iniciales.py`, con la columna de saldo;
  - en `liquidaciones.py` se quita el pago manual.
- **Frontend:**
  - `pages/admin/Cobranza.tsx`;
  - `App.tsx`;
  - `BoletaDetalle.tsx`: estado de pago de solo lectura;
  - `MiLiquidacion.tsx`: saldo y cuenta;
  - `ImportarLecturasIniciales.tsx`: los saldos en la vista previa;
  - `api/cuentaLuz.ts` y `types`.
- **Docs:** `docs/flujo-periodo.md`, `docs/ayuda-energia.md`, `CLAUDE.md`.
