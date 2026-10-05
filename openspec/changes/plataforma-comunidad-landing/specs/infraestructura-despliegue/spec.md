# Spec Delta

## MODIFIED Requirements

### Requirement: Composición de servicios

El sistema DEBE (SHALL) desplegarse como cuatro servicios orquestados por Docker Compose: una base de datos PostgreSQL 16, la API FastAPI servida por Uvicorn, el portal de administración React servido por Nginx y la landing pública React servida por Nginx. El portal y la landing DEBEN (SHALL) ser imágenes distintas, construidas desde directorios distintos, de modo que cada una pueda desplegarse, versionarse y retirarse sin afectar a la otra.

#### Scenario: Arranque ordenado

- **WHEN** se levanta la composición
- **THEN** la API espera a que la base de datos supere su verificación de salud antes de iniciar, y el portal y la landing esperan a la API

#### Scenario: Puertos publicados

- **WHEN** los servicios de desarrollo están arriba
- **THEN** la base de datos queda accesible en el puerto 5434, la API en el 8000, el portal en el 3000 y la landing en el 3001

#### Scenario: Landing caída

- **WHEN** el contenedor de la landing está detenido
- **THEN** el portal y la API siguen funcionando con normalidad

#### Scenario: Imágenes de producción

- **WHEN** el pipeline despliega a producción
- **THEN** construye, audita y publica por separado las imágenes del backend, del portal y de la landing
