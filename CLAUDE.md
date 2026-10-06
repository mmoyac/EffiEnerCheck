# CLAUDE.md — Guía para agentes de IA

Este archivo permite que cualquier agente de IA entienda rápidamente cómo está construido EnerCheck y cómo modificarlo sin romper nada.

> **Plataforma por módulos.** El repositorio es una plataforma para comunidades con **dos productos** que se contratan por separado: la **landing** pública del condominio (`landing/`) y el **portal de administración** (`frontend/`). Dentro del portal hay módulos: **Energía** (lo que históricamente se llamó EnerCheck: boletas, lecturas y liquidaciones) y **Rifas**. Ver la sección [Módulos y productos](#módulos-y-productos).

---

## ¿Qué hace el sistema?

EnerCheck distribuye el costo de una boleta eléctrica colectiva entre las parcelas de un condominio. El flujo mensual es:

```
Admin sube boleta (OCR) → Lector ingresa lecturas → Lector cierra lecturas
→ Admin calcula liquidaciones → Admin cierra período → Admin publica
→ Parcelero consulta su liquidación
```

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.11 · FastAPI (async) · SQLAlchemy 2 (async) · Alembic · Pydantic v2 |
| Base de datos | PostgreSQL 16 |
| Frontend | React 18 · TypeScript · Vite · Tailwind CSS · TanStack Query v5 |
| IA / OCR | Google Gemini Vision API (`gemini-2.5-flash`) |
| Infra | Docker · Docker Compose · Nginx |

---

## Estructura de directorios

```
EnerCheck/
├── backend/
│   ├── main.py                          # Punto de entrada FastAPI; monta /uploads y /health
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── router.py                # api_router (prefix /api/v1); agrupa los endpoints
│   │   │   └── endpoints/
│   │   │       ├── auth.py              # Login → JWT + /auth/me + recuperar / verificar-enlace / establecer-clave / cambiar-clave
│   │   │       ├── boletas.py           # CRUD boleta maestra + OCR + candados de período
│   │   │       ├── condominios.py       # CRUD condominios + parametrización comercial (módulos, dominios, portal_url, color, logo)
│   │   │       ├── lecturas.py          # CRUD lecturas de remarcadores
│   │   │       ├── liquidaciones.py     # Calcular (Motor EnerCheck) + consulta + pago
│   │   │       ├── menus.py             # GET /menus/me → navegación según rol
│   │   │       ├── parcelas.py          # CRUD parcelas del condominio
│   │   │       ├── rifas.py             # Rifas: venta, pagos, voucher, caja, cierre, imputaciones, CSV
│   │   │       ├── sitio.py             # GET /sitio: contenido PÚBLICO de la landing (resuelve el condominio por dominio)
│   │   │       └── usuarios.py          # CRUD usuarios + invitaciones ({id}/invitacion e invitaciones masivas)
│   │   ├── core/
│   │   │   ├── config.py                # Pydantic Settings (lee .env)
│   │   │   ├── modulos.py               # Catálogo de módulos: sitio, portal, energia, rifas
│   │   │   ├── dependencies.py          # get_db, TenantId, guardas de rol, modulo_requerido y exigencia de `portal`
│   │   │   ├── audit.py                 # registrar_auditoria(db, usuario_id, ...)
│   │   │   └── security.py              # hash/verify passwords, create_access_token
│   │   ├── models/                      # SQLAlchemy ORM (un archivo por entidad)
│   │   │   ├── auditoria.py             # AuditoriaLog
│   │   │   ├── boleta.py                # BoletaMaestra, BoletaItemDetalle
│   │   │   ├── condominio.py            # Condominio (+ portal_url, logo_url, color_primario)
│   │   │   ├── condominio_modulo.py     # CondominioModulo (módulos contratados), CondominioDominio (dominios de la landing)
│   │   │   ├── lectura.py               # LecturaParcela
│   │   │   ├── liquidacion.py           # LiquidacionParcela
│   │   │   ├── menu.py                  # Menu + tabla menu_roles
│   │   │   ├── parcela.py               # Parcela
│   │   │   ├── rifa.py                  # Rifa, CompraRifa, RifaNumero, ImputacionRifa
│   │   │   ├── rol.py                   # Rol
│   │   │   ├── usuario.py               # Usuario
│   │   │   └── usuario_parcela.py       # Tabla M2M usuario_parcelas
│   │   ├── schemas/                     # Pydantic v2 (request/response)
│   │   ├── services/
│   │   │   ├── enercheck.py             # Motor EnerCheck — fórmulas de distribución
│   │   │   ├── enlaces.py               # Enlaces de acceso de un solo uso (invitación 7 d, recuperación 1 h)
│   │   │   ├── correo.py                # Correo transaccional vía Resend (HTTP); nunca lanza
│   │   │   ├── claves.py                # asignar_clave(): política + hash + cierra sesiones
│   │   │   └── ocr.py                   # extraer_datos_boleta() → llama Gemini Vision
│   │   ├── arranque.py                  # Arranque de producción: valida .env, migra, catálogos, super admin
│   │   ├── db/
│   │   │   ├── session.py               # AsyncSession factory
│   │   │   ├── cargar_residentes.py     # Producción: parcelas y parceleros (pendientes) desde MATRIZ RESIDENTES.xlsx
│   │   │   ├── copiar_desde_desarrollo.py # Carga inicial: exporta un condominio de dev e importa en prod (sin datos de prueba)
│   │   │   ├── cambiar_clave.py         # Producción: cambiar una clave desde la consola del servidor
│   │   │   └── seeds/seeder.py          # Datos de prueba de DESARROLLO (roles, condominio, usuarios, boleta)
│   │   └── utils/
│   │       ├── format.py                # periodo_label(date) → "Mar. 2025"
│   │       └── telefono.py              # normalizar_telefono() → 56XXXXXXXXX (mismo criterio que utils/telefono.ts)
│   ├── alembic/                         # Migraciones de base de datos
│   ├── tests/                           # pytest contra Postgres real (motor, API, carga de producción)
│   ├── Dockerfile                       # Desarrollo
│   └── Dockerfile.prod + entrypoint.sh  # Producción: app.arranque y luego uvicorn
├── frontend/
│   ├── src/
│   │   ├── App.tsx                      # Rutas (protegidas por rol y por módulo con ModuloRoute)
│   │   ├── config/                      # modulos.ts (espejo del catálogo), marca.ts (nombre de la plataforma), inicio.ts (home por rol)
│   │   ├── pages/
│   │   │   ├── Login.tsx                # Formulario de acceso + «¿Olvidaste tu clave?»
│   │   │   ├── EstablecerClave.tsx      # Públicas /crear-clave y /restablecer-clave (token en el #)
│   │   │   ├── admin/
│   │   │   │   ├── Dashboard.tsx        # KPIs del período + boletas recientes
│   │   │   │   ├── Boletas.tsx          # Lista de boletas + botón Calcular → navega a detalle
│   │   │   │   ├── BoletaDetalle.tsx    # Detalle con tabs: Resumen / Lecturas / Liquidaciones / Boleta
│   │   │   │   ├── ModalEditDetalles.tsx# Edición manual de totales e ítems
│   │   │   │   ├── Condominios.tsx      # CRUD condominios (solo super_admin)
│   │   │   │   ├── Parcelas.tsx         # CRUD parcelas
│   │   │   │   ├── Rifas.tsx            # Lista y creación de rifas (RifaFormModal.tsx)
│   │   │   │   ├── RifaDetalle.tsx      # Compras / Registrar compra / Cobros, cerrar, reabrir, CSV
│   │   │   │   └── Usuarios.tsx         # CRUD usuarios
│   │   │   ├── lector/
│   │   │   │   ├── LectorDashboard.tsx  # Vista móvil: parcelas pendientes + progreso
│   │   │   │   └── CapturarLectura.tsx  # Pantalla de captura por parcela
│   │   │   └── parcelero/
│   │   │       ├── MiLiquidacion.tsx    # Vista del parcelero: lista de períodos → detalle (+ aviso de rifa abierta)
│   │   │       └── Rifas.tsx            # /mis-rifas: grilla de compra y compras de su parcela
│   │   │   └── porteria/
│   │   │       └── VentaRifa.tsx        # /porteria: venta rápida, comprobante, búsqueda y caja
│   │   ├── components/                  # UI atómica (Badge, Modal, etc.) + layout/ + rifas/ (NumeroGrid, CompraPanel, ComprasLista)
│   │   ├── api/                         # Clientes HTTP por recurso
│   │   │   ├── client.ts                # axios instance (lee VITE_API_URL, añade JWT, 401 → /login)
│   │   │   ├── auth.ts                  # authApi.login / authApi.me
│   │   │   ├── boletas.ts               # boletasApi.*
│   │   │   ├── condominios.ts           # condominiosApi.*
│   │   │   ├── lecturas.ts              # lecturasApi.*
│   │   │   ├── liquidaciones.ts         # liquidacionesApi.*
│   │   │   ├── menus.ts                 # menusApi.*
│   │   │   ├── parcelas.ts              # parcelasApi.*
│   │   │   ├── rifas.ts                 # rifasApi.* (incluye descarga del CSV con token)
│   │   │   └── usuarios.ts              # usuariosApi.*
│   │   ├── context/
│   │   │   └── AuthContext.tsx          # Estado de sesión; restaura vía /auth/me
│   │   ├── hooks/
│   │   │   └── useAuth.ts               # useAuth(), useRole(), useModulos(), useModulo(m)
│   │   ├── utils/color.ts               # Escala de tonos desde el color institucional (TemaCondominio la aplica)
│   │   └── types/index.ts               # Interfaces TypeScript (BoletaMaestra, Lectura, Sesion, etc.)
│   └── Dockerfile
├── landing/                             # LANDING pública: app aparte (Vite+React+Tailwind), contenedor propio
│   ├── src/                             # App.tsx, secciones/, types.ts (espejo de SitioPublico), color.ts, tema.ts
│   ├── public/sitio/<condominio>/       # Imágenes del sitio (portada.webp + su fuente portada.svg)
│   └── Dockerfile / Dockerfile.prod     # Dev :3001 / producción (nginx no root, solo lectura)
├── docker-compose.yml                   # Desarrollo
├── docker-compose.prod.yml              # Producción: compose "raw" de Dokploy, imágenes fijadas al commit (ver DEPLOY.md)
├── .env.prod.example                    # Plantilla del Environment de Dokploy (los secretos nunca van al repo)
├── .github/workflows/deploy.yml         # CI/CD: checks en develop/PR; main → aprobación → Docker Hub → Dokploy
├── infra/servidor/                      # enercheck-ci (respaldos y espera-sano, comando forzado del CI) + instalar.sh
├── security/                            # Excepciones de pip-audit y Trivy (documentadas)
├── DEPLOY.md                            # Pasos manuales de producción, respaldos, rollback
├── openspec/
│   ├── specs/                           # Specs de las capacidades actuales (línea base)
│   └── changes/                         # Propuestas de cambio en curso + archive/
├── docs/
│   ├── README.md                        # Índice de la documentación
│   ├── flujo-periodo.md                 # Ciclo mensual: pasos, endpoints, candados, reversas
│   ├── flujo-periodo.html               # El mismo flujo en formato visual
│   ├── rifas.md                         # Rifas solidarias: flujo, reglas y endpoints
│   ├── sitio-publico.md                 # Landing: contrato, contenido, secciones y plan de edición desde el portal
│   └── presentacion-comunidad.md        # Documento para reunión de la comunidad
├── schema.dbml                          # Fuente de verdad del esquema DB (DB Diagram)
├── README.md                            # Documentación técnica GitHub
├── AGENTS.md                            # Contexto de producto y decisiones de diseño
└── CLAUDE.md                            # Este archivo
```

---

## OpenSpec — specs del sistema

`openspec/specs/` contiene la **línea base**: qué hace EnerCheck hoy, capacidad por capacidad, en formato requisito + escenarios. Antes de modificar una parte del sistema, lee la spec de esa capacidad: describe el comportamiento esperado sin obligarte a reconstruirlo leyendo el código.

| Spec | Cubre |
|------|-------|
| `autenticacion` | Login JWT, bcrypt, `/auth/me`, sesión en el cliente |
| `control-acceso-multitenant` | Roles, guards, aislamiento por `condominio_id`, menús |
| `gestion-condominios` | CRUD condominios (super_admin), soft-delete |
| `gestion-parcelas` | Padrón, orden natural, flag `activa` |
| `gestion-usuarios` | Cuentas, M2M con parcelas, borrado solo super_admin |
| `boletas-maestras` | Creación del período, auto-lecturas, arrastre de ítems, imagen |
| `ocr-boletas` | Gemini Vision, IVA 19%, fuzzy matching de ítems |
| `lecturas-remarcadores` | Captura, contador no regresivo, `fecha_toma`, vista del lector |
| `ciclo-periodo` | Los 3 candados, cerrar/reabrir, publicación, inmutabilidad |
| `motor-liquidaciones` | Fórmulas, diferencial, idempotencia, consulta y pago |
| `portal-parcelero` | Desglose, estado de pago, transparencia de la boleta |
| `consola-administrativa` | Dashboard, pestañas, filtros, manejo de errores |
| `auditoria` | Vocabulario de acciones, before/after, exclusión de secretos |
| `infraestructura-despliegue` | Docker, envs, volúmenes, Alembic, seeds |

**Reglas de trabajo:**

- Las specs describen el **estado actual**, no deseos. Si cambias el comportamiento, la spec queda desactualizada hasta que la actualices.
- No edites `openspec/specs/` a mano para introducir una funcionalidad nueva. El flujo es: propuesta de cambio → implementación → archivado, y el archivado sincroniza las specs.
- Los requisitos usan `DEBE (SHALL)` / `NO DEBE (SHALL NOT)` porque el validador exige la palabra clave RFC 2119 literal en mayúsculas. Mantén esa forma.
- Valida siempre antes de dar por cerrado un cambio: `openspec validate --specs --strict`.

**Comandos:**

```bash
openspec list --specs               # Capacidades registradas
openspec show <capacidad>           # Ver una spec
openspec validate --specs --strict  # Validar todas
```

Slash commands disponibles en Claude Code: `/opsx:propose`, `/opsx:apply`, `/opsx:explore`, `/opsx:archive`.

---

## Roles y RBAC

Los guards se aplican como dependencias FastAPI en cada endpoint:

| Dependencia | Roles permitidos |
|-------------|-----------------|
| `AdminRequired` | `super_admin`, `admin_condominio` |
| `LectorRequired` | `super_admin`, `admin_condominio`, `lector` |
| `AnyRoleRequired` | `super_admin`, `admin_condominio`, `lector`, `parcelero` — **no** incluye `porteria` |
| `PorteriaRequired` | `super_admin`, `admin_condominio`, `porteria` |
| `RifaAccesoRequired` | los cinco roles; solo endpoints de consulta de rifas |
| `TenantId` | extrae `condominio_id` del JWT; `super_admin` recibe `None` (acceso global) |

En el frontend, las rutas están protegidas en `App.tsx` con `useRole()` y, las de un módulo, con `<ModuloRoute modulo="...">`. La pantalla de inicio por rol se define **una sola vez** en `config/inicio.ts` (`pantallaDeInicio(rol, modulos)`), con alternativas cuando la principal es de un módulo no contratado.

> ⚠️ `porteria` (cuenta compartida de la portería, solo vende rifas) queda **fuera** de `AnyRoleRequired` a propósito: varios endpoints `AnyRoleRequired` solo filtran por parcela cuando el rol es `parcelero`, así que un rol nuevo agregado ahí vería todo el condominio. Al crear un rol nuevo, define sus guardas explícitamente y su entrada en `config/inicio.ts`.

---

## Módulos y productos

Los **roles** dicen qué hace cada persona; los **módulos** dicen qué contrató cada condominio. Los define el `super_admin` en Condominios (spec `modulos-plataforma`).

| Módulo | Tipo | Qué habilita |
|--------|------|--------------|
| `sitio` | Producto | Landing pública (`landing/`) vía `GET /api/v1/sitio` |
| `portal` | Producto | Login de los usuarios del condominio y el núcleo (usuarios, parcelas, panel, auditoría) |
| `energia` | Módulo del portal (exige `portal`) | Boletas, lecturas, liquidaciones, Motor EnerCheck |
| `rifas` | Módulo del portal (exige `portal`) | Rifas solidarias y venta en portería |

- **Catálogo** en `backend/app/core/modulos.py` (fuente de verdad) y su espejo `frontend/src/config/modulos.ts`. Agregar uno exige además ampliar el `CHECK` de `condominio_modulos`.
- **Guarda en la API:** todo router de un módulo se incluye en `router.py` con `dependencies=[Depends(modulo_requerido("<modulo>"))]` → 403 `"El módulo <x> no está habilitado para este condominio"`. Esconder el menú no basta.
- **Sin `portal`**, `get_current_user` y el login responden 403 `"Tu condominio no tiene contratado el portal de administración"` (efecto inmediato también sobre sesiones abiertas: los módulos no van en el JWT).
- `get_current_user` deja los módulos en `current_user.modulos` (el `super_admin` tiene todos). `/auth/me` los informa junto con la marca del condominio (`condominio: {nombre, logo_url, color_primario}`).
- **Menús:** `menus.modulo` (NULL = núcleo). `/menus/me` oculta los de módulos no contratados; el Sidebar agrupa en Energía / Comunidad / Administración.
- **Parametrización comercial** (solo `super_admin`, auditada como `UPDATE_CONDOMINIO` / `UPDATE_CONDOMINIO_LOGO`): `modulos`, `portal_url`, `dominios_sitio` (únicos entre condominios), `color_primario` (`#RRGGBB`) y el logo (`POST/DELETE /condominios/{id}/logo`: PNG/JPEG/WEBP ≤ 1 MB, verificado por bytes; nunca SVG; en `/uploads/condominios/`).
- **Color institucional:** la escala `primary-*` de Tailwind del portal son variables CSS (`index.css`) que `TemaCondominio` reemplaza con `escalaDesde(color)`. Usa siempre clases `primary-*` para acentos (no hex fijos) y el portal tomará el color de cada condominio.

### Landing (`landing/`) — producto aparte

- **No importa nada de `frontend/` ni viceversa.** Comparten solo el contrato de la API. `landing/src/types.ts` replica `backend/app/schemas/sitio.py` (fuente de verdad) y `landing/src/color.ts` copia el util del portal a propósito.
- Su única llamada es `GET /api/v1/sitio` (mismo origen). En producción su nginx (`landing/nginx.prod.conf`) expone solo esa ruta y `/uploads/condominios/`, con una CSP estricta: nada de scripts, estilos ni fuentes de terceros.
- **Contenido editorial:** `backend/app/sitio/contenido/<slug>.json` (validado al arrancar; inválido = no arranca). **Parametrización** (dominios, portal_url, logo, color): en la base. Ver [docs/sitio-publico.md](docs/sitio-publico.md).
- Dev: `docker-compose up --build -d landing` → http://localhost:3001 (muestra `SITIO_POR_DEFECTO` del `backend/.env`).

---

## Acceso por invitación (claves)

Nadie conoce la clave de otro (spec `acceso-por-enlace`):

- **Cuenta pendiente** = `password_hash` NULL: no inicia sesión (401 genérico). El listado de usuarios expone `estado: pendiente|activa`. Las cargas de producción crean siempre cuentas pendientes.
- **Enlaces de un solo uso** (`enlaces_acceso`, solo el sha256 del token): invitación (7 días) y recuperación (1 hora). Emitir uno nuevo anula los vigentes del mismo tipo. El token va en el **fragmento** (`/crear-clave#<token>`), nunca en la ruta ni en logs.
- **Toda clave pasa por `services/claves.asignar_clave()`**: política (`security.validar_clave`: ≥ 10 caracteres y no una de `CLAVES_CONOCIDAS`), hash y `clave_cambiada_en`. `get_current_user` rechaza los JWT con `iat` anterior: cambiar la clave cierra las demás sesiones.
- **`/auth/recuperar` responde siempre 202 igual**, exista o no la cuenta (no revela correos). nginx limita por IP `recuperar`, `verificar-enlace` y `establecer-clave` (zona `enercheck_auth`).
- **Correo:** `services/correo.enviar()` (Resend; sin `RESEND_API_KEY` devuelve `ok=False` con el motivo). La invitación individual devuelve el enlace al admin para reenviarlo por WhatsApp (`utils/whatsapp.ts`).

---

## Multitenancy

Todos los queries deben filtrar por `condominio_id`. El patrón es:

```python
# En cada endpoint que lista recursos:
if tenant_id is not None:
    stmt = stmt.where(Modelo.condominio_id == tenant_id)
```

`TenantId` es `None` solo para `super_admin`. Para todos los demás, viene del JWT.

---

## Máquina de estados del período (BoletaMaestra)

```
lecturas_cerradas = False  →  Lector/Admin puede editar lecturas
                            →  Admin puede calcular liquidaciones (idempotente)
        ↓  cerrar-lecturas
lecturas_cerradas = True   →  Admin puede calcular y cerrar liquidaciones
        ↓  cerrar-liquidaciones (requiere al menos 1 LiquidacionParcela)
liquidaciones_cerradas = True  →  Período cerrado, sin modificaciones
        ↓  PATCH boleta_visible_usuarios=true
boleta_visible_usuarios = True  →  Parceleros pueden ver su liquidación
```

**Reverso:**
- `reabrir-lecturas`: requiere `!liquidaciones_cerradas`
- `reabrir-liquidaciones`: requiere `!boleta_visible_usuarios`

**Lógica de botones en `BoletaDetalle.tsx`:**
```
Calcular      → visible si !lecturas_cerradas && !liquidaciones_cerradas
Cerrar período → visible si lecturas_cerradas && liquidaciones.length > 0 && !liquidaciones_cerradas
Reabrir lect.  → visible si lecturas_cerradas && !liquidaciones_cerradas
Reabrir liqs.  → visible si liquidaciones_cerradas && !boleta_visible_usuarios
Publicar      → visible si liquidaciones_cerradas && !boleta_visible_usuarios
```

---

## Motor EnerCheck (`backend/app/services/enercheck.py`)

Para garantizar que el total liquidado sea exactamente igual a la emisión, el valor base se calcula a la inversa:
```
monto_total_energia = monto_total_emision - (suma_items_fijo + suma_items_variable)
valor_kwh     = monto_total_energia / total_kwh_compania
diferencial   = (total_kwh_compania − Σ kwh_remarcadores) × valor_kwh
cuota_fija    = (Σ ítems_fijo + diferencial) / total_parcelas_activas
prorrateo_var = Σ ítems_variable × (kwh_parcela / Σ kwh_remarcadores)
monto_energia = valor_kwh × kwh_parcela
total_pagar   = monto_energia + prorrateo_var + cuota_fija
```

El motor es **idempotente**: hace `DELETE FROM liquidaciones WHERE boleta_id = X` antes de insertar. Se puede llamar múltiples veces sin duplicar datos.

El endpoint `POST /liquidaciones/calcular/{boleta_id}` puede ejecutarse con `lecturas_cerradas = False` (permite recalcular tras correcciones de lecturas).

---

## Rifas solidarias (`backend/app/api/v1/endpoints/rifas.py`)

Módulo **aparte** de la boleta: nada de lo recaudado entra a `liquidaciones_parcelas` ni al Motor EnerCheck. No mezclar. Detalle en [docs/rifas.md](docs/rifas.md).

- **Formas de pago** por compra: `efectivo` (solo portería/admin; pagada al registrar), `transferencia` (pendiente hasta `confirmar-pago`) y `gasto_comun` (al cerrar genera `ImputacionRifa` por parcela, que se carga a mano en **Comunidad Feliz**). El `canal` (`portal`/`porteria`/`administracion`) lo decide el servidor según el rol.
- **Unicidad**: `UNIQUE (rifa_id, numero)` en `rifa_numeros` + `SELECT ... FOR UPDATE` sobre la rifa (que también protege el contador `ultimo_folio`). Al anular se **borran** las filas de `rifa_numeros`; la `CompraRifa` queda `anulada=True` con sus `numeros`. La portería no anula.
- **Folio** `R{rifa_id}-{folio:03d}` correlativo por rifa; no se reutiliza.
- **Vouchers** en `/app/privado/vouchers` (volumen `privado_data`), **nunca** en `/app/uploads`, que se sirve como estático público. Se entregan solo por `GET .../compras/{cid}/voucher` (staff o usuarios de la parcela). `POST /compras` es multipart (`datos` JSON + `voucher`); en transferencias de portería el voucher es obligatorio.
- `GET /rifas/{id}` recorta la respuesta: `numeros_vendidos` sin dueño para todos; `compras` e `imputaciones` solo de las parcelas del usuario (todas si es admin o portería).
- Estados: `abierta` → `cerrar` (genera imputaciones) → `cerrada` → `reabrir` (solo sin imputaciones `cargada`; las borra).
- Comprobante por WhatsApp: enlace `wa.me` armado en el frontend (`utils/comprobante.ts`); el sistema no envía mensajes.
- React Query keys: `['rifas']`, `['rifas', 'abierta']`, `['rifa', id]`, `['rifa-caja', id]`, `['rifa-parcelas', id]`, `['rifa-telefonos', id, parcelaId]`, `['rifa-compras', id, filtros]`.

---

## OCR / Gemini (`backend/app/services/ocr.py`)

`extraer_datos_boleta(image_bytes, content_type)` llama a `gemini-2.5-flash` con un prompt estructurado. Retorna un dict con los campos de la boleta. El endpoint guarda la imagen en `/app/uploads/boletas/` y añade `file_url` al response. Si el OCR falla, borra el archivo subido.

---

## Patrones de backend

### Selectinload obligatorio
Siempre cargar relaciones con `selectinload` para evitar el error `MissingGreenlet` en contextos async:

```python
select(BoletaMaestra).options(selectinload(BoletaMaestra.items_detalle))
```

### Helper `_get_X_o_404`
Cada endpoint usa un helper privado que levanta 404 si no encuentra el registro. Convención: `_get_boleta_o_404(id, db)`.

### Auditoría
Toda mutación importante llama a `await registrar_auditoria(db, usuario_id, condominio_id, accion, detalles)`. Las acciones son strings en SCREAMING_SNAKE_CASE.

### Validaciones de estado
Los endpoints de transición de estado retornan `409 Conflict` cuando la transición no es válida (e.g., cerrar lecturas que ya están cerradas).

---

## Patrones de frontend

### React Query keys
```
['boletas']                    → lista de boletas
['boleta', boletaId]           → boleta individual con items_detalle
['lecturas', boletaId]         → lecturas del período
['liquidaciones', boletaId]    → liquidaciones calculadas
['parcelas']                   → lista de parcelas del condominio
```

Siempre invalidar la key correcta en `onSuccess` de mutations.

### Navegación con tab en URL
`BoletaDetalle.tsx` usa `useSearchParams` para leer `?tab=resumen|lecturas|liquidaciones`. Después de calcular, `Boletas.tsx` navega a `/boletas/${id}?tab=liquidaciones`.

### Manejo de errores de API
```typescript
} catch (err: unknown) {
  const msg = (err as AxiosError<{detail: string}>)?.response?.data?.detail
  setError(msg ?? 'Error desconocido')
}
```

### Orden natural de parcelas
```typescript
.sort((a, b) => a.nombre.localeCompare(b.nombre, 'es', { numeric: true, sensitivity: 'base' }))
```

### Cliente HTTP
`frontend/src/api/client.ts` — axios instance con baseURL `VITE_API_URL` e interceptor que añade `Authorization: Bearer <token>` desde localStorage.

---

## Agregar un nuevo endpoint

1. Crear/editar el archivo en `backend/app/api/v1/endpoints/`
2. Si es un modelo nuevo, crear `backend/app/models/nuevo.py` y el schema en `backend/app/schemas/`
3. Registrar el router en `backend/main.py` si es un archivo nuevo
4. Crear la migración: `docker exec enercheck-backend-1 alembic revision --autogenerate -m "descripcion"`
5. Aplicar: `docker exec enercheck-backend-1 alembic upgrade head`
6. Agregar el cliente en `frontend/src/api/nuevo.ts`
7. Agregar los tipos en `frontend/src/types.ts`
8. **Rebuild el container** tras cambios en código: `docker-compose up --build -d backend`

> ⚠️ `docker-compose restart backend` NO recarga código nuevo. Siempre usar `--build`.

---

## Agregar una nueva página de admin

1. Crear `frontend/src/pages/admin/NuevaPagina.tsx`
2. Registrar la ruta en `frontend/src/App.tsx` dentro del bloque de rutas protegidas por rol admin
3. Agregar el link en el sidebar/nav (`frontend/src/components/Layout.tsx` o similar)

---

## Agregar un campo a un modelo existente

1. Editar el modelo SQLAlchemy en `backend/app/models/`
2. Editar el schema Pydantic en `backend/app/schemas/` (Request, Response, Update)
3. Crear migración Alembic y aplicar
4. Actualizar el tipo TypeScript en `frontend/src/types.ts`
5. Actualizar el endpoint si hay lógica de negocio relacionada

---

## CI/CD y producción

Detalle y pasos manuales en [DEPLOY.md](DEPLOY.md). Lo que hay que saber al cambiar código:

- **Ramas:** se trabaja en `develop` y `main` es solo producción. Cada push a `main` despliega, previa aprobación del environment `production`. No hagas push a `main` sin que lo pidan.
- **Producción = Dokploy** en `86.48.21.250` (`comunidadsantalaura.cl`, DNS en Cloudflare). El VPS **nunca construye**: el pipeline publica en Docker Hub y Dokploy solo descarga. Traefik enruta por dominio; las reglas por ruta, los encabezados de seguridad y el límite de login viven en `frontend/` y `landing/nginx.prod.conf` (+ `snippets/seguridad.conf`): un cambio de seguridad HTTP se hace ahí, no en el servidor.
- **Scripts que corren en Linux** (`*.sh`, `infra/servidor/*`, `*.conf`, `Dockerfile*`) van con LF (`.gitattributes`).
- **El CI debe quedar en verde:** `pytest`, `pip-audit`, `npm audit --omit=dev --audit-level=high` y `npm run build`. Una vulnerabilidad nueva se corrige actualizando la dependencia. Solo si no hay parche se documenta en `security/excepciones.md`.
- **Seeds:** `app/db/seeds/` es solo para desarrollo y tiene la clave pública `admin123`.
  - En producción, `app.arranque` carga únicamente roles y menús, y **se niega a arrancar si alguna cuenta tiene `admin123`**.
  - Los seeds con id explícito deben avanzar la secuencia con `setval`; si no, el próximo insert falla con «duplicate key».
- **Datos personales:** la planilla de residentes, los vouchers y los respaldos nunca van al repo ni a los logs, que en CI son públicos.
- **Tests:** `docker exec enercheck-backend-1 sh -c "pip install -q -r requirements-dev.txt && python -m pytest -q"`. Corren contra la base de desarrollo y cada test hace rollback.

---

## Variables de entorno

**Backend** (`backend/.env`):
```
DATABASE_URL=postgresql+asyncpg://enercheck:enercheck@db:5432/enercheck
SECRET_KEY=...
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
GEMINI_API_KEY=...
SITIO_POR_DEFECTO=1-9   # RUT cuyo sitio muestra la landing en localhost
```

**Frontend** (`.env` en `frontend/`):
```
VITE_API_URL=http://localhost:8000/api/v1
```

---

## Comandos frecuentes

```bash
# Levantar todo
docker-compose up --build -d

# Solo reconstruir backend tras cambios de código
docker-compose up --build -d backend

# Ver logs del backend en tiempo real
docker-compose logs -f backend

# Migraciones
docker exec enercheck-backend-1 alembic upgrade head
docker exec enercheck-backend-1 alembic revision --autogenerate -m "descripcion"

# Repoblar datos de prueba
docker exec enercheck-backend-1 python -m app.db.seeds.seeder

# Consola Python dentro del container
docker exec -it enercheck-backend-1 python
```

---

## Errores conocidos

| Error | Causa | Solución |
|-------|-------|----------|
| `MissingGreenlet` en endpoint | Relación cargada lazy en contexto async | Usar `selectinload()` en la query |
| 409 "Las lecturas ya están cerradas" | Container no fue reconstruido tras agregar endpoint | `docker-compose up --build -d backend` |
| 409 "Faltan lecturas por ingresar" | Intento de cerrar lecturas cuando hay parcelas sin `fecha_toma` | El Lector debe capturar todas las lecturas obligatoriamente. |
| Tab de lecturas en negro (React crash) | `const` usado antes de su declaración en el mismo render | Mover declaración después de todas sus dependencias |
| `calcular` no hace nada visible | Mutation sin `onError` handler | Agregar `onError: (err) => setError(...)` a la mutation |
| Sort de parcelas roto después de editar | Re-fetch trae orden de inserción de BD | Aplicar `localeCompare` con `numeric: true` al array del query |
| 409 "Debes corroborar el desglose antes de calcular" | La boleta está en `borrador`: nadie ha juzgado qué ítems entran al reparto | `POST /boletas/{id}/validar-items`, o el botón "Corroborar desglose" en el detalle |
| 409 "Queda 1 ítem sin clasificar" | El OCR creó líneas nuevas con `tipo_calculo="pendiente"` | Clasificarlas como `fijo`, `variable` o `informativo` en "Editar Totales e Ítems" |
| La boleta volvió sola a `borrador` | Es deliberado: reprocesar el OCR o editar detalles revierte la corroboración | Volver a corroborar el desglose con las cifras nuevas |

---

## Usuarios de prueba (seed)

Todos comparten la contraseña `admin123` (ver `_PWD` en `backend/app/db/seeds/usuarios.py`).

| Email | Rol |
|-------|-----|
| `mmoyainfo@gmail.com` | Super Admin |
| `hhernandez@santalaura.cl` | Admin Condominio |
| `cportero@santalaura.cl` | Lector |
| `mmoyainfo+parcela@gmail.com` | Parcelero |
| `porteria@santalaura.cl` | Portería (venta de rifas) |
