# Design

## Context

Ver proposal.md (Why). Estado actual relevante:

- `infra/servidor/enercheck-ci` genera en `/opt/enercheck/respaldos/` conjuntos `<tipo>-<fecha>[-<sha>].{dump,archivos.tar.gz,compose.yml,imagen.txt}` (diario a las 03:30 y previo a cada deploy, por SSH con comando forzado). Todo queda en el disco del VPS.
- `instalar.sh` solo instala `enercheck-ci`, la carpeta de respaldos, la zona horaria y el cron. El endurecimiento (sshd, ufw, fail2ban), Dokploy, el cierre del puerto 3000 y la llave del CI se hicieron a mano.
- Los secretos están solo en el Environment de Dokploy. `POSTGRES_PASSWORD` se usa al crear el volumen, pero `DATABASE_URL` la reutiliza: una base restaurada con `pg_restore` sobre un volumen nuevo funciona con **cualquier** contraseña nueva, porque el dump no trae los roles. `SECRET_KEY` sí importa: si cambia, se cierran todas las sesiones (tolerable, no fatal).
- Los dominios se configuran en la pestaña Domains de Dokploy.
- `frontend/nginx.prod.conf`, `landing/nginx.prod.conf` (`set_real_ip_from 10.0.1.0/24`) y `FORWARDED_ALLOW_IPS=10.0.1.0/24` asumen la subred de `dokploy-network` del servidor actual. En un servidor nuevo, Docker podría asignar otra.
- El CI es público: nada con datos personales puede imprimirse.
- Los archivos subidos (imágenes de boletas, logos, vouchers) se nombran siempre con un uuid nuevo (`boletas.py`, `condominios.py`, `rifas.py`) y **nunca se reescriben**: reemplazar una imagen crea otro archivo y borra el anterior. Se agregará la foto del medidor desde la app del lector sin conexión (~53 fotos al mes), lo que hace crecer los archivos de forma sostenida.

## Goals / Non-Goals

**Goals:**
- Recuperación sin depender de nada que viva solo en el VPS.
- Una sola llave (`age`) que el operador custodia, para respaldos y secretos.
- Que la restauración sea una orden con validaciones, no una secuencia de comandos copiados de DEPLOY.md.

**Non-Goals:**
- Alta disponibilidad, réplicas o failover automático. La recuperación es manual y guiada.
- Respaldo continuo (WAL/PITR). Se acepta perder hasta 24 h en un desastre; en una migración planificada no se pierde nada.
- Mover el almacenamiento principal de archivos a S3.
- La foto del medidor en sí (captura, compresión en el celular, almacenamiento). Es otro cambio; este solo deja el respaldo preparado para su volumen. Ese cambio DEBE comprimir la foto en el celular (≈1600 px, JPEG/WebP ~80 %, ~200 KB).
- n8n y la configuración interna de Dokploy (usuarios, otros proyectos).
- Independizarse de Dokploy: sigue siendo la plataforma; solo se reduce lo que se configura en su interfaz.

## Decisions

### D1. Cloudflare R2 como almacenamiento externo
El DNS ya está en Cloudflare, el egreso es gratis (restaurar no cuesta) y es S3-compatible: si mañana conviene Backblaze B2 o AWS, solo cambia la configuración de `rclone`.
*Alternativas:* Backblaze B2 (igual de bueno, otra cuenta más), el almacenamiento de objetos del mismo proveedor del VPS (descartado: si el proveedor suspende la cuenta, se pierde todo junto).

### D2. Base por fotos completas, archivos incrementales; `age` + `rclone`, no `restic`
El respaldo tiene dos partes con estrategias distintas:
- **Base (y `compose.yml`, `imagen.txt`):** foto completa en cada respaldo, como hoy. Pesa poco y es lo que define el punto en el tiempo.
- **Archivos (`uploads` y `privado`):** subida **incremental y de solo agregar**. Cada archivo que todavía no está en R2 se cifra por separado con `age -r <llave pública>` y se sube a `archivos/<volumen>/<ruta>.age`. Nunca se borra ni se reemplaza nada en R2, aunque el archivo se borre en el servidor (anular o eliminar una rifa, reemplazar un logo). Es seguro porque los archivos son inmutables (Context): mismo nombre = mismo contenido.

"Qué falta subir" se calcula comparando el volumen con el listado remoto (`rclone lsf -R`), no con un índice local: en un servidor recién restaurado no hay que volver a subir nada que ya esté en R2. Los archivos se leen desde el host (`docker volume inspect -f '{{.Mountpoint}}'`), sin depender de que el backend esté corriendo.

Así cada respaldo diario sube solo lo del día (unos MB, incluso con fotos de medidores) y la llave para descifrar sigue sin estar en el servidor. Restaurar a mano sigue siendo posible: `rclone copy` + `age -d -i <llave privada>` sobre cada archivo.
*Alternativas:* (a) tar completo en cada respaldo (el plan inicial): simple, pero con fotos de medidores cada conjunto crece sin fin y se sube de nuevo todo; (b) `rclone sync`: replica también los borrados y su cifrado (`crypt`) exige la contraseña en el servidor; (c) `restic`: incremental y con historial, pero también exige la contraseña en el servidor para escribir. Se descarta (b) y (c) por la llave; (a) por el crecimiento.

### D3. Solo escritura en el servidor; la retención la hace el bucket
El token de R2 del servidor tiene permiso *Object Read & Write* limitado al bucket. R2 no ofrece un permiso de "solo escribir sin sobrescribir", así que se combina con **Bucket Lock** (regla de retención por prefijo: los objetos no se pueden borrar ni reemplazar durante N días) y una **regla de ciclo de vida** que borra `diario/` a los 35 días y `predeploy/` a los 90. `archivos/` tiene retención **indefinida** y sin ciclo de vida: son la única copia externa de cada archivo. Así un servidor comprometido no puede destruir el historial.
*Alternativa:* podar desde el servidor como en local (descartado: requiere permiso de borrado).

### D4. Formato y nombres
- Conjunto de base: `r2:<bucket>/<tipo>/<prefijo>.{dump,compose.yml,imagen.txt}.age`, con `<tipo>` = `diario` | `predeploy`, y al final `<prefijo>.sha256` (sumas de los archivos **cifrados**). Un conjunto sin `.sha256` está incompleto y `restaurar` lo ignora.
- Archivos: `r2:<bucket>/archivos/{uploads,privado}/<ruta original>.age`. Un conjunto de base del momento T es consistente con todos los archivos subidos hasta T; los posteriores sobran pero no estorban (quedan huérfanos, sin fila que los apunte).
- **Orden:** primero se suben los archivos nuevos y después el dump. Así nunca existe un dump que apunte a un archivo que no está en R2.
- **Local:** el conjunto local queda con `.dump`, `.compose.yml` e `.imagen.txt` (sin cifrar, carpeta 700). Se elimina el `.archivos.tar.gz` local: un deploy no toca los archivos, y para recuperar uno borrado está R2. Así el disco del VPS no se llena con copias de las mismas fotos.

### D5. Fallo de subida: bloquea el deploy, no el diario
En `respaldar <sha>` la subida (archivos nuevos y conjunto de base) es parte del respaldo: si falla, `exit 1` y el pipeline no despliega (consistente con el requisito existente). En `respaldar diario` el fallo de subida deja la copia local, escribe en `/var/log/enercheck-respaldo.log` y sale con código distinto de cero; el siguiente diario sube su propio conjunto (no se reintentan los anteriores). La alerta activa (correo o n8n) queda como pregunta abierta.

### D6. `enercheck-ci restaurar` solo desde consola, nunca por la llave del CI
La llave del CI tiene comando forzado; `restaurar` se rechaza si llega por `SSH_ORIGINAL_COMMAND`. Uso:
```
enercheck-ci restaurar <ultimo|prefijo> [--desde r2|local] [--llave <archivo>] --confirmar
```
Pasos: localizar el conjunto → (R2) bajar y verificar `.sha256` → descifrar a un directorio temporal 700 → (R2) bajar y descifrar los archivos de `archivos/` que **no** están en los volúmenes → cargar el dump en una base **aparte** (`enercheck_restaurando`, `pg_restore --single-transaction --exit-on-error --no-owner`) con la aplicación todavía en servicio → **recién entonces** detener `enercheck_backend`, renombrar `enercheck` → `enercheck_previa` y `enercheck_restaurando` → `enercheck`, agregar los archivos faltantes a los volúmenes (sin pisar ni borrar los existentes) → arrancar el backend → esperar `healthy` (reutiliza `esperar_sano` sin exigir SHA). La llave privada se entrega por archivo o por stdin (`--llave -`) y nunca se copia a `/opt`; los temporales se borran al salir.
*Por qué una base aparte y no `pg_restore --clean`:* `--clean` solo borra los objetos que trae el dump. Si se restaura un respaldo **más antiguo** que la imagen en ejecución, las tablas nuevas quedarían y la migración siguiente fallaría al crearlas. Con la base aparte, la restaurada queda exactamente como el respaldo; el dump se valida por completo antes de tocar la vigente, y la anterior queda en `enercheck_previa` (se reemplaza en cada restauración) para volver atrás con dos `ALTER DATABASE ... RENAME`. El costo es el doble de espacio de la base durante la restauración, irrelevante a este tamaño.
Los archivos se escriben con un contenedor auxiliar de la **imagen de la base** (ya está en el servidor, sin red), empaquetados con dueño `10001` y permisos `u=rwX,go=rX`, porque el backend está detenido durante la restauración. Con `--desde local` solo se restaura la base: los archivos del volumen se dejan como están.
Se prueba con `infra/servidor/pruebas/probar-enercheck-ci.sh`: servidor y R2 falsos en Docker local, con los casos de la spec (llave incorrecta, conjunto alterado, dump truncado, sin confirmación, por SSH, servidor perdido, volúmenes completos).

### D7. Secretos: el `.env` de Dokploy viaja en cada respaldo
Dokploy escribe el Environment del proyecto como `.env` junto al compose que despliega (`/etc/dokploy/compose/<app>/code/`), el mismo directorio del que `respaldar` ya copia el `.compose.yml` (lo localiza por la etiqueta `com.docker.compose.project.config_files` de `enercheck_backend`). Se copia también como `<prefijo>.env` (600 en la carpeta 700) y se cifra y sube con el resto del conjunto. Así la copia de los secretos está **siempre al día** sin pasos manuales: un secreto cambiado en Dokploy llega en el siguiente respaldo (diario o del próximo deploy), y el texto en claro nunca sale del servidor. Al migrar, el operador descifra `<conjunto>.env.age` en su PC y lo pega en el Environment de Dokploy del servidor nuevo.
*Alternativas:* exportarlo a mano desde el PC a `secretos/` (el plan inicial: depende de acordarse y pasa por el portapapeles); `sops` en el repo (otra herramienta, y el repo es la fuente del código, no de los secretos). La regla de bloqueo `secretos/` del bucket queda sin uso, disponible para copias manuales excepcionales.

### D8. `preparar-servidor.sh` por fases
`infra/servidor/preparar-servidor.sh` (reemplaza a `instalar.sh`) reproduce la configuración que se hizo a mano en el servidor de referencia (leída de él el 2026-10-07). Cada fase es idempotente:
1. **`sistema`:** paquetes (`ufw`, `fail2ban`, `age`, `rclone`, `unattended-upgrades`), `sshd_config.d/00-endurecer.conf` (solo llaves; se niega si no hay ninguna llave autorizada), ufw (22 limit, 80, 443/tcp y udp), `fail2ban` con `jail.d/sshd.local` (backend systemd, banaction ufw, `journalmatch` de `ssh.service`), zona horaria.
2. **`dokploy`:** Docker y Dokploy con versiones fijadas (las del servidor de referencia: Docker 28.5.0, Dokploy v0.30.8). Antes del instalador, el puerto 3000 se restringe a la IP del operador en la cadena `DOCKER-USER`: Docker publica puertos saltándose ufw, y mientras no exista el administrador, quien entre primero lo crea. Si Dokploy **ya** está instalado no ejecuta el instalador, porque este hace `docker swarm leave --force` y recrea `dokploy-network`: solo verifica.
3. **`cerrar-panel`:** tras crear el administrador y el dominio del panel, `docker service update --publish-rm` del 3000 (como en el servidor de referencia) y retiro de las reglas temporales.
4. **`aplicacion`:** lo de `instalar.sh` + la llave pública `age` + `rclone.conf` (600) con el token pedido **por teclado** y verificado listando el bucket antes de guardarlo + la llave del CI con comando forzado (`--llave-ci`).
Se copia con `scp` y se ejecuta por `ssh` (con `-t` en `aplicacion`, por el token).
*Alternativa:* Ansible/cloud-init (descartado por ahora: más maquinaria para un solo servidor; el script se puede llamar desde cloud-init si el proveedor lo ofrece).

### D9. Subred `10.0.1.0/24`: se verifica, no se crea
La subred está horneada en el nginx de las imágenes (`set_real_ip_from`) y en `FORWARDED_ALLOW_IPS`. No sirve crear `dokploy-network` antes: el instalador la borra y la recrea sin subred. En un swarm recién creado, `ingress` toma `10.0.0.0/24` y la primera red overlay siguiente, `10.0.1.0/24`, que es como quedó el servidor de referencia. La fase `dokploy` (y `cerrar-panel`) verifica la subred y se detiene si no coincide (escenario de la spec).
*Alternativa:* parametrizar la subred en el nginx (plantillas en el arranque): descartado mientras la verificación baste.

### D10. Dominios como labels de Traefik con variables
En `docker-compose.prod.yml`, `frontend` y `landing` llevan `labels` de Traefik (`traefik.enable`, router `Host(...)` en `websecure` con `tls.certresolver=letsencrypt`, router en `web` con redirección a HTTPS, puerto 8080). Los hosts salen de variables del Environment (`DOMINIO_PORTAL`, `DOMINIO_SITIO`), así el simulacro usa dominios de prueba sin tocar el repo. La redirección `www` → apex la sigue haciendo nginx; Traefik solo agrega `www.${DOMINIO_SITIO}` al router de la landing. Se quitan los dominios de la pestaña Domains de Dokploy en el mismo deploy para no duplicar routers.

### D11. Mantenimiento durante una migración planificada
Para que no haya escrituras después del último respaldo: en el VPS viejo se detienen `enercheck_frontend` y `enercheck_landing` (el backend y la base siguen arriba porque `respaldar` hace `pg_dump` en la base). Sin el portal, nadie escribe; la app del lector guarda en IndexedDB y sincroniza contra el servidor nuevo cuando vuelva (base de cada lectura incluida). Luego `respaldar diario` (sube a R2) y se restaura **ese** conjunto en el nuevo.

## Risks / Trade-offs

- [Se pierde la llave privada `age`] → Los respaldos se vuelven inútiles. Mitigación: dos copias en lugares distintos (gestor de claves + copia impresa o USB guardado), y el simulacro la usa, lo que prueba que existe.
- [El token de R2 en el servidor permite sobrescribir] → Bucket Lock lo impide durante la retención (indefinida para `archivos/`); verificarlo en el simulacro intentando un `rclone deletefile`.
- [Crecimiento de R2 con los archivos, que nunca se borran] → Con fotos comprimidas son ~120 MB al año: centavos. Si algún día pesa, se archiva por año fuera del bucket.
- [Datos personales que se borraron en el servidor siguen en R2] → Un voucher de una rifa eliminada queda cifrado en R2. Es aceptable (cifrado, sin llave en el servidor) y se documenta; si se requiere borrarlo, el operador lo hace desde la cuenta de Cloudflare.
- [Un archivo que se modificara en el mismo lugar no se volvería a subir] → Hoy no ocurre (uuid nuevo en cada subida). Se deja como regla en CLAUDE.md: los archivos subidos son inmutables; reemplazar = nombre nuevo.
- [Muchos archivos pequeños hacen lento el listado] → `rclone lsf` de miles de objetos toma segundos; se revisa si se superan las decenas de miles.
- [Restaurar sobre una base con datos] → Requiere `--confirmar`, carga y valida el respaldo en una base aparte antes de detener nada y deja la base anterior en `enercheck_previa`.
- [Labels de Traefik y Dokploy en conflicto] → Hacer el cambio de dominios en un deploy aparte, con verificación de HTTPS inmediata; rollback = volver a la pestaña Domains.
- [Versión de Dokploy distinta en el servidor nuevo] → El compose solo depende de `dokploy-network`, del certresolver `letsencrypt` y de las entradas `web`/`websecure`; el simulacro lo confirma.
- [Secretos desactualizados en R2] → Se respaldan solos con cada conjunto (D7); como mucho, un día de atraso si el secreto se cambió en Dokploy sin deploy por el pipeline. Un `SECRET_KEY` viejo solo cierra sesiones, y `POSTGRES_PASSWORD` no afecta a la base restaurada (Context).

## Migration Plan

1. Crear el bucket R2, Bucket Lock, ciclo de vida y token (operador, con OK). Generar el par `age` en el PC del operador.
2. Desplegar el nuevo `enercheck-ci` en el servidor actual con `preparar-servidor.sh` (fase aplicación), ejecutar `respaldar diario` y comprobar el conjunto cifrado en R2.
3. Verificar que el conjunto del respaldo trae `.env.age` y que se descifra con las 19 variables.
4. Deploy con los labels de dominio y retiro de la pestaña Domains.
5. Simulacro en un VPS desechable con dominios de prueba: preparar → deploy → restaurar desde R2 → verificar login, boletas, vouchers → registrar tiempos → destruir.
6. Actualizar el runbook con lo aprendido.

Rollback: cada paso es aditivo. Volver al `enercheck-ci` anterior desactiva la subida; volver al compose anterior y a la pestaña Domains revierte los dominios.

## Open Questions

- Alerta activa cuando falla el respaldo diario (¿correo por Resend, n8n o un healthcheck externo tipo healthchecks.io?). No cambia el diseño: se agrega un aviso al final de `respaldar diario`.
- Días exactos de retención externa (propuesto: 35 diarios, 90 predeploy, archivos indefinido).
- Frecuencia del simulacro periódico (propuesto: cada 6 meses o tras un cambio de infraestructura).
