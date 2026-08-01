# motor-liquidaciones Specification

## Purpose

Repartir el monto total de la boleta colectiva entre las parcelas del condominio de forma transparente y cuadrada. El principio rector es que la suma de todas las liquidaciones debe corresponder al total efectivamente emitido por la compañía: por eso el valor del kWh se despeja a la inversa desde el total de emisión, descontando los cargos que se prorratean aparte. La energía que la boleta cobra pero que ningún remarcador registró (pérdidas, consumo de áreas comunes, medidores no cubiertos) se reparte en partes iguales como diferencial dentro de la cuota fija.

## Requirements

### Requirement: Clasificación de los cargos de la boleta

Cada ítem de detalle DEBE (SHALL) tener un `tipo_calculo` que determina cómo se reparte: `fijo` se divide en partes iguales entre las parcelas activas, `variable` se prorratea según el consumo de cada parcela, e `informativo` no participa del reparto.

#### Scenario: Ítem informativo

- **WHEN** la boleta contiene un ítem con `tipo_calculo` igual a `informativo`
- **THEN** su monto no se suma ni a los cargos fijos ni a los variables y no altera ninguna liquidación

### Requirement: Cálculo del valor del kWh a la inversa

El sistema DEBE (SHALL) calcular el monto atribuible a energía como el total de emisión menos la suma de los cargos fijos y variables, y obtener el valor del kWh dividiendo ese monto por el total de kWh de la compañía.

#### Scenario: Fórmula del valor del kWh

- **WHEN** el motor se ejecuta sobre una boleta con totales y cargos cargados
- **THEN** calcula `monto_total_energia = monto_total_emision − (Σ cargos fijos + Σ cargos variables)` y `valor_kwh = monto_total_energia / total_kwh_compania`

### Requirement: Diferencial de energía no registrada

El sistema DEBE (SHALL) calcular el diferencial como la energía de la boleta que los remarcadores no capturaron, valorizada al mismo valor del kWh, e incorporarla a la cuota fija que se divide entre las parcelas activas.

#### Scenario: Fórmula del diferencial y la cuota fija

- **WHEN** el motor se ejecuta
- **THEN** calcula `diferencial = (total_kwh_compania − Σ kwh_remarcadores) × valor_kwh` y `cuota_fija = (Σ cargos fijos + diferencial) / total_parcelas_activas`

#### Scenario: Ítem informativo de diferencial

- **WHEN** la boleta contiene un ítem cuya descripción incluye la palabra `diferencial`
- **THEN** el motor actualiza su monto con el diferencial calculado redondeado, dejándolo visible en el desglose de la boleta

### Requirement: Composición de la liquidación de cada parcela

Para cada parcela activa el sistema DEBE (SHALL) calcular tres componentes y su total, redondeando cada componente al entero más cercano antes de sumarlos.

#### Scenario: Fórmula por parcela

- **WHEN** el motor procesa una parcela activa con un consumo registrado
- **THEN** calcula `monto_energia = valor_kwh × kwh_parcela`, `prorrateo_variable = Σ cargos variables × (kwh_parcela / Σ kwh_remarcadores)` y `cuota_fija` igual para todas, y fija `total_pagar_mes` como la suma de los tres componentes redondeados

#### Scenario: Parcela activa sin lectura

- **WHEN** una parcela activa no tiene lectura registrada en el período
- **THEN** el motor la trata con consumo cero, por lo que solo se le imputa la cuota fija

#### Scenario: Sin consumo registrado en el condominio

- **WHEN** la suma de kWh de todos los remarcadores es cero
- **THEN** el motor asigna prorrateo variable cero a todas las parcelas y evita la división por cero

### Requirement: Alcance del cálculo a las parcelas activas

El motor DEBE (SHALL) emitir liquidación únicamente para las parcelas con `activa` en verdadero, y usar ese mismo conjunto como divisor de la cuota fija.

#### Scenario: Parcela desactivada

- **WHEN** una parcela del condominio tiene `activa` en falso
- **THEN** no se le genera liquidación y no cuenta en el divisor de la cuota fija

#### Scenario: Condominio sin parcelas activas

- **WHEN** el condominio no tiene ninguna parcela activa
- **THEN** el motor responde `422` con el mensaje `"No hay parcelas activas en este condominio"`

### Requirement: Datos mínimos para ejecutar el cálculo

El motor DEBE (SHALL) rechazar la ejecución cuando la boleta no tiene informados `total_kwh_compania` ni `monto_neto_electricidad_consumida`.

#### Scenario: Total de kWh ausente

- **WHEN** se solicita calcular sobre una boleta sin `total_kwh_compania`
- **THEN** el sistema responde `422` indicando qué campo falta y no crea liquidaciones

#### Scenario: Monto neto de electricidad ausente

- **WHEN** se solicita calcular sobre una boleta sin `monto_neto_electricidad_consumida`
- **THEN** el sistema responde `422` indicando qué campo falta y no crea liquidaciones

### Requirement: Cálculo idempotente

El sistema DEBE (SHALL) exponer `POST /api/v1/liquidaciones/calcular/{boleta_id}`, restringido a roles administrativos, que elimina las liquidaciones previas del período antes de generar las nuevas, de modo que pueda ejecutarse tantas veces como sea necesario sin duplicar registros.

#### Scenario: Recálculo tras corregir una lectura

- **WHEN** el administrador corrige una lectura y vuelve a ejecutar el cálculo
- **THEN** el sistema borra las liquidaciones anteriores del período y persiste el nuevo juego completo, registrando la acción `CALCULAR_LIQUIDACIONES`

#### Scenario: Cálculo con lecturas aún abiertas

- **WHEN** se solicita calcular sobre un período con `lecturas_cerradas` en falso
- **THEN** el sistema ejecuta el cálculo, permitiendo previsualizar y ajustar antes del cierre

#### Scenario: Cálculo sobre período cerrado

- **WHEN** se solicita calcular sobre un período con `liquidaciones_cerradas` en verdadero
- **THEN** el sistema responde `409` con el detalle `"El período ya está cerrado. No se puede recalcular."`

### Requirement: Consulta de liquidaciones

El sistema DEBE (SHALL) exponer `GET /api/v1/liquidaciones/` y `GET /api/v1/liquidaciones/{liquidacion_id}` para cualquier rol autenticado, con filtro opcional por boleta y acotados al tenant activo.

#### Scenario: Filtro por período

- **WHEN** se consultan liquidaciones indicando un `boleta_id`
- **THEN** el sistema devuelve solo las de ese período

#### Scenario: Liquidación de otro condominio

- **WHEN** se solicita por identificador una liquidación de otro condominio
- **THEN** el sistema responde `403` con el detalle `"Sin acceso a esta liquidación"`

### Requirement: Registro del pago de una liquidación

El sistema DEBE (SHALL) exponer `PATCH /api/v1/liquidaciones/{liquidacion_id}/pago`, restringido a roles administrativos, que marca la liquidación como pagada o pendiente junto con la fecha de pago.

#### Scenario: Marcado de pago

- **WHEN** un administrador marca una liquidación como pagada indicando la fecha
- **THEN** el sistema actualiza `pagado` y `fecha_pago` y registra la acción `MARCAR_PAGO`

#### Scenario: Marcado sobre período cerrado

- **WHEN** se intenta marcar el pago de una liquidación cuyo período tiene `liquidaciones_cerradas` en verdadero
- **THEN** el sistema responde `409` con el detalle `"El período está cerrado y no permite modificaciones"`
