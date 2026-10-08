# Spec Delta

## ADDED Requirements

### Requirement: Orden del recorrido del lector

El sistema DEBE (SHALL) exponer `PUT /api/v1/parcelas/orden-recorrido`, restringido a roles administrativos. Recibe la lista ordenada de parcelas que forman el recorrido del lector en un condominio. Cada parcela listada DEBE (SHALL) quedar con su posición (`orden_recorrido` = 1, 2, 3…) y las demás parcelas del condominio sin posición. Una lista vacía DEBE (SHALL) quitar el recorrido. El sistema DEBE (SHALL) rechazar con `422` las listas con parcelas repetidas, y con `403` las que incluyan parcelas de otro condominio. El cambio DEBE (SHALL) registrarse en la auditoría como `UPDATE_ORDEN_RECORRIDO`. Toda parcela DEBE (SHALL) informar su `orden_recorrido`, que es nulo si no tiene posición.

#### Scenario: Definir el recorrido

- **WHEN** el administrador guarda el recorrido 6, 5, 4, 3, 13 A, 13 B
- **THEN** esas parcelas quedan con las posiciones 1 a 6, las demás sin posición, y el cambio queda en la auditoría

#### Scenario: Quitar el recorrido

- **WHEN** el administrador guarda una lista vacía
- **THEN** ninguna parcela del condominio queda con posición

#### Scenario: Parcela de otro condominio

- **WHEN** la lista incluye una parcela de otro condominio
- **THEN** el sistema responde `403` y no modifica ninguna posición

#### Scenario: Parcela repetida

- **WHEN** la lista incluye dos veces la misma parcela
- **THEN** el sistema responde `422` y no modifica ninguna posición
