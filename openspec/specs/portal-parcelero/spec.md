# portal-parcelero Specification

## Purpose

Dar al dueño de una parcela una explicación verificable de lo que se le cobra. El portal muestra, por período publicado, el desglose de su liquidación en sus tres componentes, el estado de pago, los totales de la boleta que la compañía emitió al condominio y la imagen del documento original. La transparencia es el argumento central del sistema frente a la comunidad: el parcelero puede contrastar su cuota con la boleta real.

## Requirements

### Requirement: Visibilidad de la liquidación condicionada al cierre del período

El sistema NO DEBE (SHALL NOT) entregar liquidaciones al rol `parcelero` mientras el período no tenga `liquidaciones_cerradas` en verdadero.

#### Scenario: Listado antes del cierre

- **WHEN** un `parcelero` lista liquidaciones y el período aún no está cerrado
- **THEN** el sistema no incluye esas liquidaciones en la respuesta

#### Scenario: Consulta directa antes del cierre

- **WHEN** un `parcelero` solicita por identificador una liquidación propia de un período no cerrado
- **THEN** el sistema responde `403` indicando que el administrador debe cerrar el período primero

### Requirement: Listado de períodos publicados

La aplicación DEBE (SHALL) presentar al parcelero la lista de períodos publicados, ordenados del más reciente al más antiguo, y permitir abrir el detalle de cualquiera de ellos.

#### Scenario: Sin períodos publicados

- **WHEN** el condominio no tiene ninguna boleta con `boleta_visible_usuarios` en verdadero
- **THEN** la aplicación informa que aún no hay períodos publicados y sugiere consultar con la administración

#### Scenario: Navegación al detalle y regreso

- **WHEN** el parcelero selecciona un período y luego usa la acción de volver
- **THEN** la aplicación regresa al listado de períodos sin perder el contexto de sesión

### Requirement: Desglose de la liquidación propia

El detalle de un período DEBE (SHALL) mostrar, para cada parcela del usuario, los tres componentes de la liquidación —energía consumida, prorrateo variable y cuota fija— y el total a pagar.

#### Scenario: Usuario con varias parcelas

- **WHEN** un parcelero tiene más de una parcela asociada
- **THEN** la aplicación muestra una tarjeta de desglose independiente por cada parcela, identificada por su número y propietario

#### Scenario: Período sin liquidación para sus parcelas

- **WHEN** el período publicado no contiene liquidaciones para las parcelas del usuario
- **THEN** la aplicación muestra una advertencia en lugar de un desglose vacío

### Requirement: Estado de pago visible

El detalle DEBE (SHALL) indicar si la liquidación está pagada o pendiente, mostrando la fecha de pago cuando corresponda.

#### Scenario: Liquidación pagada

- **WHEN** la liquidación tiene `pagado` en verdadero
- **THEN** la aplicación la marca como pagada e informa la fecha registrada

#### Scenario: Liquidación pendiente

- **WHEN** la liquidación tiene `pagado` en falso
- **THEN** la aplicación la marca como pendiente e indica que el pago se gestiona con la administración

### Requirement: Transparencia de la boleta de la compañía

El detalle del período DEBE (SHALL) mostrar los totales de la boleta colectiva —total de kWh, neto de electricidad, saldo anterior y total de emisión— y el desglose completo de cargos con su clasificación de cálculo.

#### Scenario: Totales parcialmente informados

- **WHEN** alguno de los totales de la boleta no está informado
- **THEN** la aplicación omite esa fila del resumen en lugar de mostrar un valor vacío

#### Scenario: Desglose de cargos

- **WHEN** la boleta tiene ítems de detalle
- **THEN** la aplicación los lista con su descripción, su monto y una etiqueta que indica si el cargo es fijo, variable o informativo

### Requirement: Acceso a la imagen de la boleta original

Cuando la boleta tiene imagen y ha sido publicada, la aplicación DEBE (SHALL) permitir al parcelero abrirla ampliada desde el detalle del período.

#### Scenario: Boleta con imagen publicada

- **WHEN** el período publicado tiene una URL de imagen informada
- **THEN** la aplicación ofrece abrir la imagen en una ventana ampliada identificada con el período

#### Scenario: Boleta sin imagen

- **WHEN** el período no tiene imagen asociada
- **THEN** la aplicación no ofrece la acción de ver la imagen
