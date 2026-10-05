# Design

## Context

- **Servidor nuevo:** VPS Contabo con Ubuntu 24.04 y Dokploy v0.30.8. Dokploy funciona como servicio Swarm y su proxy de entrada es Traefik, con Let's Encrypt.
  - Ya están en marcha `dokploy.comunidadsantalaura.cl` y `n8n.comunidadsantalaura.cl`.
  - El servidor ya está endurecido: SSH solo con llave, `ufw` con 22/80/443 y fail2ban.
- **Red `dokploy-network`:** es overlay y attachable (`10.0.1.0/24`), y la comparten todos los proyectos del servidor.
- **Cómo despliega Dokploy un compose:** lo guarda, le inyecta las etiquetas de Traefik para los dominios definidos en su UI y ejecuta `docker compose -p <app> -f <archivo> up -d --build --remove-orphans`. **No hace `pull`**: si la etiqueta de la imagen no cambia, sigue corriendo la que ya está descargada.
- **API de Dokploy:** `POST /api/compose.update` y `POST /api/compose.deploy` (encabezado `x-api-key`). El deploy queda **encolado**: la respuesta no indica si la aplicación quedó sana.
- **Lo que el `nginx_proxy` de effi4tech hacía y hay que reubicar** (archivos de `infra/nginx/`):
  - TLS;
  - encabezados de seguridad;
  - CSP de la landing;
  - lista blanca de rutas de la landing;
  - `limit_req` al login;
  - `client_max_body_size 12m` y timeouts del OCR;
  - `X-Forwarded-Host`, que la API usa para resolver el condominio de la landing.

## Goals / Non-Goals

**Goals**
- Que lo desplegado sea siempre una imagen identificada por commit, nunca `latest`.
- Que la seguridad HTTP de la aplicación esté versionada en el repositorio y viaje con las imágenes.
- Que el pipeline tenga el mínimo acceso posible al servidor.

**Non-Goals**
- Despliegues sin corte (blue/green). Se acepta el reinicio de unos segundos de `up -d`.
- Respaldos fuera del servidor.
- Escalar a varios nodos Swarm.
- Usar el proxy de Cloudflare (nube naranja). Se documenta qué cambiaría.

## Decisions

### 1. El compose se envía a Dokploy con las imágenes fijadas al commit

El pipeline lee `docker-compose.prod.yml` y reemplaza `${TAG:-latest}` por `${TAG:-<sha>}`. Luego lo sube con `compose.update` (origen *raw*) y llama a `compose.deploy`.

- Una etiqueta nueva obliga a `up -d` a descargar la imagen, así se resuelve que Dokploy no haga `pull`.
- El compose del repositorio sigue siendo la fuente de verdad.
- **Rollback:** se define `TAG=<sha anterior>` en el Environment de Dokploy y se presiona Deploy. Para volver al flujo normal, se borra `TAG`.

*Alternativas descartadas*
- `pull_policy: always` con `latest`: no deja claro qué corre y el rollback depende de que exista la etiqueta.
- Conectar Dokploy a GitHub: exigiría construir en el VPS, lo que está prohibido por decisión del usuario.
- El webhook genérico de Dokploy: está pensado para eventos de git y no permite enviar el compose.

### 2. El acceso del pipeline al servidor: llave SSH con comando forzado

Se agrega en el servidor una llave dedicada al CI con `command="/opt/enercheck/bin/enercheck-ci",restrict` en `authorized_keys`. El script `enercheck-ci` se versiona en `infra/servidor/` y solo acepta dos órdenes:
- `respaldar <sha>`: hace lo mismo que el bloque actual del workflow (`pg_dump -Fc`, `tar` de `uploads`/`privado` y copia del compose vigente, obtenida desde la API de Dokploy) y conserva 10 respaldos.
- `esperar-sano <sha>`: espera hasta 3 minutos a que `enercheck_backend` use la imagen `…:<sha>` y quede `healthy`. Si no ocurre, imprime `docker logs --tail 100` y falla.

Aunque esa llave se filtre, no da una shell. El SHA se valida con `^[0-9a-f]{40}$` antes de usarlo.

*Alternativa descartada:* la llave root sin restricción, como hoy. Expone todo el servidor y los otros proyectos.

### 3. El nginx de cada imagen hace el proxy y la seguridad; Traefik solo hace host → contenedor

`frontend/nginx.prod.conf` y `landing/nginx.prod.conf` incorporan las reglas que hoy están en `infra/nginx/`, más estos ajustes:

- **`set_real_ip_from 10.0.1.0/24` + `real_ip_header X-Forwarded-For`:** Traefik reescribe ese encabezado con la IP del cliente, porque no confía en encabezados que vengan de fuera. Así `limit_req` y la API ven la IP real. Hacia la API se envía `X-Forwarded-For $remote_addr`, ya resuelta.
- **Encabezados de seguridad en `include /etc/nginx/snippets/seguridad.conf`:** en nginx, un `add_header` dentro de un `location` anula los heredados del `server`. Por eso el snippet se incluye en el `server` y en cada `location` que define su propio `Cache-Control`.
- **`limit_req_zone`:** se declara al comienzo del archivo de `conf.d/`, que nginx incluye en el contexto `http`.
- **El backend se alcanza por su nombre de contenedor** (`enercheck_backend:8000`) mediante `resolver 127.0.0.11` y una variable. Así nginx arranca aunque el backend todavía no esté, y no colisiona con un servicio `backend` de otro proyecto en `dokploy-network`.
- **Redirección `www` → apex en la landing:** `if ($host ~* ^www\.(.+)$) { return 301 https://$1$request_uri; }`. Es genérica y sirve para cualquier condominio sin escribir el dominio en la imagen.
- **HSTS sin `includeSubDomains`:** con ese parámetro, el navegador forzaría HTTPS en subdominios del condominio que no controlamos.

*Alternativa descartada:* middlewares y reglas por ruta en etiquetas de Traefik. Quedarían fuera de las imágenes, repartidas entre el compose y la UI de Dokploy, y no se pueden probar en local.

### 4. Redes del compose

| Servicio | Redes |
|---|---|
| `db` | `interna` (`internal: true`) |
| `backend` | `interna` y `dokploy-network` (sale a Gemini y recibe a los nginx) |
| `frontend`, `landing` | `dokploy-network` |

- Ningún servicio declara `ports`.
- `FORWARDED_ALLOW_IPS=10.0.1.0/24`.
- Se mantienen `container_name: enercheck_*` y los volúmenes con nombre fijo. Dokploy advierte sobre `container_name`, pero el script del CI y los respaldos dependen de esos nombres. En un servidor de un solo nodo no hay conflicto.

### 5. Dominios en la UI de Dokploy, no en el compose

| Dominio | Servicio | Puerto |
|---|---|---|
| `comunidadsantalaura.cl`, `www.comunidadsantalaura.cl` | `landing` | 8080 |
| `portal.comunidadsantalaura.cl` | `frontend` | 8080 |

Todos con HTTPS y certificado Let's Encrypt. Dokploy inyecta las etiquetas de Traefik en cada deploy. Agregar un condominio con dominio propio no exige cambiar el repositorio.

### 6. Carga inicial: exportar en local e importar dentro del contenedor

El script `app/db/copiar_desde_desarrollo.py` tiene dos subcomandos:

- **`exportar --condominio "Santa Laura" --salida x.json`** (corre contra la base de desarrollo):
  - escribe el condominio (nombre, RUT, dirección, plan, color y módulos) y sus parcelas;
  - escribe sus `parcelero` con nombre, email, teléfono y parcelas asignadas;
  - excluye los emails definidos en `app/db/seeds/usuarios.py`.
- **`importar x.json --portal-url ... --dominio ... [--simular]`** (corre dentro de `enercheck_backend` en producción):
  - pide la clave inicial con `getpass` y la valida con la misma regla de `cargar_residentes`;
  - crea o completa los registros y no toca las cuentas existentes;
  - registra auditoría `CARGA_INICIAL`.

El JSON contiene datos personales: se transfiere con `scp` a una carpeta `700`, se borra después de importar y **nunca** se agrega al repositorio (regla en `.gitignore`).

*Alternativa descartada:* `pg_dump` de tablas sueltas. Arrastraría hashes de `admin123`, IDs y secuencias de desarrollo.

### 7. Respaldo diario

Un `cron` de root (03:30 hora de Chile) ejecuta `enercheck-ci respaldar diario`, el mismo script con un prefijo distinto. Conserva 14 copias diarias, separadas de las 10 pre-deploy. Carpeta: `/opt/enercheck/respaldos` (`700`).

## Risks / Trade-offs

- **[El deploy de Dokploy es asíncrono y puede quedar en cola o fallar sin aviso]** → `esperar-sano` verifica la etiqueta de la imagen en ejecución, no solo que esté sana. Si el deploy no ocurrió, la etiqueta no coincide y el pipeline falla.
- **[La API de Dokploy puede cambiar entre versiones]** → Se usan solo `compose.update`/`compose.deploy`, se fija el comportamiento en `DEPLOY.md` y antes de actualizar Dokploy se prueba con un deploy manual.
- **[La API key de Dokploy da control total del panel]** → Se guarda solo en el environment `production` de GitHub, se crea con un usuario dedicado si la versión lo permite y se rota si el repositorio expone algo.
- **[Cloudflare con proxy activado cambiaría la IP de origen]** → Hoy se usa solo DNS. Si se activa el proxy, hay que confiar en los rangos de Cloudflare y usar `CF-Connecting-IP`. Queda documentado.
- **[Los respaldos viven en el mismo disco]** → Se acepta por ahora (fuera de alcance). `DEPLOY.md` indica cómo bajarlos con `scp`.
- **[Primer deploy sin base: `respaldar` debe tolerarlo]** → Si `enercheck_db` no existe, el script lo informa y sigue (lo cubre la spec).

## Migration Plan

1. Implementar en `develop` y probar el compose y los nginx en local con `-p enercheck_prodlocal`. Verificar la lista blanca de la landing, el 429 del login y los encabezados.
2. En el servidor: instalar `infra/servidor/` en `/opt/enercheck`, agregar la llave del CI con comando forzado y el cron.
3. En Dokploy: crear el proyecto y el compose *raw*, definir el Environment (secretos generados en el servidor) y los dominios, y obtener el `composeId` y la API key.
4. En GitHub (`production`): actualizar `VPS_*`, agregar `DOKPLOY_URL`, `DOKPLOY_API_KEY` y `DOKPLOY_COMPOSE_ID`, y eliminar lo que ya no se use.
5. Merge a `main` y aprobación. Primer deploy: sin respaldo, el backend migra la base vacía y crea el super admin.
6. Carga inicial: `exportar` en local, `scp`, `importar` en el contenedor y borrar el JSON.
7. Verificar: la landing, el portal, el login, el 404 de las rutas cerradas y el respaldo diario del día siguiente.

**Rollback:** el servidor nuevo no reemplaza nada en uso (effi4tech no tiene datos que conservar). Si algo falla antes del paso 6, se borra el proyecto en Dokploy y se repite. Después, se usa `TAG=<sha>` o se restauran los respaldos según `DEPLOY.md`.

## Open Questions

- Si Dokploy v0.30.8 permite API keys por usuario con permisos acotados o solo globales. Se averigua al crear la key y no cambia el diseño.
