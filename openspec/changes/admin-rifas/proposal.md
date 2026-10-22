## Why

Una comunidad pidió que una vecina administre las rifas sin acceso al resto del portal (energía, usuarios, parcelas, cobranza). Hoy operar una rifa exige `admin_condominio`, que lo abre todo. La persona es además comunera: si fuera un rol aparte, perdería con esa cuenta su liquidación de luz y la compra para su parcela, o necesitaría dos cuentas con correos distintos.

## What Changes

- Nuevo **permiso** `administra_rifas` en la cuenta de un `comunero` (no es un rol nuevo). En pantalla: «Administración de rifas».
- Con el permiso, el comunero opera el módulo de Rifas como la administración: crear y editar rifas, registrar compras a nombre de cualquier parcela (canal `administracion`), confirmar transferencias, anular, cerrar y reabrir, imputaciones, caja, CSV y vouchers.
- Revisa y resuelve los **pagos en línea en revisión solo de rifas** (concepto `rifa_compra`); los de otros conceptos no los ve.
- Sigue siendo comunero en todo lo demás: su luz, su cuenta corriente y sus compras, filtradas a sus parcelas. No gana acceso a energía, usuarios, parcelas, panel, auditoría, cobranza ni pasarelas.
- **No** puede eliminar rifas (sigue siendo solo `super_admin`) ni administrar usuarios.
- Lo activan `super_admin` y `admin_condominio` en Usuarios, solo en cuentas `comunero`. El cambio rige de inmediato (no va en el JWT) y se audita.
- Sin el módulo `rifas` contratado, el permiso no da acceso a nada.
- La planilla de onboarding de backoffice agrega el perfil «Administración de rifas», que puede repetir el correo de un comunero.

## Capabilities

### New Capabilities
- `administracion-rifas`: qué puede hacer un comunero con el permiso de administración de rifas, cómo se resuelve el canal de sus ventas, qué ve de las compras y de los pagos en revisión, y cómo llega a esas pantallas.

### Modified Capabilities
- `control-acceso-multitenant`: nueva guarda de administración de rifas basada en el permiso, y menú del comunero con el permiso.
- `gestion-usuarios`: alta y edición del permiso `administra_rifas`, restringido a cuentas `comunero`.

## Impact

- **Base de datos:** columna `usuarios.administra_rifas BOOLEAN NOT NULL DEFAULT false` (migración Alembic); `schema.dbml`.
- **Backend:** `core/dependencies.py` (guarda `RifaAdminRequired`), `endpoints/rifas.py` (reemplaza `AdminRequired` salvo en eliminar; `_es_admin`/`_es_staff`), `endpoints/pagos.py` (revisión filtrada por concepto), `endpoints/usuarios.py` y su schema, `endpoints/auth.py` (`/auth/me`), `endpoints/menus.py`.
- **Frontend:** `types`, `useAuth`, `Usuarios.tsx` (casilla), rutas `/rifas` y `/rifas/:id`, acceso desde las pantallas del comunero, bloque «Pagos por revisar» de rifas.
- **Docs:** `docs/rifas.md`, `CLAUDE.md`, planilla `docs/plantilla-onboarding-backoffice.xlsx`, recorrido de rifas en el centro de capacitación.
- **Tests:** acceso con y sin permiso, canal de venta, filtro de pagos en revisión, permiso inerte sin módulo y en roles distintos de comunero.
