# Tasks

## 1. Modelo y migración

- [x] 1.1 En `Usuario`: `password_hash` nullable y `clave_cambiada_en` (TIMESTAMPTZ NULL). Modelo nuevo `EnlaceAcceso` (`models/enlace_acceso.py`, registrado en `db/base.py`) con `CHECK` del tipo, `token_hash` único e índice por `(usuario_id, tipo)`. Verificar que `alembic revision --autogenerate` genera solo esos cambios.
- [x] 1.2 Revisar a mano la migración y aplicarla en desarrollo. Verificar con `alembic upgrade head` → `downgrade -1` → `upgrade head` sin errores, y actualizar `schema.dbml`.

## 2. Seguridad y sesiones

- [x] 2.1 En `security.py`:
  - `validar_clave()`, con `CLAVES_CONOCIDAS` movidas desde `arranque.py`;
  - `iat` en `create_access_token`;
  - `verify_password` devuelve `False` con hash `None`.

  Verificar con pruebas unitarias: largo mínimo, clave conocida y hash `None`.
- [x] 2.2 `get_current_user` rechaza los tokens con `iat` anterior a `clave_cambiada_en`, y `PATCH /usuarios` con `password` actualiza `clave_cambiada_en`. Verificar con una prueba: login → cambio de clave por un admin → el token anterior da 401.
- [x] 2.3 Validadores de `UsuarioCreate` y `UsuarioUpdate`: contraseña opcional en el alta y con `validar_clave` si viene. Schema de salida con `estado` (`pendiente`/`activa`). Verificar con pruebas de alta sin clave (estado pendiente; el login da 401 genérico) y de clave débil (422).
- [x] 2.4 `arranque.usuarios_con_clave_conocida` ignora los NULL, y `cambiar_clave.py` usa `validar_clave`. Verificar que `python -m app.arranque` funciona con una cuenta pendiente en la base.

## 3. Enlaces y correo (backend)

- [x] 3.1 `services/enlaces.py`:
  - `emitir(db, usuario, tipo) -> token`: anula los vigentes y guarda el hash;
  - `consumir(db, token) -> EnlaceAcceso | None`;
  - `url_de(usuario, tipo, token)`: `portal_url` del condominio o `PORTAL_URL_POR_DEFECTO`, con el token en `#`.

  Verificar con pruebas de uso único, vencimiento, anulación al reemitir y forma de la URL.
- [x] 3.2 `services/correo.py` (Resend por `httpx`, con timeout, sin lanzar excepciones ni registrar el cuerpo) y las plantillas de invitación y recuperación (HTML con escape y texto plano). Agregar `httpx` a `requirements.txt`, y `RESEND_API_KEY`, `EMAIL_REMITENTE` y `PORTAL_URL_POR_DEFECTO` a `config.py`. Verificar con pruebas que usan un transporte falso de `httpx`: éxito, rechazo y sin configurar.
- [x] 3.3 Endpoints `POST /usuarios/{id}/invitacion` y `POST /usuarios/invitaciones`, con tenant, 409 si la cuenta está activa, 503 si la masiva no tiene correo, y auditoría `INVITACION_ENVIADA` sin el token. Verificar con pruebas por rol, otro condominio, cuenta activa y conteo de la masiva.
- [x] 3.4 Endpoints `POST /auth/recuperar` (siempre 202, envío en `BackgroundTasks`, auditoría `RECUPERACION_SOLICITADA`), `POST /auth/verificar-enlace`, `POST /auth/establecer-clave` (política, uso único, `clave_cambiada_en`, `CLAVE_ESTABLECIDA`) y `POST /auth/cambiar-clave` (clave actual, token nuevo, `CLAVE_CAMBIADA`). Verificar con pruebas de todos los escenarios de la spec `acceso-por-enlace`, incluida la respuesta idéntica para un email inexistente.
- [x] 3.5 Comprobar que el token y la clave no aparecen en la auditoría ni en los logs, con una prueba que busca el token en `auditoria_logs.detalles`.

## 4. Cargas de producción sin clave

- [x] 4.1 `cargar_residentes` y `copiar_desde_desarrollo importar` crean las cuentas pendientes y ya no piden clave; se elimina `pedir_clave_inicial`. Ajustar sus pruebas: las cuentas cargadas quedan con `password_hash` NULL. Verificar que `pytest` completo pasa.

## 5. Frontend

- [x] 5.1 `api/auth.ts` y `api/usuarios.ts`: métodos nuevos. `types`: `estado` en el usuario. `utils/whatsapp.ts` extraído de `comprobante.ts`, sin cambiar el comportamiento de las rifas. Verificar con `npm run build`.
- [ ] 5.2 Página pública `EstablecerClave`, que atiende `/crear-clave` y `/restablecer-clave`:
  - lee el token del hash y lo borra de la URL;
  - verifica el enlace, pide la clave dos veces y muestra los estados de enlace inválido y de éxito.

  Rutas públicas en `App.tsx`. Verificar en el navegador con un enlace real de desarrollo.
- [ ] 5.3 "¿Olvidaste tu clave?" en `Login.tsx` y "Cambiar mi clave" en el `Header`, que guarda el token nuevo. Verificar en el navegador que el cambio mantiene la sesión y cierra otra sesión abierta.
- [ ] 5.4 `Usuarios.tsx`: columna Estado, *Invitar* / *Reenviar* con el panel de resultado (correo, *WhatsApp*, *Copiar enlace*), *Invitar a todos los pendientes (N)* con confirmación y contraseña opcional en el alta. Verificar en el navegador con usuarios pendientes y activos.

## 6. Infraestructura y documentación

- [x] 6.1 En `frontend/nginx.prod.conf`, la zona `enercheck_auth` en `recuperar`, `verificar-enlace` y `establecer-clave`. Verificar con `nginx -t` y una ráfaga local que produzca 429.
- [x] 6.2 Agregar `RESEND_API_KEY`, `EMAIL_REMITENTE` y `PORTAL_URL_POR_DEFECTO` a `.env.prod.example`. En `DEPLOY.md`: Resend (cuenta, verificación del dominio en Cloudflare, API key en Dokploy); el §6 sin clave inicial y con "Invitar a todos los pendientes"; y el aviso de rollback con cuentas pendientes. Actualizar `CLAUDE.md` (estructura, endpoints y patrón de enlaces). Verificar con `grep` que no queden menciones a la "clave inicial" de los residentes.

## 7. Puesta en marcha

- [ ] 7.1 CI en verde en `develop`, merge a `main` y aprobación. Verificar que el backend queda sano y que la migración se aplicó.
- [ ] 7.2 Con el usuario: cuenta en Resend, verificación de `comunidadsantalaura.cl` en Cloudflare, API key y `EMAIL_REMITENTE` en Dokploy, y Deploy. Verificar con "¿Olvidaste tu clave?" del super admin que llega el correo y que el enlace funciona.
- [ ] 7.3 Archivar `migrar-produccion-dokploy` y luego este cambio, y ejecutar `openspec validate --specs --strict` en verde.
