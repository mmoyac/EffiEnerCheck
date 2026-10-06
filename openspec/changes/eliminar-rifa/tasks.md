# Tasks

## 1. Backend

- [x] 1.1 `GET /rifas/{id}/eliminacion` (`SuperAdminRequired`) con el resumen: compras vigentes y anuladas, números vendidos, monto pagado, imputaciones pendientes y cargadas, y vouchers. Verificar con una prueba que el resumen de una rifa con compras e imputaciones es correcto y que `admin_condominio` recibe 403.
- [x] 1.2 `DELETE /rifas/{id}?confirmacion=<nombre>` (`SuperAdminRequired`): verifica el nombre (422 si no coincide), lee los vouchers, registra `ELIMINAR_RIFA` con el resumen, borra con una sentencia SQL (cascade), confirma la transacción y luego borra los archivos de voucher. Verificar con pruebas: la eliminación deja la rifa, las compras, los números y las imputaciones en cero y borra los archivos; una confirmación incorrecta no borra nada; `admin_condominio` recibe 403; la auditoría queda registrada.

## 2. Frontend

- [x] 2.1 `api/rifas.ts`: `resumenEliminacion` y `eliminar`. En `RifaDetalle.tsx`, botón "Eliminar rifa" visible solo para `super_admin`, con un modal que muestra el resumen, un aviso rojo si hay imputaciones cargadas y el campo para escribir el nombre. Al eliminar, invalida `['rifas']` y navega a `/rifas`. Verificar con `npm run build` y en el navegador.

## 3. Documentación

- [x] 3.1 `docs/rifas.md` y `CLAUDE.md`: la eliminación (quién puede, qué borra, cómo se confirma). Verificar con `openspec validate eliminar-rifa --strict`.
