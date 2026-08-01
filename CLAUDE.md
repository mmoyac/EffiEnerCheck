# CLAUDE.md — Guía para agentes de IA

Este archivo permite que cualquier agente de IA entienda rápidamente cómo está construido EnerCheck y cómo modificarlo sin romper nada.

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
│   │   │       ├── auth.py              # Login → JWT + /auth/me
│   │   │       ├── boletas.py           # CRUD boleta maestra + OCR + candados de período
│   │   │       ├── condominios.py       # CRUD condominios (super_admin)
│   │   │       ├── lecturas.py          # CRUD lecturas de remarcadores
│   │   │       ├── liquidaciones.py     # Calcular (Motor EnerCheck) + consulta + pago
│   │   │       ├── menus.py             # GET /menus/me → navegación según rol
│   │   │       ├── parcelas.py          # CRUD parcelas del condominio
│   │   │       └── usuarios.py          # CRUD usuarios
│   │   ├── core/
│   │   │   ├── config.py                # Pydantic Settings (lee .env)
│   │   │   ├── dependencies.py          # get_db, TenantId, SuperAdminRequired, AdminRequired, LectorRequired, AnyRoleRequired
│   │   │   ├── audit.py                 # registrar_auditoria(db, usuario_id, ...)
│   │   │   └── security.py              # hash/verify passwords, create_access_token
│   │   ├── models/                      # SQLAlchemy ORM (un archivo por entidad)
│   │   │   ├── auditoria.py             # AuditoriaLog
│   │   │   ├── boleta.py                # BoletaMaestra, BoletaItemDetalle
│   │   │   ├── condominio.py            # Condominio
│   │   │   ├── lectura.py               # LecturaParcela
│   │   │   ├── liquidacion.py           # LiquidacionParcela
│   │   │   ├── menu.py                  # Menu + tabla menu_roles
│   │   │   ├── parcela.py               # Parcela
│   │   │   ├── rol.py                   # Rol
│   │   │   ├── usuario.py               # Usuario
│   │   │   └── usuario_parcela.py       # Tabla M2M usuario_parcelas
│   │   ├── schemas/                     # Pydantic v2 (request/response)
│   │   ├── services/
│   │   │   ├── enercheck.py             # Motor EnerCheck — fórmulas de distribución
│   │   │   └── ocr.py                   # extraer_datos_boleta() → llama Gemini Vision
│   │   ├── db/
│   │   │   ├── session.py               # AsyncSession factory
│   │   │   └── seeds/seeder.py          # Datos de prueba (roles, condominio, usuarios, boleta)
│   │   └── utils/
│   │       └── format.py                # periodo_label(date) → "Mar. 2025"
│   ├── alembic/                         # Migraciones de base de datos
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx                      # Rutas + ROLE_HOME (home por rol)
│   │   ├── pages/
│   │   │   ├── Login.tsx                # Formulario de acceso
│   │   │   ├── admin/
│   │   │   │   ├── Dashboard.tsx        # KPIs del período + boletas recientes
│   │   │   │   ├── Boletas.tsx          # Lista de boletas + botón Calcular → navega a detalle
│   │   │   │   ├── BoletaDetalle.tsx    # Detalle con tabs: Resumen / Lecturas / Liquidaciones / Boleta
│   │   │   │   ├── ModalEditDetalles.tsx# Edición manual de totales e ítems
│   │   │   │   ├── Condominios.tsx      # CRUD condominios (solo super_admin)
│   │   │   │   ├── Parcelas.tsx         # CRUD parcelas
│   │   │   │   └── Usuarios.tsx         # CRUD usuarios
│   │   │   ├── lector/
│   │   │   │   ├── LectorDashboard.tsx  # Vista móvil: parcelas pendientes + progreso
│   │   │   │   └── CapturarLectura.tsx  # Pantalla de captura por parcela
│   │   │   └── parcelero/
│   │   │       └── MiLiquidacion.tsx    # Vista del parcelero: lista de períodos → detalle
│   │   ├── components/                  # UI atómica (Badge, Modal, etc.) + layout/
│   │   ├── api/                         # Clientes HTTP por recurso
│   │   │   ├── client.ts                # axios instance (lee VITE_API_URL, añade JWT, 401 → /login)
│   │   │   ├── auth.ts                  # authApi.login / authApi.me
│   │   │   ├── boletas.ts               # boletasApi.*
│   │   │   ├── condominios.ts           # condominiosApi.*
│   │   │   ├── lecturas.ts              # lecturasApi.*
│   │   │   ├── liquidaciones.ts         # liquidacionesApi.*
│   │   │   ├── menus.ts                 # menusApi.*
│   │   │   ├── parcelas.ts              # parcelasApi.*
│   │   │   └── usuarios.ts              # usuariosApi.*
│   │   ├── context/
│   │   │   └── AuthContext.tsx          # Estado de sesión; restaura vía /auth/me
│   │   ├── hooks/
│   │   │   └── useAuth.ts               # Exporta useAuth() y useRole()
│   │   └── types/index.ts               # Interfaces TypeScript (BoletaMaestra, Lectura, etc.)
│   └── Dockerfile
├── docker-compose.yml
├── openspec/
│   ├── specs/                           # Specs de las capacidades actuales (línea base)
│   └── changes/                         # Propuestas de cambio en curso + archive/
├── schema.dbml                          # Fuente de verdad del esquema DB (DB Diagram)
├── README.md                            # Documentación técnica GitHub
├── PRESENTACION_COMUNIDAD.md            # Documento para reunión de la comunidad
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
openspec validate --specs --strict  # Validar todas (debe dar 14 passed)
```

Slash commands disponibles en Claude Code: `/opsx:propose`, `/opsx:apply`, `/opsx:explore`, `/opsx:archive`.

---

## Roles y RBAC

Los guards se aplican como dependencias FastAPI en cada endpoint:

| Dependencia | Roles permitidos |
|-------------|-----------------|
| `AdminRequired` | `super_admin`, `admin_condominio` |
| `LectorRequired` | `super_admin`, `admin_condominio`, `lector` |
| `AnyRoleRequired` | cualquier rol autenticado |
| `TenantId` | extrae `condominio_id` del JWT; `super_admin` recibe `None` (acceso global) |

En el frontend, las rutas están protegidas en `App.tsx` con `useRole()`.

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

## Variables de entorno

**Backend** (`backend/.env`):
```
DATABASE_URL=postgresql+asyncpg://enercheck:enercheck@db:5432/enercheck
SECRET_KEY=...
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
GEMINI_API_KEY=...
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

---

## Usuarios de prueba (seed)

| Email | Contraseña | Rol |
|-------|-----------|-----|
| `super@enercheck.cl` | `admin123` | Super Admin |
| `henry@santalauracl` | `admin123` | Admin Condominio |
| `claudio@santalauracl` | `lector123` | Lector |
| `parcela2@santalauracl` | `parcelero123` | Parcelero |
