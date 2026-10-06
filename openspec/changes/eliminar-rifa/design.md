# Design

## Context

- Las FK de `compras_rifa`, `rifa_numeros` e `imputaciones_rifa` hacia `rifas` ya tienen `ON DELETE CASCADE`.
- Los vouchers son archivos en `/app/privado/vouchers` (`CompraRifa.voucher_archivo`), fuera de la base.
- `auditoria_logs` no tiene FK a `rifas`, así que el registro sobrevive a la eliminación.

## Decisions

1. **El borrado se apoya en el `CASCADE` de la base:** `DELETE FROM rifas WHERE id = …` mediante una sentencia SQL, no con `session.delete()`. Así no depende de la configuración de *cascade* del ORM y se borra todo en una sola sentencia.
2. **Los vouchers se borran después del commit:** se leen sus nombres, se confirma la transacción y recién entonces se eliminan los archivos.
   - Si el commit falla, los archivos siguen ahí y la rifa también.
   - Si falla el borrado de un archivo, queda un huérfano sin referencia, que no es accesible porque solo se sirve por endpoint con una compra vigente. Se registra un aviso en el log.
3. **Confirmación por el nombre en el query string** (`?confirmacion=`): un `DELETE` con cuerpo no es fiable en todos los proxies. La comparación es exacta, sin distinguir los espacios de los extremos.
4. **El resumen es un endpoint aparte** (`GET /rifas/{id}/eliminacion`), con el mismo cálculo que se registra en la auditoría.
5. **Solo `SuperAdminRequired`.** Como el super admin no tiene tenant, no hay filtro por condominio.

## Risks / Trade-offs

- **[Se pierde el historial de una rifa real]** → Es irreversible desde la app. Mitigaciones: el resumen previo, la confirmación con el nombre, el aviso rojo si hay imputaciones cargadas, el registro en auditoría y los respaldos diarios y pre-deploy, que permiten recuperar desde la base si fue un error.
