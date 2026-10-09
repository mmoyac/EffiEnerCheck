# Spec Delta

## ADDED Requirements

### Requirement: PDF de las liquidaciones del período

El sistema DEBE (SHALL) exponer `GET /api/v1/liquidaciones/pdf/{boleta_id}`, restringido a roles administrativos y acotado al tenant, que entrega un PDF con los datos de la boleta, su desglose de cargos, una fila por parcela en orden natural y el cuadre de la suma de las liquidaciones contra el total de emisión. El PDF DEBE (SHALL) indicar si el período está publicado, cerrado o en borrador.

#### Scenario: Descarga por la administración

- **WHEN** un administrador descarga el PDF de un período con liquidaciones calculadas
- **THEN** recibe un `application/pdf` llamado `liquidaciones-AAAA-MM.pdf` que muestra la suma de las liquidaciones junto al total de emisión

#### Scenario: Período sin liquidaciones

- **WHEN** se pide el PDF de un período que aún no tiene liquidaciones
- **THEN** el sistema responde `409` y pide calcularlas primero

#### Scenario: Comunero

- **WHEN** un comunero pide el PDF
- **THEN** el sistema responde `403`
