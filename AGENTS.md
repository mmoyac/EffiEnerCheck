# AGENTS.md: Proyecto EnerCheck (SaaS de Gestión Eléctrica)

## 1. Objetivo del Proyecto
Desarrollar **EnerCheck**, una plataforma SaaS multitenant diseñada para automatizar el prorrateo de cuentas eléctricas en condominios. El sistema procesa boletas maestras, gestiona lecturas de remarcadores por parcela y genera liquidaciones individuales transparentes.

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
- **Diseño:** Mobile-first. La interfaz del **lector** está optimizada para uso en campo con móvil de 5". Admin y parcelero priorizan escritorio.

### Infraestructura
- **Docker & Docker Compose:** orquesta Backend (FastAPI), Frontend (Nginx), y Base de Datos (PostgreSQL) como servicios independientes
- **PWA:** manifiesto (`manifest.json`) + service worker para instalación en dispositivos móviles (iOS/Android). Modo siempre-online; offline es mejora futura.

## 3. Identidad Visual
- **Logo:** Condominio Santa Laura (colibri + arco verde)
- **Tema:** Dark moderno
- **Color de acento primario:** Verde Santa Laura `#2E7D32` (variantes Tailwind: `green-700` / `green-500`)
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
      pages/           # Vistas por rol (admin/, lector/, parcelero/)
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
| `parcelero` | Mi liquidación del período, historial, estado de pago |

## 6. Carga de Boleta con IA (Gemini Vision)
Al crear una boleta maestra, el sistema copia automáticamente los ítems del período anterior dejándolos en $0. Luego, el admin puede subir una imagen y el OCR de Gemini:
1. Extrae totales de cabecera (`monto_total_emision`, `total_kwh_compania`, etc.).
2. Identifica los ítems de detalle y utiliza "Fuzzy Matching" (SequenceMatcher) para actualizar los montos de los ítems existentes creados por el período anterior.
3. El OCR aplica automáticamente el 19% de IVA a los montos extraídos, ya que el motor EnerCheck requiere los ítems con IVA incluido. No añade ítems nuevos que no existan en la comunidad.

Variable de entorno requerida: `GEMINI_API_KEY=xxxx`

## 7. Integración con el Esquema de Base de Datos (schema.dbml)
- El archivo `schema.dbml` es la **fuente única de verdad** para estructura de tablas, campos y relaciones.
- Multitenancy mediante `condominio_id` en todas las tablas operativas.
- Roles: `super_admin`, `admin_condominio`, `lector`, `parcelero`.
- M2M usuario ↔ parcelas via tabla `usuario_parcelas`.

## 8. Motor de Cálculo EnerCheck
Para garantizar que la suma de todas las liquidaciones cuadre exactamente con la emisión real de la boleta, el motor calcula el valor de la energía a la inversa:
```
monto_total_energia = monto_total_emision - (suma_items_fijo + suma_items_variable)
valor_kwh     = monto_total_energia / total_kwh_compania
diferencial   = (total_kwh_compania − Σ kwh_remarcadores) × valor_kwh
cuota_fija    = (Σ ítems_fijo + diferencial) / total_parcelas_activas
prorrateo_var = Σ ítems_variable × (kwh_parcela / Σ kwh_remarcadores)
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
7. Parcelero puede ver su liquidación (Vista de lista navegable a detalle en móvil).

## 10. Seguridad y Auditoría
- `boleta_visible_usuarios`: condiciona acceso del parcelero a la imagen original.
- Toda inserción/modificación en boletas, lecturas y liquidaciones registra entrada en `auditoria_logs` (`usuario_id` + acción).
- JWT almacenado en `localStorage`; React Query adjunta el token en cada request.
