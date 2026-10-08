# Spec Delta

## ADDED Requirements

### Requirement: La vista del lector sigue el recorrido

Cuando el condominio tiene un recorrido definido, la aplicación del lector DEBE (SHALL) mostrar primero las parcelas con posición, en ese orden, y después las parcelas sin posición, en orden numérico natural. Sin recorrido definido, DEBE (SHALL) mostrar todas las parcelas en orden numérico natural. El orden DEBE (SHALL) aplicarse a todas las pestañas de la vista y también sin conexión, usando el recorrido descargado.

#### Scenario: Con recorrido

- **WHEN** el recorrido del condominio es 6, 5, 4 y el lector abre la pestaña de pendientes
- **THEN** la aplicación muestra 6, 5 y 4 en ese orden, seguidas de las demás parcelas pendientes en orden numérico

#### Scenario: Sin recorrido

- **WHEN** el condominio no tiene recorrido definido
- **THEN** la aplicación muestra las parcelas en orden numérico, como siempre

#### Scenario: Parcela agregada después de definir el recorrido

- **WHEN** se agrega una parcela nueva sin posición
- **THEN** aparece al final de la lista del lector, hasta que la administración la ubique en el recorrido
