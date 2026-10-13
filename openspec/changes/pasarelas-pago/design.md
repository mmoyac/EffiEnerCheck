# Design

## Context

- Las compras de rifa reservan sus números con `rifa_numeros` (`UNIQUE (rifa_id, numero)`) y bloquean la rifa con `SELECT ... FOR UPDATE` para el folio. Anular una compra borra sus `RifaNumero` y deja `anulada=True`. Ese mecanismo ya sirve como reserva: un pago en línea en curso es una compra pendiente con sus números asignados.
- La sesión es JWT por cabecera, sin cookies: no hay anti-CSRF que eximir. Los límites por IP viven en `frontend/nginx.prod.conf` (zona `enercheck_auth`).
- Producción corre `uvicorn --workers 2` y no hay scheduler. `main.py` ya tiene un `lifespan`.
- `httpx` ya es dependencia. `cryptography` es nueva.
- El portal de cada condominio tiene su URL en `condominios.portal_url`, con `PORTAL_URL_POR_DEFECTO` como respaldo.

## Goals / Non-Goals

**Goals:**
- Un núcleo `pagos` que no sepa de rifas y en el que un proveedor nuevo sea un archivo nuevo.
- Que el flujo de compra de rifas cambie lo mínimo: `en_linea` es una forma de pago más.

**Non-Goals:**
- Pagar los abonos de la luz en línea (solo queda el contrato de consumidor para hacerlo después).
- Pagos en línea desde la portería, la administración o la landing.
- Devoluciones o reembolsos desde la plataforma: se resuelven en el panel del proveedor.
- Verificar la firma `x-khipu-signature`: la notificación solo identifica, y el resultado siempre se consulta.

## Decisions

### Estructura

```
backend/app/services/pagos/
├── cifrado.py         # AES-256-GCM: cifrar(dict, aad) / descifrar(bytes, aad); rotar
├── proveedores/
│   ├── base.py        # Adaptador (ABC), Redireccion, Resultado, CampoCredencial, ErrorCredenciales, ErrorProveedor
│   ├── flow.py
│   ├── khipu.py
│   └── __init__.py    # REGISTRO = {"flow": Flow(), "khipu": Khipu()}
├── consumidores.py    # Consumidor (Protocol) + REGISTRO por concepto; rifas se registra al importar
├── comision.py        # total_con_comision(monto, pct, fijo)
├── flujo.py           # iniciar(), confirmar(intencion_id, origen), cancelar(), expirar()
└── conciliacion.py    # vuelta() + bucle del lifespan con pg_try_advisory_lock
backend/app/services/rifas_pago.py   # Consumidor "rifa_compra"
backend/app/api/v1/endpoints/pasarelas.py   # CRUD admin, probar, activar
backend/app/api/v1/endpoints/pagos.py       # disponibles, iniciar (vía rifas), estado, consultar, retorno, webhook, revisión
```

### Modelo

- `pasarelas_pago`: `id`, `condominio_id`, `proveedor`, `nombre_visible`, `ambiente` (`integracion|produccion`, CHECK), `credenciales_cifradas` (BYTEA, nonce incluido), `comision_porcentaje` (NUMERIC(5,2)), `comision_fija` (INT), `orden`, `activa`, `prueba_at`, `prueba_ok`, `prueba_mensaje`, `credenciales_at`, timestamps.
- `intenciones_pago`: `id` UUID (PK), `condominio_id`, `pasarela_id`, `usuario_id`, `concepto` (`rifa_compra`), `referencia_id` (int: la `compra_id`), `monto`, `comision`, `total`, `estado` (CHECK con los 5 estados), `vence_at`, `orden_comercio` (CHAR(26) UNIQUE), `token_proveedor` (índice), `transaccion_proveedor`, `email_pagador` (solo para enviarlo; se borra al terminar), `autorizacion`, `ultimos_digitos`, `medio`, `monto_confirmado`, `respuesta_proveedor` (JSONB filtrado), `motivo`, `consultado_at` (límite de 10 s), `confirmado_at`, timestamps.
- `compras_rifa.intencion_pago_id` (FK nullable). El CHECK de `rifas.medios_pago` se amplía con `en_linea`, y `MEDIOS_PAGO` también.
- **Una intención = una cosa pagada** (`concepto` + `referencia_id`), sin tabla de detalle. Una compra de rifa ya agrupa varios números. Si después hace falta pagar varias cosas juntas (varios abonos), se agrega `intencion_pago_items` sin romper esto.

### Cifrado

- Sin compatibilidad hacia atrás: el sistema aún no está en producción, así que no hay compras previas que migrar.
- `PAGOS_CLAVE_MAESTRA` = 32 bytes en base64. AAD = `condominio:{cid}:pasarela:{pid}`. El texto cifrado es `nonce(12) || ciphertext`.
- Crear una pasarela exige su `id`: se inserta, se hace `flush()` y luego se cifra con la AAD.
- `python -m app.db.rotar_clave_pagos --nueva <b64>` recifra todo en una transacción. La clave anterior se lee de `PAGOS_CLAVE_MAESTRA`.
- En desarrollo, sin clave, la pasarela no se puede guardar con credenciales (`422` claro). `app.arranque` exige la clave en producción.

### Contrato de adaptador

```python
class Adaptador(ABC):
    campos_credenciales: list[CampoCredencial]   # nombre, etiqueta, secreto: bool
    requiere_email: bool
    monto_minimo: int
    async def crear(self, pasarela, intencion, urls) -> Redireccion
    def token_de(self, datos: dict) -> str | None
    async def verificar(self, pasarela, token) -> Resultado
    async def consultar(self, pasarela, intencion) -> Resultado
    async def probar(self, pasarela) -> None          # lanza ErrorCredenciales / ErrorProveedor
    async def anular(self, pasarela, token) -> bool   # opcional; por defecto False
```

Las credenciales en claro las entrega el flujo al adaptador como `pasarela.credenciales` (un dict en memoria); nunca pasan por un schema de respuesta. El cliente `httpx.AsyncClient` se inyecta (atributo del adaptador) para que los tests usen `httpx.MockTransport`.

### Flujo (`flujo.py`)

1. **Iniciar** (`POST /rifas/{id}/compras` con `medio_pago=en_linea` y `pasarela_id`):
   - En una transacción: valida la pasarela (activa, del condominio, ambiente permitido, mínimo), crea la `CompraRifa` pendiente con sus `RifaNumero` (reutiliza el bloqueo de la rifa), crea la intención `INICIADO` y hace commit.
   - Fuera de la transacción: `adaptador.crear()`.
   - En otra transacción: guarda el token y la transacción del proveedor. Si `crear` falla → `_rechazar()`, que libera la compra.
   - La respuesta incluye `redireccion` (`url`, `metodo`, `campos`) además de la compra.
2. **Confirmar(intencion_id, origen)**: el único camino, usado por el retorno, el webhook, la conciliación y la consulta a pedido.
   - (a) Lee la intención sin bloquear; si está en estado final (`CONFIRMADO`, `RECHAZADO`, `EN_REVISION`), sale.
   - (b) Consulta al proveedor **sin transacción abierta**.
   - (c) Abre una transacción con `SELECT ... FOR UPDATE` de la intención y vuelve a revisar el estado. Aplica según el `Resultado`:
     - `APROBADO`: si el monto difiere → `EN_REVISION`; si no → `consumidor.aplicar()`, que devuelve `ok` o un motivo de revisión, y queda `CONFIRMADO` o `EN_REVISION`.
     - `RECHAZADO` (definitivo) → `_rechazar()`.
     - `PENDIENTE` → si venció → `EXPIRADO` + `consumidor.liberar()`.
   - El candado de fila reemplaza la "clave de idempotencia" del prompt original: la segunda petición encuentra `CONFIRMADO` en (c) y no aplica nada.
3. **Consumidor de rifas** (`rifas_pago.py`):
   - `aplicar`: si la compra no está anulada → pagada. Si está anulada, toma `FOR UPDATE` de la rifa y comprueba que siga abierta y que los números estén libres; si es así, recrea los `RifaNumero` y deja `anulada=False`, pagada. Si no, devuelve el motivo.
   - `liberar`: anula la compra (borra `RifaNumero`) con auditoría `ANULAR_COMPRA_RIFA` y `detalles.origen="pago_en_linea"`.
   - `descripcion`: "Rifa <nombre> – números 7, 8". Va como `subject`. A Flow no se le manda nada en `optional`, porque lo muestra al pagador.

### Proveedores

- **Flow:** firma HMAC-SHA256 en hex sobre `nombre+valor` ordenados (vector de prueba en los tests).
  - `payment/create` con `timeout` = vigencia restante + 120 s; redirección GET a `url?token=`.
  - Verificar con `getStatusExtended`; conciliar con `getStatusByCommerceId` (sirve con o sin token).
  - Estados: 2 = `APROBADO`; 3 y 4 = `RECHAZADO`; 1 = `PENDIENTE`.
  - Prueba de conexión: `getStatusByCommerceId` con una orden inventada. Código 1700 = OK; cualquier mensaje que mencione apiKey, firma o secret = credenciales.
  - Mínimo: 350.
- **Khipu:** cabecera `x-api-key`.
  - `POST /v3/payments` con `transaction_id = orden_comercio`, `custom = intención.id`, `return_url = …/pagos/retorno/khipu?intencion=<id>` y `cancel_url = …&cancelado=1`. Se envían `notify_url` y `notify_api_version` solo si la URL es https.
  - Estados: `done` + `normal` = `APROBADO`; `pending` y `verifying` = `PENDIENTE`; el resto = `RECHAZADO`.
  - Prueba de conexión: `GET /v3/banks`. Mínimo: 1 (se ajusta si Khipu informa otro).
  - `anular` = `DELETE /v3/payments/{id}`, que devuelve True solo con 2xx.
- **Filtrado de la respuesta:** cada adaptador declara una lista blanca de claves que se guardan en `respuesta_proveedor`.

### URLs

- Retorno y notificación: `{base}/api/v1/pagos/retorno/{proveedor}`.
  - `base` = `portal_url` del condominio o `PORTAL_URL_POR_DEFECTO` (el portal y la API comparten origen detrás de nginx; en desarrollo Vite hace proxy de `/api`).
  - Para la URL de notificación, `URL_PUBLICA_PAGOS` reemplaza solo la base (túnel `cloudflared`). En producción queda vacía.
- El retorno responde `303` a `{base}/pagos/{id}/resultado`.
- Para Flow, la intención se identifica por el `token`, que llega en el POST de retorno y en el webhook. Para Khipu, por `?intencion=` (retorno) o por `payment_id` (webhook).
- En ambos casos se busca localmente primero, y por `?intencion=` también se verifica que el proveedor de la URL coincida con el de la intención.

### Endpoints

| Método y ruta | Guarda | Uso |
|---|---|---|
| `GET /pasarelas` | `AdminRequired` + `TenantId` (super_admin indica `condominio_id`) | Lista; el `admin_condominio` la ve sin acciones |
| `POST/PATCH/DELETE /pasarelas…` | `SuperAdminRequired` | Crear, modificar o eliminar |
| `PUT /pasarelas/{id}/credenciales` | Super admin | Reemplaza las credenciales (desactiva la pasarela) |
| `POST /pasarelas/{id}/probar`, `/activar`, `/desactivar` | Super admin | |
| `GET /pasarelas/proveedores` | Super admin | Catálogo con `campos_credenciales` para el formulario dinámico |
| `GET /pagos/disponibles?monto=` | `AnyRoleRequired` | Pasarelas ofrecibles con su total y su comisión, o el motivo de exclusión |
| `GET /pagos/{id}` | Dueño o admin del condominio | Estado para la pantalla de resultado |
| `POST /pagos/{id}/consultar` | Dueño o admin | Consulta a pedido (429 si hubo otra hace menos de 10 s) |
| `GET /pagos/revision` + `POST /pagos/{id}/resolver` | Admin | Intenciones `EN_REVISION`; resolver = nota + `resuelta_at` (el dinero se arregla por fuera) |
| `GET/POST /pagos/retorno/{proveedor}`, `POST /pagos/webhook/{proveedor}` | Públicos | |

El router `pagos` y el de `pasarelas` son núcleo (exigen `portal`, no un módulo). La aplicación a una rifa ya pasa por la guarda del módulo `rifas` en `POST /rifas/{id}/compras`.

### Conciliación

- El bucle `asyncio` arranca en el `lifespan` y se cancela al apagar. Cada 120 s toma `pg_try_advisory_lock(<constante>)` en una conexión propia: si no lo obtiene, otro worker está conciliando.
- Procesa `INICIADO` con `created_at < now() − 5 min` y `EXPIRADO` con `updated_at > now() − 24 h`, de a una, con `confirmar(id, "conciliacion")`. Un error en una intención no detiene las demás.
- Se desactiva en los tests (`PAGOS_CONCILIACION=0`).

### Frontend

- **Formas de pago por canal:** una función `medios_permitidos(rifa, canal, hay_pasarela)` en el backend (fuente de verdad, validada en `POST /compras`) con su espejo en el frontend:
  - portal: `en_linea` + `gasto_comun`, o `transferencia` + `gasto_comun` si no hay pasarela disponible (o la rifa no acepta `en_linea`);
  - portería y administración: lo que acepta la rifa salvo `en_linea` (sin cambios respecto de antes).

  Todo se intersecta con `rifa.medios_pago`. En el respaldo del portal, la `transferencia` acepta `en_linea` o `transferencia` en la rifa y el voucher es obligatorio, como en portería.
- `CompraPanel` (modo `portal`) suma la opción `en_linea` ("Pago en línea", ayuda "Tarjeta, Webpay o transferencia inmediata · con costo adicional").
  - Al elegirla llama a `GET /pagos/disponibles?monto=`. Con una sola pasarela muestra su total directamente; con varias, la lista con el total de cada una.
  - El botón final envía la compra y redirige: GET con `window.location.assign`, POST con un formulario oculto.
- `pages/pagos/Resultado.tsx` en `/pagos/:id/resultado` (con sesión). Consulta el estado cada 3 s y llama a `consultar` cada 15 s durante 5 min.
- `pages/admin/Pasarelas.tsx`: lista apilada en celular y sección "Pagos por revisar".
  - `super_admin`: selector de condominio, modal con formulario dinámico (secretos en `type=password`, nunca precargados) y botones Probar, Activar y Desactivar.
  - `admin_condominio`: solo lectura.
- Menú: migración que agrega "Pasarelas de pago" en Administración (roles `super_admin` y `admin_condominio`, `modulo` NULL).
- React Query keys: `['pasarelas']`, `['pagos-disponibles', monto]`, `['pago', id]`, `['pagos-revision']`.

## Risks / Trade-offs

- [Un pago aprobado sin aplicar: números ya vendidos o rifa cerrada] → `EN_REVISION` visible para la administración. La devolución se hace en el panel del proveedor.
- [El comunero paga la comisión estimada y el proveedor cobra otra] → la comisión es configuración de la administración. La comunidad recibe el monto neto que le liquide el proveedor; si la diferencia es mínima, la absorbe la comunidad.
- [Reservar números 15 min permite que alguien bloquee números sin pagar] → la intención vence y se libera sola. Cada comunero puede tener una sola intención `INICIADO` vigente por rifa (409 si inicia otra).
- [Un worker reiniciado a mitad de la conciliación] → cada intención se confirma en su propia transacción. La vuelta siguiente retoma lo pendiente.
- [Khipu cambia o amplía sus estados] → todo estado desconocido = `PENDIENTE`, y nunca se aprueba por omisión.

## Migration Plan

1. Migración Alembic: tablas nuevas, columna en `compras_rifa`, CHECK de `medios_pago` y menú.
2. Generar `PAGOS_CLAVE_MAESTRA` (`python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"`) y cargarla en el Environment de Dokploy **antes** del deploy (sin ella, producción no arranca).
3. nginx: zona `enercheck_pagos` para retorno y webhook.
4. Deploy. Ninguna rifa acepta `en_linea` hasta que la administración la marque y active una pasarela.
5. Rollback: desactivar las pasarelas (sin deploy). El downgrade de la migración solo es posible si no hay compras `en_linea`.

## Open Questions

- El mínimo real por transacción de Khipu: se confirma con el proveedor y se ajusta la constante sin cambiar nada más.
