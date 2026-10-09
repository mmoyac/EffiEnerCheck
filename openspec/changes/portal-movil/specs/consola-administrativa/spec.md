# Spec Delta

## ADDED Requirements

### Requirement: Portal usable en celular

Toda pantalla del portal DEBE (SHALL) poder usarse en un celular sin desplazamiento horizontal:
- en pantallas angostas, las tablas de más de tres columnas DEBEN (SHALL) mostrarse como listas apiladas con los mismos datos y las mismas acciones, incluida la edición en línea;
- las barras de botones y filtros DEBEN (SHALL) acomodarse al ancho;
- las ventanas (modales) NO DEBEN (SHALL NOT) superar la altura de la pantalla: su contenido DEBE (SHALL) desplazarse en vertical dentro de la ventana, y las listas largas que contengan DEBEN (SHALL) tener una altura acotada.

#### Scenario: Lista de lecturas en el celular

- **WHEN** el administrador abre la pestaña Lecturas de un período desde un celular
- **THEN** ve cada parcela como una fila apilada con sus lecturas, consumo, foto y edición, sin desplazarse en horizontal

#### Scenario: Ventana con una lista larga

- **WHEN** se abre una ventana cuyo contenido es más alto que la pantalla, como la vista previa de una planilla de 53 parcelas
- **THEN** la ventana se ajusta a la pantalla, la lista se desplaza dentro de ella y los botones de acción quedan alcanzables

#### Scenario: Pantalla ancha

- **WHEN** la misma pantalla se abre en un computador
- **THEN** se muestra la tabla de siempre
