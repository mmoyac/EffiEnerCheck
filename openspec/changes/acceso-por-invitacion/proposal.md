# Proposal

## Why

Hoy todas las cuentas de residentes nacen con **la misma clave inicial**. Ningún usuario puede cambiar su propia clave: solo un administrador puede hacerlo, desde Usuarios. Tampoco existe "olvidé mi clave". En la práctica, cualquier vecino que conozca la clave común y el correo de otro puede entrar como él y ver su liquidación, sus compras y su teléfono.

Producción ya está desplegada, pero Santa Laura todavía no está cargada. Es el momento de partir bien: cada persona crea su propia clave desde un enlace personal, y nadie más la conoce.

## What Changes

- **Invitación por enlace de un solo uso.** Un administrador (`super_admin`, o `admin_condominio` sobre su condominio) invita a un usuario, o a todos los pendientes de su condominio.
  - El usuario recibe un enlace "crea tu clave", que vence en 7 días.
  - El enlace llega **por correo** (Resend, remitente del dominio verificado).
  - Además, el administrador tiene un botón para enviarlo **por WhatsApp** (`wa.me`, con el teléfono del usuario).
- **"Olvidé mi clave" en el login.** Envía por correo un enlace que vence en 1 hora.
  - La respuesta es siempre la misma, exista o no la cuenta.
  - Tiene límite de frecuencia por IP.
- **"Cambiar mi clave"** para cualquier usuario con sesión: pide la clave actual.
- **Cuentas pendientes.** Una cuenta sin clave queda "invitación pendiente" y no puede iniciar sesión.
  - **BREAKING:** `usuarios.password_hash` admite NULL.
  - La contraseña deja de ser obligatoria al crear un usuario.
  - Las cargas de producción (`cargar_residentes`, `copiar_desde_desarrollo importar`) **dejan de pedir una clave inicial** y crean las cuentas pendientes.
- **Las sesiones abiertas se cierran** al establecer o cambiar la clave: los tokens emitidos antes del cambio dejan de valer.
- **Seguridad de los enlaces.**
  - Token aleatorio largo; solo se guarda su hash.
  - Un solo uso; emitir uno nuevo anula los anteriores del mismo tipo.
  - El token viaja en el **fragmento** de la URL (`#`), así no queda en los logs de los servidores ni en el `Referer`.
- **Política de clave única:** al menos 10 caracteres y ninguna clave conocida. Se aplica igual en invitación, recuperación, cambio propio y alta o edición por un administrador.
- **Pantalla Usuarios:**
  - estado de cada cuenta (pendiente o activa);
  - acciones *Invitar*, *Reenviar* y *WhatsApp*;
  - acción masiva *Invitar a todos los pendientes*.
- **Auditoría:** `INVITACION_ENVIADA`, `CLAVE_ESTABLECIDA`, `RECUPERACION_SOLICITADA` y `CLAVE_CAMBIADA`. El token y la clave nunca se registran.

Fuera de alcance:
- login con RUT;
- 2FA para usuarios;
- plantillas de correo editables desde el portal;
- envío automático de WhatsApp (el sistema solo arma el enlace `wa.me`).

## Capabilities

### New Capabilities

- `acceso-por-enlace`: ciclo de vida de los enlaces de invitación y recuperación (emisión, vigencia, uso único, anulación), envío por correo y WhatsApp, establecimiento y cambio de la propia clave, y política de claves.

### Modified Capabilities

- `autenticacion`:
  - las cuentas pendientes no inician sesión;
  - el token incluye su hora de emisión, y los emitidos antes del último cambio de clave se rechazan;
  - el cliente ofrece "olvidé mi clave", las páginas públicas para crear o restablecer la clave, y "cambiar mi clave".
- `gestion-usuarios`:
  - la contraseña es opcional al crear un usuario (sin ella, la cuenta queda pendiente);
  - el listado informa el estado de cada cuenta;
  - las claves que asigna un administrador cumplen la política.

## Impact

- **Base de datos:** migración con `usuarios.password_hash` nullable, `usuarios.clave_cambiada_en` y la tabla nueva `enlaces_acceso`.
- **Backend:**
  - endpoints nuevos en `auth.py` (`recuperar`, `verificar-enlace`, `establecer-clave`, `cambiar-clave`) y en `usuarios.py` (`{id}/invitacion` e `invitaciones`);
  - servicio de correo `services/correo.py` (Resend, por HTTP);
  - servicio `services/enlaces.py`;
  - `security.py` (`iat` en el token y política de clave);
  - `dependencies.py` (rechazo de tokens anteriores al cambio de clave);
  - `arranque.py` (cuentas sin clave);
  - `cargar_residentes.py` y `copiar_desde_desarrollo.py` (sin clave inicial).
- **Configuración:** `RESEND_API_KEY`, `EMAIL_REMITENTE` y `PORTAL_URL_POR_DEFECTO` en `.env.prod.example` y en el Environment de Dokploy. En Cloudflare, los registros DNS que pide Resend para `comunidadsantalaura.cl`.
- **nginx del portal:** límite de frecuencia para `auth/recuperar`, `auth/establecer-clave` y `auth/verificar-enlace`.
- **Frontend:**
  - rutas públicas `/crear-clave` y `/restablecer-clave`;
  - enlace "¿Olvidaste tu clave?" en `Login.tsx`;
  - "Cambiar mi clave" en el `Header`;
  - estado y acciones en `Usuarios.tsx`;
  - `utils/whatsapp` para el mensaje de invitación.
- **Docs:** `DEPLOY.md` §6 (la carga ya no pide clave y luego se invita) y la configuración de Resend.
