## ADDED Requirements

### Requirement: Tratamiento de los montos negativos

Un ítem con monto negativo representa un crédito de la compañía —descuento, nota de crédito, abono o devolución— y DEBE (SHALL) repartirse según su propio `tipo_calculo`, con el mismo criterio que un cargo positivo. Las fórmulas del motor NO DEBEN (SHALL NOT) modificarse para acomodarlo: la aritmética existente ya lo trata correctamente.

#### Scenario: Crédito de tipo fijo

- **WHEN** la boleta contiene un ítem `fijo` con monto negativo
- **THEN** el crédito reduce en partes iguales la cuota fija de cada parcela activa

#### Scenario: Crédito de tipo variable

- **WHEN** la boleta contiene un ítem `variable` con monto negativo
- **THEN** el crédito reduce el prorrateo variable de cada parcela en proporción a su consumo

#### Scenario: El valor del kWh no se distorsiona

- **WHEN** se compara un período con un crédito registrado contra el mismo período sin ese crédito y con la emisión correspondientemente mayor
- **THEN** el `valor_kwh` resultante es el mismo, porque `monto_total_emision` ya viene rebajado por el crédito y la resta de la suma de ítems lo compensa exactamente

#### Scenario: Crédito no registrado

- **WHEN** un crédito presente en la boleta no queda registrado como ítem
- **THEN** el total liquidado sigue cuadrando con la emisión, pero el crédito se absorbe en el componente de energía y se reparte por consumo en lugar de según su naturaleza, distorsionando el desglose

## MODIFIED Requirements

### Requirement: Clasificación de los cargos de la boleta

Cada ítem de detalle DEBE (SHALL) tener un `tipo_calculo` que determina cómo se reparte: `fijo` se divide en partes iguales entre las parcelas activas, `variable` se prorratea según el consumo de cada parcela, e `informativo` no participa del reparto. El valor `pendiente` identifica a los ítems que el administrador aún no ha juzgado y tampoco participa del reparto. `informativo` es el mecanismo explícito por el cual el administrador deja un cargo fuera del reparto conservándolo visible en el desglose.

#### Scenario: Ítem informativo

- **WHEN** la boleta contiene un ítem con `tipo_calculo` igual a `informativo`
- **THEN** su monto no se suma ni a los cargos fijos ni a los variables y no altera ninguna liquidación

#### Scenario: Ítem pendiente

- **WHEN** la boleta contiene un ítem con `tipo_calculo` igual a `pendiente`
- **THEN** su monto no se suma ni a los cargos fijos ni a los variables, del mismo modo que un ítem informativo

#### Scenario: Exclusión deliberada de un cargo

- **WHEN** el administrador determina que un cargo de la compañía no debe repartirse entre los parceleros
- **THEN** lo clasifica como `informativo`, con lo que el monto queda visible en el desglose de la boleta pero fuera del reparto

### Requirement: Cálculo idempotente

El sistema DEBE (SHALL) exponer `POST /api/v1/liquidaciones/calcular/{boleta_id}`, restringido a roles administrativos, que elimina las liquidaciones previas del período antes de generar las nuevas, de modo que pueda ejecutarse tantas veces como sea necesario sin duplicar registros. El cálculo DEBE (SHALL) exigir que la boleta esté en estado `validada`, garantizando que el administrador ya juzgó qué entra al reparto.

#### Scenario: Recálculo tras corregir una lectura

- **WHEN** el administrador corrige una lectura y vuelve a ejecutar el cálculo
- **THEN** el sistema borra las liquidaciones anteriores del período y persiste el nuevo juego completo, registrando la acción `CALCULAR_LIQUIDACIONES`

#### Scenario: Cálculo con lecturas aún abiertas

- **WHEN** se solicita calcular sobre un período con `lecturas_cerradas` en falso
- **THEN** el sistema ejecuta el cálculo, permitiendo previsualizar y ajustar antes del cierre

#### Scenario: Cálculo sobre período cerrado

- **WHEN** se solicita calcular sobre un período con `liquidaciones_cerradas` en verdadero
- **THEN** el sistema responde `409` con el detalle `"El período ya está cerrado. No se puede recalcular."`

#### Scenario: Cálculo sin corroborar el desglose

- **WHEN** se solicita calcular sobre una boleta en estado `borrador`
- **THEN** el sistema responde `409` indicando que el administrador debe corroborar los ítems antes de calcular, y no genera liquidaciones
