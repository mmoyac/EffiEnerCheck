# Tasks

## 1. Modelo de datos y migración

- [x] 1.1 Crear `backend/app/models/rifa.py` con `Rifa`, `CompraRifa`, `RifaNumero` y `CobroRifa` según design.md §1 (incluye `UNIQUE (rifa_id, numero)` y `UNIQUE (rifa_id, parcela_id)` en cobros) y exportarlos en `app/models/__init__.py`; verificar con `docker exec enercheck-backend-1 python -c "import app.models"` sin errores
- [x] 1.2 Ejecutar `alembic heads` (si hay más de un head, encadenar o hacer merge), generar la migración `rifas_solidarias` y aplicarla con `alembic upgrade head`; verificar con `\d rifa_numeros` en psql que existe la restricción única, y que `alembic downgrade -1` seguido de `upgrade head` funciona
- [x] 1.3 Agregar las tablas de rifas a `schema.dbml` y verificar que el archivo describe las cuatro tablas con sus claves foráneas

## 2. Gestión de la rifa (admin)

- [x] 2.1 Crear `backend/app/schemas/rifa.py` con `RifaCreate` (precio y cantidad > 0), `RifaUpdate`, `RifaResponse` y `RifaDetalleResponse`; verificar que un POST con precio 0 responde 422
- [x] 2.2 Crear `backend/app/api/v1/endpoints/rifas.py` con `_get_rifa_o_404`, `GET /rifas` (filtro por tenant y `estado`), `POST /rifas` y `GET /rifas/{id}`, y registrarlo en `router.py`; verificar con curl que un admin crea y lista, que un parcelero recibe 403 al crear y que una rifa de otro condominio da 403
- [x] 2.3 Implementar `PATCH /rifas/{id}` con las reglas de edición (precio bloqueado con compras vigentes, cantidad no menor al máximo vendido, 409 si está cerrada) y auditoría `UPDATE_RIFA` con antes/después; verificar cada caso de 409 con curl

## 3. Compra y anulación

- [x] 3.1 Implementar `POST /rifas/{id}/compras`: rifa leída con `FOR UPDATE`, validación de rango y duplicados (422), parcela asociada al usuario o parcela activa del condominio si es admin (403), inserción de la compra y sus números, captura de `IntegrityError` → 409 con los números en conflicto, monto congelado y auditoría `COMPRAR_RIFA`; verificar con curl la compra feliz, número tomado (409), parcela ajena (403) y rifa cerrada (409)
- [x] 3.2 Verificar la concurrencia: lanzar dos compras simultáneas del mismo número (dos `curl` en paralelo) y comprobar que una responde 200, la otra 409 y que en `rifa_numeros` hay una sola fila
- [x] 3.3 Implementar `POST /rifas/{id}/compras/{compra_id}/anular` (autor no admin-registrada, o admin; 403 para otro integrante; 409 si está cerrada), que borra los números, marca la compra anulada con quién y cuándo, y audita `ANULAR_COMPRA_RIFA`; verificar que el número vuelve a poder comprarse y que la compra sigue listada como anulada
- [x] 3.4 Completar `GET /rifas/{id}` con `numeros_vendidos` (sin dueño), `mis_compras` y `mis_cobros` filtrados por las parcelas del usuario (todo para admins), y `GET /rifas/{id}/compras` solo para admins; verificar con el token del parcelero seed que no aparecen datos de otras parcelas

## 4. Cierre, cobros y exportación

- [x] 4.1 Implementar `POST /rifas/{id}/cerrar` (genera un cobro por parcela con números vigentes, monto = cantidad × precio, audita `CERRAR_RIFA`) y `POST /rifas/{id}/reabrir` (409 si hay algún cobro pagado; borra los cobros; audita `REABRIR_RIFA`); verificar con un caso de dos parcelas que los montos coinciden y que reabrir con un cobro pagado da 409
- [x] 4.2 Implementar `PATCH /rifas/{id}/cobros/{cobro_id}/pago` con auditoría `MARCAR_PAGO_RIFA`; verificar que el parcelero ve el cobro como pagado en `mis_cobros`
- [x] 4.3 Implementar `GET /rifas/{id}/export.csv` (UTF-8 con BOM, ordenado por número, sin anuladas, columnas número/parcela/comprador/registrada por admin/fecha); verificar que el CSV abre en Excel con tildes correctas
- [x] 4.4 Verificar que calcular las liquidaciones de un período después de cerrar una rifa produce los mismos totales que antes (el motor no toca cobros de rifa)

## 5. Frontend: administración

- [x] 5.1 Agregar los tipos en `frontend/src/types/index.ts` y el cliente `frontend/src/api/rifas.ts` con todas las operaciones (incluida la descarga del CSV con el token); verificar con `npm run build` sin errores de tipos
- [x] 5.2 Crear `pages/admin/Rifas.tsx` (lista con estado, recaudado y números vendidos, y modal de creación y edición) y registrar `/rifas` en `App.tsx` dentro de `AppLayout`; agregar el menú id 9 "Rifas" en `db/seeds/menus.py` para `super_admin` y `admin_condominio`, y ejecutar el seed; verificar que aparece en el sidebar del admin y no en el del lector
- [x] 5.3 Crear `pages/admin/RifaDetalle.tsx` (`/rifas/:id`) con las pestañas Compras (anular y "Registrar compra" con selector de parcela y grilla), Cobros (marcar pagado) y Exportar CSV, y los botones Cerrar y Reabrir según el estado, con `onError` en cada mutation; verificar el flujo completo en el navegador con `hhernandez@santalaura.cl`

## 6. Frontend: portal del parcelero

- [x] 6.1 Crear un componente de grilla de números reutilizable (libre, seleccionado, de mi parcela, no disponible; botones de al menos 44 px; paginación por rangos de 100 cuando hay más de 200 números); verificar en la vista móvil del navegador
- [x] 6.2 Crear `pages/parcelero/Rifas.tsx` con `/mis-rifas` (lista) y `/mis-rifas/:id` (selector de parcela si tiene varias, grilla, barra "N números · $total — Confirmar", modal de confirmación, compras de la parcela con autor y fecha, anulación de las propias y cobros con estado), y manejar el 409 refrescando la grilla y conservando los números aún libres; verificar con `mmoyainfo+parcela@gmail.com` comprando, anulando y viendo una compra hecha por otro usuario de la misma parcela
- [x] 6.3 Agregar en `MiLiquidacion.tsx` el aviso de rifa abierta con enlace a `/mis-rifas/{id}` y un enlace "Rifas" en su cabecera; verificar que el aviso aparece solo cuando hay una rifa abierta

## 7. Documentación e integración

- [x] 7.1 Documentar el flujo de rifas en `docs/` (crear `docs/rifas.md` y enlazarlo en `docs/README.md`) y agregar los endpoints y archivos nuevos a `CLAUDE.md`; verificar que los enlaces funcionan
- [x] 7.2 Prueba de integración de punta a punta: crear una rifa, comprar desde dos parcelas (una de ellas registrada por el admin), anular una compra, cerrar, revisar los cobros, marcar uno pagado, intentar reabrir (409), exportar el CSV y revisar en `auditoria_logs` las siete acciones; finalmente, `openspec validate --specs --strict` y `openspec validate rifas-solidarias --strict` sin errores

## 8. Ajustes de modelo: premios, formas de pago, folio, imputaciones y teléfono

- [x] 8.1 Actualizar `models/rifa.py` (premios, datos_transferencia, ultimo_folio; folio, canal, comprador_nombre, telefono, medio_pago, pagada, pagada_at, pago_confirmado_por_id en compras; cargada/cargada_at en cobros) y agregar `telefono` a `models/usuario.py`; generar y aplicar la migración, y verificar `downgrade -1` / `upgrade head` y la restricción `UNIQUE (rifa_id, folio)` en psql
- [x] 8.2 Agregar `app/utils/telefono.py` con `normalizar_telefono()` según design §7 y verificar con un script los casos `9 9332 7142`, `56993327142`, `+56 9 9332 7142`, `93327142` y uno inválido
- [x] 8.3 Agregar `telefono` a los schemas de usuario (create/update/response) con normalización y 422 si es inválido; verificar con curl el alta con `9 9332 7142` → `56993327142` y un valor inválido → 422
- [x] 8.4 Actualizar `schemas/rifa.py` (premios con al menos uno, datos_transferencia, medio_pago, comprador_nombre, telefono, folio, canal, pagada; imputaciones) y verificar que crear una rifa sin premios responde 422

## 9. Rol porteria y guardas

- [x] 9.1 Agregar el rol `porteria` al seed de roles y el usuario `porteria@santalaura.cl` al seed de usuarios; en `dependencies.py`, definir `AnyRoleRequired` explícito con los 4 roles originales y agregar `PorteriaRequired` y `RifaAccesoRequired`; ejecutar solo esos seeds y verificar que la portería inicia sesión y recibe 403 en `/boletas/`, `/liquidaciones/`, `/parcelas/`, `/lecturas/` y `/usuarios/`
- [x] 9.2 Actualizar `useAuth`/`App.tsx` con `ROLE_HOME.porteria = '/porteria'` y la etiqueta del rol en `Header`; verificar que al iniciar sesión la portería llega a `/porteria`

## 10. Backend: venta, pagos, folio, caja e imputaciones

- [x] 10.1 Reescribir `POST /rifas/{id}/compras` con canal según el rol, reglas de `medio_pago` (efectivo solo staff → 422 para el portal; efectivo queda pagada), comprador_nombre, telefono normalizado y folio correlativo; verificar con curl la venta de portería en efectivo a un externo, el parcelero con efectivo (422) y los folios R?-001..003 con uno anulado en medio
- [x] 10.1b Agregar el volumen `privado_data` en `/app/privado` (docker-compose) y `backend/privado/` a `.gitignore`; convertir `POST /compras` a multipart (`datos` + `voucher`), con validación de tipo y tamaño (422) y la regla de voucher obligatorio en transferencias de portería (422 sin reservar números), borrando el archivo si la transacción falla; agregar `POST` y `GET .../compras/{cid}/voucher` con los permisos de la spec. Verificar con curl: transferencia de portería sin voucher (422, número libre) y con voucher (201); descarga como admin, como usuario de la parcela, como usuario de otra parcela (403) y sin sesión (401); y que `/uploads/...` no expone el archivo
- [x] 10.2 Ajustar la anulación (portería 403; el autor de portal solo si no está pagada; admin cualquiera, auditando el medio de pago) y agregar `POST .../confirmar-pago` (solo transferencia, también con la rifa cerrada; 409 en otro medio); verificar cada caso con curl
- [x] 10.3 Agregar `GET /rifas/{id}/parcelas`, `GET /rifas/{id}/telefonos?parcela_id=` y `GET /rifas/{id}/compras?parcela_id=&folio=` para la portería; verificar que la portería obtiene los teléfonos de la parcela 23 y encuentra una compra por folio
- [x] 10.4 Agregar `GET /rifas/{id}/caja` (efectivo vigente por día en America/Santiago y por cuenta); verificar el escenario de la spec (5 números vendidos, 1 anulado → 4 y 8000)
- [x] 10.5 Cambiar el cierre para generar imputaciones solo de `gasto_comun`, la reapertura con 409 si hay alguna `cargada`, `PATCH /imputaciones/{iid}` y `GET /imputaciones.csv`; verificar el escenario de formas de pago mixtas (una sola imputación de 6000) y el CSV
- [x] 10.6 Agregar folio, comprador, canal y forma de pago a `export.csv`, y actualizar los códigos de auditoría (`CONFIRMAR_PAGO_RIFA`, `MARCAR_IMPUTACION_RIFA`); verificar el CSV y los registros en `auditoria_logs`

## 11. Frontend: portería

- [x] 11.1 Crear `utils/telefono.ts` (misma regla que el backend) y `utils/comprobante.ts` (texto del mensaje y URL `wa.me`); verificar con `npm run build` y revisando el texto generado para una venta en efectivo y otra por transferencia
- [x] 11.2 Crear `pages/porteria/VentaRifa.tsx` (`/porteria`): rifa, buscador de parcela, grilla, comprador, forma de pago con efectivo por defecto, chips de teléfono y campo editable, confirmar; verificar con Playwright en vista de tablet una venta completa
- [x] 11.2b Paso "Tomar foto del voucher" en la venta por transferencia (cámara trasera, vista previa, repetir, reducción a 1600 px JPEG en el cliente; Confirmar deshabilitado sin voucher); verificar con Playwright subiendo una imagen de prueba de varios MB y comprobando en el contenedor que el archivo guardado pesa menos de 1 MB
- [x] 11.3 Pantalla de éxito con folio grande, "Enviar por WhatsApp" (enlace `wa.me`), "Imprimir comprobante" (`@media print` de ancho reducido) y "Nueva venta"; verificar la URL generada y una captura de la vista de impresión
- [x] 11.4 Pestañas "Buscar compra" (por parcela o folio) y "Caja" en la pantalla de portería; verificar con Playwright

## 12. Frontend: parcelero y administración

- [x] 12.1 En el portal, mostrar los premios, elegir `gasto_comun` / `transferencia` (con los datos para transferir y un voucher opcional, que también puede adjuntarse después desde la compra) y, por compra, la forma de pago y el estado; verificar con Playwright una compra con gasto común y otra por transferencia
- [x] 12.2 En `RifaFormModal`, agregar la lista editable de premios y los datos para transferir; en `RifaDetalle`, canal, comprador, folio y forma de pago en *Compras*, "Ver voucher" y "Confirmar pago" en las transferencias, *Imputaciones* (marcar como cargada y CSV) y *Caja*; verificar el flujo completo como admin con Playwright
- [x] 12.3 Agregar el campo teléfono en `Usuarios.tsx`; verificar que se guarda normalizado

## 13. Datos, documentación e integración

- [x] 13.1 Cargar los teléfonos de los residentes desde `docs/planillas/MATRIZ RESIDENTES.xlsx` (script fuera del repo, idempotente, normalizando) y verificar en psql cuántos usuarios quedaron con teléfono y cuántos números se descartaron por inválidos
- [x] 13.2 Agregar `docs/planillas/` a `.gitignore` (datos personales) y verificar con `git status` que la planilla no aparece
- [x] 13.3 Actualizar `docs/rifas.md` y `CLAUDE.md` (rol porteria, formas de pago, imputaciones, comprobante) y la tabla de roles y guardas de `CLAUDE.md`; verificar que los enlaces funcionan
- [x] 13.4 Prueba de punta a punta: crear una rifa con los 3 premios reales; la portería vende en efectivo a un externo sin teléfono (folio en pantalla), a un residente con teléfono (enlace WhatsApp) y por transferencia con foto del voucher; un parcelero compra con gasto común y otro por transferencia; el admin confirma la transferencia, revisa la caja, cierra, descarga imputaciones y la lista del sorteo, y marca una imputación como cargada; reabrir da 409. Finalmente `openspec validate rifas-solidarias --strict` y `openspec validate --specs --strict`
