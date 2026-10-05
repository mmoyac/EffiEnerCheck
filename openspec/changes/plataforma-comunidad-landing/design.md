# Design

## Context

- **Menús.** Viven en `menus` + `menu_roles`, y `GET /menus/me` filtra por rol. Los seeds (`app/db/seeds/menus.py`) insertan por id y **omiten las filas que ya existen**, y `app.arranque` los vuelve a ejecutar en cada arranque de producción. Por eso, cambiar menús existentes exige una migración con datos.
- **Portal.** Es una SPA (React Router) servida por su propio nginx (`frontend/`). El nginx compartido del VPS envía `/api/` y `/uploads/` al backend y el resto al frontend. En producción `VITE_API_URL=/api/v1`: el portal y la API comparten origen y no hay CORS.
- **Producción.** `docker-compose.prod.yml` define `db`, `backend` y `frontend`. El pipeline (`.github/workflows/deploy.yml`) construye las imágenes, las audita (`npm audit` en una matriz `app: [frontend]` y Trivy por imagen) y las despliega.
- **Condominio.** `Condominio` tiene `plan_suscripcion` (texto libre), pero nada indica qué funciones tiene contratadas.
- **Cambio en curso.** `rifas-solidarias` sigue sin archivar y modifica `control-acceso-multitenant`. Este cambio solo toca allí la exigencia del menú, que `rifas-solidarias` no modifica.

## Goals / Non-Goals

**Goals:**
- Dos productos vendibles por separado: la **landing** y la **administración** (el portal con sus módulos), con contenedores, imágenes y dominios distintos.
- Separación por módulos dentro del portal, aplicada en la API y no solo en el menú.
- Que pasar el contenido de la landing de un archivo a la base de datos cambie **un solo** componente del backend, sin tocar el contrato ni la landing.

**Non-Goals:**
- Una landing que funcione sin el backend de la plataforma. Su contenido sale de la API, y es la misma API que mañana usará el portal para editarlo.
- Que la plataforma se presente con la marca de cada condominio más allá del nombre (colores y logo del portal).
- Renderizado en servidor (SSR).
- Que los módulos reemplacen a los roles. Los roles definen qué hace cada persona y los módulos qué tiene contratado el condominio.

## Decisions

### D1. Módulos como catálogo en código y habilitación en tabla

`app/core/modulos.py` define `MODULOS = ("sitio", "portal", "energia", "rifas")` con su etiqueta y su grupo de menú. Por condominio se guarda la tabla `condominio_modulos (condominio_id FK, modulo VARCHAR, PK compuesta, CHECK modulo IN (...))`.

- *Alternativa:* una tabla catálogo `modulos`. Se descarta porque cada módulo nuevo exige código, así que el catálogo no crece solo con datos y tenerlo en la base sería una fuente de verdad duplicada.
- *Alternativa:* un `ARRAY`/`JSONB` en `condominios`. Se descarta porque la tabla permite el `CHECK`, joins simples y crecer a columnas por módulo (fecha de alta, plan).
- **Dos productos y dos módulos de administración.** `sitio` (landing) y `portal` (administración) son los productos. `energia` y `rifas` viven dentro del portal y exigen `portal`, regla que se valida al guardar (422). Con los dos productos, el `super_admin` expresa los tres casos comerciales: solo administración, solo landing o ambos.
- **Toda la parametrización comercial vive en la base y la edita el `super_admin` en Condominios:** módulos, `condominios.portal_url` y `condominio_dominios (dominio PK, condominio_id FK)`. Agregar un cliente o un dominio no exige desplegar. Solo el contenido editorial de la landing queda en archivos en v1 (D6).
- *Futuro:* cuando exista la edición del sitio desde el portal, un condominio "solo landing" necesitará que su `admin_condominio` entre al portal solo para eso. Se resolverá en ese cambio con un acceso limitado a la pantalla del sitio. Hoy ese caso no inicia sesión.
- `plan_suscripcion` no se toca.

### D2. Guardas: `portal` en la sesión y módulos en los routers

`get_current_user` rechaza con 403 a los usuarios no `super_admin` cuyo condominio no tiene `portal`. Como todas las guardas de rol dependen de esa función, el bloqueo cubre login, `/auth/me` y cualquier endpoint, también con sesiones ya abiertas. El login aplica la misma regla antes de emitir el token.

`modulo_requerido("energia")` es una fábrica de dependencias en `dependencies.py`. Reutiliza el usuario actual, deja pasar al `super_admin`, consulta `condominio_modulos` y responde `403` si el módulo no está habilitado. Se aplica al incluir los routers:

```python
api_router.include_router(boletas.router, dependencies=[Depends(modulo_requerido("energia"))])
```

- Así ningún endpoint de un módulo queda sin guarda por olvido, y los endpoints individuales no cambian.
- *Alternativa:* poner los módulos en el JWT. Se descarta porque el token dura hasta 60 minutos y deshabilitar un módulo debe tener efecto inmediato.

### D3. Pertenencia de menús: columna `menus.modulo`

La columna es nullable y `NULL` significa núcleo. La migración etiqueta por `path`: `/boletas`, `/lecturas` y `/liquidaciones` → `energia`, y `/rifas` → `rifas`. `/menus/me` agrega `modulo IS NULL OR modulo IN (...)`. El Sidebar agrupa con una constante del portal que replica el grupo de cada módulo.

- *Alternativa:* usar `parent_id` con menús "encabezado". Se descarta porque habría filas no navegables y el filtro por rol se complicaría.

### D4. La landing es una aplicación y un contenedor aparte

```
                    ┌─ www.condominiosantalaura.cl ──┐   ┌─ portal.condominiosantalaura.cl ─┐
                    │  (y el dominio sin www)        │   │  enercheck-santalaura.effi4tech.cl│
                    └───────────────┬────────────────┘   └────────────────┬─────────────────┘
                                    │        nginx_proxy (TLS)            │
                     /  ──► enercheck_landing            /  ──► enercheck_frontend (portal)
          /api/v1/sitio ──► enercheck_backend       /api/ ──► enercheck_backend
```

- **Código.** Directorio nuevo `landing/` con Vite, React, TS y Tailwind y su propio `package.json`. **No importa nada de `frontend/`**. El tipo `SitioPublico` se replica allí (es el contrato con la API, no código compartido) para que cada aplicación tenga su propio ciclo de dependencias y auditoría.
- **Imagen.** `landing/Dockerfile` (desarrollo) y `landing/Dockerfile.prod` (build multi-stage → nginx no root, `read_only`, como el portal), publicada como `enercheck-landing`. Contenedor `enercheck_landing` en `general-net`, con 32–64 MB.
- **API desde la landing.** El vhost de la landing solo envía al backend `location = /api/v1/sitio`. El resto de la API **no** queda expuesta en el dominio público: aunque alguien lo intente, desde `www.` no se llega al login ni a los endpoints privados. La landing llama a `/api/v1/sitio` en su mismo origen, sin CORS.
- **Enlace al portal.** El contenido trae `portal_url` (opcional). Si no está, la landing no muestra el acceso. Es el caso de un condominio que solo contrató la landing. A la inversa, un condominio con sitio propio solo enlaza a su `portal_url`. El portal no sabe nada de la landing.
- **El portal no cambia de rutas.** `/` sigue siendo el inicio por rol.
- *Alternativa descartada:* la landing dentro de la SPA del portal, en `/`. Es más simple de desplegar, pero amarra los dos productos: no se puede vender uno sin el otro, el portal arrastraría código público y un problema en uno obliga a redesplegar el otro.
- *Alternativa descartada:* sitio estático puro (Astro/HTML) con el contenido horneado en el build. Mejora el SEO, pero cada cambio de contenido exigiría reconstruir la imagen, lo que contradice el objetivo de que mañana el administrador edite el contenido desde el portal. Si el SEO llega a importar, se puede prerenderizar la landing en el build sin cambiar el contrato.

### D5. Contrato del sitio: schema Pydantic como fuente de verdad

`app/schemas/sitio.py` define `SitioPublico`, y `landing/src/types.ts` lo replica:

```
SitioPublico
  version_esquema: 1
  condominio: { nombre, lema?, descripcion_corta, logo_url?, color_primario? }   # logo y color los agrega el servicio desde la base
  portal_url?: str      # NO viene del archivo: lo agrega el servicio desde condominios.portal_url, solo si hay `portal`
  portada:    { titulo, subtitulo?, imagen_url?, cta_texto }
  comunidad?: { titulo, parrafos[], imagenes[]?, datos_clave[]? {etiqueta, valor} }
  avisos?:    [{ titulo, fecha, cuerpo, destacado? }]
  espacios?:  [{ nombre, descripcion, icono?, imagen_url? }]
  administracion?: { empresa?, directiva[] {cargo, nombre}, horario_atencion? }
  documentos?: [{ titulo, descripcion?, url }]
  contacto:   { telefonos[] {etiqueta, numero}, correo?, whatsapp?, horarios[]? }
  ubicacion?: { direccion, comuna, region, mapa_url? }
  pie:        { texto?, enlaces[]? }
```

- Las secciones opcionales que vienen ausentes o vacías no se dibujan.
- Los íconos se eligen por nombre de una lista cerrada. **Solo texto plano, sin HTML**: la landing no usa `dangerouslySetInnerHTML`. Así, cuando el administrador edite el contenido, no habrá XSS almacenado.
- `portal_url` y las URL de documentos e imágenes se validan como `https://` o como rutas relativas.

### D6. Origen del contenido detrás de un proveedor

`app/services/sitio.py` expone una sola función:

```python
async def obtener_sitio(host: str, db: AsyncSession) -> SitioPublico | None
```

- **Resolución (en la base, desde v1).** Host normalizado → `condominio_dominios` → condominio activo con `sitio`. Si no hay coincidencia, se usa `SITIO_POR_DEFECTO`.
- **Contenido hoy, desde archivos.** Lee `backend/app/sitio/contenido/*.json` al arrancar y valida cada uno; si alguno es inválido, el arranque falla con un mensaje claro. Cada archivo envuelve el contenido con `ruts_comunidad`, una lista que nunca se devuelve: el RUT de desarrollo es ficticio (`1-9`) y el de producción es el real, así que el mismo archivo sirve en ambos. El servicio busca el archivo por el RUT del condominio resuelto y le agrega `portal_url` desde la base. Un condominio con `sitio` y sin archivo responde 404, con una advertencia en el log.
- **Sitio por defecto.** `SITIO_POR_DEFECTO` cubre `localhost:3001` en desarrollo y cualquier host temporal antes de tener el dominio propio.
- **Host.** Se toma de `X-Forwarded-Host` o `Host`, que el nginx compartido ya fija con `$host`. Se pasa a minúsculas y se quitan el puerto y el `www.`.
- **Mañana, desde la base de datos.** Se reemplaza el proveedor de archivos y la landing no cambia:
  - Tabla nueva `sitio_contenido (condominio_id PK, contenido JSONB, version_esquema, publicado_en, actualizado_por)`, validada con el mismo schema al guardar. Es un solo JSONB con el schema como contrato, en vez de una tabla por sección. Los dominios y la `portal_url` ya están en la base desde v1.
  - Endpoints del portal: `GET` y `PUT /sitio/admin`, con `AdminRequired` y `modulo_requerido("sitio")`, y auditoría `SITIO_ACTUALIZADO`. Habrá un menú "Sitio web" en el grupo Comunidad.
  - Las imágenes se suben a `/app/uploads/sitio/<condominio_id>/`, y el vhost de la landing agrega `location /uploads/sitio/`.
  - Un script migra los JSON a la tabla.
  - El borrador y la publicación se deciden en ese cambio.
- **Caché.** `Cache-Control: public, max-age=300`.

### D7. Imágenes del sitio

En v1 van en `landing/public/sitio/<slug>/` y entran en la imagen de la landing. Para Santa Laura ya existe la portada provisoria: una ilustración vectorial original (`portada.svg`, que es la fuente editable) de la entrada del condominio con dos queltehues, exportada a `portada.webp` de 1600×900. Se regenera con cairosvg y Pillow si se edita la fuente. Se optimizan antes de subirlas (WebP, ≤ 1600 px y < 300 KB cada una). Agregar una foto exige desplegar la landing, y eso se acepta mientras el contenido lo administremos nosotros. Con la base de datos pasan a `/uploads/sitio/` (D6). Son públicas por naturaleza, así que no hay conflicto con la regla de los vouchers.

### D8. Marca

`frontend/src/config/marca.ts` exporta `PLATAFORMA = { nombre, modulos: { energia: 'EnerCheck', ... } }`. El Sidebar del portal muestra el nombre del condominio (de `/auth/me`) como título y `PLATAFORMA.nombre` como subtítulo. La landing muestra solo la marca del condominio, con un "Plataforma <nombre>" discreto en el pie. Mientras no haya nombre comercial, el nombre es `'EnerCheck'`.

### D10. Logo del condominio

- **Campo.** `condominios.logo_url` (nullable). Es parte de la parametrización del condominio, como `portal_url`, y no del contenido editorial: lo usan los dos productos. Lo exponen la respuesta del condominio, `/auth/me` (dentro de los datos del condominio del usuario) y `GET /sitio` (`condominio.logo_url`).
- **Almacenamiento.** `/app/uploads/condominios/<id>/logo-<uuid8>.<ext>`, en el volumen `uploads`, que ya es estático público y donde un logo puede vivir sin problema; nunca en `privado`. El nombre con uuid cambia en cada reemplazo y rompe la caché del navegador. El archivo anterior se borra después de confirmar la transacción.
- **Validación.** Máximo 1 MB (413) y tipo comprobado por los bytes iniciales: PNG `89 50 4E 47`, JPEG `FF D8 FF`, WEBP `RIFF....WEBP` (422). La extensión sale del tipo detectado, no del nombre recibido. **SVG queda excluido**: se serviría desde el mismo origen que la API y puede contener script. No se agrega Pillow: el logo no se transforma, y la landing y el portal lo ajustan con CSS (`object-contain`, altura fija).
- **Endpoints.** `POST` y `DELETE /condominios/{id}/logo`, con `SuperAdminRequired` y auditoría `UPDATE_CONDOMINIO_LOGO` (URL anterior y nueva).
- **Servido desde la landing.** El vhost de la landing agrega `location /uploads/condominios/` hacia el backend, solo ese prefijo. En el portal ya funciona con `/uploads/`.
- **Open Graph.** La landing usa el logo como `og:image` cuando no hay imagen de portada.

### D11. Color institucional

- **Campo.** `condominios.color_primario VARCHAR(7)` (nullable, `CHECK` contra `^#[0-9A-F]{6}$`). Va en `CondominioCreate`/`Update`/`Response`, con un validador que pasa a mayúsculas, y es parte de la parametrización, como el logo. Se expone en `/auth/me` y en `GET /sitio` (`condominio.color_primario`). Un solo color: con logo y color se reconoce la marca, y una paleta completa por condominio sería un editor de temas que nadie necesita todavía.
- **Santa Laura** usa el verde actual del portal, `#22C55E` (tono 500 de la escala de hoy). Así, `escalaDesde('#22C55E')` debe reproducir aproximadamente la escala `primary` vigente, y eso sirve de prueba visual de que la tematización no cambió nada para el condominio actual.
- **Escala derivada en el cliente.** A partir del hex, una función pura `escalaDesde(hex)` genera los tonos 50–950 en HSL: conserva el matiz, ajusta la luminosidad por tono y modera la saturación en los extremos. Hay una copia en el portal y otra en la landing, sin código compartido (D4); son unas 30 líneas con su test.
- **Portal.** `tailwind.config.ts` cambia `primary` de hex fijos a variables CSS (`'rgb(var(--primary-500) / <alpha-value>)'`). Así, las ~130 clases `primary-*` existentes toman el color del condominio sin tocar ninguna pantalla. Un `ThemeProvider` escribe las variables en `:root` al cargar `/auth/me` y restaura el verde actual (el default de la plataforma) al cerrar sesión o si no hay color.
- **Landing.** Usa el mismo mecanismo de variables CSS con el color recibido en `/sitio`, y `<meta name="theme-color">` con el color del condominio.
- **Legibilidad.** El texto sobre el color (botones) se elige por contraste WCAG: blanco o casi negro, según cuál supere 4.5:1. El portal es oscuro (`slate-900`), así que para texto y enlaces sobre ese fondo usa los tonos claros de la escala (300–400), igual que hoy. En Condominios, el selector de color muestra una vista previa del botón y del menú activo, y avisa si el color elegido da poco contraste.

### D9. Datos de Santa Laura en el archivo de contenido

El contenido inicial usa lo que se sabe (nombre, RUT y dirección de `condominios`, y que es una comunidad de parcelas con portería). Lo desconocido (fotos, directiva, teléfonos, horarios y documentos) va con el marcador explícito `"[POR CONFIRMAR] ..."` o con la sección omitida. Nada se inventa. Un test `xfail` informativo lista los marcadores que quedan.

## Risks / Trade-offs

- [Más piezas que desplegar: una imagen, un contenedor y un vhost más] → La landing sigue el mismo patrón que el portal, con nginx no root y `read_only`. El pipeline la trata igual (matriz y Trivy), y si se cae no afecta al portal.
- [El tipo del contrato está duplicado en el backend y en la landing] → El schema Pydantic es la fuente de verdad, y `version_esquema` permite detectar desajustes. Un test del backend compara las claves del JSON de ejemplo con las del schema. La duplicación es el precio de no acoplar las dos aplicaciones.
- [Que se publique un dato personal en el JSON] → La spec lo prohíbe, el schema solo tiene campos institucionales y la revisión del PR es el control.
- [Que la API privada quede accesible desde el dominio público] → El vhost de la landing solo envía `= /api/v1/sitio`, y se verifica en la tarea del vhost.
- [Deshabilitar `energia` en pleno período deja al lector sin pantalla] → Solo el `super_admin` cambia módulos, con confirmación y auditoría.
- [El SEO de una SPA es limitado] → Se aceptan los metadatos en tiempo de ejecución para v1. La mejora es prerenderizar la ruta `/` de la landing.

## Migration Plan

1. **Migración Alembic** (`modulos_y_sitio`): crea `condominio_modulos` con los cuatro módulos para cada condominio existente, crea `condominio_dominios`, agrega `condominios.portal_url` y agrega y etiqueta `menus.modulo`. El `downgrade` borra la tabla y la columna, sin pérdida de datos de negocio.
2. **Seeds.** `menus.py` declara `modulo` y `seed_condominios` habilita los cuatro módulos.
3. **Pipeline.** Agrega `landing` a la matriz de chequeos y construye, escanea y publica `enercheck-landing`. `docker-compose.prod.yml` suma `enercheck_landing`. El primer despliegue deja el contenedor arriba aunque todavía no exista el dominio.
4. **Dominio propio**, cuando NIC entregue el dominio:
   1. Crear en NIC los registros A de `condominiosantalaura.cl`, `www` y `portal` hacia la IP del VPS.
   2. Emitir un certificado con el certbot webroot del VPS que cubra los tres nombres.
   3. Instalar los vhosts:
      - `infra/nginx/condominiosantalaura-landing.conf`: `www` y el dominio sin `www` (que redirige a `www`), hacia la landing, más `= /api/v1/sitio`.
      - `infra/nginx/condominiosantalaura-portal.conf`: `portal.`, hacia el portal y `/api/`, y reutiliza la zona `enercheck_auth`.
   4. El `super_admin` registra en Condominios los dominios de la landing y la `portal_url`. No hace falta desplegar.
   - Todo queda en `DEPLOY.md`.
5. **Rollback.** Revertir el commit y ejecutar `alembic downgrade -1`. La landing se retira deteniendo su contenedor y su vhost, sin tocar el portal.

## Open Questions

- **Nombre comercial de la plataforma.** Hoy es `'EnerCheck'` en `marca.ts` y se puede cambiar sin afectar specs ni tareas.
- **Contenido real de Santa Laura** (fotos, directiva, teléfonos, horarios, reglamento público): lo entrega la administración. Mientras tanto quedan los marcadores (D9).
- **Si `enercheck-santalaura.effi4tech.cl` sigue como alias del portal** cuando exista `portal.condominiosantalaura.cl`: es una decisión del vhost que no afecta el código.
