# Design

## Context

- Cada cuenta tiene un solo rol (`usuarios.rol_id`) y un correo es una cuenta. Las operaciones de administración de rifas usan hoy `AdminRequired`, la misma guarda de energía, usuarios y parcelas. Dentro de `rifas.py`, `_es_admin()` y `_es_staff()` deciden el canal de una venta y si se ven todas las compras.
- Varios endpoints `AnyRoleRequired` solo filtran por parcela cuando el rol es exactamente `comunero` (por eso `porteria` quedó fuera de esa guarda).
- `get_current_user` relee la cuenta en cada petición, y los módulos ya se resuelven así, no en el JWT.
- «Pagos por revisar» vive en `/pasarelas` (núcleo, `AdminRequired`) y lista intenciones de todos los conceptos. El de rifas es `rifa_compra`.
- Las pantallas del comunero (`/liquidaciones`, `/mis-rifas`) van fuera de `AppLayout`; `/rifas` y `/rifas/:id` van dentro, con el menú de `/menus/me`.

## Goals / Non-Goals

**Goals:**
- Una sola cuenta para la vecina: comunera en lo suyo, administradora en rifas.
- Ningún endpoint fuera de rifas (y de su bandeja de pagos) cambia de comportamiento para ella.

**Non-Goals:**
- Un sistema general de permisos por módulo. Si aparece un segundo caso (p. ej. «administra energía»), se evalúa entonces.
- Que el permiso sirva en roles distintos de `comunero`. Lector y portería no lo necesitan, y admin ya lo tiene todo.

## Decisions

**1. Permiso booleano en `usuarios`, no un rol nuevo.**
`usuarios.administra_rifas BOOLEAN NOT NULL DEFAULT false`. Se descartó el rol `admin_rifas` porque la persona es comunera: un rol aparte le exigiría dos cuentas y, si se agregaba a las guardas del comunero, vería todo el condominio (los filtros miran `rol == "comunero"`). También se descartó una tabla de permisos: hoy hay un único caso, y una columna es auditable y simple de migrar.

**2. Guarda `RifaAdminRequired` en `core/dependencies.py`.**
Admite a `super_admin` y `admin_condominio`, y a un `comunero` con `administra_rifas`. Reemplaza `AdminRequired` en todos los endpoints de `rifas.py` excepto en eliminar (`SuperAdminRequired`, sin cambio). Como lee `current_user`, quitar el permiso rige en la siguiente petición. `AdminRequired` y el resto no cambian.

**3. Un helper para decidir quién administra en `rifas.py`.**
`_es_admin(user)` pasa a ser «administra rifas» (roles admin, o comunero con el permiso), y `_es_staff` lo incluye. Así, el canal de venta (`administracion` si la parcela no es suya, `portal` si es suya) y la visibilidad completa del detalle salen de la lógica actual, sin ramas nuevas. El canal sigue decidiéndolo el servidor.

**4. Bandeja de pagos en revisión filtrada por concepto.**
`GET /pagos/revision` y `POST /pagos/{id}/resolver` pasan a `RifaAdminRequired`. Si el usuario no es `super_admin` ni `admin_condominio`, la consulta se filtra por `concepto == "rifa_compra"` (constante del consumidor de rifas, no un literal repetido). Al resolver, una intención de otro concepto responde `404`, igual que una de otro condominio.

**5. Menú: unión con el ítem de Rifas.**
`/menus/me` agrega el menú cuya ruta es `/rifas` cuando el comunero tiene el permiso, y luego aplica el filtro de módulos que ya existe. No se toca `menu_roles` (es por rol, y el permiso es por persona).

**6. Cliente.**
- `Sesion`/`/auth/me` exponen `administra_rifas`; `useAuth` agrega `useAdministraRifas()`, verdadero para admins o para un comunero con el permiso.
- `/rifas` y `/rifas/:id` redirigen a la pantalla de inicio si el usuario no administra rifas. Dentro, las acciones dependen de ese mismo helper y no del rol, y «Eliminar» sigue solo para `super_admin`.
- Las pantallas del comunero muestran «Administrar rifas» (→ `/rifas`) en el `Header` si tiene el permiso. En `AppLayout`, el comunero ve en el menú Rifas y un enlace de vuelta a «Mis liquidaciones».
- El componente «Pagos por revisar» sale de `Pasarelas.tsx` a `components/pagos/` y se reutiliza en `/rifas` para quien administra rifas, sin las pasarelas.
- `Usuarios.tsx` muestra la casilla «Administra rifas» solo con rol `comunero`, y una insignia en el listado.

**7. Validación en la API de usuarios.**
Si se envía `administra_rifas=true` y el rol resultante no es `comunero`, se responde 422. Si se cambia el rol de un comunero con el permiso, se fuerza `false`. El cambio queda en el before/after de `UPDATE_USER`/`CREATE_USER`.

## Risks / Trade-offs

- [Un endpoint de rifas que siga en `AdminRequired` dejaría a la vecina sin poder hacer esa operación] → test que recorre las operaciones de administración de rifas con un comunero con el permiso.
- [Un comunero con el permiso alcanza un endpoint de administración general] → `AdminRequired` no se toca, y hay tests 403 en usuarios, parcelas, boletas, cobranza y pasarelas.
- [Ve compras y teléfonos de todas las parcelas en las rifas] → es lo pedido (opera como la administración). Queda en la ayuda del permiso en Usuarios.
- [La auditoría de rifas no distingue si actuó un admin o la vecina] → el `usuario_id` ya identifica a la persona. No se agrega campo.

## Migration Plan

- Migración Alembic que agrega la columna con `server_default false`: no cambia a nadie y no requiere datos. Rollback: `downgrade` elimina la columna. El código anterior no la usa.
- Despliegue normal (develop → main). El permiso se activa a mano en Usuarios después del despliegue.
