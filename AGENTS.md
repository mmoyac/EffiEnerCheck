# AGENTS.md: Plataforma para comunidades (EnerCheck es su módulo de energía)

## 1. Objetivo del Proyecto
Una plataforma SaaS multitenant para condominios, con **dos productos** que se venden por separado:

- **Landing pública** (`landing/`): el sitio web de cada condominio.
- **Portal de administración** (`frontend/`), organizado en módulos:
  - **Energía (EnerCheck):** procesa las boletas maestras, gestiona las lecturas de remarcadores por parcela y genera liquidaciones individuales transparentes.
  - **Rifas:** rifas solidarias de la comunidad.

Un condominio puede tener solo la landing, solo la administración (enlazada desde su propia web) o ambas. El `super_admin` lo parametriza por condominio, junto con sus dominios, su logo y su color institucional. El nombre comercial de la plataforma está pendiente (`frontend/src/config/marca.ts`).

## 2. Stack Tecnológico

### Backend
- **Lenguaje:** Python 3.11+
- **Framework:** FastAPI (async)
- **Base de Datos:** PostgreSQL + SQLAlchemy 2.x (asyncpg)
- **Migraciones:** Alembic
- **Autenticación:** JWT con RBAC (4 roles)
- **OCR / IA:** Gemini Vision API (`GEMINI_API_KEY`) para extracción automática de datos desde imagen de boleta eléctrica

### Frontend
- **Framework:** React + Vite + TypeScript
- **Estilos:** Tailwind CSS — tema **dark moderno** con verde Santa Laura como color de acento primario
- **Iconos:** Lucide React
- **Data fetching:** React Query (TanStack Query v5)
- **Routing:** React Router v6
- **Diseño:** Mobile-first. La interfaz del **lector** está optimizada para uso en campo con móvil de 5". Admin y comunero priorizan escritorio.

### Infraestructura
- **Docker & Docker Compose:** orquesta Backend (FastAPI), Frontend (Nginx), y Base de Datos (PostgreSQL) como servicios independientes
- **PWA:** manifiesto (`manifest.json`) + service worker para instalación en dispositivos móviles (iOS/Android). Modo siempre-online; offline es mejora futura.

## 3. Identidad Visual
- **Logo:** Condominio Santa Laura (colibri + arco verde)
- **Tema:** Dark moderno
- **Color de acento primario:** el **color institucional de cada condominio** (`condominios.color_primario`). El portal usa la escala `primary-*` de Tailwind sobre variables CSS. Por defecto es el verde histórico `#22C55E` (escala green de Tailwind), que es también el de Santa Laura.
- **Superficies:** `gray-900` (fondo base), `gray-800` (cards/sidebar), `gray-700` (bordes/inputs)
- **Texto:** `gray-100` (primario), `gray-400` (secundario/muted)

## 4. Estructura de Directorios

```text
EnerCheck/
  backend/
    app/
      api/v1/          # Endpoints (auth, boletas, parcelas, lecturas, liquidaciones, menus)
      core/            # Seguridad (JWT), configuración, dependencias, auditoría
      models/          # Modelos SQLAlchemy (1:1 con schema.dbml)
      schemas/         # Pydantic v2 (Input/Output)
      services/        # Motor EnerCheck (enercheck.py) + OCR Gemini (ocr.py)
      db/              # Sesión async, seeds
    main.py
    Dockerfile
  frontend/
    src/
      components/      # Componentes reutilizables (UI atómica)
      pages/           # Vistas por rol (admin/, lector/, comunero/)
      hooks/           # Custom hooks (useAuth, useQueryX…)
      api/             # Clientes React Query por recurso
      types/           # Tipos TypeScript generados o manuales
    public/
      manifest.json    # PWA manifest
      icons/           # Iconos PWA (192x192, 512x512)
    index.html
    vite.config.ts
    Dockerfile
  docker-compose.yml   # Backend + Frontend + PostgreSQL
  schema.dbml          # Fuente única de verdad del esquema DB
```

## 5. Roles y Navegación

| Rol | Pantallas principales |
|-----|-----------------------|
| `super_admin` | Gestión de condominios, usuarios globales |
| `admin_condominio` | Dashboard, boletas (+ carga con IA), lecturas, liquidaciones, usuarios del condominio |
| `lector` | Vista móvil optimizada: lista de parcelas pendientes → captura de lectura → confirmación |
| `comunero` | Mi liquidación del período, historial, estado de pago |

## 6. Carga de Boleta con IA (Gemini Vision)
Al crear una boleta maestra, el sistema copia automáticamente los ítems del período anterior dejándolos en $0. Luego, el admin puede subir una imagen y el OCR de Gemini:
1. Extrae totales de cabecera (`monto_total_emision`, `total_kwh_compania`, etc.).
2. Identifica los ítems de detalle y utiliza "Fuzzy Matching" (SequenceMatcher) para actualizar los montos de los ítems existentes creados por el período anterior.
3. El OCR aplica automáticamente el 19% de IVA a los montos extraídos, ya que el motor EnerCheck requiere los ítems con IVA incluido. No añade ítems nuevos que no existan en la comunidad.

Variable de entorno requerida: `GEMINI_API_KEY=xxxx`

## 7. Integración con el Esquema de Base de Datos (schema.dbml)
- El archivo `schema.dbml` es la **fuente única de verdad** para estructura de tablas, campos y relaciones.
- Multitenancy mediante `condominio_id` en todas las tablas operativas.
- Roles: `super_admin`, `admin_condominio`, `lector`, `comunero`.
- M2M usuario ↔ parcelas via tabla `usuario_parcelas`.

## 8. Motor de Cálculo EnerCheck
Para garantizar que la suma de todas las liquidaciones cuadre exactamente con la emisión real de la boleta, el motor calcula el valor de la energía a la inversa:
```
monto_total_energia = monto_total_emision - (suma_items_fijo + suma_items_variable)
valor_kwh     = monto_total_energia / total_kwh_compania
diferencial   = (total_kwh_compania − Σ kwh_remarcadores) × valor_kwh
cuota_fija    = Σ ítems_fijo / total_parcelas_activas
prorrateo_var = (Σ ítems_variable + diferencial) × (kwh_parcela / Σ kwh_remarcadores)
monto_energia = valor_kwh × kwh_parcela
total_pagar   = monto_energia + prorrateo_var + cuota_fija
```
Todos los componentes se redondean al entero más cercano (`round()`).
El motor es idempotente: elimina liquidaciones previas antes de recalcular.

## 9. Flujo de Período (Locking)
1. Admin crea boleta (estado `borrador`, auto-genera lecturas del mes e ítems de detalle en $0).
2. Lector registra lecturas de todas las parcelas.
3. Lector cierra lecturas → Requiere estrictamente que todas las lecturas tengan `fecha_toma` asignada.
4. Admin calcula liquidaciones (`POST /liquidaciones/calcular/{boleta_id}`).
5. Admin revisa y cierra período → `liquidaciones_cerradas = true`.
6. Admin publica boleta → `boleta_visible_usuarios = true`.
7. Comunero puede ver su liquidación (Vista de lista navegable a detalle en móvil).

## 10. Seguridad y Auditoría
- `boleta_visible_usuarios`: condiciona acceso del comunero a la imagen original.
- Toda inserción/modificación en boletas, lecturas y liquidaciones registra entrada en `auditoria_logs` (`usuario_id` + acción).
- JWT almacenado en `localStorage`; React Query adjunta el token en cada request.
