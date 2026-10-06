# Design

## Context

- **Login hoy:** `POST /auth/token` (`OAuth2PasswordRequestForm`) emite un JWT sin estado con `sub`, `rol`, `condominio_id` y `exp`. `get_current_user` lo valida y consulta al usuario en cada petición; esa consulta permite revocar tokens sin una lista negra.
- **`usuarios.password_hash` es `NOT NULL`:**
  - `UsuarioCreate` exige `password`, con un mínimo de 8 caracteres en el validador actual.
  - `cargar_residentes` y `copiar_desde_desarrollo` piden una clave común por teclado.
  - `arranque.usuarios_con_clave_conocida` recorre todos los hashes.
- **Teléfonos:** las cuentas ya los tienen normalizados (`56XXXXXXXXX`), y el frontend ya arma enlaces `wa.me` en `utils/comprobante.ts`.
- **nginx del portal:** la zona `enercheck_auth` (10/min, ráfaga de 5) protege `/api/v1/auth/token`.
- **Producción en Dokploy:** el backend tiene salida a internet por `dokploy-network` (la usa para Gemini). El `.env` vive en el Environment de Dokploy.
- **Orden de archivado:** este cambio **modifica** el requisito "Carga inicial de producción sin datos de prueba", que agrega `migrar-produccion-dokploy`. Por eso hay que archivar primero ese cambio.

## Goals / Non-Goals

**Goals**
- Que ninguna clave pase por otra persona: ni por el administrador, ni por la consola de carga, ni por el chat.
- No revelar qué correos tienen cuenta.
- Que un enlace filtrado sirva lo menos posible: dura poco, se usa una vez y nunca queda en los logs.

**Non-Goals**
- Verificar la propiedad del teléfono.
- Bloquear la cuenta tras N intentos: basta el límite por IP de nginx.
- Cola de envíos o reintentos automáticos de correo.

## Decisions

### 1. Tabla `enlaces_acceso`, con el hash del token

| Columna | Detalle |
|---|---|
| `id` | |
| `usuario_id` | FK, `ON DELETE CASCADE` |
| `tipo` | `CHECK IN ('invitacion','recuperacion')` |
| `token_hash` | `CHAR(64) UNIQUE`: sha256 en hexadecimal |
| `creado_en` | |
| `expira_en` | |
| `usado_en` | NULL hasta que se usa |
| `anulado_en` | NULL salvo que lo anule un enlace nuevo |

- **Token:** `secrets.token_urlsafe(32)`, es decir, 256 bits.
- **sha256 sin sal:** el token ya es aleatorio y de alta entropía, así que basta un hash rápido para buscarlo y no hace falta bcrypt.
- **Enlace vigente:** `usado_en IS NULL AND anulado_en IS NULL AND expira_en > now()`.
- **Emisión de un enlace nuevo:** marca `anulado_en` en los vigentes del mismo usuario y tipo, dentro de la misma transacción.

*Alternativa descartada:* un JWT firmado como enlace. No permite el uso único ni la anulación sin guardar estado, y además es más largo.

### 2. Revocar sesiones con `clave_cambiada_en`

- Se agrega `usuarios.clave_cambiada_en TIMESTAMPTZ NULL`, y el JWT incluye `iat`.
- `get_current_user` rechaza con 401 si `iat < clave_cambiada_en`. Lo compara en segundos enteros, con margen de 1 s, porque `iat` es entero.
- `cambiar-clave` entrega un token nuevo, con `iat` posterior, para que la sesión en curso siga abierta.
- `PATCH /usuarios` con `password` también actualiza `clave_cambiada_en`.

*Alternativa descartada:* una lista negra de tokens. Requiere estado adicional, y la consulta al usuario ya ocurre en cada petición.

### 3. Correo con Resend por HTTP, en `services/correo.py`

- **Envío:** `POST https://api.resend.com/emails` con `httpx`, que se agrega a `requirements.txt` con versión fijada.
- **Interfaz:** `enviar(destino, asunto, texto, html, nombre_remitente) -> ResultadoEnvio(ok, motivo)`.
  - Nunca lanza excepciones hacia el endpoint.
  - Timeout de 10 s.
  - Registra solo `ok`/`motivo` y el id que devuelve Resend, nunca el cuerpo.
- **Sin `RESEND_API_KEY`:** `ok=False, motivo="no configurado"`. La invitación individual sigue funcionando y el administrador usa WhatsApp; la masiva responde 503 (ver spec).
- **Remitente:** `"<nombre del condominio> <EMAIL_REMITENTE>"`. Con el remitente `no-responder@comunidadsantalaura.cl`, el dominio se verifica en Resend con los registros SPF/DKIM en Cloudflare. Un condominio con dominio propio podría tener su remitente más adelante (fuera de alcance).
- **Plantillas:** una por tipo, en Python con `string.Template` y escape HTML del nombre. Incluyen una versión en texto plano y no cargan imágenes externas.

*Alternativas descartadas:* SMTP con `aiosmtplib`, que agrega dependencia y configuración sin aportar nada aquí; y el SDK oficial de Resend, que suma una dependencia para una sola llamada.

### 4. Endpoints

| Método y ruta | Acceso | Notas |
|---|---|---|
| `POST /usuarios/{id}/invitacion` | `AdminRequired` + tenant | 409 si la cuenta está activa. Devuelve `{enlace, correo_enviado, motivo}` |
| `POST /usuarios/invitaciones` | `AdminRequired`; `condominio_id` obligatorio para `super_admin` | Envía en serie, con una pausa corta entre correos para respetar los límites de Resend. Devuelve `{enviados, fallidos}` |
| `POST /auth/recuperar` | Público | Siempre 202. Si la cuenta existe y su condominio tiene `portal`, emite y envía. El tiempo de respuesta se iguala con un envío en segundo plano (`BackgroundTasks`), para no revelar por demora si la cuenta existe |
| `POST /auth/verificar-enlace` | Público | `{tipo, nombre}` o 410 |
| `POST /auth/establecer-clave` | Público | `{token, password}` → 204. 410 si el enlace no es válido; 422 si la clave no cumple la política |
| `POST /auth/cambiar-clave` | `CurrentUser` | `{actual, nueva}` → `{access_token}` |

El `admin_condominio` puede recibir el enlace de invitación porque ya podía fijar la clave de ese usuario con `PATCH`. No hay escalamiento de privilegios.

### 5. Política de claves en un solo lugar

`security.validar_clave(clave)` exige `len >= 10` y que la clave no esté en `CLAVES_CONOCIDAS`, que se mueve de `arranque.py` a `security.py`. La usan:
- los validadores de Pydantic de `UsuarioCreate`/`UsuarioUpdate`;
- `establecer-clave` y `cambiar-clave`;
- `cambiar_clave.py` (consola).

Las semillas de desarrollo siguen escribiendo el hash de `admin123` directamente, porque no pasan por la API.

### 6. Cuentas pendientes

- `password_hash` NULL equivale a pendiente.
- `verify_password` devuelve `False` si el hash es NULL, así el login responde el mismo 401 genérico.
- El estado (`pendiente`/`activa`) se calcula en el schema de salida y no se guarda en una columna.
- `arranque.usuarios_con_clave_conocida` ignora los NULL.
- `cargar_residentes` y `copiar_desde_desarrollo importar` dejan de pedir la clave y crean las cuentas con `password_hash=None`. La regla de clave inicial desaparece de ambos.

### 7. Frontend

- **Rutas públicas** `/crear-clave` y `/restablecer-clave`, con un solo componente `EstablecerClave` parametrizado por tipo:
  - lee el token de `location.hash` y lo borra de la barra de direcciones con `history.replaceState` apenas lo lee;
  - llama a `verificar-enlace`, muestra el nombre y pide la clave dos veces, con indicador de largo.
- **Login:** enlace "¿Olvidaste tu clave?", que abre un modal con el email.
- **Header:** "Cambiar mi clave" en el menú del usuario. Al terminar, guarda el token nuevo.
- **`Usuarios.tsx`:**
  - columna Estado (badge);
  - botón *Invitar* o *Reenviar* en las cuentas pendientes; al responder, muestra un panel con "Correo enviado ✓ / no enviado: motivo", el botón *WhatsApp* y *Copiar enlace*;
  - botón superior *Invitar a todos los pendientes (N)*, con confirmación.
- **`utils/whatsapp.ts`:** extraer de `comprobante.ts` el armado de `wa.me/<telefono>?text=` para reutilizarlo.
- **Formulario de alta:** el campo contraseña queda opcional, con la ayuda "déjala vacía para enviar una invitación".

### 8. nginx

En `frontend/nginx.prod.conf`, las rutas `location = /api/v1/auth/recuperar`, `/verificar-enlace` y `/establecer-clave` usan la misma zona `enercheck_auth`, que limita por IP. La landing no expone ninguna de ellas, porque mantiene su lista blanca.

## Risks / Trade-offs

- **[El correo cae en spam o no llega]** → Se mitiga con el dominio verificado (SPF/DKIM), el texto plano y sin imágenes; además está el reenvío por WhatsApp y "¿Olvidaste tu clave?". El panel muestra el motivo si Resend rechaza.
- **[Un enlace de invitación reenviado por WhatsApp a la persona equivocada]** → Dura 7 días y es de un solo uso. Si alguien lo usa indebidamente, el vecino verdadero lo nota al recibir un enlace usado y el administrador reenvía la invitación. Queda auditado.
- **[El administrador ve el enlace]** → Es equivalente a su facultad actual de fijar claves; queda auditado como `INVITACION_ENVIADA`.
- **[Resend caído en la invitación masiva]** → Cada fallo se cuenta y se informa; volver a ejecutar reenvía solo a los que siguen pendientes, y anula sus enlaces anteriores.
- **[Diferencia de tiempos en `recuperar` revela cuentas]** → El envío va en segundo plano y la respuesta es inmediata en ambos casos.
- **[`iat` en segundos frente a `clave_cambiada_en` en microsegundos]** → Se compara con la hora truncada al segundo. Un token emitido en el mismo segundo del cambio se acepta; el riesgo es despreciable.

## Migration Plan

1. Migración Alembic: `password_hash` nullable, `clave_cambiada_en` y `enlaces_acceso`. No hay datos que transformar: producción no tiene usuarios salvo el super admin.
2. Desplegar con `RESEND_API_KEY` vacío: todo funciona y las invitaciones se envían por WhatsApp.
3. Cuenta en Resend: verificar `comunidadsantalaura.cl` (registros DNS en Cloudflare), crear la API key, cargarla en el Environment de Dokploy y presionar Deploy.
4. Archivar `migrar-produccion-dokploy` y luego este cambio.
5. Cargar Santa Laura (todas las cuentas quedan pendientes), probar con una cuenta propia y luego *Invitar a todos los pendientes*.

**Rollback:** la imagen anterior no entiende `password_hash` NULL. Si se vuelve atrás después de la carga, hay que restaurar el respaldo pre-deploy (DEPLOY.md §8). Antes de la carga, el rollback es directo.

## Open Questions

- El texto final de los correos y del mensaje de WhatsApp: se ajusta en la implementación con la directiva, sin cambiar la spec.
