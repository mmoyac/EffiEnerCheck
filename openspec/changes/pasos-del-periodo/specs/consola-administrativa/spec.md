# Spec Delta

## ADDED Requirements

### Requirement: Guía de pasos del período

El detalle de un período DEBE (SHALL) mostrar la secuencia de pasos del ciclo:
- en un período regular: datos de la boleta, corroborar desglose, lecturas, calcular, cerrar período y publicar;
- en la lectura inicial: lecturas de partida, cerrar lecturas y lista.

Las acciones del ciclo DEBEN (SHALL) ofrecerse solo en el detalle, junto a esta guía; la lista de períodos DEBE (SHALL) ofrecer «Continuar» hacia el detalle. La guía DEBE (SHALL) marcar cuáles están hechos, resaltar el siguiente y explicar en una línea qué corresponde hacer. El botón de la acción del siguiente paso DEBE (SHALL) ser el único destacado; las demás acciones permitidas DEBEN (SHALL) mostrarse sin destacar. Cuando el siguiente paso depende del lector, la guía DEBE (SHALL) mostrar el avance de las lecturas («X de N») y no destacar ninguna acción.

#### Scenario: Lista de períodos

- **WHEN** el administrador abre la lista de boletas
- **THEN** cada período en curso ofrece «Continuar» hacia su detalle, en vez de atajos a las acciones del ciclo

#### Scenario: Lecturas completas sin cerrar

- **WHEN** el desglose está corroborado y todas las lecturas del período están tomadas pero abiertas
- **THEN** el siguiente paso es «Cerrar lecturas» y su botón es el único destacado

#### Scenario: Lecturas en curso

- **WHEN** el desglose está corroborado y faltan lecturas por tomar
- **THEN** la guía muestra el avance «X de N», indica que el lector las está tomando y no destaca ninguna acción

#### Scenario: Faltan los datos de la boleta

- **WHEN** el período no tiene los totales de la boleta
- **THEN** el siguiente paso es «Datos de la boleta», con un botón destacado para ingresarlos

#### Scenario: Período publicado

- **WHEN** el período está publicado
- **THEN** todos los pasos aparecen hechos y la guía indica que los comuneros ya ven su liquidación
