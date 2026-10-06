# Despliegue de EnerCheck en producción (Dokploy)

Producción corre en un VPS dedicado administrado con **Dokploy**:

- **Servidor:** Contabo, Ubuntu 24.04, IP `86.48.21.250`, alias SSH `comunidad`.
- **Dominio:** `comunidadsantalaura.cl` (registrado en NIC Chile, DNS en Cloudflare).

Las marcas **[PC]**, **[VPS]**, **[Dokploy]**, **[GitHub]** y **[Cloudflare]** indican dónde se ejecuta cada paso.

```
visitante ─HTTPS─▶ Traefik (Dokploy: TLS Let's Encrypt, dominio → contenedor)
                     ├─ comunidadsantalaura.cl, www.  ─▶ enercheck_landing  (nginx: solo GET /api/v1/sitio y /uploads/condominios/)
                     └─ portal.comunidadsantalaura.cl ─▶ enercheck_frontend (nginx: /api/, /uploads/, límite de login)
                                                              └──────────────▶ enercheck_backend ─▶ enercheck_db (red interna)
```

- **Traefik solo enruta por dominio.** Las reglas por ruta, los encabezados de seguridad (HSTS, CSP de la landing), el límite de intentos de login y la IP real del visitante los aplica el nginx de cada imagen:
  - `frontend/nginx.prod.conf` y `landing/nginx.prod.conf`;
  - `*/snippets/seguridad.conf`.

  Todo eso está versionado en el repo y viaja con las imágenes.
- **Nada publica puertos.** El servidor solo expone 22, 80 y 443 (`ufw`); SSH acepta solo llaves y hay fail2ban.
- **El VPS nunca construye imágenes.** Las construye y escanea GitHub Actions, se publican en Docker Hub y Dokploy solo las descarga.

---

## Qué hace el pipeline

`.github/workflows/deploy.yml`:

- **Push a `develop` o pull request:** solo los chequeos.
  - `pytest` contra Postgres, migraciones y seeds idempotentes, `pip-audit`;
  - `npm audit` y build del portal y de la landing.
- **Push a `main`:** chequeos y luego **aprobación manual** del environment `production`. Después:
  1. Build de las 3 imágenes y **Trivy**: una vulnerabilidad CRÍTICA con parche detiene el deploy (excepciones en `.trivyignore`).
  2. Push a Docker Hub con la etiqueta del commit y `latest`.
  3. **Respaldo previo** por SSH: `enercheck-ci respaldar <sha>`. Si falla, no se despliega.
  4. Envía el compose a Dokploy con las imágenes **fijadas al commit** (`${TAG:-<sha>}`, mediante `compose.update`) y llama a `compose.deploy`.
  5. Espera hasta 3 minutos con `enercheck-ci esperar-sano <sha>` a que `enercheck_backend` corra **esa** imagen y quede sano. Si no lo logra, el job falla y muestra el arranque del backend.

¿Por qué se fijan las imágenes al commit? Dokploy despliega con `docker compose up -d` **sin `pull`**: con `latest` seguiría corriendo la imagen anterior.

La llave SSH del pipeline tiene **comando forzado**: solo puede ejecutar `infra/servidor/enercheck-ci` (respaldar y esperar-sano), así que no abre una shell.

---

## 1. Cloudflare (una vez)

[Cloudflare] Registros A → `86.48.21.250`, con **Solo DNS** (nube gris): `comunidadsantalaura.cl`, `www`, `portal`, `dokploy` y `n8n`.

> Si algún día se activa el proxy de Cloudflare (nube naranja):
> - SSL/TLS debe estar en **Full (strict)**;
> - nginx debe confiar en los rangos de Cloudflare y leer `CF-Connecting-IP`; si no, el límite de login vería la IP de Cloudflare.

## 2. Servidor (una vez)

[PC]:

```powershell
scp infra/servidor/* comunidad:/tmp/enercheck-instalar/
ssh comunidad "bash /tmp/enercheck-instalar/instalar.sh && rm -rf /tmp/enercheck-instalar"
```

`instalar.sh` es idempotente y hace cuatro cosas:
- instala `/opt/enercheck/bin/enercheck-ci`;
- crea `/opt/enercheck/respaldos` (700);
- deja el servidor en hora `America/Santiago`;
- programa el respaldo diario a las 03:30.

**Llave del pipeline** [PC], de uso exclusivo del CI:

```powershell
ssh-keygen -t ed25519 -N '""' -C enercheck-ci@github-actions -f enercheck_ci
```

[VPS] Agrega a `/root/.ssh/authorized_keys` **una línea** con la parte pública:

```
command="/opt/enercheck/bin/enercheck-ci",restrict ssh-ed25519 AAAA... enercheck-ci@github-actions
```

Comprueba [PC]:
- `ssh -i enercheck_ci root@86.48.21.250` debe responder con el uso de `enercheck-ci`, no con una shell;
- `ssh -i enercheck_ci root@86.48.21.250 "respaldar diario"` debe funcionar, aunque la base todavía no exista.

## 3. Dokploy (una vez)

[Dokploy] `https://dokploy.comunidadsantalaura.cl`:

1. **Registro:** en Settings → Registry, agrega Docker Hub con el usuario `mmoyac` y un token de **solo lectura**. Es obligatorio si los repositorios de Docker Hub son privados; si son públicos, no hace falta.
2. **Proyecto:** crea el proyecto `enercheck` y, dentro, un servicio **Compose** con origen **Raw**. El contenido inicial da igual: el pipeline lo reemplaza en cada deploy.
3. **Environment:** pega `.env.prod.example` y completa los `CAMBIAR_*`. Genera los secretos **en el servidor**, para que no pasen por el chat ni por tu PC:
   ```sh
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # POSTGRES_PASSWORD
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # SECRET_KEY
   ```
   - `POSTGRES_PASSWORD` se usa **solo al crear** el volumen: cambiarla después no cambia la base.
   - `GEMINI_API_KEY`: usa una clave **exclusiva de producción**, distinta de la de `backend/.env` de desarrollo. Así su consumo se ve aparte y se puede revocar una sin afectar a la otra. Se crea en https://aistudio.google.com/apikey (*Create API key*, en el mismo proyecto de Google Cloud).
     > ⚠️ **Pendiente:** el primer deploy usa la misma clave de desarrollo. Para reemplazarla, crea la clave de producción, pégala en el Environment de Dokploy, presiona **Deploy** y luego revisa en AI Studio que la de desarrollo deje de recibir llamadas desde producción.
   - Escribe los valores **sin comillas** (`SUPERADMIN_EMAIL=correo@dominio.cl`). Las comillas pueden terminar como parte del valor.
   - `TAG` queda vacío.
4. **Domains:** todos con HTTPS y certificado Let's Encrypt.

   | Host | Servicio | Puerto |
   |---|---|---|
   | `comunidadsantalaura.cl` | `landing` | 8080 |
   | `www.comunidadsantalaura.cl` | `landing` | 8080 (nginx redirige a la versión sin www) |
   | `portal.comunidadsantalaura.cl` | `frontend` | 8080 |

5. **API key:** créala en Profile → API/CLI Keys. El **composeId** aparece en la URL del servicio compose.

> No conectes el servicio a GitHub. Dokploy no debe construir nada.

## 4. GitHub (una vez)

[GitHub] Settings → Environments → **`production`**. Ya está creado, con aprobación obligatoria y solo desde `main`. Sus secretos:

| Secreto | Valor |
|---|---|
| `DOCKER_USERNAME` | `mmoyac` |
| `DOCKER_PASSWORD` | Token de Docker Hub con permiso *Read & Write* |
| `VPS_HOST` / `VPS_PORT` | `86.48.21.250` / `22` |
| `VPS_SSH_KEY` | La llave privada `enercheck_ci` del §2 (después bórrala de tu PC) |
| `VPS_KNOWN_HOSTS` | Salida de `ssh-keyscan -t ed25519 86.48.21.250` |
| `DOKPLOY_URL` | `https://dokploy.comunidadsantalaura.cl` |
| `DOKPLOY_API_KEY` | La API key del §3 |
| `DOKPLOY_COMPOSE_ID` | El composeId del §3 |

Para cargar uno sin que el valor quede en el historial [PC]: `gh secret set NOMBRE --env production -R mmoyac/EffiEnerCheck`.

## 5. Primer deploy

```powershell
git checkout main && git merge --ff-only develop && git push      # [PC]
```

1. [GitHub] Aprueba el deploy en Actions.
2. El respaldo previo se salta, porque la base aún no existe.
3. El backend migra la base vacía, carga los roles y menús y crea el super admin desde `SUPERADMIN_*`.

Comprueba:
- que `https://portal.comunidadsantalaura.cl` permita iniciar sesión con el super admin;
- que `https://comunidadsantalaura.cl` responda. Mostrará «sitio no encontrado» hasta el §6.

## 6. Carga inicial (una vez): Santa Laura desde desarrollo

Solo pasan a producción la configuración del condominio, sus parcelas y sus parceleros con sus asignaciones. **No** pasan boletas, lecturas, liquidaciones, rifas, auditoría, otros condominios ni las cuentas del seed. Todos los parceleros reciben una clave inicial nueva (`app/db/copiar_desde_desarrollo.py`).

> **El JSON tiene datos personales.** `*.carga.json` está en `.gitignore`. Se borra apenas termina la carga.

[PC], con el entorno de desarrollo arriba:

```powershell
docker exec enercheck-backend-1 python -m app.db.copiar_desde_desarrollo exportar --condominio "Santa Laura" --salida /tmp/santa-laura.carga.json
docker cp enercheck-backend-1:/tmp/santa-laura.carga.json .
docker exec enercheck-backend-1 rm -f /tmp/santa-laura.carga.json
scp santa-laura.carga.json comunidad:/root/santa-laura.carga.json
Remove-Item santa-laura.carga.json
```

[VPS]:

```sh
chmod 600 /root/santa-laura.carga.json
docker cp /root/santa-laura.carga.json enercheck_backend:/tmp/carga.json
ARGS="--portal-url https://portal.comunidadsantalaura.cl --dominio comunidadsantalaura.cl --dominio www.comunidadsantalaura.cl"
docker exec enercheck_backend python -m app.db.copiar_desde_desarrollo importar /tmp/carga.json $ARGS --simular
docker exec -it enercheck_backend python -m app.db.copiar_desde_desarrollo importar /tmp/carga.json $ARGS   # pide la clave inicial
docker exec -u 0 enercheck_backend rm -f /tmp/carga.json
shred -u /root/santa-laura.carga.json
```

- La carga es idempotente.
- Con los datos de desarrollo actuales crea **53 parcelas y 69 parceleros**.

**Después de la carga**, desde el portal con el super admin:
1. Crea las cuentas del personal: `admin_condominio`, los lectores y `porteria`.
2. Sube el logo en Condominios.
3. Comunica a los residentes la clave inicial por un canal privado.

> ⚠️ Todos los residentes parten con la misma clave inicial y todavía no pueden cambiarla ellos mismos: solo un administrador puede hacerlo, desde **Usuarios**.

> ⚠️ **Primer período:** las lecturas se generan con `lectura_anterior = 0`. Antes de calcular, la lectura anterior de cada parcela debe ser la última lectura real. Hoy solo la API permite editarla: `PATCH /api/v1/lecturas/{id}` con `lectura_anterior`.

> El RUT de Santa Laura en desarrollo es el provisorio `1-9`. El contenido de la landing (`backend/app/sitio/contenido/santa-laura.json`) se asocia por RUT. Si cambias el RUT real en Condominios, agrégalo también a `ruts_comunidad` de ese archivo y despliega.

## 7. Respaldos

Todos van en `/opt/enercheck/respaldos/` (700, solo root). Los genera `enercheck-ci`.

| Tipo | Cuándo | Conserva |
|---|---|---|
| `predeploy-<fecha>-<sha>.*` | En cada deploy, antes de cambiar las imágenes | 10 |
| `diario-<fecha>.*` | Cron a las 03:30, hora de Chile (`/etc/cron.d/enercheck-respaldo`, log en `/var/log/enercheck-respaldo.log`) | 14 |

Cada conjunto incluye:
- `.dump`: la base, con `pg_dump -Fc`;
- `.archivos.tar.gz`: `uploads` (imágenes de boletas y logos) y `privado` (**vouchers, datos personales**);
- `.compose.yml`: el compose que estaba corriendo;
- `.imagen.txt`: la imagen que estaba corriendo.

> Las imágenes de boletas y los vouchers **no están en la base**: PostgreSQL guarda solo su ruta. La base y los archivos se restauran siempre juntos.

> Los respaldos están en el mismo disco del servidor. Para guardar una copia fuera [PC]: `scp comunidad:/opt/enercheck/respaldos/diario-<fecha>.* .`. Guárdala cifrada, porque tiene datos personales.

**Restaurar** [VPS], con el backend detenido para que nadie escriba mientras tanto:

```sh
R=/opt/enercheck/respaldos/predeploy-X      # prefijo del conjunto
docker stop enercheck_backend
docker exec -i enercheck_db pg_restore -U enercheck -d enercheck --clean --if-exists < $R.dump
docker start enercheck_backend
docker exec -i enercheck_backend tar -C /app -xzf - < $R.archivos.tar.gz
```

## 8. Rollback

Cada imagen está publicada con el SHA de su commit: **un rollback no reconstruye nada**.

1. [Dokploy] En el Environment del proyecto, define `TAG=<sha completo anterior>` y presiona **Deploy**.
2. Para volver al flujo normal, borra `TAG`. El próximo deploy del pipeline usará su commit.

> ⚠️ **Las migraciones no se revierten solas.** Si la versión nueva migró la base, primero restaura el respaldo `predeploy-…-<sha_nuevo>` (§7) y después levanta la imagen anterior. Se pierde lo escrito en producción entre ese deploy y la restauración.

Si el deploy nuevo también cambió el compose, `predeploy-…-<sha_nuevo>.compose.yml` tiene el anterior. Pégalo en el compose Raw de Dokploy antes de presionar Deploy.

## 9. Claves y acceso de emergencia

**Cambiar la clave de una cuenta desde el servidor** (por ejemplo, la del super admin) [VPS]:

```sh
docker exec -it enercheck_backend python -m app.db.cambiar_clave --email <correo>
```

**Si el backend no arranca** con «N cuenta(s) tienen la clave pública del seed»:
- alguna cuenta quedó con `admin123`;
- el mensaje no lista los correos, porque los logs del pipeline son públicos;
- con el backend detenido, usa un contenedor de un solo uso [VPS]:

```sh
cd "$(dirname "$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project.config_files"}}' enercheck_backend)")"
P=$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' enercheck_backend)
docker compose -p "$P" run --rm --entrypoint python backend -m app.db.cambiar_clave --expuestas
docker compose -p "$P" run --rm --entrypoint python backend -m app.db.cambiar_clave --email <correo>
```

Después, presiona **Deploy** en Dokploy.

**Acceso al servidor:**
- solo por llave, desde el PC autorizado (`ssh comunidad`);
- si se pierde, queda la consola VNC del panel de Contabo.

## 10. Probar la topología en local

> ⚠️ **Usa siempre otro nombre de proyecto (`-p`).** El compose de producción se llama `enercheck`, igual que el proyecto de desarrollo. Sin `-p`, Compose **reemplaza los contenedores de desarrollo**.

[PC] Trabaja en una carpeta fuera del repo, con:
- una copia de `docker-compose.prod.yml`;
- un `.env` de prueba creado desde `.env.prod.example`, con `DOCKER_USERNAME=local` y `TAG=ci`.

```powershell
docker network create --subnet 10.0.1.0/24 dokploy-network          # la misma subred que en el VPS
docker build -f backend/Dockerfile.prod -t local/enercheck-backend:ci backend      # desde la raíz del repo
docker build -f frontend/Dockerfile.prod -t local/enercheck-frontend:ci frontend
docker build -f landing/Dockerfile.prod -t local/enercheck-landing:ci landing
# en la carpeta de prueba:
docker compose -p enercheck_prodlocal -f docker-compose.prod.yml up -d
# hacer de Traefik: un curl dentro de la red, con el Host del dominio
docker run --rm --network dokploy-network curlimages/curl -si -H "Host: comunidadsantalaura.cl" http://enercheck_landing:8080/api/v1/boletas/   # 404
docker compose -p enercheck_prodlocal -f docker-compose.prod.yml down -v
docker network rm dokploy-network
```

## 11. Otro condominio

Agregar un condominio **no requiere cambios en el repo**:

1. [Cloudflare] Si tiene dominio propio, crea los registros A hacia el VPS, igual que en el §1.
2. [Dokploy] Agrega los dominios en *Domains*: el de la landing va al servicio `landing` y el del portal a `frontend`, con HTTPS.
3. [Portal, super admin] En Condominios, define los módulos, `portal_url`, los dominios de la landing, el color y el logo.
4. Si contrata la landing, crea su contenido en `backend/app/sitio/contenido/<slug>.json` (ver [docs/sitio-publico.md](docs/sitio-publico.md)) y despliega.
