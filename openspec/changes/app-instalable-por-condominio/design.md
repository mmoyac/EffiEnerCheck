# Design

## Decisions

1. **Resolución por `portal_url`:** se normaliza el host de la petición (`X-Forwarded-Host` o `Host`) con `utils.dominio.normalizar_host` y se compara con el host de `condominios.portal_url` de los condominios activos. Son pocos condominios: la consulta lee solo `id`, `nombre`, `color_primario` y `portal_url`, sin caché, para que un cambio se vea de inmediato.
2. **Manifiesto servido por la API, publicado como `/manifest.webmanifest`:** el nginx del portal (desarrollo y producción) reescribe esa ruta hacia `/api/v1/portal/manifest`, con `Content-Type: application/manifest+json` y `Cache-Control: no-cache`. En vite-plugin-pwa se usa `manifest: false`: el plugin sigue generando el service worker, pero no el manifiesto estático. El manifiesto no entra al precache.
3. **Íconos estáticos de la plataforma:** se generan una vez a partir del SVG del favicon (círculo y figuras en blanco sobre `#16a34a`) y se versionan en `frontend/public/icons/`:
   - `icon-192.png` e `icon-512.png`;
   - `icon-maskable-512.png`, con margen de seguridad;
   - `apple-touch-icon.png` (180 px).
4. **iPhone:** no usa `short_name` del manifiesto. Lee `<meta name="apple-mobile-web-app-title">` y `document.title`. Un módulo `marca.ts` pide `/portal/marca` al arrancar y los ajusta; también ajusta `theme-color`.

## Risks / Trade-offs

- **[El nombre bajo el ícono se fija al instalar]** → Android lo refresca con el tiempo al consultar el manifiesto; en iPhone hay que reinstalar. Se acepta.
- **[Nombres largos se cortan]** → Es el nombre del condominio tal como se registró; el super admin puede acortarlo.
