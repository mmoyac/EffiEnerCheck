# Sitio público del condominio (landing)

La landing es uno de los **dos productos** de la plataforma. El otro es el portal de administración. Un condominio puede contratar solo la landing, solo el portal (enlazado desde su propia web) o ambos. Lo define el `super_admin` en **Condominios → Contratación**.

| Pieza | Dónde |
|---|---|
| Aplicación | `landing/` (Vite + React + Tailwind), contenedor `enercheck_landing` |
| Contrato | `GET /api/v1/sitio`, público, schema `backend/app/schemas/sitio.py` |
| Resolución y armado | `backend/app/services/sitio.py` |
| Contenido editorial (v1) | `backend/app/sitio/contenido/<slug>.json` |
| Parametrización | Base de datos: `condominio_modulos`, `condominio_dominios`, `condominios.portal_url`, `logo_url`, `color_primario` |
| Imágenes | `landing/public/sitio/<slug>/` |
| Spec | `openspec/specs/sitio-publico` (tras archivar el cambio `plataforma-comunidad-landing`) |

---

## Cómo se arma la respuesta

```
Host de la petición (X-Forwarded-Host / Host)
  → normalizado: minúsculas, sin puerto, sin "www."
  → condominio_dominios           (si no hay coincidencia: SITIO_POR_DEFECTO, por RUT)
  → condominio activo con módulo `sitio`            (si no: 404 "Sitio no encontrado")
  → contenido del archivo cuyo `ruts_comunidad` incluye su RUT   (si no hay archivo: 404 y aviso en el log)
  → + condominio.logo_url y condominio.color_primario  (desde la base)
  → + portal_url, solo si el condominio tiene el módulo `portal`
```

- La respuesta nunca incluye el RUT ni los dominios. Se cachea 5 minutos (`Cache-Control: public, max-age=300`).
- Sin `portal_url` en la respuesta, la landing no muestra **Acceso propietarios**. Es el caso de los condominios que solo contratan la landing.

## Secciones

Las secciones opcionales que vienen vacías o ausentes no se dibujan, ni tampoco su enlace en la navegación.

| Sección | Campo | Obligatoria | Para qué |
|---|---|---|---|
| Portada | `portada` | Sí | Nombre, lema, imagen y botón **Acceso propietarios** |
| Comunidad | `comunidad` | No | Presentación, datos clave (parcelas, superficie) y fotos |
| Avisos | `avisos[]` | No | Novedades públicas; las destacadas van primero |
| Espacios y servicios | `espacios[]` | No | Áreas comunes y servicios, con ícono de una lista cerrada |
| Administración y directiva | `administracion` | No | Empresa administradora, cargos y nombres aprobados, horario |
| Documentos | `documentos[]` | No | Documentos **públicos** (por ejemplo, el reglamento) |
| Contacto | `contacto` | Sí | Teléfonos, correo, WhatsApp y horarios |
| Ubicación | `ubicacion` | No | Dirección y enlace al mapa |
| Pie | `pie` | Sí (puede ir vacío) | Texto y enlaces |

**Por qué estas secciones.** Los portales de comunidades más usados en Chile, como ComunidadFeliz, Edipro o Kastor, concentran su valor en el área privada: gastos comunes, pagos, reservas y comunicados. Su cara pública suele limitarse a una página de acceso. Los sitios públicos de condominios y loteos de parcelas, en cambio, coinciden en un patrón que responde lo que pregunta un visitante, sea vecino, visita, corredor o postulante a comprar:

- qué es la comunidad (portada y comunidad);
- qué está pasando (avisos);
- con qué cuenta (espacios);
- quién la administra (administración);
- dónde están las reglas (documentos);
- cómo contactarla y llegar (contacto y ubicación).

El botón al portal une la cara pública con el área privada. Lo que es del área privada, como reservas, cobros y avisos internos, queda en el portal.

**Íconos permitidos:** `piscina`, `quincho`, `cancha`, `juegos`, `sendero`, `porteria`, `seguridad`, `estacionamiento`, `areas-verdes`, `sede`, `agua`, `luz`, `internet`, `mascotas`, `bicicleta`, `arbol`.

## Reglas del contenido

- **Solo texto plano.** El schema rechaza HTML y la landing nunca lo interpreta. Así, cuando el administrador lo edite, no habrá XSS almacenado.
- **URLs:** `https://…` o rutas relativas que empiecen con `/`.
- **Datos personales:** solo contacto institucional (portería y administración) y los cargos y nombres de la directiva que **la comunidad haya aprobado publicar**. Nunca datos del padrón, como parcelas, residentes o sus teléfonos y correos.
- Un teléfono o un correo que no tiene forma válida, como `[POR CONFIRMAR]`, se muestra como texto, sin enlace.
- **WhatsApp:** solo dígitos con código de país (`569XXXXXXXX`).

## Cómo editar el contenido hoy (v1)

1. Edita `backend/app/sitio/contenido/<slug>.json`. El archivo envuelve el contenido:

   ```json
   {
     "ruts_comunidad": ["1-9", "<RUT real>"],
     "sitio": { "condominio": {…}, "portada": {…}, "contacto": {…}, … }
   }
   ```

   `ruts_comunidad` es una lista porque el RUT de desarrollo es ficticio (`1-9`) y el de producción es el real: el mismo archivo sirve en ambos.
2. Comprueba que el archivo cumple el esquema con `python -m pytest tests/test_sitio.py -rx`. La prueba de marcadores lista cada `[POR CONFIRMAR]` pendiente.
3. Despliega el backend. Si un archivo no cumple el esquema, **el backend no arranca** y el mensaje indica el archivo y el campo.

Las imágenes van en `landing/public/sitio/<slug>/`, en WebP de hasta 1600 px y menos de 300 KB, y requieren desplegar la landing. La portada provisoria de Santa Laura es una ilustración original: `portada.svg` es la fuente y `portada.webp` la exportación. Para regenerarla:

```sh
python -c "import cairosvg,io;from PIL import Image;Image.open(io.BytesIO(cairosvg.svg2png(url='portada.svg',output_width=1600,output_height=900))).convert('RGB').save('portada.webp','WEBP',quality=86,method=6)"
```

Lo que **no** está en el archivo lo cambia el `super_admin` en Condominios, sin desplegar: dominios, URL del portal, logo, color y productos contratados.

## Plan: contenido en la base de datos, editado desde el portal

El contrato (`SitioPublico`) y la landing no cambian. Solo se reemplaza el origen del contenido en `services/sitio.py` (`_contenido_por_rut`):

1. **Tabla `sitio_contenido`**: `condominio_id` (PK), `contenido` JSONB, `version_esquema`, `publicado_en`, `actualizado_por`.
   - Se valida con el mismo `SitioPublico` al guardar.
   - Es un solo documento por condominio y no una tabla por sección: el schema ya es el contrato, y el formulario se arma por sección.
   - Si hace falta borrador y publicación, se resuelve en ese cambio, con dos filas o un campo de estado.
2. **Endpoints del portal:** `GET` y `PUT /api/v1/sitio/admin`, con `AdminRequired` y `modulo_requerido("sitio")`, y auditoría `SITIO_ACTUALIZADO`.
3. **Pantalla "Sitio web"** en el grupo Comunidad del menú, con un formulario por sección y vista previa. Las imágenes se suben a `/uploads/sitio/<condominio_id>/` y el vhost de la landing agrega esa ruta.
4. **Migración:** un script lee los JSON actuales y los inserta.
5. **Condominios solo con landing:** hoy sus usuarios no entran al portal. Para editar su sitio, el `admin_condominio` necesitará un acceso limitado a esa pantalla, que se define en ese cambio.

## Desarrollo

```bash
docker-compose up --build -d landing     # http://localhost:3001
```

- En `localhost`, el backend responde con el condominio de `SITIO_POR_DEFECTO` (`backend/.env`, RUT `1-9` = Santa Laura de prueba).
- El nginx de desarrollo de la landing aplica la misma CSP que producción. Si algo nuevo la rompe, se ve aquí.
- Para probar un dominio: regístralo en Condominios y llama a la API con ese host: `curl -H "Host: midominio.cl" http://localhost:8000/api/v1/sitio`.

Producción y dominio propio: [DEPLOY.md §11](../DEPLOY.md).
