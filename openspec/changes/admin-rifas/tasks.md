# Tasks

## 1. Modelo y cuentas

- [x] 1.1 Columna `usuarios.administra_rifas` (modelo, migración Alembic con `server_default false`, `schema.dbml`); verificar `alembic upgrade head` y `downgrade -1` en desarrollo
- [x] 1.2 Schemas y `endpoints/usuarios.py`: campo en alta, edición y listado; 422 si el rol resultante no es `comunero`; se fuerza `false` al cambiar de rol; queda en el before/after de la auditoría. Tests de los cuatro escenarios de `gestion-usuarios`
- [x] 1.3 `/auth/me` informa `administra_rifas`; test del escenario «El comunero consulta su sesión»

## 2. Guardas y API de rifas

- [x] 2.1 `RifaAdminRequired` en `core/dependencies.py` (super_admin, admin_condominio, comunero con el permiso, leído de la cuenta); test de permiso quitado con la sesión abierta
- [x] 2.2 `endpoints/rifas.py`: reemplazar `AdminRequired` por `RifaAdminRequired` (salvo eliminar) y que `_es_admin`/`_es_staff` incluyan al comunero con el permiso. Tests: crea, edita, confirma, anula, cierra, reabre, imputaciones, caja, CSV y voucher con el permiso; 403 sin el permiso; 403 al eliminar; rifa de otro condominio
- [x] 2.3 Tests del canal: venta a otra parcela → `administracion`; compra para su parcela → `portal` con los medios del portal
- [x] 2.4 Test de que fuera de rifas sigue siendo comunero: sus liquidaciones filtradas a sus parcelas; 403 en usuarios, parcelas, boletas, cobranza y pasarelas
- [x] 2.5 Test del condominio sin el módulo `rifas`: 403 con el detalle del módulo

## 3. Pagos en revisión y menú

- [x] 3.1 `endpoints/pagos.py`: `revision` y `resolver` con `RifaAdminRequired`; para quien no es admin, filtrar por el concepto del consumidor de rifas (constante, no literal); resolver otro concepto → 404. Tests de ambos escenarios
- [x] 3.2 `endpoints/menus.py`: agregar el menú `/rifas` al comunero con el permiso, respetando el filtro de módulos. Tests con y sin permiso, y sin módulo

## 4. Cliente

- [x] 4.1 Tipos (`Sesion`, `Usuario`), cliente de usuarios y `useAdministraRifas()` en `hooks/useAuth.ts`; `npm run build` sin errores
- [x] 4.2 `Usuarios.tsx`: casilla «Administra rifas» visible solo con rol comunero, con una ayuda («ve las compras y teléfonos de todas las parcelas en las rifas»), e insignia en el listado (tabla y lista de celular)
- [x] 4.3 Rutas `/rifas` y `/rifas/:id`: redirigir a quien no administra rifas; acciones según `useAdministraRifas()`; «Eliminar» solo `super_admin`. Revisar en ~390 px de ancho
- [x] 4.4 Acceso «Administrar rifas» en el `Header` de las pantallas del comunero con el permiso, y regreso a «Mis liquidaciones» desde `AppLayout`; probar el ida y vuelta en el navegador
- [x] 4.5 Extraer «Pagos por revisar» de `Pasarelas.tsx` a `components/pagos/` y mostrarlo en `/rifas` a quien administra rifas; `/pasarelas` sigue igual para los admins

## 5. Documentación y capacitación

- [x] 5.1 `docs/rifas.md` y `CLAUDE.md` (sección Roles y Rifas): el permiso, la guarda y por qué no es un rol
- [x] 5.2 Recorrido de rifas en `frontend/public/capacitacion/recorridos/rifas.js`: paso del comunero con el permiso (acceso «Administrar rifas»), con datos ficticios; revisar en `/capacitacion/`
- [x] 5.3 Planilla `docs/plantilla-onboarding-backoffice.xlsx`: perfil «Administración de rifas», que puede repetir el correo de la planilla de comuneros (y en ese caso no crea otra cuenta); regenerar y abrirla
- [x] 5.4 `openspec validate admin-rifas --strict` y suite completa de `pytest` en verde

## Workflow follow-up

- Archivar el cambio con `/opsx:archive` cuando esté desplegado (sincroniza `control-acceso-multitenant`, `gestion-usuarios` y crea `administracion-rifas`).
