## 1. Modelo de datos y contratos

- [x] 1.1 Agregar `pendiente` al `Literal` `TipoCalculo` en `backend/app/schemas/boleta.py`
- [x] 1.2 Actualizar el comentario de `tipo_calculo` en `backend/app/models/boleta.py` con los cuatro valores y la semántica de `informativo` como exclusión deliberada
- [x] 1.3 Actualizar el comentario de `estado` en `backend/app/models/boleta.py` documentando que `validada` significa desglose corroborado
- [x] 1.4 Agregar `'pendiente'` al tipo `tipo_calculo` en `frontend/src/types/index.ts`
- [x] 1.5 Verificar que no exista restricción de base de datos sobre `tipo_calculo` ni `estado` que impida los valores nuevos (no debería requerir migración)

## 2. OCR: signo y líneas no reconocidas

- [x] 2.1 Ampliar `_PROMPT` en `backend/app/services/ocr.py` para instruir que descuentos, notas de crédito, abonos, devoluciones y bonificaciones se devuelvan con signo negativo
- [x] 2.7 Excluir del `_PROMPT` los totales y las líneas de saldo anterior de `items_detalle` (descubierto en pruebas: un saldo anterior clasificado como cargo produce `valor_kwh` negativo)
- [x] 2.2 Verificar que la conversión a IVA `round(monto_sin_iva * 1.19)` preserve el signo en montos negativos
- [x] 2.3 En `procesar_ocr_boleta` de `backend/app/api/v1/endpoints/boletas.py`, reemplazar el descarte de líneas sin coincidencia por la creación de un `BoletaItemDetalle` con `tipo_calculo="pendiente"`
- [x] 2.4 Mantener el descarte solo cuando la descripción quede vacía tras normalizar
- [x] 2.5 Al final de `procesar_ocr_boleta`, devolver la boleta a `borrador` si estaba en `validada`
- [x] 2.6 Incluir en el registro de auditoría `PROCESS_OCR` cuántos ítems nuevos se crearon como pendientes

## 3. Corroboración del desglose

- [x] 3.1 Crear el endpoint `POST /boletas/{boleta_id}/validar-items` en `backend/app/api/v1/endpoints/boletas.py`, restringido a `AdminRequired`, con validación de tenant
- [x] 3.2 Rechazar con `409` si la boleta ya está en `validada`
- [x] 3.3 Rechazar con `409` si `liquidaciones_cerradas` es verdadero
- [x] 3.4 Rechazar con `409` indicando el conteo si existe al menos un ítem con `tipo_calculo="pendiente"`
- [x] 3.5 Fijar `estado = "validada"` y registrar la acción `VALIDAR_ITEMS`
- [x] 3.6 Construir la instantánea de auditoría con descripción, monto y `tipo_calculo` de cada ítem más los totales de la boleta
- [x] 3.7 En `actualizar_detalles_boleta`, devolver la boleta a `borrador` si estaba en `validada`

## 4. Motor y guarda de cálculo

- [x] 4.1 Excluir los ítems con `tipo_calculo="pendiente"` de `suma_items_fijo` y `suma_items_variable` en `backend/app/services/enercheck.py` (verificar: la clasificación por tipo ya los excluye implícitamente)
- [x] 4.2 En `calcular_liquidaciones` de `backend/app/api/v1/endpoints/liquidaciones.py`, rechazar con `409` si `boleta.estado != "validada"`, con mensaje que indique corroborar el desglose primero
- [x] 4.3 Documentar en el docstring de `enercheck.py` la semántica de los montos negativos y por qué no afectan `valor_kwh`
- [x] 4.4 Confirmar con un caso numérico que un crédito `fijo` reduce la cuota pareja y que el total sigue cuadrando con `monto_total_emision`

## 5. Cliente HTTP y consola

- [x] 5.1 Agregar `boletasApi.validarItems(id)` en `frontend/src/api/boletas.ts`
- [x] 5.2 En `ModalEditDetalles.tsx`, agregar la opción `Pendiente` al selector de tipo y etiquetar las opciones con su efecto en el reparto
- [x] 5.3 En `ModalEditDetalles.tsx`, diferenciar visualmente los montos negativos y permitir su ingreso sin bloqueo
- [x] 5.4 En `BoletaDetalle.tsx`, mostrar un aviso destacado con el conteo de ítems pendientes cuando existan
- [x] 5.5 En `BoletaDetalle.tsx`, agregar el botón de corroborar desglose visible con la boleta en `borrador` y el período abierto
- [x] 5.6 En `BoletaDetalle.tsx`, ocultar o deshabilitar la acción de calcular mientras la boleta no esté en `validada`, indicando el motivo
- [x] 5.7 Invalidar las queries `['boleta', boletaId]` y `['boletas']` tras corroborar
- [x] 5.8 Manejar el `409` de corroboración y el de cálculo mostrando el detalle del backend
- [x] 5.9 Incorporar el estado corroborado a `EstadoBadge` en `Boletas.tsx` y `Dashboard.tsx`

## 6. Verificación

- [x] 6.1 Reconstruir el backend con `docker-compose up --build -d backend`
- [x] 6.2 Probar el flujo completo: crear boleta, subir imagen, procesar OCR, verificar que las líneas nuevas aparecen como pendientes
- [x] 6.3 Probar que calcular sobre una boleta en `borrador` devuelve `409`
- [x] 6.4 Probar que corroborar con ítems pendientes devuelve `409` y que sin pendientes pasa a `validada`
- [x] 6.5 Probar que reprocesar el OCR y que editar detalles devuelven la boleta a `borrador`
- [x] 6.6 Verificar con una boleta real que un ítem de crédito se extrae con signo negativo
- [x] 6.7 Verificar en `auditoria_logs` que `VALIDAR_ITEMS` contiene la instantánea completa del desglose
- [x] 6.8 Confirmar que el total liquidado sigue cuadrando exactamente con `monto_total_emision`

## 7. Cierre

- [x] 7.1 Ejecutar `openspec validate --specs --strict` y confirmar que pasa
- [x] 7.2 Actualizar la tabla de errores conocidos de `CLAUDE.md` con el `409` de boleta sin corroborar
- [ ] 7.3 Archivar el cambio con `/opsx:archive` para sincronizar las specs principales
