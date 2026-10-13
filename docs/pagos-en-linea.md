# Pagos en línea (pasarelas de pago)

Los comuneros pagan desde el portal con la cuenta de la comunidad en **Flow** (tarjetas, Webpay, Mach) o **Khipu** (transferencia bancaria). Es una base común de la plataforma: hoy la usan las **rifas**, y otro módulo puede sumarse sin tocar el flujo.

> **El pago en línea es opcional y se usa solo si la comunidad lo decide** (asamblea o acuerdo del comité). La pasarela es una cuenta **de la propia comunidad**, con su contrato y su comisión, que paga el comunero que elige pagar así. Sin ese acuerdo no se crea ninguna pasarela y todo sigue funcionando con efectivo, transferencia y gasto común. Orden: la comunidad decide → abre su cuenta en el proveedor → el equipo de EFFIComunidad la configura y la prueba → la administración marca «Pago en línea» en cada rifa.

Spec: [`openspec/changes/pasarelas-pago/`](../openspec/changes/pasarelas-pago/) (`pagos-en-linea` y el delta de `rifas-solidarias`).

## Quién hace qué

| Rol | Puede |
|-----|-------|
| `super_admin` | Crear, editar, probar, activar, desactivar y eliminar pasarelas de cualquier condominio. Cargar y reemplazar credenciales. |
| `admin_condominio` | Ver las pasarelas de su condominio (sin credenciales). Resolver los **pagos por revisar**. |
| Comunero | Pagar en línea desde `/mis-rifas`. Ver el resultado en `/pagos/<id>/resultado`. |
| Portería | Nada nuevo: sigue con efectivo y transferencia con voucher. |

## Configurar una pasarela

1. **Pasarelas de pago** (menú Administración) → **Nueva pasarela**.
2. Elige el proveedor, el nombre que verá el comunero (p. ej. «Tarjeta o Webpay»), el ambiente y la comisión.
3. Pega las credenciales. Se guardan cifradas (AES-256-GCM con `PAGOS_CLAVE_MAESTRA`) y **nunca** se vuelven a mostrar: para cambiarlas, se reemplazan.
4. **Probar conexión**: llama al proveedor sin crear cobros.
5. **Activar**. Una pasarela de **producción** solo se activa con una prueba exitosa posterior al último cambio de credenciales. Cambiar el ambiente o las credenciales la desactiva.
6. En la rifa, marca **Pago en línea** entre las formas de pago.

### Ambientes

Cada ambiente es una cuenta distinta del proveedor. En el entorno de producción (`ENTORNO=produccion`) **nunca** se ofrece al comunero una pasarela de integración. Pasar a producción es configuración, no código: se crea una pasarela de producción con las credenciales reales, se prueba y se activa.

### Comisión

La paga el comunero. Cada pasarela define un porcentaje (con IVA incluido) y un monto fijo, y el total se calcula para que a la comunidad le llegue el valor completo:

```
total = ⌈(monto + fija) / (1 − porcentaje/100)⌉       ej.: $6.000 al 3,8 % → $6.238
```

El comunero ve la comisión y el total de cada pasarela antes de pagar. La compra de la rifa registra el monto de los números; la intención de pago guarda además la comisión y el total.

## Lo que ve el comunero

| Situación | Formas de pago en `/mis-rifas` |
|-----------|-------------------------------|
| La rifa acepta pago en línea y hay una pasarela disponible | **Pago en línea** (y gasto común, si la rifa lo acepta) |
| Sin pasarela disponible (o la rifa no acepta pago en línea) | **Transferencia** manual con voucher obligatorio, igual que en portería |

Si hay una sola pasarela, se elige sola. Si hay varias, el comunero elige y ve el total de cada una. Una pasarela cuyo mínimo supera el total no se ofrece y se explica por qué.

Al confirmar, la compra queda **pendiente con los números reservados por 15 minutos** y el navegador va a la pasarela. Al volver, `/pagos/<id>/resultado` muestra el estado y, mientras siga en proceso, lo consulta cada 3 s (y al proveedor cada 15 s) durante 5 minutos.

## Estados de una intención

| Estado | Significa | La compra de la rifa |
|--------|-----------|----------------------|
| `INICIADO` | Esperando el pago (vigente 15 min) | Pendiente, números reservados. No se anula ni se confirma a mano |
| `CONFIRMADO` | El proveedor confirmó el pago por el total esperado | Pagada |
| `RECHAZADO` | Respuesta definitiva del proveedor, o cancelación anulada en el proveedor | Anulada, números libres |
| `EXPIRADO` | Venció sin confirmación | Anulada, números libres. Si después llega aprobado, se aplica |
| `EN_REVISION` | Aprobado pero no se pudo aplicar (monto distinto, números ya vendidos o rifa cerrada), **o pagado y anulado después por la administración** (devolución pendiente) | La administración lo resuelve en **Pagos por revisar**: devuelve el dinero en el panel de la pasarela y lo marca resuelto con una nota. El sistema nunca devuelve dinero por sí mismo |

Una rifa **no se cierra** mientras tenga pagos `INICIADO`.

## Reglas del flujo

- **El resultado lo decide siempre el backend consultando al proveedor.** Lo que llega por el navegador o por el webhook solo identifica la intención.
- **Ninguna llamada al proveedor con una transacción abierta:** se hace commit, se llama y luego se toma `SELECT … FOR UPDATE` de la intención para aplicar el resultado.
- **Un solo pago aunque compitan el retorno, el webhook, la conciliación y la consulta a pedido:** todos pasan por `services/pagos/flujo.confirmar()`, que bloquea la fila y no reaplica un estado final.
- **Endpoints públicos** `GET|POST /api/v1/pagos/retorno/{proveedor}` (303 a la pantalla de resultado) y `POST /api/v1/pagos/webhook/{proveedor}` (200 o 404). Buscan la intención en la base **antes** de llamar al proveedor. nginx los limita por IP (zona `enercheck_pagos`).
- **Conciliación** cada 2 minutos (tarea del `lifespan`, con `pg_try_advisory_lock` porque producción corre 2 workers): `INICIADO` de más de 5 minutos y `EXPIRADO` de las últimas 24 horas.
- **Sin datos personales:** de la respuesta del proveedor se guarda solo una lista blanca (estado, montos, operación, autorización, últimos dígitos, medio). Nunca RUT, nombre, correo ni cuenta del pagador. El correo del comunero se envía al proveedor y se borra al terminar.

## Proveedores

### Flow (API 3.0.1)

- Integración: `https://sandbox.flow.cl/api`. Producción: `https://www.flow.cl/api`. **Son cuentas distintas con keys distintas.**
- Credenciales: API Key y Secret Key. Cada llamada se firma con HMAC-SHA256.
- Exige el correo del pagador. Mínimo: $350.
- **Sandbox:** tarjeta `4051885600446623`, CVV `123`, cualquier vencimiento. Simulación del banco: RUT `11111111-1`, clave `123`.

### Khipu (API 3.0)

- Misma URL para ambos ambientes (`https://payment-api.khipu.com/v3`). Para pruebas, en khipu.com: Perfil → Opciones de desarrollador → «Crear cuenta en modo desarrollador» (banco ficticio **DemoBank**, cualquier RUT, clave `1234`). La key de esa cuenta va en una pasarela de **integración**.
- Credencial: API Key.
- Solo `status=done` + `status_detail=normal` es un pago. `verifying` puede durar minutos (en DemoBank, unos 3).
- Si el comunero cancela, el sistema intenta borrar el cobro en Khipu. Si Khipu no lo permite (porque ya se pagó), consulta el estado y lo aplica.
- Khipu solo notifica a URLs https; sin ella, el pago se registra por el retorno o por la conciliación.

## Desarrollo local

1. `backend/.env` necesita `PAGOS_CLAVE_MAESTRA` (32 bytes en base64):
   ```sh
   python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"
   ```
2. Los webhooks no llegan a `localhost`. Para recibirlos, abre un túnel y pon su URL en `URL_PUBLICA_PAGOS`. Esa variable reemplaza **solo** la base de la URL de notificación:
   ```sh
   cloudflared tunnel --url http://localhost:8000
   # URL_PUBLICA_PAGOS=https://<algo>.trycloudflare.com
   ```
   Sin túnel todo funciona igual: el retorno y la conciliación registran el pago.
3. Prueba de punta a punta: crea una pasarela de integración (Flow sandbox o Khipu DemoBank), actívala, marca «Pago en línea» en una rifa y compra como comunero. Verifica en la base que queda una sola intención `CONFIRMADO` y una sola compra pagada:
   ```sql
   SELECT estado, total, transaccion_proveedor FROM intenciones_pago ORDER BY created_at DESC LIMIT 5;
   ```

## Agregar un proveedor

1. Una clase en `backend/app/services/pagos/proveedores/<proveedor>.py` que implemente `Adaptador` (`crear`, `token_de`, `verificar`, `consultar`, `probar` y, si el proveedor lo permite, `anular`), con su `campos_credenciales`, `requiere_email` y `monto_minimo`.
2. Registrarla en `proveedores/__init__.py`.
3. Tests con `httpx.MockTransport` como los de `tests/test_pagos_proveedores.py`.

El flujo, las pantallas y la contabilidad no cambian.

## Cobrar otra cosa en línea

Un módulo nuevo implementa el contrato `Consumidor` de `services/pagos/consumidores.py` (`aplicar`, `liberar`, `volver_a`) y lo registra con su `concepto`. Ejemplo: `services/rifas_pago.py`.

## Producción

Sin `PAGOS_CLAVE_MAESTRA` el backend arranca, pero no se pueden crear pasarelas (se configura cuando la comunidad decide usar pago en línea). Si está mal escrita, el arranque falla. `URL_PUBLICA_PAGOS` debe quedar vacía. En producción solo se ofrecen pasarelas de ambiente **Producción**: para probar, usa la cuenta real con un monto bajo. Para rotar la clave: `python -m app.db.rotar_clave_pagos --nueva <clave>`. Ver [DEPLOY.md §3.2](../DEPLOY.md).
