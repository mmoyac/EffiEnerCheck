# Spec Delta

## Purpose

Describir el proceso del módulo de Energía de punta a punta, tal como lo vive un condominio: desde la incorporación, con la lectura inicial de los medidores, hasta que cada comunero consulta la liquidación publicada de su parcela, pasando por la boleta de la compañía, la toma de lecturas en terreno y el cálculo cuadrado al peso. Cada requisito resume una etapa y remite a la spec que la norma en detalle ([`boletas-maestras`](../boletas-maestras/spec.md), [`ciclo-periodo`](../ciclo-periodo/spec.md), [`lecturas-remarcadores`](../lecturas-remarcadores/spec.md), [`ocr-boletas`](../ocr-boletas/spec.md), [`motor-liquidaciones`](../motor-liquidaciones/spec.md), [`portal-parcelero`](../portal-parcelero/spec.md)).

## ADDED Requirements

### Requirement: Etapa 0 — Lectura inicial en la incorporación del condominio

Antes de la primera boleta, el sistema DEBE (SHALL) permitir registrar, una sola vez, la lectura de partida de cada medidor en un período de **lectura inicial**. Ese período no tiene boleta ni liquidaciones y nunca se publica. La lectura de partida DEBE (SHALL) poder registrarse con la aplicación del lector (con o sin conexión, con foto del medidor) o, solo en este período de incorporación, mediante una carga masiva desde una planilla Excel con vista previa. La lectura inicial DEBE (SHALL) cerrarse con todas las parcelas registradas antes de crear la primera boleta. Detalle en [`boletas-maestras`](../boletas-maestras/spec.md) y [`lecturas-remarcadores`](../lecturas-remarcadores/spec.md).

#### Scenario: Incorporación con planilla

- **WHEN** el administrador abre la lectura inicial de un condominio sin boletas, carga la planilla con las lecturas de partida y cierra las lecturas
- **THEN** cada parcela queda con su lectura inicial registrada y el condominio queda listo para su primera boleta

#### Scenario: Primera boleta sin lectura inicial

- **WHEN** se intenta crear la primera boleta de un condominio cuyas parcelas no tienen lectura previa
- **THEN** el sistema advierte qué parcelas partirían en cero y solo crea la boleta si el administrador lo acepta explícitamente

### Requirement: Etapa 1 — Primera boleta del período

Al crear la boleta de un período, el sistema DEBE (SHALL) generar una lectura por parcela con la lectura anterior tomada del período previo (la lectura inicial, en la primera boleta) y asignar el mes siguiente al último período. La imagen de la boleta de la compañía DEBE (SHALL) ser opcional. Para liquidar bastan los totales de kWh de la compañía, monto neto y total de emisión, ingresados a mano o leídos por OCR. Los cargos de detalle son opcionales y pueden variar mes a mes. Detalle en [`boletas-maestras`](../boletas-maestras/spec.md) y [`ocr-boletas`](../ocr-boletas/spec.md).

#### Scenario: Primera boleta tras la lectura inicial

- **WHEN** el administrador genera el período después de cerrar la lectura inicial
- **THEN** la boleta queda en el mes siguiente y cada parcela parte con su lectura inicial como lectura anterior

#### Scenario: Sin boleta física

- **WHEN** el administrador ingresa a mano solo los tres totales de la boleta, sin imagen ni cargos de detalle
- **THEN** el período puede corroborarse y liquidarse

### Requirement: Etapa 2 — Toma de lecturas en terreno

El lector DEBE (SHALL) registrar la lectura actual de cada parcela con la aplicación del lector. La aplicación DEBE (SHALL) mostrar la lectura anterior, calcular los kWh consumidos al ingresar la lectura actual e impedir una lectura menor que la anterior. La toma DEBE (SHALL) funcionar sin conexión, con foto opcional del medidor, y sincronizarse sin pisar cambios hechos en el servidor. Las lecturas solo se cierran cuando todas las parcelas tienen su lectura tomada. Detalle en [`lecturas-remarcadores`](../lecturas-remarcadores/spec.md) y [`ciclo-periodo`](../ciclo-periodo/spec.md).

#### Scenario: Lectura del mes

- **WHEN** el lector ingresa la lectura actual de una parcela cuya lectura anterior es 1.000 y el medidor marca 1.250
- **THEN** la aplicación muestra 250 kWh consumidos y la lectura queda registrada para el período

#### Scenario: Cierre de lecturas incompleto

- **WHEN** se intenta cerrar las lecturas con alguna parcela sin lectura tomada
- **THEN** el sistema lo impide e informa que faltan lecturas

### Requirement: Etapa 3 — Desglose corroborado

Antes de calcular, el administrador DEBE (SHALL) corroborar el desglose del período: los cargos de detalle, clasificados como fijo, variable o informativo, y los totales. Cualquier cambio posterior en las cifras DEBE (SHALL) exigir una nueva corroboración. Detalle en [`ciclo-periodo`](../ciclo-periodo/spec.md) y [`motor-liquidaciones`](../motor-liquidaciones/spec.md).

#### Scenario: Cálculo sin corroborar

- **WHEN** se intenta calcular un período cuyo desglose no está corroborado
- **THEN** el sistema lo impide e indica que primero debe corroborarse el desglose

### Requirement: Etapa 4 — Cálculo de las liquidaciones cuadrado al peso

El sistema DEBE (SHALL) calcular una liquidación por parcela activa, con su energía, su prorrateo variable y su cuota fija. La suma de las liquidaciones DEBE (SHALL) ser exactamente el total de emisión de la boleta. El cálculo DEBE (SHALL) poder repetirse sin duplicar resultados mientras el período no esté cerrado. Detalle en [`motor-liquidaciones`](../motor-liquidaciones/spec.md).

#### Scenario: Cuadre con la boleta

- **WHEN** el administrador calcula las liquidaciones de un período con las lecturas cerradas y el desglose corroborado
- **THEN** cada parcela activa tiene su liquidación y la suma de todas es exactamente el total de emisión

### Requirement: Etapa 5 — Cierre y publicación

El administrador DEBE (SHALL) cerrar el período para fijar las liquidaciones y luego publicarlo para hacerlo visible a los comuneros. Antes de publicar, el período DEBE (SHALL) poder reabrirse para corregir. Una vez publicado, NO DEBE (SHALL NOT) poder reabrirse. Detalle en [`ciclo-periodo`](../ciclo-periodo/spec.md).

#### Scenario: Publicación

- **WHEN** el administrador publica un período cerrado
- **THEN** el período queda visible para los comuneros y ya no puede reabrirse

### Requirement: Etapa 6 — Consulta del comunero

Cada comunero DEBE (SHALL) poder consultar, solo para sus parcelas y solo en períodos publicados:
- su liquidación, con sus tres componentes y el estado de pago;
- los totales de la boleta del condominio;
- la foto de su medidor, si se tomó.

El comunero NO DEBE (SHALL NOT) acceder a liquidaciones de otras parcelas ni de períodos no publicados. Detalle en [`portal-parcelero`](../portal-parcelero/spec.md) y [`lecturas-remarcadores`](../lecturas-remarcadores/spec.md).

#### Scenario: Comunero consulta su período publicado

- **WHEN** un comunero abre un período publicado
- **THEN** ve solo la liquidación de sus parcelas, con su desglose y estado de pago

#### Scenario: Período cerrado pero no publicado

- **WHEN** un comunero consulta sus liquidaciones de un período cerrado que aún no se publica
- **THEN** el sistema no le entrega esas liquidaciones

### Requirement: Meses siguientes

Desde el segundo período, la boleta nueva DEBE (SHALL) tomar como lectura anterior la lectura del mes previo y proponer los cargos de detalle del mes anterior, con su clasificación y montos en cero, para que el administrador los ajuste. Las lecturas mensuales DEBEN (SHALL) tomarse siempre con la aplicación del lector. La carga desde planilla NO DEBE (SHALL NOT) estar disponible fuera de la lectura inicial. Detalle en [`boletas-maestras`](../boletas-maestras/spec.md) y [`lecturas-remarcadores`](../lecturas-remarcadores/spec.md).

#### Scenario: Segundo período

- **WHEN** el administrador genera el período siguiente a uno ya publicado
- **THEN** cada parcela parte con la lectura del mes previo como lectura anterior y la boleta propone los cargos del mes anterior en cero

#### Scenario: Recorrido completo

- **WHEN** un condominio sin boletas completa la lectura inicial, su primera boleta, la toma de lecturas, el cálculo, el cierre y la publicación
- **THEN** cada comunero ve la liquidación de sus parcelas, su consumo es la diferencia entre la lectura del mes y la inicial, y la suma de todas las liquidaciones es el total de emisión
