# infraestructura-despliegue Specification

## Purpose

Definir cómo se ejecuta EnerCheck: tres servicios contenedorizados (base de datos, API y sitio web), su configuración por variables de entorno, la persistencia de los archivos subidos y el mecanismo de evolución del esquema. El objetivo es que levantar el sistema completo desde cero sea un solo comando y que el esquema de base de datos tenga una única fuente de verdad.

## Requirements

### Requirement: Composición de servicios

El sistema DEBE (SHALL) desplegarse como tres servicios orquestados por Docker Compose: una base de datos PostgreSQL 16, la API FastAPI servida por Uvicorn y el sitio web React servido por Nginx.

#### Scenario: Arranque ordenado

- **WHEN** se levanta la composición
- **THEN** la API espera a que la base de datos supere su verificación de salud antes de iniciar, y el sitio web espera a la API

#### Scenario: Puertos publicados

- **WHEN** los servicios están arriba
- **THEN** la base de datos queda accesible en el puerto 5432, la API en el 8000 y el sitio web en el 3000

### Requirement: Verificación de salud de la API

La API DEBE (SHALL) exponer `GET /health` sin autenticación, devolviendo el estado y la versión de la aplicación.

#### Scenario: Comprobación de disponibilidad

- **WHEN** se consulta el endpoint de salud
- **THEN** la API responde con estado correcto y la versión configurada

### Requirement: Configuración por variables de entorno

La API DEBE (SHALL) leer su configuración desde variables de entorno, incluyendo la cadena de conexión a la base de datos, la clave y el algoritmo de firma del token, la vigencia del token y la clave de la API de Gemini. El sitio web DEBE (SHALL) leer la URL base de la API desde `VITE_API_URL`.

#### Scenario: URL de la API no configurada en el cliente

- **WHEN** `VITE_API_URL` no está definida
- **THEN** el cliente usa `/api/v1` como ruta relativa, apoyándose en el proxy del servidor web

#### Scenario: Secretos fuera del control de versiones

- **WHEN** se despliega el sistema
- **THEN** la clave de firma del token y la clave de Gemini se proveen por archivo de entorno y no se versionan en el repositorio

### Requirement: Persistencia de los archivos subidos

Las imágenes y PDF de boletas DEBEN (SHALL) almacenarse en un volumen persistente montado en `/app/uploads` y servirse públicamente bajo la ruta `/uploads`.

#### Scenario: Reinicio del contenedor

- **WHEN** el contenedor de la API se reconstruye o reinicia
- **THEN** los archivos de boletas previamente subidos siguen disponibles

#### Scenario: Creación del directorio al arrancar

- **WHEN** la API inicia y el directorio de subidas no existe
- **THEN** lo crea automáticamente antes de montar la ruta estática

### Requirement: Documentación interactiva de la API

La API DEBE (SHALL) publicar su documentación interactiva en `/api/docs` y `/api/redoc`.

#### Scenario: Exploración de los endpoints

- **WHEN** un desarrollador abre la documentación
- **THEN** encuentra los endpoints agrupados por etiqueta: autenticación, usuarios, condominios, parcelas, boletas, lecturas, liquidaciones y menús

### Requirement: Prefijo de versión en la API

Todos los endpoints de negocio DEBEN (SHALL) publicarse bajo el prefijo `/api/v1`, permitiendo introducir versiones futuras sin romper a los clientes existentes.

#### Scenario: Ruta de un recurso

- **WHEN** el cliente consulta las boletas
- **THEN** lo hace sobre `/api/v1/boletas/`

### Requirement: Evolución del esquema mediante migraciones

Todo cambio en los modelos DEBE (SHALL) materializarse mediante una migración de Alembic aplicada al contenedor, manteniendo `schema.dbml` como documentación de referencia del esquema.

#### Scenario: Nuevo campo en un modelo

- **WHEN** se agrega un campo a un modelo de SQLAlchemy
- **THEN** se genera y aplica la migración correspondiente antes de usar el campo en los endpoints

### Requirement: Recarga de código en el contenedor

El código de la API se monta como volumen y Uvicorn se ejecuta con recarga automática, pero un reinicio del contenedor NO DEBE (SHALL NOT) considerarse suficiente tras cambios que alteren las dependencias o la imagen.

#### Scenario: Cambio que requiere reconstrucción

- **WHEN** se modifican las dependencias o el Dockerfile del backend
- **THEN** el contenedor debe reconstruirse para que los cambios tengan efecto

### Requirement: Datos de prueba reproducibles

El sistema DEBE (SHALL) incluir un poblador de datos que cree los roles, los menús, un condominio de ejemplo con sus parcelas, usuarios de cada rol y un período de referencia con su boleta y sus lecturas.

#### Scenario: Entorno recién levantado

- **WHEN** se ejecuta el poblador sobre una base de datos vacía
- **THEN** queda disponible un usuario por cada uno de los cuatro roles para probar el flujo completo de principio a fin
