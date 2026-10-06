# Proposal

## Why

Hoy una rifa no se puede eliminar: solo se pueden anular sus compras. Una rifa creada por error, de prueba o que ya no corresponde queda para siempre en las listas, con sus compras e imputaciones. El super admin necesita eliminarla por completo, junto con todo lo que depende de ella.

## What Changes

- **Eliminar una rifa (solo `super_admin`).** Borra la rifa y todo lo que depende de ella:
  - sus compras, incluidas las anuladas;
  - los números vendidos;
  - las imputaciones al gasto común;
  - las fotos de vouchers de transferencia guardadas en el almacenamiento privado.
- **Resumen previo.** Antes de eliminar, el sistema informa qué se borrará: compras vigentes y anuladas, números vendidos, monto pagado, imputaciones pendientes y cargadas, y vouchers. Si hay imputaciones ya **cargadas en Comunidad Feliz**, lo advierte en rojo: esos cobros ya figuran en el gasto común y habrá que revertirlos allá a mano.
- **Confirmación fuerte.** Para eliminar hay que escribir el nombre exacto de la rifa.
- **Se permite en cualquier estado:** abierta o cerrada.
- **Auditoría** `ELIMINAR_RIFA` con el resumen de lo borrado (conteos y montos, sin datos personales). El registro de auditoría sobrevive a la eliminación.

## Capabilities

### New Capabilities

_(ninguna)_

### Modified Capabilities

- `rifas-solidarias`:
  - nuevo requisito "Eliminación de una rifa";
  - el requisito de auditoría suma el código `ELIMINAR_RIFA`.

## Impact

- **Backend:** `endpoints/rifas.py`:
  - `GET /rifas/{id}/eliminacion` (resumen);
  - `DELETE /rifas/{id}?confirmacion=<nombre>`;
  - borrado de vouchers con `_borrar_voucher`.
- **Frontend:** botón "Eliminar rifa" en `RifaDetalle.tsx`, solo para `super_admin`, con un modal de resumen y confirmación. Al terminar, vuelve a `/rifas`.
- **Orden de archivado:** este cambio modifica la capacidad `rifas-solidarias`, que agrega el cambio del mismo nombre, todavía sin archivar. Hay que archivar primero `rifas-solidarias`.
