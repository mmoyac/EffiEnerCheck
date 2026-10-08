# Spec Delta

## ADDED Requirements

### Requirement: Candados del período de lectura inicial

Un período de lectura inicial solo registra lecturas. El sistema DEBE (SHALL) responder `409` con el detalle `"El período de lectura inicial no se liquida"` a estas operaciones sobre él:
- calcular liquidaciones;
- corroborar el desglose;
- cargar la imagen de la boleta;
- procesar el OCR;
- editar los totales y los ítems;
- cerrar las liquidaciones;
- publicarlo a los comuneros.

Cerrar y reabrir sus lecturas DEBE (SHALL) funcionar como en un período regular, incluida la exigencia de que todas las parcelas tengan su lectura tomada.

#### Scenario: Calcular sobre la lectura inicial

- **WHEN** un administrador pide calcular las liquidaciones de un período de lectura inicial
- **THEN** el sistema responde `409` y no crea liquidaciones

#### Scenario: Publicar la lectura inicial

- **WHEN** un administrador intenta hacer visible a los comuneros un período de lectura inicial
- **THEN** el sistema responde `409` y el período sigue sin publicar

#### Scenario: Cierre de la lectura inicial

- **WHEN** el lector cierra las lecturas de la lectura inicial con todas las parcelas tomadas
- **THEN** el sistema marca las lecturas como cerradas y el período queda listo para servir de base a la primera boleta

## MODIFIED Requirements

### Requirement: Reapertura de lecturas

El sistema DEBE (SHALL) exponer `POST /api/v1/boletas/{boleta_id}/reabrir-lecturas`, restringido a roles administrativos, que devuelve el período a captura de lecturas siempre que las liquidaciones no estén cerradas. Un período de lectura inicial NO DEBE (SHALL NOT) reabrirse si ya existe un período posterior del condominio, porque ese período tomó sus lecturas como base.

#### Scenario: Reapertura permitida

- **WHEN** un administrador reabre las lecturas de un período con `liquidaciones_cerradas` en falso
- **THEN** el sistema marca `lecturas_cerradas` en falso y registra la acción `REABRIR_LECTURAS`

#### Scenario: Reapertura bloqueada por período cerrado

- **WHEN** se intenta reabrir las lecturas de un período con las liquidaciones ya cerradas
- **THEN** el sistema responde `409` con el detalle `"El período ya está cerrado y no se puede reabrir"`

#### Scenario: Lecturas ya abiertas

- **WHEN** se intenta reabrir lecturas que no están cerradas
- **THEN** el sistema responde `409` con el detalle `"Las lecturas ya están abiertas"`

#### Scenario: Lectura inicial con un período posterior

- **WHEN** se intenta reabrir las lecturas de una lectura inicial y el condominio ya tiene una boleta posterior
- **THEN** el sistema responde `409` indicando que la lectura inicial ya es la base de un período posterior
