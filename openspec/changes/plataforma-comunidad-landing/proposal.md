# Proposal

## Why

El condominio Santa Laura pidió un sitio web propio (`www.condominiosantalaura.cl`) que presente a la comunidad y tenga un botón **"Acceso propietarios"** hacia el portal privado. Al mismo tiempo, el sistema creció más allá de la energía: las rifas solidarias son de la comunidad y no tienen relación con los medidores, y la landing tampoco la tendrá.

Para vender esto a otros condominios hay que separar dos productos que hoy se confunden:

- **La landing**: el sitio público del condominio, para cualquier visitante.
- **La administración**: el portal privado con login, compuesto por módulos. **Energía** es lo que hoy es EnerCheck (boletas, lecturas y liquidaciones). **Rifas** es de la comunidad.

Un condominio puede contratar **solo la administración**, porque ya tiene su propio sitio y solo lo enlaza; **solo la landing**; o **ambas**. Por eso la landing y el portal son aplicaciones distintas, con contenedores y dominios distintos, que solo comparten la API.

Conviene hacerlo antes del primer despliegue a producción. Así el condominio estrena la estructura definitiva.

## What Changes

- **Dos aplicaciones y dos contenedores.**
  - **Landing**: aplicación nueva en `landing/`, con su imagen Docker propia y servida en el dominio público del condominio (`www.condominiosantalaura.cl`).
  - **Portal de administración**: el frontend actual, que sigue en su contenedor y pasa a su propio subdominio (`portal.condominiosantalaura.cl`, además del host actual de `effi4tech.cl`).
  - Ninguna importa código de la otra. Se pueden desplegar, escalar y contratar por separado.
- **Contratación por condominio, parametrizada por el `super_admin`.** Catálogo fijo de módulos:
  - **`sitio`** (landing) y **`portal`** (administración) son los productos.
  - **`energia`** y **`rifas`** son módulos dentro del portal y exigen `portal`.

  Desde la pantalla Condominios, el `super_admin` define para cada cliente sus productos y módulos (solo administración, solo landing o ambos), la **URL del portal**, los **dominios de la landing** el **logo del condominio** (PNG, JPEG o WEBP) y su **color institucional**. El logo y el color se aplican a la landing y al portal: los botones, los acentos y el menú del portal toman el color de cada condominio. Todo queda en la base: sumar un cliente o un dominio no exige desplegar. Sin `portal`, los usuarios del condominio no pueden iniciar sesión. Lo que no pertenece a un módulo (usuarios, parcelas, panel y auditoría) es el **núcleo** del portal.
- **Menús por módulo y por rol.** Cada ítem de menú declara su módulo, o ninguno si es del núcleo. `GET /menus/me` devuelve solo los ítems del rol cuyos módulos estén habilitados en el condominio. El menú lateral los agrupa en "Energía", "Comunidad" y "Administración".
- **Guarda de módulo en el backend.** Los endpoints de boletas, lecturas y liquidaciones exigen `energia`, y los de rifas exigen `rifas`. Si el módulo no está habilitado, la respuesta es `403`, aunque el rol esté autorizado.
- **`/auth/me` informa los módulos.** El portal oculta las rutas de módulos no habilitados y elige una pantalla de inicio alternativa: por ejemplo, un parcelero sin `energia` aterriza en sus rifas.
- **Landing con las secciones habituales** en sitios de comunidades: portada con "Acceso propietarios", presentación, avisos, espacios y servicios, administración y directiva, documentos públicos, contacto (portería, administración, WhatsApp, horarios), ubicación y pie.
- **El contenido de la landing viene de un contrato de API.**
  - `GET /api/v1/sitio` es público. Identifica el condominio por el dominio y devuelve el contenido con un esquema fijo, que incluye la URL del portal cuando el condominio tiene `portal`.
  - En esta versión el contenido sale de un archivo JSON versionado, que configuramos nosotros.
  - Más adelante saldrá de la base de datos y lo editará el `admin_condominio` desde el portal. No cambian ni el contrato ni la landing.
- **Marca.** El portal se presenta con el nombre del condominio. "EnerCheck" identifica al módulo de energía. El nombre comercial de la plataforma se define en una sola constante.
- **Dominios.** Se documentan los vhosts de `condominiosantalaura.cl`/`www`, que van a la landing, y de `portal.condominiosantalaura.cl`, que va al portal, con un certificado Let's Encrypt. Se mantiene `enercheck-santalaura.effi4tech.cl` para el portal.

Fuera de alcance: la edición del contenido de la landing desde el portal, el formulario de contacto con envío de correo, la reserva de espacios comunes, los avisos internos, el cobro de gastos comunes y la facturación por plan.

## Capabilities

### New Capabilities

- `modulos-plataforma`: catálogo de módulos, habilitación por condominio, pertenencia de menús y endpoints a un módulo, guarda en la API, módulos en `/auth/me` y comportamiento del portal cuando un módulo no está habilitado.
- `sitio-publico`: landing pública como aplicación independiente del portal, resolución del condominio por dominio, contrato del contenido, origen del contenido (archivo hoy, base de datos mañana), enlace al portal y reglas sobre los datos personales publicados.

### Modified Capabilities

- `control-acceso-multitenant`: el menú de navegación filtra también por los módulos habilitados del condominio.
- `gestion-condominios`: al crear o editar un condominio, el `super_admin` define sus módulos habilitados.
- `infraestructura-despliegue`: se agrega el contenedor de la landing a los entornos de desarrollo y producción y al pipeline.

## Impact

**Backend**
- Tablas nuevas `condominio_modulos` y `condominio_dominios` y columnas `condominios.portal_url` y `menus.modulo`, con una migración que carga datos (los condominios existentes quedan con los cuatro módulos).
- Catálogo en `app/core/modulos.py` y guarda `modulo_requerido(...)` aplicada al incluir los routers.
- `menus.py`, `auth.py` y `condominios.py`, con sus schemas, incorporan los módulos.
- Endpoint público nuevo `sitio.py`, con el schema `schemas/sitio.py`, el servicio `services/sitio.py` y el contenido en `app/sitio/contenido/santa-laura.json`.

**Portal (`frontend/`)**
- Sidebar agrupado por módulo y con la marca del condominio, rutas protegidas por módulo, inicio por rol con alternativas, panel sin energía y selección de módulos en Condominios.
- Las rutas actuales no cambian: `/` sigue siendo el inicio por rol.

**Landing (`landing/`, nueva)**
- Vite, React, TypeScript y Tailwind, con sus propios `package.json`, `Dockerfile`, `Dockerfile.prod` y `nginx.conf`. Las imágenes van en `landing/public/sitio/<condominio>/`.

**Infraestructura**
- Servicio `landing` en `docker-compose.yml` y `docker-compose.prod.yml`.
- El pipeline construye, audita (`npm audit`, Trivy) y despliega la imagen de la landing.
- Vhosts en `infra/nginx/` y pasos en `DEPLOY.md`.

**Documentación**
- `CLAUDE.md`, `README.md`, `AGENTS.md` y `docs/` describen la plataforma: dos aplicaciones y un portal por módulos.

**Dependencias**
- Este cambio se archiva **después** de `rifas-solidarias`, que también modifica `control-acceso-multitenant`.

**Sin impacto** en el Motor EnerCheck, el OCR, los candados del período ni las reglas de las rifas.
