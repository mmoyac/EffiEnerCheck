# Despliegue de EnerCheck en producción (Dokploy)

Producción corre en un VPS dedicado administrado con **Dokploy**:

- **Servidor:** Contabo, Ubuntu 24.04, IP `86.48.21.250`, alias SSH `comunidad`.
- **Dominio:** `comunidadsantalaura.cl` (registrado en NIC Chile, DNS en Cloudflare).

Las marcas **[PC]**, **[VPS]**, **[Dokploy]**, **[GitHub]** y **[Cloudflare]** indican dónde se ejecuta cada paso.

> **¿Se cayó el servidor o te cambias de proveedor?** Ve directo al [§12. Migrar o recuperar el VPS](#12-migrar-o-recuperar-el-vps).

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

Todo lo del servidor lo hace `infra/servidor/preparar-servidor.sh`, en fases idempotentes (se pueden repetir). Requisito: un **Ubuntu 24.04** recién creado con **tu llave SSH** ya autorizada para `root` (la mayoría de los proveedores la piden al crear el VPS) y el alias en `~/.ssh/config`.

[PC] Copia los scripts:

```powershell
ssh comunidad "mkdir -p /tmp/enercheck-instalar"
scp infra/servidor/preparar-servidor.sh infra/servidor/enercheck-ci infra/servidor/respaldos.age.pub infra/servidor/llave-ci.pub comunidad:/tmp/enercheck-instalar/
```

**2.1 Sistema** [PC]: paquetes (`age`, `rclone`, `ufw`, `fail2ban`), SSH solo con llaves, `ufw` (22 limitado, 80, 443), fail2ban, hora `America/Santiago` y actualizaciones de seguridad automáticas.

```powershell
ssh comunidad "bash /tmp/enercheck-instalar/preparar-servidor.sh sistema"
```

> Se niega a seguir si no hay ninguna llave autorizada: desactivar las contraseñas te dejaría fuera.

**2.2 Dokploy** [PC]: Docker y Dokploy con las versiones fijadas en el script. El panel queda en `:3000` **solo para tu IP** mientras creas el administrador (hasta que exista, quien entre primero lo crea).

```powershell
ssh comunidad "bash /tmp/enercheck-instalar/preparar-servidor.sh dokploy"
```

- Verifica que `dokploy-network` tenga la subred `10.0.1.0/24`, en la que confían los nginx de las imágenes y `FORWARDED_ALLOW_IPS`. Si no coincide, se detiene.
- En un servidor que **ya** tiene Dokploy no reinstala nada (el instalador desarma el swarm): solo verifica.

[Navegador] Sin demora: entra a `http://<IP>:3000`, crea la cuenta de administrador y en **Settings → Web Server** pon el dominio del panel (`dokploy.<dominio>`, HTTPS). [Cloudflare] El registro A de ese dominio → IP del VPS, **Solo DNS**. Cuando el panel responda por HTTPS, cierra `:3000` [PC]:

```powershell
ssh comunidad "bash /tmp/enercheck-instalar/preparar-servidor.sh cerrar-panel"
```

**2.3 Aplicación**: `enercheck-ci`, el cron del respaldo diario (03:30), la llave pública de respaldos, el **token de R2** y la **llave del pipeline**.

[PC] Con `-t`, porque el script te pide el token de R2 por teclado (el ID, la clave secreta sin mostrarla y el endpoint; están en tu archivo privado «EnerCheck – token R2 servidor»). Nunca va como argumento ni por el chat. Cada dato se vuelve a pedir si no tiene el formato esperado:

```powershell
ssh -t comunidad "bash /tmp/enercheck-instalar/preparar-servidor.sh aplicacion; rm -rf /tmp/enercheck-instalar"
```

- Verifica el token listando el bucket `efficomunidad-respaldos` antes de guardarlo (`/opt/enercheck/rclone.conf`, 600). Para cambiarlo después: `--reemplazar-token`.
- Agrega la **llave del pipeline** a `/root/.ssh/authorized_keys` con **comando forzado** (`command="/opt/enercheck/bin/enercheck-ci",restrict`): esa llave solo puede respaldar y esperar el deploy, no abre una shell. Su parte pública está versionada en `infra/servidor/llave-ci.pub` y la privada es el secreto `VPS_SSH_KEY` de GitHub, así que un servidor nuevo no obliga a cambiarla.
- Para **cambiar** la llave del pipeline (si se filtra): genera otra en el PC (`ssh-keygen -t ed25519 -N '""' -C enercheck-ci@github-actions -f enercheck_ci`), reemplaza `llave-ci.pub` con su parte pública, ejecuta esta fase con `--llave-ci "$(Get-Content enercheck_ci.pub)"`, quita la línea vieja de `authorized_keys`, carga la privada en `VPS_SSH_KEY` y bórrala del PC.
- Para actualizar `enercheck-ci` tras un cambio en el repo, repite la copia y esta fase: lo ya configurado no se toca.

Comprueba [VPS]: `grep -c 'command="/opt/enercheck/bin/enercheck-ci",restrict' /root/.ssh/authorized_keys` debe dar `1`. La prueba de punta a punta de la llave es el próximo deploy (respaldo previo y espera por SSH).

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

### 3.1 Correo de invitaciones (Resend)

Las invitaciones y "¿Olvidaste tu clave?" se envían por correo con [Resend](https://resend.com). Sin Resend todo funciona igual, pero las invitaciones solo pueden enviarse por WhatsApp y la recuperación de clave no llega.

1. [Resend] Crea la cuenta. En **Domains → Add domain**, agrega `comunidadsantalaura.cl`.
2. [Cloudflare] Crea los registros DNS que muestra Resend (MX y TXT de SPF, y TXT de DKIM), con **Solo DNS**. Espera a que Resend marque el dominio como *Verified*.
3. [Resend] En **API Keys**, crea una key con permiso *Sending access*, limitada al dominio.
4. [Dokploy] En el Environment, completa:
   - `RESEND_API_KEY=` con la key;
   - `EMAIL_REMITENTE=no-responder@comunidadsantalaura.cl`.

   Presiona **Deploy**.
5. Prueba: en el ingreso del portal, usa **«¿Olvidaste tu clave?»** con tu correo. Debe llegar el correo de "Santa Laura" y el enlace debe funcionar.

> Plan gratuito de Resend: alrededor de 3.000 correos al mes y 100 al día. Alcanza de sobra para invitar a los 69 vecinos de una vez.

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

Solo pasan a producción la configuración del condominio, sus parcelas y sus parceleros con sus asignaciones. **No** pasan boletas, lecturas, liquidaciones, rifas, auditoría, otros condominios ni las cuentas del seed. Los parceleros quedan como **cuentas pendientes, sin clave**: nadie puede entrar como ellos hasta que cada uno cree la suya con su invitación (`app/db/copiar_desde_desarrollo.py`).

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
# Por stdin, no con docker cp: así el archivo queda del usuario `app` (el contenedor no tiene CAP_CHOWN)
docker exec -i enercheck_backend sh -c "umask 077; cat > /tmp/carga.json" < /root/santa-laura.carga.json
ARGS="--portal-url https://portal.comunidadsantalaura.cl --dominio comunidadsantalaura.cl"
docker exec enercheck_backend python -m app.db.copiar_desde_desarrollo importar /tmp/carga.json $ARGS --simular
docker exec enercheck_backend python -m app.db.copiar_desde_desarrollo importar /tmp/carga.json $ARGS
docker exec enercheck_backend rm -f /tmp/carga.json
shred -u /root/santa-laura.carga.json
```

- La carga es idempotente.
- Con los datos de desarrollo actuales crea **53 parcelas y 69 parceleros**, todos pendientes.
- `www.` no hace falta como dominio aparte: se guarda sin `www`, y la landing redirige `www` al dominio sin él.

**Después de la carga**, desde el portal con el super admin:
1. Crea las cuentas del personal (`admin_condominio`, lectores, `porteria`) **sin contraseña** y envíales su invitación con **Invitar**.
2. Sube el logo en Condominios.
3. Prueba primero con una cuenta propia: **Invitar** → abre el enlace → crea la clave → ingresa.
4. En **Usuarios**, filtra Santa Laura y presiona **Invitar pendientes (N)**: cada vecino recibe su correo. A quien no lo reciba, reenvíale el enlace con **Invitar → Enviar por WhatsApp**.

Los vecinos también pueden pedir su enlace solos con **«¿Olvidaste tu clave? ¿Primera vez?»** en el ingreso.

> ⚠️ **Primer período:** las lecturas se generan con `lectura_anterior = 0`. Antes de calcular, la lectura anterior de cada parcela debe ser la última lectura real. Hoy solo la API permite editarla: `PATCH /api/v1/lecturas/{id}` con `lectura_anterior`.

> El RUT de Santa Laura en desarrollo es el provisorio `1-9`. El contenido de la landing (`backend/app/sitio/contenido/santa-laura.json`) se asocia por RUT. Si cambias el RUT real en Condominios, agrégalo también a `ruts_comunidad` de ese archivo y despliega.

## 7. Respaldos

Los genera `enercheck-ci` en dos lugares: una copia **local** en `/opt/enercheck/respaldos/` (700, solo root), para volver atrás rápido tras un deploy, y una copia **externa cifrada** en Cloudflare R2, que sobrevive aunque se pierda el servidor.

| Tipo | Cuándo | Local (conserva) | R2 (se borra sola a los) |
|---|---|---|---|
| `predeploy-<fecha>-<sha>` | En cada deploy, antes de cambiar las imágenes | 10 | 91 días |
| `diario-<fecha>` | Cron a las 03:30, hora de Chile (`/etc/cron.d/enercheck-respaldo`, log en `/var/log/enercheck-respaldo.log`) | 14 | 36 días |

Cada respaldo tiene dos partes:
- **La base**, completa: `.dump` (`pg_dump -Fc`), `.compose.yml` (el compose que estaba corriendo), **`.env` (el Environment de Dokploy: los secretos de producción, siempre al día)** e `.imagen.txt` (la imagen que estaba corriendo).
- **Los archivos subidos**, de forma **incremental**: imágenes de boletas, logos y vouchers (`uploads` y `privado`). Cada respaldo sube a R2 solo los que aún no están, y en R2 **nunca se borra ninguno**, aunque se borre en el servidor. En el respaldo local no van: un deploy no toca los archivos, y para recuperar uno borrado está R2.

> Las imágenes y los vouchers **no están en la base**: PostgreSQL guarda solo su ruta. El respaldo incremental funciona porque **los archivos subidos son inmutables**: cada subida crea un archivo con nombre nuevo y nunca se reescribe uno existente.

**R2** (bucket `efficomunidad-respaldos`, cuenta Cloudflare del DNS):

```
diario/<nombre>.{dump,compose.yml,env,imagen.txt}.age  +  <nombre>.sha256   ← el .sha256 se sube al final
predeploy/...                                                            (sin él, el conjunto está incompleto)
archivos/uploads/<ruta>.age   archivos/privado/<ruta>.age
```

- Todo va **cifrado con `age`** antes de salir del servidor. En el servidor está solo la llave **pública** (`/opt/enercheck/respaldos.age.pub`, copia de `infra/servidor/respaldos.age.pub`): puede cifrar, no descifrar. La **privada** la guarda el operador fuera del servidor, en dos lugares.
- El token del servidor (`/opt/enercheck/rclone.conf`, 600) solo puede escribir en ese bucket, y las **reglas de bloqueo** impiden borrar o reemplazar objetos: `diario/` 35 días, `predeploy/` 90, `secretos/` 365 y `archivos/` indefinido. Las **reglas de ciclo de vida** borran `diario/` a los 36 días y `predeploy/` a los 91. Ni un servidor comprometido puede destruir el historial.
- Si la subida a R2 falla, la copia local se conserva y `enercheck-ci` termina con error: antes de un deploy, **el deploy no sigue**; en el diario, queda en el log.

**Ver los respaldos** [VPS]: `enercheck-ci listar` (R2) o `enercheck-ci listar local`. También en el panel de Cloudflare: R2 → `efficomunidad-respaldos` → Objetos.

**Restaurar** [VPS], con la aplicación ya desplegada (`enercheck_db` y `enercheck_backend` existen):

```sh
enercheck-ci restaurar ultimo --llave - --confirmar          # desde R2: pega la llave privada y Ctrl-D
enercheck-ci restaurar <nombre> --desde local --confirmar    # un respaldo local, p. ej. tras un deploy fallido
```

- Sin `--confirmar` solo dice qué haría. Por la llave del CI se rechaza: es solo de consola.
- **Desde R2** baja el conjunto, verifica su `.sha256`, lo descifra y baja los archivos que **faltan** en el servidor (no pisa ni borra los que están). **Desde local** restaura solo la base.
- Valida todo antes de tocar nada: carga el respaldo en una base aparte (`enercheck_restaurando`) con la aplicación en servicio. Si la llave es incorrecta, el respaldo está alterado o el dump dañado, se detiene **sin modificar nada**.
- Luego detiene `enercheck_backend`, intercambia las bases y repone los archivos con el dueño de la API. La base vigente queda como **`enercheck_previa`** hasta la próxima restauración: para volver atrás, se intercambian los nombres de nuevo.
- Termina esperando que la API quede sana.

**Bajar y descifrar a mano** [PC], sin el script (necesitas `age` y `rclone` con las credenciales del token en variables `RCLONE_CONFIG_R2_*`, como en la prueba del bucket):

```powershell
rclone copy r2:efficomunidad-respaldos/diario/ . --include "diario-<fecha>.*"
age -d -i "$HOME\.secretos\enercheck-respaldos.key" -o base.dump diario-<fecha>.dump.age
age -d -i "$HOME\.secretos\enercheck-respaldos.key" -o produccion.env diario-<fecha>.env.age   # secretos: para el Environment de Dokploy
rclone copy r2:efficomunidad-respaldos/archivos/privado/vouchers/<archivo>.age .
age -d -i "$HOME\.secretos\enercheck-respaldos.key" -o <archivo> <archivo>.age
```

> El contenido descifrado tiene **datos personales**: no lo dejes en carpetas sincronizadas ni lo envíes por chat, y bórralo al terminar.

**Prueba local de `enercheck-ci`** [PC]: `infra/servidor/pruebas/probar-enercheck-ci.sh` levanta un servidor falso en Docker con un R2 falso y ejercita respaldos y restauraciones (instrucciones en su encabezado). **Nunca** en el servidor.

## 8. Rollback

Cada imagen está publicada con el SHA de su commit: **un rollback no reconstruye nada**.

1. [Dokploy] En el Environment del proyecto, define `TAG=<sha completo anterior>` y presiona **Deploy**.
2. Para volver al flujo normal, borra `TAG`. El próximo deploy del pipeline usará su commit.

> ⚠️ **Cuentas pendientes:** desde `acceso-por-invitacion`, `usuarios.password_hash` admite NULL. Una imagen anterior a ese cambio no arranca con cuentas pendientes en la base, y su migración no se puede bajar mientras existan. Si hay que volver atrás, restaura el respaldo previo.

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

## 12. Migrar o recuperar el VPS

Dos casos con la misma receta: **migración planificada** (el servidor viejo sigue vivo: no se pierde nada) y **servidor perdido** (se pierde lo escrito después del último respaldo en R2, como mucho un día). Meta: producción de vuelta en **alrededor de una hora**.

**Lo que necesitas a mano** (nada de esto está en el servidor):
- tu **llave privada de respaldos** (`$HOME\.secretos\enercheck-respaldos.key` o su copia fuera del PC);
- el **token de R2** («EnerCheck – token R2 servidor»);
- acceso a Cloudflare, GitHub, Docker Hub y al panel del proveedor nuevo;
- `age` y `rclone` en el PC (`winget install FiloSottile.age Rclone.Rclone`).

| Paso | Dónde | Planificada | Perdido | Tiempo |
|---|---|---|---|---|
| 0. Bajar el TTL de los registros A a 60 s | Cloudflare | Un día antes | — | — |
| 1. Crear el VPS y el alias SSH | Proveedor, PC | ✔ | ✔ | 10 min |
| 2. Preparar el servidor | PC | ✔ | ✔ | 15 min |
| 3. Configurar Dokploy y desplegar la versión vigente | Dokploy | ✔ | ✔ | 15 min |
| 4. Mantenimiento y último respaldo en el viejo | VPS viejo | ✔ | — | 2 min |
| 5. Restaurar | PC → VPS nuevo | ✔ | ✔ | 5 min |
| 6. DNS y certificados | Cloudflare | ✔ | ✔ | 5–10 min |
| 7. GitHub y verificación | GitHub, navegador | ✔ | ✔ | 10 min |

En una migración planificada, los pasos 1 a 3 se hacen con calma y con el sitio en servicio; el corte va solo del paso 4 al 6.

### 12.1 Crear el VPS

1. [Proveedor] Ubuntu **24.04**, con tu llave SSH pública (`~/.ssh/comunidad_vps.pub`) autorizada para `root` al crearlo. Mínimo 2 vCPU y 4 GB de RAM.
2. [PC] En `~/.ssh/config`, cambia el `HostName` del alias `comunidad` a la IP nueva (o crea `comunidad-nuevo` si el viejo sigue vivo y usa ese nombre en lo que sigue). Borra la huella vieja: `ssh-keygen -R <IP nueva>`.
3. [PC] `ssh comunidad "hostname"` debe responder.

### 12.2 Preparar el servidor

Las fases del §2, en orden: `sistema` → `dokploy` → (administrador y dominio del panel) → `cerrar-panel` → `aplicacion` (pide el token de R2; la llave del pipeline va sola).

- En una **migración planificada**, el dominio del panel sigue apuntando al servidor viejo: trabaja en `http://<IP nueva>:3000` (abierto solo a tu IP) y deja `cerrar-panel` para después del paso 6, cuando `dokploy.<dominio>` ya apunte al nuevo.
- La fase `dokploy` debe terminar con `dokploy-network: 10.0.1.0/24 ✔`.

### 12.3 Configurar Dokploy y desplegar la versión vigente

1. **Los secretos** [PC], desde el último respaldo (con las credenciales de R2 cargadas como en el §7, «Bajar y descifrar a mano»):

   ```powershell
   mkdir $HOME\migracion; cd $HOME\migracion
   rclone lsf r2:efficomunidad-respaldos/diario/ --include "*.sha256"        # el último es el más reciente
   rclone copy r2:efficomunidad-respaldos/diario/ . --include "diario-<fecha>.env.age" --include "diario-<fecha>.imagen.txt.age"
   age -d -i "$HOME\.secretos\enercheck-respaldos.key" -o produccion.env diario-<fecha>.env.age
   age -d -i "$HOME\.secretos\enercheck-respaldos.key" diario-<fecha>.imagen.txt.age   # …/enercheck-backend:<SHA>
   ```

   Anota el **nombre del respaldo** (`diario-<fecha>`) y el **SHA** de la imagen: es la versión que estaba corriendo.

2. [Dokploy] Los pasos del §3 (registro, proyecto `enercheck`, servicio Compose **Raw**, API key):
   - **Compose:** pega `docker-compose.prod.yml` **del repo** (rama `main`). **No** uses el `.compose.yml` del respaldo: Dokploy le agrega etiquetas de Traefik con nombres internos de la instalación vieja.
   - **Environment:** pega `produccion.env` **quitando** las líneas `APP_NAME=`, `COMPOSE_PROJECT_NAME=` y `DOCKER_CONFIG=` (las agrega Dokploy), y pon `TAG=<SHA>`.
   - **Domains:** los del §3, paso 4.
3. [Dokploy] **Deploy**. [PC] `ssh comunidad "enercheck-ci esperar-sano <SHA>"` debe terminar con `enercheck_backend sano`. La base está vacía: el arranque crea las tablas y el super admin de `SUPERADMIN_*`; el paso 5 la reemplaza entera.
4. Borra lo descifrado: `cd $HOME; Remove-Item -Recurse -Force $HOME\migracion` (tiene todos los secretos).

### 12.4 Mantenimiento y último respaldo (solo planificada)

[VPS viejo] Sin el portal nadie escribe; la app del lector sigue capturando sin conexión y sincroniza cuando vuelva:

```sh
docker stop enercheck_frontend enercheck_landing
enercheck-ci respaldar diario        # debe terminar con «Externo: diario/<nombre> subido»
```

Anota ese `<nombre>`: es el que se restaura en el paso siguiente.

### 12.5 Restaurar

[PC] La llave privada viaja al servidor solo durante la restauración y se borra al terminar:

```powershell
scp "$HOME\.secretos\enercheck-respaldos.key" comunidad:/root/.llave-restaurar
ssh comunidad "enercheck-ci restaurar <nombre> --llave /root/.llave-restaurar --confirmar; shred -u /root/.llave-restaurar"
```

> ⚠️ Usa el **nombre** anotado (§12.4 en una planificada, §12.3 si el servidor se perdió), **no** `ultimo`: si el servidor nuevo ya pasó por las 03:30, su cron subió a R2 un respaldo de su base **vacía**, y ese sería el «último». `enercheck-ci listar` muestra los disponibles.

Debe terminar con «Restauración terminada». Repone la base y **todos** los archivos (boletas, logos, vouchers, fotos de medidores) desde R2.

### 12.6 DNS y certificados

[Cloudflare] Registros A de `comunidadsantalaura.cl`, `www`, `portal`, `dokploy` (y `n8n` si corresponde) → **IP nueva**, Solo DNS. Traefik pide los certificados de Let's Encrypt en cuanto el DNS apunta al nuevo: puede tardar unos minutos. Si después de 10 minutos el navegador sigue mostrando un certificado inválido, [VPS] `docker restart dokploy-traefik` para que lo vuelva a pedir. En una migración planificada, ahora corresponde `cerrar-panel` (§12.2).

### 12.7 GitHub y verificación

1. [GitHub] Environment `production`: actualiza `VPS_HOST`, `VPS_KNOWN_HOSTS` (`ssh-keyscan -t ed25519 <IP nueva>`), `DOKPLOY_API_KEY` y `DOKPLOY_COMPOSE_ID`. `DOKPLOY_URL` y `VPS_SSH_KEY` no cambian.
2. [Navegador] Comprueba:
   - `https://portal.<dominio>`: inicia sesión con una cuenta real (las claves de siempre);
   - una boleta con su imagen, un voucher de rifa y una foto de medidor;
   - `https://<dominio>`: la landing con su logo.
3. [VPS nuevo] `enercheck-ci respaldar diario` termina subiendo a R2 (los archivos dirán «nada nuevo»).
4. El próximo push a `main` despliega en el servidor nuevo: confirma que el respaldo previo y `esperar-sano` pasan.
5. **Planificada:** deja el servidor viejo **apagado** (no destruido) una semana y luego elimínalo en el proveedor. Vuelve a subir el TTL en Cloudflare.

> **n8n** (`n8n.<dominio>`) vive en el mismo servidor con sus datos propios y **no** está cubierto por estos respaldos: en una migración planificada, expórtalo antes desde su panel; si el servidor se perdió, hay que reconfigurarlo.

> Este procedimiento se ensaya en un VPS desechable (simulacro, tarea 8.1 de `portabilidad-vps`). Anota aquí la fecha y el tiempo total de cada ensayo: _pendiente_.
