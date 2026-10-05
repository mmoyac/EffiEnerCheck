## ADDED Requirements

### Requirement: Legibilidad de qué entra al reparto

El desglose de la boleta en la consola DEBE (SHALL) dejar evidente, para cada ítem, si entra al reparto y bajo qué criterio, de modo que el administrador pueda ejercer su juicio mensual sin tener que deducirlo.

#### Scenario: Etiquetado por tratamiento

- **WHEN** el administrador abre el desglose de una boleta
- **THEN** cada ítem indica si se reparte parejo entre parcelas, si se prorratea por consumo, si queda fuera del reparto o si aún está sin clasificar

#### Scenario: Ítems pendientes destacados

- **WHEN** la boleta contiene ítems con `tipo_calculo` igual a `pendiente`
- **THEN** la consola los destaca visualmente por sobre el resto e indica cuántos faltan por clasificar

### Requirement: Distinción entre cargo y abono

La consola DEBE (SHALL) distinguir visualmente los ítems de monto negativo de los de monto positivo, para que un crédito no se confunda con un cargo al revisar el desglose.

#### Scenario: Ítem de crédito en el desglose

- **WHEN** un ítem tiene monto negativo
- **THEN** la consola lo presenta diferenciado de los cargos, con el signo visible en el monto

#### Scenario: Ingreso manual de un crédito

- **WHEN** el administrador agrega o edita un ítem en el modal de detalles
- **THEN** el campo de monto acepta valores negativos y la fila refleja de inmediato que se trata de un abono

### Requirement: Acción de corroborar el desglose

La consola DEBE (SHALL) ofrecer al administrador una acción explícita para corroborar el desglose del período, disponible mientras la boleta esté en `borrador` y el período no esté cerrado.

#### Scenario: Corroboración disponible

- **WHEN** la boleta está en `borrador` y no tiene ítems pendientes
- **THEN** la consola ofrece la acción de corroborar el desglose

#### Scenario: Corroboración bloqueada por ítems pendientes

- **WHEN** la boleta tiene al menos un ítem `pendiente`
- **THEN** la consola impide corroborar y dirige al administrador a clasificar los ítems que faltan

#### Scenario: Estado corroborado visible

- **WHEN** la boleta pasa a `validada`
- **THEN** la consola lo refleja en la etiqueta de estado del período y habilita la acción de calcular

## MODIFIED Requirements

### Requirement: Etiqueta de estado del período

La consola DEBE (SHALL) traducir el estado y los tres candados del período en una única etiqueta legible, con la precedencia: publicada, período cerrado, lecturas cerradas, desglose corroborado y, en ausencia de todas, borrador.

#### Scenario: Período con lecturas cerradas y liquidaciones abiertas

- **WHEN** una boleta tiene `lecturas_cerradas` en verdadero y `liquidaciones_cerradas` en falso
- **THEN** la consola la etiqueta como lecturas cerradas

#### Scenario: Boleta corroborada sin lecturas cerradas

- **WHEN** una boleta está en estado `validada` y sus lecturas siguen abiertas
- **THEN** la consola la etiqueta como corroborada, distinguiéndola de una boleta en borrador
