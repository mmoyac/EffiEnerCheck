# Proposal

## Why

El portal se instala como app (PWA), pero hoy:
- el manifiesto es uno solo, fijo para toda la plataforma;
- apunta a íconos que no existen, así que el celular muestra un ícono genérico;
- bajo el ícono se lee "EFFIComunidad" (cortado en algunos Android), sin decir de qué condominio es.

Como la plataforma es multitenant y cada condominio entra por su propio dominio, la app instalada debe presentarse con el nombre del condominio.

## What Changes

- **Manifiesto dinámico por dominio:** `GET /manifest.webmanifest` lo genera la API según el dominio por el que se entra.
  - El condominio se identifica comparando el dominio con su `portal_url`.
  - Nombre bajo el ícono: el `nombre` del condominio (p. ej. "Santa Laura").
  - Nombre completo: "<nombre> · EFFIComunidad".
  - Color de la barra: el `color_primario` del condominio.
  - Sin coincidencia: la marca de la plataforma.
- **Marca pública del portal** (`GET /api/v1/portal/marca`): nombre y color según el dominio. El portal la usa antes del login para el título de la pestaña y para la etiqueta que lee iPhone al "Agregar a inicio".
- **Íconos reales de la plataforma:** 192 y 512 px (incluida la versión *maskable* para Android) y 180 px para iPhone, con el ícono de comunidad en verde. El logo de cada condominio como ícono queda fuera de alcance.

## Capabilities

### New Capabilities

_(ninguna)_

### Modified Capabilities

- `modulos-plataforma`: se agrega la presentación de la app instalable por condominio.

## Impact

- **Backend:** endpoint público `portal.py` (`/portal/marca` y `/portal/manifest`).
- **nginx del portal** (desarrollo y producción): `/manifest.webmanifest` hacia la API.
- **Frontend:**
  - `vite.config.ts` (`manifest: false`, se mantiene el service worker);
  - `index.html` (enlace al manifiesto y `apple-touch-icon`);
  - `public/icons/`;
  - la marca de la pestaña antes del login.
- **Orden de archivado:** `modulos-plataforma` la agrega el cambio `plataforma-comunidad-landing`, que se archiva primero.
