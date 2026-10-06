# Proposal

## Why

Hoy toda rifa acepta efectivo, transferencia y gasto común. La administración necesita elegir por rifa qué formas de pago se aceptan. Por ahora, la rifa de Santa Laura debe aceptar solo transferencia.

## What Changes

- **Cada rifa define sus formas de pago** (`rifas.medios_pago`, al menos una).
  - Las rifas existentes quedan con las tres.
  - Las compras ya hechas conservan su forma de pago.
- **Al crear o editar la rifa:** casillas *Efectivo*, *Transferencia* y *Gasto común*.
- **Al vender:** solo aparecen las formas aceptadas, y el servidor rechaza las demás con `422`.

## Capabilities

### Modified Capabilities

- `rifas-solidarias`: formas de pago configurables por rifa.

## Impact

- **Backend:** migración `b4e2c7d91f30` (columna y CHECK), `models/rifa.py`, `schemas/rifa.py` y la validación en `POST /rifas/{id}/compras`.
- **Frontend:** `RifaFormModal` (casillas) y `CompraPanel` (filtra las formas).
- Pendiente para un cambio posterior: el folio en la glosa de la transferencia, el comprobante obligatorio desde el portal y la liberación de reservas sin confirmar.
