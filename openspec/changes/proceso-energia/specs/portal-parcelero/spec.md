# Spec Delta

## REMOVED Requirements

### Requirement: Visibilidad de la liquidación condicionada al cierre del período

**Reason**: Cerrar el período no basta. Antes de publicar, las liquidaciones todavía pueden reabrirse y cambiar, y el portal ya mostraba solo los períodos publicados: la API quedaba más abierta que la pantalla.

**Migration**: La reemplaza «Visibilidad de la liquidación condicionada a la publicación del período». Un comunero solo recibe liquidaciones de períodos con `boleta_visible_usuarios` en verdadero. Ningún cliente del portal cambia.

## ADDED Requirements

### Requirement: Visibilidad de la liquidación condicionada a la publicación del período

El sistema NO DEBE (SHALL NOT) entregar liquidaciones al rol `comunero` mientras el período no esté publicado (`boleta_visible_usuarios` en verdadero), aunque el período ya esté cerrado.

#### Scenario: Listado antes de publicar

- **WHEN** un `comunero` lista liquidaciones y el período está cerrado pero aún no publicado
- **THEN** el sistema no incluye esas liquidaciones en la respuesta

#### Scenario: Consulta directa antes de publicar

- **WHEN** un `comunero` solicita por identificador una liquidación propia de un período no publicado
- **THEN** el sistema responde `403` indicando que la liquidación aún no está publicada

#### Scenario: Período publicado

- **WHEN** un `comunero` lista liquidaciones de un período publicado
- **THEN** el sistema entrega las de sus parcelas
