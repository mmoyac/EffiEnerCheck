# Tasks

## 1. Cuenta externa y llave (operador, con OK)

- [x] 1.1 [PC] Generar el par `age` (`age-keygen -o enercheck-respaldos.key`) y guardar la llave privada en dos lugares fuera del servidor (gestor de claves + copia offline). Versionar solo la **pública** en `infra/servidor/respaldos.age.pub`. Verificar que `age -r $(cat infra/servidor/respaldos.age.pub)` cifra y que `age -d -i <privada>` descifra un archivo de prueba.
- [x] 1.2 [Cloudflare] Crear el bucket R2 privado `efficomunidad-respaldos`, con Bucket Lock por prefijo (`diario/` 35 d, `predeploy/` 90 d, `secretos/` 365 d, `archivos/` indefinido), reglas de ciclo de vida que borren `diario/` y `predeploy/` después de esos plazos (nunca `archivos/`) y un token *Object Read & Write* limitado al bucket. Verificar con `rclone` desde el PC: subir un objeto de prueba funciona, y borrarlo o sobrescribirlo falla.

## 2. Respaldo externo en `enercheck-ci`

- [x] 2.1 En `infra/servidor/enercheck-ci`, subida incremental de archivos (D2, D4): listar `uploads` y `privado` desde el punto de montaje de cada volumen, compararlos con `rclone lsf -R r2:<bucket>/archivos/`, cifrar con la llave pública (`/opt/enercheck/respaldos.age.pub`) solo los que faltan y subirlos a `archivos/<volumen>/<ruta>.age`, sin borrar nada remoto. La salida informa solo cantidades y tamaño, nunca nombres de archivos. Verificar con `shellcheck` y en local: la primera ejecución sube todo, la segunda no sube nada, y tras agregar un archivo sube solo ese.
- [ ] 2.2 En `respaldar`, después de los archivos: dejar el conjunto local con `.dump`, `.compose.yml` e `.imagen.txt` (quitar el `.archivos.tar.gz`), cifrar esas partes, subirlas a `r2:<bucket>/<tipo>/` y subir al final `<prefijo>.sha256` con las sumas de los archivos cifrados. Borrar los `.age` temporales. Verificar con una ejecución de `respaldar diario` en el servidor actual: el conjunto y los archivos aparecen en R2, y `age -d` en el PC restaura un `.dump` que `pg_restore --list` acepta y un voucher que se abre.
- [x] 2.3 Manejo de fallos según D5: en `respaldar <sha>` un fallo de cifrado o subida termina con `exit 1` (el deploy no sigue); en `respaldar diario` se conserva la copia local, se registra el error y el script sale distinto de cero. Verificar ambos casos simulando un remoto inválido (`RCLONE_CONFIG` apuntando a un archivo vacío).
- [ ] 2.4 Actualizar DEPLOY.md §7 (respaldos externos: base por conjuntos y archivos incrementales, retención, cómo bajar y descifrar a mano desde el PC un dump y un archivo) y agregar a CLAUDE.md la regla «los archivos subidos son inmutables: reemplazar = nombre nuevo», de la que depende el respaldo incremental. Verificar que los comandos documentados funcionan copiados tal cual.

## 3. Restauración

- [x] 3.1 Agregar `enercheck-ci restaurar <ultimo|prefijo> [--desde r2|local] [--llave <archivo>] --confirmar` según D6: rechazado si llega por `SSH_ORIGINAL_COMMAND`; sin `--confirmar` no toca nada; descarga y verifica `.sha256`; descifra a un directorio 700; valida con `pg_restore --list` antes de detener nada; (R2) baja y descifra solo los archivos que faltan en los volúmenes; hace un respaldo local del estado vigente; detiene el backend, restaura la base (`--clean --if-exists`) y copia los archivos faltantes a los volúmenes con el dueño del contenedor, sin pisar ni borrar los existentes (con `--desde local`, solo la base); arranca el backend, espera `healthy` y borra los temporales con `shred`. Verificar con `shellcheck`.
- [x] 3.2 Probar `restaurar` en local con `-p enercheck_prodlocal`: restaurar un conjunto real, un conjunto con el `.dump` truncado (debe abortar sin tocar la base), una llave incorrecta (idem) y la ejecución sin `--confirmar` (no hace nada). Verificar login y apertura de un voucher tras la restauración correcta, y que restaurar desde R2 sobre volúmenes vacíos repone todos los archivos mientras que sobre volúmenes completos no copia ninguno.
- [x] 3.3 Reemplazar en DEPLOY.md §7 el bloque manual «Restaurar» por `enercheck-ci restaurar`, dejando el procedimiento manual como respaldo del respaldo. Verificar que el ejemplo coincide con el uso que imprime el script.

## 4. Secretos recuperables

- [ ] 4.1 Documentar en DEPLOY.md el comando del PC para cifrar el Environment de Dokploy y subirlo a `r2:<bucket>/secretos/produccion-<fecha>.env.age` (D7), y agregar el recordatorio en `.env.prod.example` y en cada sección de DEPLOY.md que cambia un secreto (§3, §3.1). Verificar subiendo la copia actual y descifrándola en el PC: las claves coinciden con las de Dokploy.

## 5. Servidor reproducible

- [ ] 5.1 Crear `infra/servidor/preparar-servidor.sh` (D8) con las tres fases, idempotente: sistema (paquetes, sshd solo llaves, ufw 22 limit/80/443, fail2ban `ssh.service`, zona horaria), plataforma (`dokploy-network` con `10.0.1.0/24` creada antes de Dokploy o verificada, instalación de Dokploy, cierre del puerto 3000) y aplicación (lo de `instalar.sh`, llave pública `age`, `rclone.conf` 600 con el token leído por stdin, línea de la llave del CI con comando forzado). Retirar `instalar.sh`. Verificar con `shellcheck` y ejecutándolo dos veces sobre el servidor actual sin cambios en la segunda pasada (fase plataforma: solo verificaciones).
- [x] 5.2 Actualizar DEPLOY.md §2 para usar `preparar-servidor.sh` y CLAUDE.md (estructura de `infra/servidor/`). Verificar con `grep -rn instalar.sh` sin referencias vigentes.

## 6. Dominios en el compose

- [ ] 6.1 Agregar a `frontend` y `landing` en `docker-compose.prod.yml` los labels de Traefik (D10) con `${DOMINIO_PORTAL}` y `${DOMINIO_SITIO}` (+ `www.`), y las variables a `.env.prod.example`. Verificar con `docker compose -f docker-compose.prod.yml config -q` y revisando que los labels resultantes tengan los hosts esperados.
- [ ] 6.2 [Dokploy, con OK] Agregar `DOMINIO_PORTAL` y `DOMINIO_SITIO` al Environment, desplegar y quitar los dominios de la pestaña Domains. Verificar `https://comunidadsantalaura.cl`, `https://www.…` (→ apex) y `https://portal.…` con certificados válidos, y que `http://` redirige. Actualizar DEPLOY.md §3 (paso Domains).

## 7. Runbook

- [ ] 7.1 Escribir en DEPLOY.md la sección «Migrar o recuperar el VPS» con dos variantes (migración planificada con mantenimiento según D11, y servidor perdido), marcas [PC]/[VPS]/[Dokploy]/[GitHub]/[Cloudflare], tiempos estimados, la lista de secretos de GitHub a actualizar, la verificación final y la mención de n8n como pendiente aparte. Verificar leyéndolo de corrido contra los scripts: cada orden existe con esos argumentos.

## 8. Simulacro (integración)

- [ ] 8.1 [Con OK] Crear un VPS desechable, apuntar dominios de prueba (p. ej. `prueba-portal.comunidadsantalaura.cl`) y seguir el runbook variante «servidor perdido» con un proyecto Dokploy de prueba: preparar → deploy de la imagen vigente → `restaurar ultimo --desde r2`. Verificar login con una cuenta real, detalle de una boleta con su imagen, apertura de un voucher, landing con logo, HTTPS válido y que el token R2 del servidor no puede borrar objetos. Registrar el tiempo total y la fecha en DEPLOY.md.
- [ ] 8.2 Corregir el runbook y los scripts con lo aprendido, destruir el VPS de prueba y borrar sus registros DNS. Ejecutar `openspec validate --specs --strict` y `openspec validate portabilidad-vps --strict` en verde.
