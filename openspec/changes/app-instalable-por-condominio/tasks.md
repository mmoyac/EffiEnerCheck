# Tasks

## 1. Backend

- [x] 1.1 `endpoints/portal.py`: `GET /portal/marca` y `GET /portal/manifest`, que resuelven el condominio por el dominio del `portal_url`, son públicos y se registran en `router.py`. Verificar con pruebas pytest: dominio de Santa Laura → su nombre y color; dominio desconocido → la plataforma; el manifiesto declara íconos de 192, 512 y *maskable*; no expone otros datos.

## 2. Frontend e íconos

- [x] 2.1 Generar `public/icons/` (192, 512, maskable 512 y apple-touch 180) y actualizar `index.html` (enlaces al manifiesto y `apple-touch-icon`). En `vite.config.ts`, `manifest: false`. Verificar que los archivos existen y que `npm run build` funciona.
- [x] 2.2 `src/marca.ts`: al arrancar, pide `/portal/marca` y ajusta el título, `apple-mobile-web-app-title` y `theme-color`. Verificar en el navegador que la pestaña del login dice "Santa Laura · EFFIComunidad".

## 3. nginx y documentación

- [x] 3.1 `frontend/nginx.conf` y `nginx.prod.conf`: `/manifest.webmanifest` hacia la API. Verificar con `nginx -t` y con `curl` en desarrollo que responde el manifiesto de Santa Laura.
- [x] 3.2 `CLAUDE.md` y `docs/sitio-publico.md` (o DEPLOY): explicar que la app instalada toma el nombre y el color del condominio. Verificar con `openspec validate app-instalable-por-condominio --strict`.
