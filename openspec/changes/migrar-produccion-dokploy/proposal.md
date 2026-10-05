# Proposal

## Why

La producción vivía en el VPS compartido de effi4tech. Allí la entrada era un `nginx_proxy` externo al repositorio (TLS, enrutamiento y encabezados de seguridad), los contenedores se unían a la red `general-net` y el pipeline desplegaba por SSH. La plataforma ya es un SaaS de comunidades con dominio propio (`comunidadsantalaura.cl`) y se muda a un VPS dedicado (86.48.21.250) administrado con **Dokploy**, cuyo proxy es Traefik. Ninguna de esas tres piezas existe ahí, así que el despliegue actual no funciona en el servidor nuevo. Conviene migrar ahora: producción aún no tiene datos reales que trasladar.

## What Changes

- **El VPS nunca construye imágenes.**
  - GitHub Actions mantiene los chequeos (pytest, pip-audit, npm audit, build), la aprobación del environment `production`, el build de las tres imágenes, Trivy y el push a Docker Hub.
  - Dokploy despliega un compose de imágenes de registro, sin conexión al repositorio.
  - El pipeline dispara el despliegue con el webhook de Dokploy y termina bien solo si el backend queda sano.
- **Respaldo de la base y de los archivos.**
  - Antes de cada deploy, el pipeline respalda por SSH la base, `uploads`, `privado` y el compose vigente (conserva 10). Si el respaldo falla, no despliega.
  - Además, un respaldo diario programado en el servidor conserva 14 días.
- **Enrutamiento y seguridad.** Traefik solo enruta dominio → contenedor y termina TLS (Let's Encrypt). El enrutamiento por ruta y los encabezados de seguridad pasan al nginx de cada imagen:
  - el portal expone `/api/` y `/uploads/`;
  - la landing expone solo `GET /api/v1/sitio` y `/uploads/condominios/`.

  **BREAKING**: `infra/nginx/` deja de usarse.
- **Compose de producción.**
  - `general-net` se reemplaza por la red externa `dokploy-network`, y ningún servicio publica puertos.
  - La base queda en la red interna, sin salida a internet.
  - Se mantienen los nombres `enercheck_*` de contenedores, volúmenes e imágenes.
- **Dominios.**
  - `comunidadsantalaura.cl` y `www.comunidadsantalaura.cl` → landing.
  - `portal.comunidadsantalaura.cl` → portal.
  - DNS en Cloudflare (solo DNS).
  - Se retiran `enercheck-santalaura.effi4tech.cl` y `condominiosantalaura.cl`.
- **Datos iniciales copiados desde desarrollo, sin datos de prueba.** Un script nuevo e idempotente lleva a producción solo:
  - el condominio Santa Laura con sus módulos, color, `portal_url` y dominios de la landing;
  - sus parcelas;
  - sus parceleros con sus asignaciones, con una clave inicial nueva pedida por teclado.

  Excluye otros condominios, las cuentas de prueba del seed y todo dato operativo: boletas, lecturas, liquidaciones, rifas y auditoría.
- **Documentación.** `DEPLOY.md` se reescribe para Dokploy y Cloudflare: secretos, primer despliegue, rollback por `TAG` y restauración de respaldos. Se actualizan también `.env.prod.example` y `CLAUDE.md`, y se eliminan las referencias a effi4tech, `condominiosantalaura.cl` y `general-net`.

Fuera de alcance:
- renombrar la plataforma o los identificadores técnicos (el nombre comercial sigue en `config/marca.ts`);
- la configuración de `dokploy.` y `n8n.comunidadsantalaura.cl`, y el endurecimiento del servidor, ya hechos;
- respaldos fuera del servidor (S3).

## Capabilities

### New Capabilities

_(ninguna)_

### Modified Capabilities

- `infraestructura-despliegue`: se agregan los requisitos del despliegue a producción. La plataforma de despliegue no construye imágenes, cada despliegue lo precede un respaldo y lo cierra una verificación de salud, la entrada pública es por dominio con TLS automático, cada imagen web limita las rutas que expone, hay respaldos diarios y la carga inicial de datos no admite datos de prueba.

## Impact

- **Pipeline:** `.github/workflows/deploy.yml`, en el job `build-and-deploy`; el SSH queda limitado a una llave de comando forzado (respaldo y verificación de salud) y se agrega la llamada a la API de Dokploy. Secretos nuevos en el environment `production`: `DOKPLOY_URL`, `DOKPLOY_API_KEY`, `DOKPLOY_COMPOSE_ID` y `VPS_KNOWN_HOSTS`; `VPS_HOST`, `VPS_SSH_KEY` y `VPS_PORT` apuntan al servidor nuevo.
- **Imágenes:** `frontend/nginx.prod.conf` y `landing/nginx.prod.conf` (proxy al backend y encabezados de seguridad), `landing/Dockerfile.prod` y `landing/nginx.conf`.
- **Compose:** `docker-compose.prod.yml` y `.env.prod.example` (`FORWARDED_ALLOW_IPS` de `dokploy-network`).
- **Backend:** script nuevo `app/db/copiar_desde_desarrollo.py`.
- **Servidor:** proyecto compose en Dokploy y `infra/servidor/` (script `enercheck-ci` para respaldos y verificación, cron diario), que reemplaza a `infra/nginx/`.
- **Frontend:** `Login.tsx` (referencia a un dominio antiguo).
- **Docs:** `DEPLOY.md`, `CLAUDE.md` e `infra/nginx/`, que se elimina.
