# EnerCheck ⚡

Plataforma SaaS para la gestión y prorrateo automático de cuentas eléctricas en condominios. Digitaliza el proceso completo: desde la carga de la boleta eléctrica hasta la publicación de liquidaciones individuales para cada parcelero.

---

## Características principales

- **OCR con Gemini Vision** — sube la imagen de la boleta y los datos se extraen automáticamente
- **Motor de cálculo propio** — distribuye el costo eléctrico entre parcelas según consumo real + cuotas fijas
- **Flujo de período con candados** — lecturas → cálculo → cierre → publicación; cada etapa auditable
- **Multitenant** — soporta múltiples condominios desde una misma instancia
- **PWA** — instalable en móvil; la interfaz del lector está optimizada para uso en campo
- **Auditoría completa** — cada acción queda registrada con usuario, timestamp e IP

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.11 · FastAPI (async) · SQLAlchemy 2 · Alembic |
| Base de datos | PostgreSQL 16 |
| Frontend | React 18 · TypeScript · Vite · Tailwind CSS · TanStack Query v5 |
| IA / OCR | Google Gemini Vision API (`gemini-2.5-flash`) |
| Infraestructura | Docker · Docker Compose · Nginx |

---

## Roles de usuario

| Rol | Acceso |
|-----|--------|
| `super_admin` | Gestión global de condominios y usuarios |
| `admin_condominio` | Operación completa: boletas, lecturas, liquidaciones, usuarios del condominio |
| `lector` | Captura de lecturas de remarcadores (interfaz móvil optimizada) |
| `parcelero` | Consulta de su propia liquidación y estado de pago |

---

## Flujo de período

```
1. Admin crea boleta (sube imagen → Gemini extrae los datos automáticamente)
        ↓
2. Lector registra lecturas de cada remarcador
        ↓
3. Lector cierra lecturas  [lecturas_cerradas = true]
        ↓
4. Admin calcula liquidaciones  ← Motor EnerCheck
        ↓
5. Admin revisa y cierra período  [liquidaciones_cerradas = true]
        ↓
6. Admin publica  [boleta_visible_usuarios = true]
        ↓
7. Parcelero consulta su liquidación desde el móvil
```

**Correcciones:** si se detecta un error en una lectura antes de publicar, el admin puede reabrir el período, editar la lectura y el sistema recalcula automáticamente.

---

## Motor de cálculo EnerCheck

El valor del kWh se despeja **a la inversa** desde el Total Emisión, de modo que la suma de todas las liquidaciones cuadre exactamente con lo que la compañía cobró al condominio:

```
monto_total_energia = monto_total_emision − (Σ ítems_fijo + Σ ítems_variable)
valor_kwh     = monto_total_energia / total_kwh_compania
diferencial   = (total_kwh_compania − Σ kwh_remarcadores) × valor_kwh
cuota_fija    = (Σ ítems_fijo + diferencial) / total_parcelas_activas
prorrateo_var = Σ ítems_variable × (kwh_parcela / Σ kwh_remarcadores)
monto_energia = valor_kwh × kwh_parcela
total_pagar   = monto_energia + prorrateo_var + cuota_fija
```

Los ítems de detalle se manejan **con IVA incluido** (el OCR aplica el 19% al extraerlos). Los de tipo `informativo` no participan del reparto. Cada componente se redondea al entero más cercano.

El **diferencial** es la energía que la boleta cobra pero que ningún remarcador registró —pérdidas, áreas comunes, medidores no cubiertos— y se reparte en partes iguales dentro de la cuota fija.

El motor es **idempotente**: elimina y recrea las liquidaciones en cada ejecución, garantizando consistencia.

---

## Instalación

### Requisitos previos
- Docker Desktop
- Git

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/enercheck.git
cd enercheck
```

### 2. Configurar variables de entorno

```bash
cp backend/.env.example backend/.env
```

Edita `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://enercheck:enercheck@db:5432/enercheck
SECRET_KEY=cambia-esto-por-una-clave-segura
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
GEMINI_API_KEY=tu-api-key-de-google-gemini
```

### 3. Levantar los servicios

```bash
docker-compose up --build -d
```

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Docs Swagger | http://localhost:8000/docs |

### 4. Ejecutar migraciones y semilla de datos

```bash
# Migraciones
docker exec enercheck-backend-1 alembic upgrade head

# Datos de prueba (roles, condominios, usuarios, boleta marzo 2025)
docker exec enercheck-backend-1 python -m app.db.seeds.seeder
```

### Usuarios de prueba (seed)

| Email | Contraseña | Rol |
|-------|-----------|-----|
| `super@enercheck.cl` | `admin123` | Super Admin |
| `henry@santalauracl` | `admin123` | Admin Condominio |
| `claudio@santalauracl` | `lector123` | Lector |
| `parcela2@santalauracl` | `parcelero123` | Parcelero |

---

## Estructura del proyecto

```
EnerCheck/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # boletas, lecturas, liquidaciones, parcelas, usuarios, auth
│   │   ├── core/               # JWT, configuración, dependencias RBAC, auditoría
│   │   ├── models/             # SQLAlchemy ORM
│   │   ├── schemas/            # Pydantic v2
│   │   ├── services/           # Motor EnerCheck + OCR Gemini
│   │   └── db/                 # Sesión async, migraciones, seeds
│   ├── main.py
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/              # admin/ · lector/ · parcelero/
│   │   ├── components/         # UI atómica reutilizable
│   │   ├── api/                # Clientes por recurso (React Query)
│   │   └── hooks/              # useAuth, useRole
│   └── Dockerfile
├── docker-compose.yml
├── schema.dbml                 # Fuente de verdad del esquema DB
└── AGENTS.md                   # Guía para agentes de IA
```

---

## API destacada

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/token` | Login (JWT) |
| `POST` | `/api/v1/boletas/ocr` | Extraer datos de boleta con Gemini |
| `POST` | `/api/v1/boletas/{id}/cerrar-lecturas` | Cerrar lecturas del período |
| `POST` | `/api/v1/boletas/{id}/reabrir-lecturas` | Reabrir para correcciones |
| `POST` | `/api/v1/liquidaciones/calcular/{id}` | Ejecutar Motor EnerCheck |
| `POST` | `/api/v1/boletas/{id}/cerrar-liquidaciones` | Cerrar período |
| `POST` | `/api/v1/boletas/{id}/reabrir-liquidaciones` | Reabrir período (antes de publicar) |
| `PATCH` | `/api/v1/boletas/{id}` | Publicar boleta a parceleros |

Documentación interactiva completa en `/docs` (Swagger UI).

---

## Licencia

Uso interno — Condominio Santa Laura.
