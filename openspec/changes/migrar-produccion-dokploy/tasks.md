# Tasks

## 1. Nginx de las imágenes (proxy y seguridad)

- [ ] 1.1 Crear `frontend/snippets/seguridad.conf` y `landing/snippets/seguridad.conf` con HSTS (sin `includeSubDomains`), `nosniff`, `X-Frame-Options DENY`, `Referrer-Policy` y `Permissions-Policy`. El portal permite `camera=(self)`; la landing además lleva la CSP estricta. Copiarlos a `/etc/nginx/snippets/` en cada `Dockerfile.prod`. Verificar que `docker build` de ambas imágenes termina bien.
- [ ] 1.2 En `frontend/nginx.prod.conf`:
  - agregar `limit_req_zone` del login, `set_real_ip_from 10.0.1.0/24` y `real_ip_header X-Forwarded-For`;
  - agregar `location = /api/v1/auth/token` con `limit_req`/429, `/api/` (12m, 120s) y `/uploads/`, con proxy a `enercheck_backend:8000` vía `resolver 127.0.0.11` y los encabezados `X-Forwarded-*`;
  - incluir el snippet en el `server` y en cada `location` con `add_header`.

  Verificar con `nginx -t` en la imagen.
- [ ] 1.3 En `landing/nginx.prod.conf`:
  - agregar la redirección `www` → apex, el real IP y `GET` solo para `= /api/v1/sitio` y `/uploads/condominios/`;
  - responder `404` a `/api/` y `/uploads/`;
  - incluir el snippet en cada `location` con `add_header`.

  Verificar con `nginx -t`.
- [ ] 1.4 Actualizar los comentarios de `frontend/Dockerfile.prod`, `landing/Dockerfile.prod` y `landing/nginx.conf`, que hoy apuntan al `nginx_proxy`/`infra/nginx`. Verificar con `grep -r "infra/nginx\|nginx_proxy" frontend landing` sin resultados.

## 2. Compose de producción

- [ ] 2.1 En `docker-compose.prod.yml`:
  - cambiar `general-net` por la red externa `dokploy-network`, con `backend` en `interna` y `dokploy-network` y `frontend`/`landing` solo en `dokploy-network`;
  - dejar ningún `ports` y `TAG` con el formato `${TAG:-latest}`, que el pipeline reemplaza;
  - actualizar el encabezado de comentarios (Dokploy, rollback por `TAG`).

  Verificar con `docker compose -f docker-compose.prod.yml config -q` usando un `.env` de ejemplo.
- [ ] 2.2 En `.env.prod.example`: quitar `CAMBIAR_*` de lo que gestiona Dokploy, poner `FORWARDED_ALLOW_IPS=10.0.1.0/24` y explicar `TAG` (vacío = commit desplegado; `<sha>` = rollback). Verificar que el compose valida con el ejemplo.
- [ ] 2.3 Prueba local con `-p enercheck_prodlocal` y una red `dokploy-network` creada a mano. Verificar con `curl`:
  - landing: `/api/v1/sitio` 200, `/api/v1/boletas/` 404, `/uploads/boletas/x` 404, encabezados y CSP presentes en `/` y en `/assets/...`, `www.` → 301;
  - portal: `/api/v1/auth/me` llega a la API; 20 POST rápidos a `/api/v1/auth/token` producen 429.

  Bajar el proyecto al terminar.

## 3. Script del servidor (respaldos y verificación)

- [ ] 3.1 Crear `infra/servidor/enercheck-ci` (bash, `set -eu`). Debe leer la orden de `$SSH_ORIGINAL_COMMAND` o de los argumentos y aceptar solo:
  - `respaldar <sha|diario>`: `pg_dump -Fc`, tar de `uploads`+`privado` y compose vigente. Conserva 10 pre-deploy y 14 diarios. Si la base no existe, lo informa y sigue. Si un volcado falla o queda vacío, falla;
  - `esperar-sano <sha>`: espera hasta 180 s la imagen `…:<sha>` en `enercheck_backend` con estado `healthy`; si no, `docker logs --tail 100` y falla.

  El SHA se valida con `^[0-9a-f]{40}$`. Verificar con `shellcheck` y ejecutando órdenes inválidas, que deben rechazarse.
- [ ] 3.2 Crear `infra/servidor/instalar.sh`: copia a `/opt/enercheck/bin`, crea `/opt/enercheck/respaldos` (700), instala el cron diario a las 03:30 (`TZ=America/Santiago`) y documenta la línea `command=...,restrict` de `authorized_keys`. Verificar que ejecutarlo dos veces no duplica el cron.
- [ ] 3.3 Eliminar `infra/nginx/`. Verificar que ningún archivo del repo lo referencia (`grep -r "infra/nginx"`).

## 4. Pipeline

- [ ] 4.1 En el job `build-and-deploy` de `.github/workflows/deploy.yml`, reemplazar el paso SSH por:
  1. `ssh … respaldar $SHA` con la llave de comando forzado y `known_hosts` fijado desde un secreto (sin `StrictHostKeyChecking=no`);
  2. generar el compose con `${TAG:-<sha>}` y enviarlo con `compose.update`, y luego `compose.deploy`, ambos con `curl --fail` y la key en el encabezado, sin imprimirla;
  3. `ssh … esperar-sano $SHA`.

  Los chequeos, Trivy y el push a Docker Hub se mantienen. Verificar con `actionlint` (o revisión manual de la sintaxis) que ningún paso hace `echo` de secretos.
- [ ] 4.2 Actualizar el comentario de cabecera del workflow y la lista de secretos del environment `production`:
  - siguen `DOCKER_USERNAME` y `DOCKER_PASSWORD`;
  - nuevos `VPS_HOST`, `VPS_PORT`, `VPS_SSH_KEY`, `VPS_KNOWN_HOSTS`, `DOKPLOY_URL`, `DOKPLOY_API_KEY` y `DOKPLOY_COMPOSE_ID`;
  - se elimina `VPS_USERNAME` si queda fijo.

  Verificar que cada secreto usado en el YAML aparece en la lista y en `DEPLOY.md`.

## 5. Carga inicial desde desarrollo

- [ ] 5.1 Crear `backend/app/db/copiar_desde_desarrollo.py` con `exportar`: condominio, módulos, color, parcelas y parceleros con teléfono y asignaciones. Excluye los emails de `app/db/seeds/usuarios.py` y no incluye hashes. Verificar contra la base de desarrollo que el JSON trae 53 parcelas, ningún email del seed y ningún campo `password_hash`.
- [ ] 5.2 Agregar `importar <json> --portal-url --dominio … [--simular]`:
  - pide la clave inicial con `getpass` y aplica la misma validación que `cargar_residentes`;
  - es idempotente por nombre de condominio, número de parcela y email;
  - no toca las cuentas existentes y registra la auditoría `CARGA_INICIAL`.

  Verificar con pruebas pytest: base vacía → crea todo; segunda ejecución → sin cambios; clave débil → no escribe; el JSON con un email del seed se ignora.
- [ ] 5.3 Agregar `*.carga.json` y la carpeta de exportación al `.gitignore`. Verificar con `git check-ignore`.

## 6. Documentación

- [ ] 6.1 Reescribir `DEPLOY.md` con:
  - arquitectura (Cloudflare → Traefik → nginx de las imágenes → API);
  - registros DNS y creación del proyecto compose *raw* en Dokploy (Environment, dominios, API key);
  - instalación de `infra/servidor/` y de la llave del CI;
  - secretos de GitHub, primer deploy y carga inicial paso a paso;
  - rollback por `TAG`, restauración de un respaldo y descarga de respaldos;
  - qué cambiar si se activa el proxy de Cloudflare.

  Verificar que cada comando del documento se ejecutó al menos una vez durante la migración.
- [ ] 6.2 Actualizar `CLAUDE.md` en la estructura (`infra/servidor/`, sin `infra/nginx/`), en CI/CD y en el comando de la carga inicial. Revisar `README.md` y `docs/` en busca de effi4tech, `condominiosantalaura.cl` y `general-net`. Verificar con `grep` que solo quedan referencias históricas intencionales (el enlace a effi4tech.cl en `Login.tsx` es la empresa desarrolladora y se mantiene).

## 7. Puesta en marcha (en el servidor, con el usuario)

- [ ] 7.1 Instalar `infra/servidor/` en el VPS, agregar la llave del CI con comando forzado y comprobar que `ssh -i llave_ci comunidad` sin orden se rechaza y que `respaldar <sha>` funciona con la base ausente.
- [ ] 7.2 Crear en Dokploy el proyecto compose *raw*, con un Environment cuyos secretos se generan en el servidor, los dominios `comunidadsantalaura.cl`, `www.` y `portal.` con HTTPS, y la API key. Cargar los secretos en el environment `production` de GitHub.
- [ ] 7.3 Merge de `develop` a `main`, aprobar y verificar el primer deploy: pipeline en verde, backend `healthy` con la imagen del commit y certificados válidos en los tres dominios.
- [ ] 7.4 Ejecutar la carga inicial: `exportar` en local, `scp`, `importar` en `enercheck_backend` (el usuario ingresa la clave) y borrar el JSON en ambos lados. Verificar los conteos en producción y el login de un parcelero.
- [ ] 7.5 Verificación integral: landing con el contenido de Santa Laura; `www` → apex; portal con el color institucional; 404 en las rutas cerradas de la landing; 429 en ráfagas de login; respaldo pre-deploy y diario presentes al día siguiente; `openspec validate --specs --strict` en verde.
