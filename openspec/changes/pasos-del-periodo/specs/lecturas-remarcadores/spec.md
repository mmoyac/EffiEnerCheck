# Spec Delta

## ADDED Requirements

### Requirement: Aviso de lecturas cerradas en la app del lector

Cuando el período del recorrido tiene las lecturas cerradas, la aplicación del lector DEBE (SHALL) mostrar un aviso visible: las lecturas están cerradas, ya no se pueden modificar y, para corregir una, hay que pedir a la administración que las reabra. El aviso complementa la deshabilitación de la captura; no la reemplaza.

#### Scenario: Lector abre un período cerrado

- **WHEN** el lector abre la aplicación y el período del recorrido tiene las lecturas cerradas
- **THEN** ve las parcelas deshabilitadas y el aviso de que las lecturas están cerradas y de cómo pedir una corrección
