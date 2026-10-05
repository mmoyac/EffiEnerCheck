# Despliegue de EnerCheck en el VPS de effi4tech

Guía de operación del pipeline de CI/CD (`.github/workflows/deploy.yml`) y de los pasos manuales, que se hacen una sola vez.

- **Producción:** `https://enercheck-santalaura.effi4tech.cl`, en el VPS compartido `168.231.96.205`, detrás del `nginx_proxy`.
- **Ramas:** se trabaja en `develop`, donde cada push corre solo los chequeos. Un push a `main` despliega a producción después de tu aprobación. `main` queda solo para producción.
- **Archivos en el VPS:**
  - El pipeline crea `/root/docker/enercheck/` y copia ahí `docker-compose.prod.yml` y `.env.prod.example` en cada deploy.
  - Quedan a mano solo el `.env`, que tiene los secretos (§3.3), y el vhost del nginx compartido (§3.4).

Cada comando indica dónde se ejecuta:

- **[PC]:** tu equipo, en PowerShell, desde la raíz del repo.
- **[VPS]:** el servidor (`ssh root@168.231.96.205`).
- **[GitHub]**, **[Cloudflare]** y **[Docker Hub]:** su interfaz web.

---

## Qué hace el pipeline

| Evento | Jobs |
|---|---|
| Push a `develop` o PR a `develop` o `main` | `checks · backend`, `checks · frontend` y `checks · landing` |
| Push a `main` | Los mismos chequeos → **espera tu aprobación** → `build + deploy (producción)` |

- **`checks · backend`:**
  - Usa un Postgres 16 de servicio.
  - Corre `python -m app.arranque` y el seeder de desarrollo **dos veces**, para probar que las migraciones y los seeds son idempotentes.
  - Después corre `pytest`, verifica que `main` importe y ejecuta `pip-audit`.
- **`checks · frontend` y `checks · landing`:** en cada aplicación, `npm ci`, `npm audit --omit=dev --audit-level=high` y `npm run build`, que incluye `tsc`.
- **`build + deploy`:**
  1. Construye `enercheck-backend`, `enercheck-frontend` (portal) y `enercheck-landing` con su `Dockerfile.prod`, usando caché gha.
  2. Las escanea con Trivy: una vulnerabilidad CRITICAL **con parche** detiene el deploy.
  3. Publica las imágenes en Docker Hub con las etiquetas `latest` y SHA del commit.
  4. Por SSH en el VPS:
     - Crea `/root/docker/enercheck/` si no existe y deja ahí el compose y el `.env.prod.example` del commit. Viajan en base64 dentro del mismo `ssh-action`, sin otra action de terceros.
     - **Se detiene sin tocar nada** si no hay `.env`, si quedan valores `CAMBIAR_*` o si el compose no es válido con ese `.env`.
     - Respalda la base, los archivos y el compose vigente. Si el respaldo falla, no despliega.
     - Instala el compose nuevo y ejecuta `compose pull` y `up -d`.
     - Espera hasta 3 minutos a que `enercheck_backend` quede *healthy*. Si no queda, muestra sus últimas 100 líneas de log y falla.

La base usa la imagen oficial `postgres:16-alpine`: no se construye ni se publica.

---

## 1. Credenciales (una vez)

| Credencial | Cómo se crea | Dónde queda |
|---|---|---|
| **Token de Docker Hub** | [Docker Hub] Account settings → Personal access tokens → *Generate*: `enercheck-github-actions`, permiso **Read & Write** | Secret `DOCKER_PASSWORD` de GitHub |
| **Llave SSH exclusiva de EnerCheck** | [PC] `ssh-keygen -t ed25519 -C "enercheck-deploy" -f $env:USERPROFILE\.ssh\enercheck_deploy` y luego `type $env:USERPROFILE\.ssh\enercheck_deploy.pub \| ssh root@168.231.96.205 "cat >> ~/.ssh/authorized_keys"` | Privada: secret `VPS_SSH_KEY` y tu PC. Pública: `authorized_keys` del VPS |

La llave es solo de EnerCheck. Para revocarla basta con borrar su línea de `authorized_keys`, y eso no afecta a EffiCheck ni a los demás proyectos.

## 2. GitHub (una vez)

**Rama `develop`:** [PC] `git push -u origin develop`.

**Environment `production`** ([GitHub] Settings → Environments → New environment → `production`):

- **Required reviewers:** `mmoyac`, con *Prevent self-review* desmarcado. Cada deploy espera tu aprobación.
- **Deployment branches and tags:** *Selected branches* → `main`.
- **Environment secrets**, no *Repository secrets*: así los workflows de `develop` y de los PR no los reciben.

| Secret | Valor |
|---|---|
| `DOCKER_USERNAME` | `mmoyac` |
| `DOCKER_PASSWORD` | El token de Docker Hub (no la contraseña) |
| `VPS_HOST` | `168.231.96.205` |
| `VPS_USERNAME` | `root` |
| `VPS_SSH_KEY` | Contenido completo de `enercheck_deploy`, con las líneas `BEGIN`/`END` ([PC] `Get-Content $env:USERPROFILE\.ssh\enercheck_deploy -Raw \| Set-Clipboard`) |
| `VPS_PORT` | `22` |

Los secretos de la aplicación (`SECRET_KEY`, `GEMINI_API_KEY`, la clave de la base y del super admin) **no van en GitHub**: viven solo en el `.env` del VPS (§3.3).

**Protección del repositorio público:**

| Dónde | Configuración |
|---|---|
| Settings → Rules → Rulesets → New branch ruleset `main` | Target: `main`. Activo, sin *bypass*. **Restrict deletions** y **Block force pushes**. Sin PR obligatorio (hay un solo desarrollador). Después del primer run en `develop`: **Require status checks to pass** con `checks · backend` y `checks · frontend` |
| Settings → Collaborators | Vacío: nadie más tiene permiso de escritura |
| Settings → Actions → General | *Workflow permissions*: **Read repository contents**. *Fork pull request workflows*: **Require approval for all outside collaborators** |
| Settings → Code security | **Dependabot alerts**, **Secret scanning** con **Push protection** y **Private vulnerability reporting** |
| Tu cuenta de GitHub, Docker Hub y Cloudflare | **2FA** activo |

## 3. VPS (una vez)

**No se toca nada de los otros proyectos**: ni sus carpetas, ni sus vhosts, ni la red `general-net`, que ya existe y nunca se crea ni se recrea. EnerCheck vive solo en `/root/docker/enercheck/` y en su vhost `enercheck.conf`.

**3.1 Revisar el entorno** [VPS]:

```sh
docker network inspect general-net --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'   # → FORWARDED_ALLOW_IPS (hoy 172.18.0.0/16)
ls /root/docker/nginx-proxy/conf.d/ | grep -i enercheck      # no debe existir otro enercheck*.conf
ls /root/docker/ | grep -i enercheck                          # la carpeta no debe existir todavía
docker ps -a --format '{{.Names}}' | grep -i enercheck        # no debe haber contenedores enercheck_*
```

**3.2 Carpeta del proyecto.** La crea el primer deploy (§5): `/root/docker/enercheck/`, con permisos 700, `docker-compose.prod.yml` y `.env.prod.example`. Como todavía no hay `.env`, ese primer run se detiene ahí sin levantar nada.

**3.3 El `.env` de producción** [VPS]. Se crea en el servidor a partir del ejemplo, después del primer run, y nunca sale de ahí:

```sh
cd /root/docker/enercheck
cp .env.prod.example .env && chmod 600 .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"    # repetir para cada secreto
nano .env                                                         # reemplazar TODOS los CAMBIAR_*
grep -n CAMBIAR .env || echo "sin valores de ejemplo"
```

- **`POSTGRES_PASSWORD` y `SECRET_KEY`:** un secreto generado para cada uno. La clave de la base solo se usa al crear el volumen; cambiarla después en el `.env` no cambia la base.
- **`SUPERADMIN_EMAIL` y `SUPERADMIN_PASSWORD`:** tu acceso de super admin, con al menos 12 caracteres. Se crea solo si no existe ninguno.
  - Usa un correo **distinto** al de tu fila de la planilla de residentes, por ejemplo `mmoyainfo+admin@gmail.com`. Si es el mismo, la carga de §6 no puede asignarte la parcela 23.
- **`GEMINI_API_KEY`:** la clave de Google AI Studio para el OCR de boletas.
- **`FORWARDED_ALLOW_IPS`:** la subred de §3.1.
- **El backend no arranca** si queda algún `CAMBIAR_*`, si `SECRET_KEY` mide menos de 32 caracteres o si alguna cuenta tiene la clave pública del seed (`admin123`).

**3.4 Vhost en el nginx compartido** [PC] y luego [VPS]:

```powershell
scp infra/nginx/enercheck.conf root@168.231.96.205:/root/docker/nginx-proxy/conf.d/enercheck.conf
```

```sh
docker exec nginx_proxy nginx -t && docker exec nginx_proxy nginx -s reload
```

- Si `nginx -t` falla, **no recargues**: los demás sitios siguen funcionando con la configuración anterior. Corrige el archivo, o quita `enercheck.conf`, y vuelve a probar.
- Hasta que los contenedores existan, `enercheck-santalaura` responde 502, y eso no afecta a nadie más.
- El vhost termina TLS con el wildcard `*.effi4tech.cl` (`effi4tech.cl-0001`). Los contenedores de EnerCheck no manejan certificados.

## 4. DNS (una vez)

[Cloudflare] Registro **A**, nombre `enercheck-santalaura`, valor `168.231.96.205`, en modo **DNS only (nube gris)**.

> ⚠️ Con el proxy de Cloudflare activo (nube naranja), nginx vería la IP de Cloudflare y no la del usuario: el límite de intentos de login (10 por minuto por IP) bloquearía a todos a la vez.

## 5. Primer deploy

1. Completa las secciones 1, 2, 3.1, 3.4 y 4.
2. [PC] `git push origin develop` y espera los chequeos en verde en [GitHub] Actions.
3. [PC] `git push origin develop:main`. En [GitHub] Actions, el run de `main` queda en **Review deployments**: apruébalo.
4. Las imágenes se publican en Docker Hub. El primer push crea solo los repositorios `mmoyac/enercheck-backend`, `mmoyac/enercheck-frontend` y `mmoyac/enercheck-landing`, públicos salvo que tu cuenta tenga otro valor por defecto.
5. El job crea la carpeta en el VPS y **falla a propósito** con «Falta /root/docker/enercheck/.env». Crea el `.env` (§3.3).
6. En [GitHub] Actions abre ese run y usa **Re-run failed jobs**: vuelve a pedir tu aprobación y ahora sí despliega.
7. El backend crea el esquema, los roles, los menús y el super admin en su primer arranque. Para revisarlo: [VPS] `docker logs enercheck_backend | head -20`.
8. Abre `https://enercheck-santalaura.effi4tech.cl/` y entra con `SUPERADMIN_EMAIL`.
9. Haz la carga inicial de residentes (§6).

Flujo de trabajo habitual:

```powershell
git checkout develop
# … cambios y commits …
git push origin develop          # corren los checks; build-and-deploy queda "skipped"
git push origin develop:main     # con develop en verde: despliega (tras tu aprobación)
```

## 6. Carga inicial de residentes (una vez)

Las parcelas y los parceleros se cargan desde `docs/planillas/MATRIZ RESIDENTES.xlsx`.

> **La planilla tiene datos personales.** Está en `.gitignore` y nunca va al repo ni a la imagen. En el VPS vive solo mientras dura la carga.

[PC]:

```powershell
scp "docs/planillas/MATRIZ RESIDENTES.xlsx" root@168.231.96.205:/root/docker/enercheck/residentes.xlsx
```

[VPS]:

```sh
cd /root/docker/enercheck && chmod 600 residentes.xlsx
docker cp residentes.xlsx enercheck_backend:/tmp/residentes.xlsx

# 1. Simular: muestra cuántas parcelas, usuarios y asignaciones se crearían, sin guardar nada
docker exec enercheck_backend python -m app.db.cargar_residentes /tmp/residentes.xlsx \
  --condominio "Santa Laura" --rut <RUT de la comunidad> --simular

# 2. Cargar: pide por teclado la clave inicial de los residentes (-it para que no quede en los logs)
docker exec -it enercheck_backend python -m app.db.cargar_residentes /tmp/residentes.xlsx \
  --condominio "Santa Laura" --rut <RUT de la comunidad>

# 3. Borrar la planilla del contenedor y del VPS
docker exec -u 0 enercheck_backend rm -f /tmp/residentes.xlsx
shred -u residentes.xlsx
```

La planilla actual crea **53 parcelas y 69 parceleros**:

- **Parceleros:** uno por cada correo, sin importar si la fila dice Dueño, Arrendatario o Familiar. Cada uno queda asignado a su unidad, con el teléfono normalizado a `56XXXXXXXXX`.
- **Propietario de la parcela:** el primer «Dueño» de la unidad.
- **Avisos:** el comando lista las filas omitidas, los teléfonos inválidos y los correos que ya pertenecen a otra cuenta.

La carga es idempotente: si la planilla se actualiza, se puede volver a correr. Solo agrega lo que falta y no cambia claves ni datos existentes, salvo completar un teléfono vacío.

**Después de la carga**, desde la app con el super admin:

1. Crea las cuentas del personal, que no vienen en la planilla: `admin_condominio`, los lectores y la cuenta compartida de `porteria`.
2. Comunica a los residentes la clave inicial por un canal privado.

> ⚠️ **Todos los residentes parten con la misma clave inicial** y la aplicación todavía no permite que cada uno cambie la suya. Solo puede cambiarla un administrador, desde **Usuarios**. Mientras no exista ese cambio, cualquiera que conozca la clave inicial y el correo de un vecino puede entrar como él.

> ⚠️ **Primer período en producción:** las lecturas se generan con `lectura_anterior = 0`, porque no hay un período previo. Antes de calcular, la lectura anterior de cada parcela tiene que ser la última lectura real. Hoy la interfaz la muestra pero no permite editarla; solo la API la acepta (`PATCH /api/v1/lecturas/{id}` con `lectura_anterior`).

## 7. Respaldos

**Antes de cada deploy** (automático):

- El pipeline guarda, con el mismo prefijo y permisos 600:
  - la base: `backups/predeploy-<fecha>-<sha>.dump`;
  - los archivos, es decir las imágenes de boletas y los vouchers: `backups/predeploy-<fecha>-<sha>.archivos.tar.gz`;
  - el compose vigente, para el rollback: `backups/predeploy-<fecha>-<sha>.compose.yml`.
- Conserva los 10 más recientes de cada tipo.
- Si cualquiera de los dos respaldos falla, **no se despliega**.

> Los respaldos incluyen los **vouchers de transferencia**, que son datos personales. `backups/` tiene permisos 700 y no sale del VPS.

> Las imágenes de boletas y los vouchers **no están en la base**: PostgreSQL guarda solo su ruta. Por eso la base y los archivos se restauran siempre juntos.

No hay respaldo diario ni copia fuera del VPS: queda pendiente.

**Restaurar** [VPS], con el backend detenido para que nadie escriba mientras tanto:

```sh
cd /root/docker/enercheck && docker stop enercheck_backend
docker exec -i enercheck_db pg_restore -U enercheck -d enercheck --clean --if-exists < backups/predeploy-X.dump
docker start enercheck_backend
docker exec -i enercheck_backend tar -C /app -xzf - < backups/predeploy-X.archivos.tar.gz
```

## 8. Claves y acceso de emergencia

**Cambiar la clave de una cuenta desde el servidor** (por ejemplo, si olvidaste la del super admin) [VPS]:

```sh
docker exec -it enercheck_backend python -m app.db.cambiar_clave --email <correo>
```

**Si el backend no arranca** con «N cuenta(s) tienen la clave pública del seed»:

- Significa que alguna cuenta quedó con `admin123`.
- El mensaje no lista los correos porque llega a los logs públicos de GitHub Actions.
- Con el backend detenido, lístalas y cámbialas con un contenedor de un solo uso [VPS]:

```sh
cd /root/docker/enercheck
docker compose -f docker-compose.prod.yml run --rm --entrypoint python backend -m app.db.cambiar_clave --expuestas
docker compose -f docker-compose.prod.yml run --rm --entrypoint python backend -m app.db.cambiar_clave --email <correo>
docker compose -f docker-compose.prod.yml up -d
```

## 9. Rollback

Cada imagen está publicada con el SHA de su commit: **un rollback no reconstruye nada**.

```sh
cd /root/docker/enercheck
TAG=<sha_anterior> docker compose -f docker-compose.prod.yml up -d
```

- Si el deploy nuevo cambió el compose, usa el de la versión anterior. Cada deploy lo guarda como `backups/predeploy-<fecha>-<sha>.compose.yml`:
  - `cp backups/predeploy-<fecha>-<sha_nuevo>.compose.yml docker-compose.prod.yml`, antes del `up`.
- El próximo deploy lo vuelve a reemplazar por el del commit.

> ⚠️ **Las migraciones no se revierten solas.** Si la versión nueva migró la base, restaura el respaldo previo a ese deploy (§7, `predeploy-<fecha>-<sha_nuevo>`) antes de levantar la imagen anterior. Lo escrito en producción entre el deploy y la restauración se pierde.

Para volver a `latest`, borra `TAG` o déjalo en `latest` en el `.env`, y ejecuta `docker compose -f docker-compose.prod.yml up -d`.

## 10. Probar la topología en local

> ⚠️ **Usa siempre otro nombre de proyecto (`-p`).** El compose de producción se llama `enercheck`, igual que el proyecto de desarrollo de esta carpeta. Sin `-p`, Compose **reemplaza los contenedores de desarrollo**. Los datos sobreviven, porque los volúmenes tienen otros nombres, pero hay que volver a levantar dev con `docker compose up -d --build`.

[PC], en una carpeta fuera del repo con una copia de `docker-compose.prod.yml` y un `.env` de prueba (a partir de `.env.prod.example`, con `DOCKER_USERNAME=local` y `TAG=ci`):

```powershell
docker network create general-net      # solo en tu PC; en el VPS ya existe y no se toca
docker build -f backend/Dockerfile.prod -t local/enercheck-backend:ci backend      # desde la raíz del repo
docker build -f frontend/Dockerfile.prod -t local/enercheck-frontend:ci frontend
docker build -f landing/Dockerfile.prod -t local/enercheck-landing:ci landing
# en la carpeta de prueba:
docker compose -p enercheck_prodlocal -f docker-compose.prod.yml up -d
docker compose -p enercheck_prodlocal -f docker-compose.prod.yml down -v
docker network rm general-net
```

Los contenedores usan `container_name` fijos (`enercheck_db`, `enercheck_backend`, `enercheck_frontend` y `enercheck_landing`), distintos de los de desarrollo (`enercheck-db-1`, …).

## 11. Dominio propio de un condominio (landing + portal)

Ejemplo con Santa Laura. Se hace **una vez por condominio** y no requiere desplegar código: los dominios y
la URL del portal son parámetros del condominio, y la landing (`enercheck_landing`) ya corre desde el
primer deploy.

| Nombre | Sirve | Vhost |
|---|---|---|
| `www.condominiosantalaura.cl` | Landing pública + `GET /api/v1/sitio` y logos | `infra/nginx/condominiosantalaura-landing.conf` |
| `condominiosantalaura.cl` | Redirige a `www` | el mismo |
| `portal.condominiosantalaura.cl` | Portal de administración y API completa | `infra/nginx/condominiosantalaura-portal.conf` |

> Desde `www` solo se alcanza `GET /api/v1/sitio` y `/uploads/condominios/`: el login y el resto de la
> API responden 404 en ese dominio.

1. **DNS** [NIC Chile]: registros **A** de `condominiosantalaura.cl`, `www` y `portal` hacia `168.231.96.205`.
   Espera a que resuelvan: [PC] `nslookup www.condominiosantalaura.cl`.
2. **Desafío HTTP para el certificado** [VPS]. Los vhosts definitivos referencian un certificado que aún
   no existe y `nginx -t` fallaría; primero se publica solo el puerto 80:

   ```sh
   cat > /root/docker/nginx-proxy/conf.d/condominiosantalaura-acme.conf <<'NGINX'
   server {
       listen 80;
       server_name condominiosantalaura.cl www.condominiosantalaura.cl portal.condominiosantalaura.cl;
       location /.well-known/acme-challenge/ { root /var/www/certbot; }
   }
   NGINX
   docker exec nginx_proxy nginx -t && docker exec nginx_proxy nginx -s reload
   ```

3. **Certificado** [VPS]: uno solo para los tres nombres, con el certbot webroot que ya renueva los
   certificados del proxy. Revisa primero cómo está montado `/var/www/certbot` en `nginx_certbot` y ajusta el
   comando si difiere:

   ```sh
   docker exec nginx_certbot certbot certonly --webroot -w /var/www/certbot      --cert-name condominiosantalaura.cl      -d condominiosantalaura.cl -d www.condominiosantalaura.cl -d portal.condominiosantalaura.cl
   ```

4. **Vhosts definitivos** [PC] y luego [VPS]:

   ```powershell
   scp infra/nginx/condominiosantalaura-landing.conf infra/nginx/condominiosantalaura-portal.conf root@168.231.96.205:/root/docker/nginx-proxy/conf.d/
   ```

   ```sh
   rm /root/docker/nginx-proxy/conf.d/condominiosantalaura-acme.conf
   docker exec nginx_proxy nginx -t && docker exec nginx_proxy nginx -s reload
   ```

   `condominiosantalaura-portal.conf` reutiliza la zona `enercheck_auth` de `enercheck.conf`: los dos
   archivos deben estar instalados.
5. **Parámetros del condominio** [portal, como super admin] → Condominios → editar Santa Laura:
   - **Dominios de la landing:** `condominiosantalaura.cl` (con o sin `www`, se reconocen igual).
   - **URL del portal:** `https://portal.condominiosantalaura.cl`.
   - Productos **Landing** y **Administración** marcados; logo y color institucional.
6. **Contenido de la landing:** `backend/app/sitio/contenido/santa-laura.json`. Debe incluir el RUT real de la
   comunidad en `ruts_comunidad` y no debe quedar ningún `[POR CONFIRMAR]` (`pytest -rx` los lista). Cambiar
   ese archivo sí requiere desplegar (ver `docs/sitio-publico.md`).
7. **Verificación** [PC]:

   ```powershell
   curl.exe -I https://condominiosantalaura.cl/                      # 301 → https://www.condominiosantalaura.cl/
   curl.exe -I https://www.condominiosantalaura.cl/                  # 200, con Content-Security-Policy
   curl.exe https://www.condominiosantalaura.cl/api/v1/sitio         # JSON con "portal_url"
   curl.exe -X POST https://www.condominiosantalaura.cl/api/v1/auth/token   # 404
   curl.exe -I https://portal.condominiosantalaura.cl/               # 200: el login del portal
   ```

`enercheck-santalaura.effi4tech.cl` sigue sirviendo el portal; puede quedar como alias o retirarse quitando
su vhost.

Un **condominio que solo contrata la administración** no necesita los pasos 2 a 4 de la landing: basta con
el vhost del portal (o el host de effi4tech) y su URL en los parámetros, para enlazarla desde su propia web.

