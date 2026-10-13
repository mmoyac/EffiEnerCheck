# Proposal

## Why

Hoy el comunero que compra números de rifa por transferencia tiene que transferir por su cuenta, subir el voucher y esperar a que la administración confirme el pago a mano. Un pago en línea (Flow, Khipu) se confirma solo y libera a la administración de conciliar transferencias. Como otras partes de la plataforma también cobran (por ejemplo, los abonos de la luz), el cobro en línea se construye como una base común con varias pasarelas, y rifas es su primer uso.

## What Changes

- **Base común de pagos en línea (plataforma):**
  - Pasarelas por condominio, creadas y configuradas por el `super_admin` (el `admin_condominio` las ve, sin modificarlas ni ver credenciales): proveedor, nombre visible, ambiente (integración o producción), credenciales cifradas, comisión, orden y estado activo. Hay prueba de conexión y la activación en producción queda condicionada a una prueba exitosa.
  - **Intenciones de pago** con vigencia de 15 minutos. El resultado lo decide siempre el backend consultando al proveedor. La confirmación es idempotente aunque compitan el retorno, el webhook y la conciliación.
  - Contrato de **adaptador por proveedor**: Flow (API 3.0.1) y Khipu (API 3.0). Agregar un proveedor nuevo es agregar un adaptador.
  - Contrato de **consumidor**: qué se paga y qué pasa al aprobar o liberar. Rifas es el primero; los abonos de la luz quedan previstos, no implementados.
  - Endpoints públicos de retorno y webhook, conciliación en segundo plano cada 2 minutos y pantalla de resultado que consulta el estado mientras el pago está en proceso.
  - **Comisión a cargo del comunero:** cada pasarela define su comisión (porcentaje con IVA incluido + monto fijo). El cobro se calcula para que a la comunidad le llegue completo el valor de lo pagado, y el recargo se muestra antes de elegir la pasarela.
- **Rifas:**
  - Forma de pago nueva `en_linea` ("Pago en línea"), que la rifa acepta o no en `medios_pago`.
  - **Formas de pago según el canal:**
    - Comunero desde el portal: `en_linea` y `gasto_comun`.
    - Portería y administración: sin cambios (las formas de la rifa salvo `en_linea`; la transferencia manual con voucher sigue aquí).
  - **Respaldo:** si el condominio no tiene una pasarela disponible, el comunero ve la `transferencia` manual con voucher obligatorio, igual que en portería.
  - Al iniciar un pago en línea, la compra se registra pendiente y sus números quedan **reservados** mientras la intención está vigente. Si el pago se rechaza o vence, la compra se anula y los números se liberan.
  - Un pago aprobado tarde se aplica si los números siguen libres. Si no, queda **en revisión** para que la administración lo resuelva.
  - Una rifa no se cierra mientras haya pagos en línea en curso. Una compra en línea no se confirma a mano ni la anula el comunero mientras su pago está en curso.
- **Por ahora, solo el comunero desde el portal** paga en línea.
- **Sin compatibilidad hacia atrás:** el sistema aún no sale a producción, así que no se contemplan compras previas.
- **Pagos en revisión:** los resuelve el `admin_condominio` (o el `super_admin`).

## Capabilities

### New Capabilities

- `pagos-en-linea`: pasarelas por condominio, credenciales cifradas, comisión, intenciones, adaptadores Flow y Khipu, retorno y webhook, confirmación idempotente, conciliación y pantalla de resultado.

### Modified Capabilities

- `rifas-solidarias`: forma de pago `en_linea`, reserva de números durante el pago, aplicación tardía o revisión, y bloqueo del cierre con pagos en curso.

## Impact

- **Backend:**
  - Modelos y migración `pasarelas_pago`, `intenciones_pago`; `compras_rifa.intencion_pago_id`; CHECK de `rifas.medios_pago` ampliado con `en_linea`.
  - `services/pagos/` (cifrado, contrato, adaptadores `flow.py` y `khipu.py`, flujo, conciliación, registro de consumidores) y `endpoints/pagos.py` y `endpoints/pasarelas.py`.
  - Tarea de conciliación en el `lifespan` (con candado de PostgreSQL, porque producción corre 2 workers).
  - Variables `PAGOS_CLAVE_MAESTRA` (obligatoria en producción, validada por `app.arranque`) y `URL_PUBLICA_PAGOS` (solo desarrollo). Comando para rotar la clave maestra.
  - Dependencia nueva: `cryptography` (AES-256-GCM).
- **Frontend:**
  - Página de administración "Pasarelas de pago" (menú Administración).
  - `CompraPanel` con dos opciones, "Transferencia" y "Pago en línea", más la selección de pasarela con su recargo (se salta si hay una sola).
  - Página pública de resultado `/pagos/:id/resultado`.
- **Infra:** `frontend/nginx.prod.conf` expone `/api/v1/pagos/retorno/*` y `/api/v1/pagos/webhook/*` con límite por IP; `.env.prod.example` y `DEPLOY.md` documentan las variables nuevas.
- **Capacitación:** el recorrido de rifas del comunero agrega el pago en línea, y la administración tiene un recorrido para configurar una pasarela.
- **Docs:** `docs/rifas.md` y un `docs/pagos-en-linea.md` nuevo (pruebas en el sandbox de Flow y en DemoBank de Khipu, túnel en desarrollo).
