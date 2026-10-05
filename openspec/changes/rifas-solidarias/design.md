# Design

## Context

Ver proposal.md (Why). Datos del sistema actual que condicionan el diseño:

- La identidad ya está resuelta: `get_current_user` carga el usuario con `rol` y `parcelas` (relación M2M `usuario_parcelas`). Una parcela puede tener varios usuarios.
- El portal del parcelero (`/liquidaciones`, `MiLiquidacion.tsx`) se renderiza **fuera** de `AppLayout`, sin sidebar.
- `AnyRoleRequired` se construye hoy con la tupla `ROLES` completa, y varios endpoints `AnyRoleRequired` (liquidaciones, parcelas) solo restringen por parcela cuando el rol es `parcelero`. Un rol nuevo agregado a `ROLES` heredaría acceso a todo el condominio.
- No hay suite de tests en `backend/`. Se verifica con `curl` contra el contenedor y con Playwright en la UI.
- No hay infraestructura de correo ni de mensajería. El gasto común se cobra en **Comunidad Feliz**, fuera de EnerCheck.
- La primera versión del módulo (grupos 1 a 7 de tasks.md) ya está implementada con un cobro por parcela al cierre. Este diseño incorpora los ajustes de la primera rifa real: premios, portería, formas de pago, comprobante e imputaciones.

## Goals / Non-Goals

**Goals:**
- Que dos ventas simultáneas no puedan quedarse con el mismo número.
- Historial completo de compras (también las anuladas) sin depender solo de la auditoría.
- Que la portería venda en pocos toques y que quien compra sin teléfono tenga igual un comprobante.
- Que el efectivo de la portería se pueda cuadrar.
- Que lo recaudado quede fuera de las liquidaciones eléctricas.

**Non-Goals:**
- Pagos en línea, reservas temporales de números, sorteo, ganadores.
- Envío automático de mensajes e integración automática con Comunidad Feliz.
- Rifas compartidas entre condominios.

## Decisions

### 1. Modelo de datos

- `rifas`: `id`, `condominio_id`, `nombre`, `beneficiario`, `descripcion`, **`premios` (text[], ordenado)**, **`datos_transferencia` (text)**, `precio_numero`, `cantidad_numeros`, `estado` (`abierta` | `cerrada`), `creado_por_id`, `created_at`, `cerrada_at`, **`ultimo_folio` (int, contador del correlativo)**.
- `compras_rifa`: `id`, `rifa_id`, **`folio` (int, correlativo por rifa; `UNIQUE (rifa_id, folio)`)**, `parcela_id`, `usuario_id` (cuenta que la registró), **`canal` (`portal` | `porteria` | `administracion`)** — reemplaza a `registrada_por_admin` —, **`comprador_nombre` (texto libre opcional)**, **`telefono` (opcional, normalizado)**, `numeros` (int[]), `monto`, **`medio_pago` (`efectivo` | `transferencia` | `gasto_comun`)**, **`pagada` (bool)**, **`pagada_at`**, **`pago_confirmado_por_id`**, **`voucher_archivo` (nombre del archivo, opcional)**, **`voucher_mime`**, `created_at`, `anulada`, `anulada_at`, `anulada_por_id`.
- `rifa_numeros`: sin cambios, con **`UNIQUE (rifa_id, numero)`**.
- `cobros_rifa` se reemplaza por **`imputaciones_rifa`** (modelo `ImputacionRifa`), que representa las imputaciones al gasto común: `id`, `rifa_id`, `parcela_id`, `cantidad_numeros`, `monto`, **`cargada` (bool)**, **`cargada_at`** (renombran `pagado` y `fecha_pago`), con `UNIQUE (rifa_id, parcela_id)`.
- `usuarios.telefono` (string, opcional, normalizado).
- Rol `porteria` (id 5) en el seed de roles.

**¿Por qué separar compra y número?** La compra es la unidad que ve el usuario y la que se anula; el número es la unidad que tiene que ser única. Al anular se **borran las filas de `rifa_numeros`** y la compra queda `anulada = true`, así que el historial sobrevive y la restricción única solo considera números vigentes.

**Folio con contador en la rifa.** Al comprar, la rifa ya está bloqueada con `FOR UPDATE` (§3), así que `ultimo_folio += 1` es seguro y no se reutiliza al anular. Se muestra como `R{rifa_id}-{folio:03d}`.
*Alternativa descartada:* usar el `id` global de la compra. Es único, pero no es corto ni correlativo por rifa, y no sirve para anotarlo en papel.

**Migración.** Hoy no hay rifas en ninguna base: las alteraciones de `compras_rifa` y `cobros_rifa` son seguras sin migrar datos. La migración igual mapea `registrada_por_admin=true` a `canal='administracion'` por coherencia.

### 1b. Voucher de transferencia: almacenamiento privado

`/app/uploads` se sirve como estático **público** (`main.py` monta `StaticFiles`), así que el voucher no puede guardarse ahí. Se guarda en **`/app/privado/vouchers/<uuid>.<ext>`**, en un volumen nuevo `privado_data` de `docker-compose.yml` (sin él, el bind mount `./backend:/app` del entorno de desarrollo lo dejaría dentro del repositorio; además se agrega `backend/privado/` a `.gitignore`). Se entrega solo por `GET /rifas/{id}/compras/{cid}/voucher`, que valida sesión, tenant y que el usuario sea staff o pertenezca a la parcela, y responde con `Content-Disposition: inline`.

**Una sola petición para la venta con voucher.** `POST /rifas/{id}/compras` pasa a aceptar `multipart/form-data`: un campo `datos` (JSON con la compra) y un archivo `voucher` opcional. Así la regla "transferencia en portería exige voucher" se valida antes de reservar números, y no queda una venta sin voucher si la subida falla. El archivo se escribe antes del commit y se borra si la transacción falla, igual que el OCR de boletas.
*Alternativa descartada:* crear la compra y subir el voucher en una segunda petición. Si la segunda falla, queda una transferencia de portería sin respaldo y con los números tomados.

**Adjuntar después**: `POST /rifas/{id}/compras/{cid}/voucher` (multipart), para el autor de la compra o el staff, mientras `pagada` sea falso. Reemplaza el anterior y borra el archivo viejo.

**Tamaño en el cliente.** Antes de enviar, el frontend reduce las fotos a un máximo de 1600 px por lado y las convierte a JPEG (canvas). Una foto de teléfono de 4–8 MB queda en unos 300 KB, se sube rápido con el wifi de la portería y ocupa poco disco. Los PDF y los HEIC que el navegador no puede decodificar se envían tal cual, con el límite de 10 MB.

### 2. La concurrencia la resuelve la base de datos

La compra inserta la compra y sus números en una transacción. Si otra petición ganó un número, el `UNIQUE (rifa_id, numero)` lanza `IntegrityError` y el endpoint responde `409` con los números en conflicto. También se verifica la disponibilidad antes de insertar, para dar un mensaje claro en el caso común.

### 3. Bloqueo de la rifa al comprar, anular y cerrar

Estas operaciones leen la rifa con `SELECT ... FOR UPDATE`. Así se serializan con el cierre y el contador de folio queda consistente.

### 4. Formas de pago y quién puede usarlas

| Canal (quién registra) | `efectivo` | `transferencia` | `gasto_comun` |
|---|---|---|---|
| `portal` (usuario vinculado a la parcela) | 422 | pendiente | se imputa al cierre |
| `porteria` | pagada al registrar | pendiente | se imputa al cierre |
| `administracion` | pagada al registrar | pendiente | se imputa al cierre |

El canal lo decide el servidor según el rol: admin → `administracion`, porteria → `porteria`, resto → `portal`. Si un admin compra a nombre de una parcela suya, cuenta como `portal`. `POST /compras/{id}/confirmar-pago` (admin) solo aplica a `transferencia`, y también funciona con la rifa cerrada.

### 5. Guardas y el rol `porteria`

En `dependencies.py`: `ROLES` incluye `porteria`, pero **`AnyRoleRequired` se define explícitamente con los cuatro roles originales**. Así ningún endpoint existente cambia de comportamiento. Se agregan `PorteriaRequired` (super_admin, admin_condominio, porteria) y `RifaAccesoRequired` (los cinco). `TenantId` funciona igual: la cuenta de portería tiene `condominio_id`.

En los endpoints de rifas, el criterio de "ve todo" pasa de `_es_admin` a `_es_staff` (admin o porteria) para el detalle, la búsqueda y la caja. Anular, editar, cerrar, reabrir, confirmar pagos y exportar siguen siendo solo de los roles administrativos.

### 6. Endpoints (`/api/v1/rifas`)

| Método | Ruta | Guard | Uso |
|---|---|---|---|
| GET | `/rifas/` | RifaAcceso | Lista (filtro `estado`) |
| POST | `/rifas/` | Admin | Crear (con `premios` y `datos_transferencia`) |
| GET | `/rifas/{id}` | RifaAcceso | Detalle recortado: el staff ve todo, el parcelero solo lo suyo |
| PATCH | `/rifas/{id}` | Admin | Editar |
| GET | `/rifas/{id}/compras?parcela_id=&folio=` | Porteria | Búsqueda de compras para responder consultas |
| POST | `/rifas/{id}/compras` | RifaAcceso\* | multipart: `datos` = `{parcela_id, numeros[], medio_pago, comprador_nombre?, telefono?}` + `voucher?` (\*el lector sin parcelas recibe 403 por la regla de parcela) |
| POST | `/rifas/{id}/compras/{cid}/anular` | AnyRole (autor de portal) o Admin | La portería recibe 403 |
| POST | `/rifas/{id}/compras/{cid}/confirmar-pago` | Admin | Solo `transferencia` |
| POST | `/rifas/{id}/compras/{cid}/voucher` | Autor o Porteria | Adjuntar o reemplazar el voucher mientras no esté pagada |
| GET | `/rifas/{id}/compras/{cid}/voucher` | RifaAcceso + parcela | Entrega el archivo; staff o usuarios de la parcela |
| GET | `/rifas/{id}/caja` | Porteria | Efectivo vigente agrupado por día (America/Santiago) y cuenta |
| GET | `/rifas/{id}/telefonos?parcela_id=` | Porteria | Teléfonos de los usuarios vinculados a la parcela, para proponerlos |
| POST | `/rifas/{id}/cerrar` | Admin | Genera imputaciones solo de `gasto_comun` |
| POST | `/rifas/{id}/reabrir` | Admin | 409 si alguna imputación está cargada |
| PATCH | `/rifas/{id}/imputaciones/{iid}` | Admin | `{cargada}` |
| GET | `/rifas/{id}/imputaciones.csv` | Admin | Para Comunidad Feliz |
| GET | `/rifas/{id}/export.csv` | Admin | Lista para el sorteo (con folio, comprador, canal y forma de pago) |

La portería no puede listar `/parcelas` (queda fuera de `AnyRoleRequired`), así que el buscador de parcelas sale de un endpoint propio: `GET /rifas/{id}/parcelas` (Porteria) devuelve las parcelas activas del condominio con su propietario.

### 7. Comprobante: WhatsApp por enlace, folio e impresión

- **WhatsApp por enlace `https://wa.me/<telefono>?text=<mensaje>`**: la app lo abre en el equipo de la portería y el portero toca "Enviar". No tiene costo ni necesita aprobaciones.
  *Alternativa descartada por ahora:* la API de WhatsApp Business (Meta Cloud API), que envía sin intervención pero cobra por conversación, exige plantillas aprobadas y una verificación de empresa. Si el volumen lo justifica, se reemplaza el enlace por un envío desde el backend sin cambiar el resto del flujo.
- El **mensaje** lo arma el frontend con los datos de la respuesta de la compra: rifa, folio, números, parcela, monto, forma de pago, premios y, si es transferencia, los datos para transferir.
- **Sin teléfono**: la pantalla de éxito muestra el folio y los números en tipografía grande para anotarlos, y un botón "Imprimir comprobante" que usa `window.print()` con una hoja de estilos `@media print` de ancho reducido (sirve para impresoras térmicas de 58/80 mm y también para impresoras A4). Sin impresora, el botón simplemente no se usa.
- **Normalización del teléfono** (backend y frontend, misma regla): se quitan los no dígitos; con 8 dígitos se antepone `569`; con 9 dígitos (celular o fijo) se antepone `56`; con 11 dígitos que empiezan en `56` queda igual; cualquier otro caso es inválido.

### 8. Frontend

- **Portería** (`/porteria`, sin `AppLayout`, estilo móvil como `MiLiquidacion`): selector de rifa abierta (si hay una sola, se elige sola) → buscador de parcela (número o propietario) → grilla compartida (`NumeroGrid`) → nombre del comprador (opcional) → forma de pago (botones grandes, `efectivo` por defecto) → si es transferencia, **"Tomar foto del voucher"** (`<input type="file" accept="image/*,application/pdf" capture="environment">`, que en tablet o teléfono abre directo la cámara), con vista previa y opción de repetir; Confirmar queda deshabilitado hasta que haya voucher → teléfono (propuestos de la parcela como chips, más un campo editable) → confirmar. Tras confirmar: pantalla de éxito con folio grande, "Enviar por WhatsApp", "Imprimir" y "Nueva venta". Pestañas secundarias: "Buscar compra" (por parcela o folio) y "Caja".
- **Parcelero**: `CompraPanel` agrega la elección `gasto_comun` / `transferencia` (sin efectivo) y muestra los datos para transferir. El detalle muestra los premios y, por compra, la forma de pago y el estado (pagada, pendiente de confirmación o se imputa al gasto común).
- **Administración**: el formulario de la rifa suma premios (lista editable) y datos para transferir. En `RifaDetalle`, la pestaña *Compras* muestra canal, comprador, folio y forma de pago, con "Ver voucher" y "Confirmar pago" en las transferencias pendientes (el voucher se abre en un modal; los PDF, en una pestaña nueva). *Cobros* pasa a llamarse *Imputaciones* (marcar como cargada y descargar el CSV para Comunidad Feliz). Se agrega la pestaña *Caja*.
- React Query keys: `['rifas']`, `['rifa', id]`, `['rifa-caja', id]`, `['rifa-compras', id, filtros]`.

### 9. Menú y acceso

Menú "Rifas" (id 9) solo para `super_admin` y `admin_condominio`. La portería no usa sidebar: `ROLE_HOME.porteria = '/porteria'`. Se agrega al seed un usuario de portería para Santa Laura (`porteria@santalaura.cl`).

### 10. Auditoría sin tocar la spec `auditoria`

Las acciones se declaran en la spec `rifas-solidarias`, para no chocar con `items-credito-y-validacion`, que ya modifica el requisito "Vocabulario de acciones". `MARCAR_PAGO_RIFA` se reemplaza por `CONFIRMAR_PAGO_RIFA` (compras) y `MARCAR_IMPUTACION_RIFA` (imputaciones).

## Risks / Trade-offs

- [Cuenta de portería compartida: no se sabe qué turno vendió] → La caja se agrupa por día; cada turno cuadra su efectivo antes de entregar. Si hiciera falta distinguir turnos, se crean cuentas separadas con el mismo rol, sin cambios de código.
- [La portería no puede anular: un error de digitación obliga a llamar al administrador] → Es deliberado, para que el efectivo no se pueda "anular" sin rastro. La portería ve la compra y la informa; el administrador la anula y la caja se ajusta sola.
- [Enlace de WhatsApp: si el portero no toca "Enviar", el mensaje no sale] → Queda el folio en pantalla y el respaldo en el portal y el sorteo. El texto del botón deja claro que falta enviar.
- [Comprador sin teléfono pierde el papel] → La compra está registrada a nombre de la parcela con su nombre; la portería la busca por parcela o folio y la lista del sorteo la identifica.
- [Un integrante de la parcela compra con gasto común sin acuerdo de los demás] → Las compras son visibles para toda la parcela y el admin puede anularlas mientras la rifa esté abierta. La imputación se genera recién al cerrar.
- [El formato de importación de Comunidad Feliz puede no calzar con el CSV] → Se exporta un CSV genérico (unidad, propietario, cantidad, monto, concepto). Ver Open Questions.
- [Vouchers con datos bancarios y personales] → Almacenamiento fuera del estático público, entrega solo con sesión y permiso de parcela, nombres de archivo aleatorios (uuid). Nunca se incluyen en los CSV ni en la auditoría (solo el nombre de archivo).
- [El volumen `privado_data` no tiene respaldo propio] → Se documenta junto a `uploads_data` y `postgres_data` en las instrucciones de despliegue.
- [Dos cambios en curso con migraciones] → Antes de generar la migración, `alembic heads`; si hay más de una, encadenar o hacer merge.

## Migration Plan

0. `docker-compose.yml`: volumen `privado_data` montado en `/app/privado`; `.gitignore`: `backend/privado/`.
1. Migración Alembic: columnas nuevas en `rifas` y `compras_rifa`, renombres en `cobros_rifa`, `usuarios.telefono`. Sin rifas existentes, no hay datos que transformar.
2. Seeds idempotentes: rol `porteria`, usuario de portería de Santa Laura y menú.
3. Carga de teléfonos de residentes desde la planilla, normalizados (script fuera del repo, por los datos personales).
4. Rollback: `alembic downgrade -1` revierte las columnas; la migración anterior elimina las tablas.

## Open Questions

- Formato exacto de importación de cargos en Comunidad Feliz. Si tienen una plantilla de carga masiva, se ajustan las columnas del CSV de imputaciones sin cambiar el resto del diseño.
