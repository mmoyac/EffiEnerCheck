# Proposal

## Why

Hoy producción depende de un único VPS: la base, las imágenes de boletas, los vouchers **y sus respaldos** están en el mismo disco, y los secretos de producción existen solo en el Environment de Dokploy. Si el servidor muere, se pierde todo. Cambiar de proveedor (por precio o por servicio) significa además rehacer a mano el endurecimiento, Dokploy, los dominios y la llave del CI.

El objetivo es que el proveedor sea desechable: volver a estar en producción en **alrededor de una hora** con la misma receta, sea porque el VPS murió o porque se decidió migrar.

## What Changes

- **Respaldo externo cifrado:** cada respaldo (diario y previo a un deploy) se cifra con `age` y se sube a un bucket S3-compatible (Cloudflare R2). La base va completa en cada respaldo; los archivos (imágenes de boletas, vouchers y, más adelante, fotos de medidores) se suben de forma **incremental**: solo los nuevos, y nunca se borran en R2. Así el respaldo no crece con cada foto ya respaldada. La llave privada para descifrar vive **fuera** del servidor. Las credenciales del servidor solo permiten escribir, no borrar; la antigüedad de los respaldos remotos la maneja una regla de ciclo de vida del bucket.
- **Restauración en un comando:** `enercheck-ci restaurar <ultimo|prefijo> [--desde r2|local]` baja el conjunto, lo descifra y restaura la base y los archivos que falten (`uploads` y `privado`), con la API detenida y verificación al final.
- **Secretos recuperables:** el Environment de producción se guarda cifrado con la misma llave `age` (en el bucket), de modo que un servidor nuevo recibe exactamente los mismos `POSTGRES_PASSWORD`, `SECRET_KEY` y claves de servicios.
- **Servidor reproducible:** `preparar-servidor.sh` deja un Ubuntu recién creado listo para producción: endurecimiento SSH, ufw, fail2ban, zona horaria, Dokploy, `dokploy-network` con la subred que esperan las imágenes, `enercheck-ci`, cron y llave del CI. Reemplaza a `instalar.sh` (que queda como la parte "aplicación" del mismo script).
- **Sin configuración solo en la interfaz:** los dominios del portal y de la landing pasan a declararse como `labels` de Traefik en `docker-compose.prod.yml`, versionados en el repo, en vez de la pestaña Domains de Dokploy.
- **Runbook «Migrar o recuperar el VPS»** en `DEPLOY.md`, con checklist y tiempos: TTL de Cloudflare, sitio en mantenimiento, último respaldo, servidor nuevo, restauración, secretos de GitHub, cambio de IP y verificación.
- **Simulacro obligatorio:** el runbook se ejecuta completo una vez en un VPS desechable antes de dar el cambio por cerrado, y se repite periódicamente.
- Fuera de alcance: **n8n** (mismo servidor, datos propios). El runbook lo menciona como pendiente aparte.

## Capabilities

### New Capabilities
- `recuperacion-produccion`: respaldo externo cifrado, restauración desde un respaldo externo, secretos de producción recuperables, preparación reproducible de un servidor nuevo y procedimiento documentado y probado de migración o recuperación.

### Modified Capabilities
<!-- Los requisitos de respaldo diario y previo al deploy viven todavía en el cambio sin archivar
     migrar-produccion-dokploy; aquí se agregan requisitos nuevos en vez de modificarlos. -->

## Impact

- **Código / infraestructura:** `infra/servidor/enercheck-ci` (subida a R2, archivos incrementales, `restaurar`, verificación; el respaldo local deja de incluir el `.archivos.tar.gz`), `CLAUDE.md` (regla de archivos inmutables), `infra/servidor/preparar-servidor.sh` (nuevo, absorbe `instalar.sh`), `docker-compose.prod.yml` (labels de Traefik), `DEPLOY.md` (§1–§3 simplificados, §7 respaldos, runbook nuevo), `.env.prod.example` (comentarios).
- **Dependencias en el servidor:** `age` y `rclone` (paquetes de Ubuntu). Ninguna dependencia nueva en la aplicación.
- **Servicios externos:** Cloudflare R2 (bucket privado, token con permiso solo de escritura, regla de ciclo de vida). Costo esperado: centavos al mes.
- **Pipeline:** el paso de respaldo previo al deploy sigue igual por SSH; ahora además sube a R2. Si la subida falla, el deploy se detiene igual que si falla el respaldo local.
- **Secretos de GitHub:** sin cambios de nombre; al migrar se actualizan `VPS_HOST`, `VPS_KNOWN_HOSTS`, `DOKPLOY_URL`, `DOKPLOY_API_KEY` y `DOKPLOY_COMPOSE_ID` (el runbook lo indica).
- **Datos personales:** los respaldos remotos siempre van cifrados; nada de su contenido se imprime en los logs del CI, que son públicos.
