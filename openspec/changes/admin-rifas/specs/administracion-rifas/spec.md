# Spec Delta

## Purpose

Permitir que la administración delegue la operación de las rifas en un comunero de confianza, sin darle acceso al resto del portal y sin que deje de ser comunero en su propia parcela.

## ADDED Requirements

### Requirement: Facultades del comunero con permiso de administración de rifas

Un `comunero` con el permiso `administra_rifas` DEBE (SHALL) poder ejecutar, en las rifas de su condominio, las mismas operaciones que la administración: crear y editar rifas, registrar compras a nombre de cualquier parcela, confirmar transferencias, anular compras, cerrar y reabrir rifas, marcar imputaciones, consultar la caja, ver los vouchers y descargar los CSV. NO DEBE (SHALL NOT) poder eliminar una rifa, que sigue reservado al `super_admin`.

#### Scenario: Crea una rifa

- **WHEN** un comunero con el permiso crea una rifa en su condominio
- **THEN** el sistema la crea igual que si la creara un `admin_condominio` y registra la auditoría a su nombre

#### Scenario: Comunero sin el permiso

- **WHEN** un comunero sin el permiso intenta crear, cerrar o reabrir una rifa, confirmar un pago o anular una compra
- **THEN** el sistema responde `403` y no ejecuta la operación

#### Scenario: Intenta eliminar una rifa

- **WHEN** un comunero con el permiso pide eliminar una rifa
- **THEN** el sistema responde `403`

#### Scenario: Rifa de otro condominio

- **WHEN** un comunero con el permiso opera sobre una rifa de otro condominio
- **THEN** el sistema responde `403`, igual que a la administración, y no ejecuta la operación

### Requirement: Canal de las ventas del administrador de rifas

Una compra registrada por un comunero con el permiso DEBE (SHALL) quedar con canal `administracion` cuando es a nombre de una parcela que no es suya, y con canal `portal` cuando es a nombre de una de sus parcelas, con las formas de pago de cada canal.

#### Scenario: Venta a otra parcela

- **WHEN** el administrador de rifas registra una compra en efectivo a nombre de una parcela que no es suya
- **THEN** la compra queda con canal `administracion`, pagada al registrarse

#### Scenario: Compra para su propia parcela

- **WHEN** el administrador de rifas compra números para su propia parcela
- **THEN** la compra queda con canal `portal` y solo admite las formas de pago del portal

### Requirement: Visibilidad completa de las rifas para el administrador de rifas

El detalle de una rifa DEBE (SHALL) mostrar a un comunero con el permiso todas las compras e imputaciones de la rifa, como a la administración. Fuera de las rifas, sus consultas DEBEN (SHALL) seguir filtradas a sus parcelas como las de cualquier comunero.

#### Scenario: Ve todas las compras

- **WHEN** el administrador de rifas abre el detalle de una rifa
- **THEN** recibe las compras e imputaciones de todas las parcelas

#### Scenario: Su liquidación de luz sigue siendo solo suya

- **WHEN** el administrador de rifas consulta liquidaciones de energía
- **THEN** recibe solo las de sus parcelas, como cualquier comunero

### Requirement: Pagos en línea en revisión de las rifas

Un comunero con el permiso DEBE (SHALL) poder listar y resolver los pagos en línea en revisión de su condominio cuyo concepto es una compra de rifa. NO DEBE (SHALL NOT) ver ni resolver los de otros conceptos.

#### Scenario: Lista los pagos en revisión

- **WHEN** el administrador de rifas lista los pagos en revisión
- **THEN** recibe solo los de concepto compra de rifa de su condominio

#### Scenario: Pago de otro concepto

- **WHEN** el administrador de rifas intenta resolver un pago en revisión de otro concepto
- **THEN** el sistema responde `404` y no lo modifica

### Requirement: Permiso sin efecto fuera de su ámbito

El permiso NO DEBE (SHALL NOT) otorgar acceso a energía, usuarios, parcelas, panel, auditoría, cobranza ni pasarelas. Sin el módulo `rifas` contratado, el permiso NO DEBE (SHALL NOT) dar acceso a ninguna operación de rifas.

#### Scenario: Pide la lista de usuarios

- **WHEN** el administrador de rifas pide la lista de usuarios o de parcelas, o crea una boleta
- **THEN** el sistema responde `403`

#### Scenario: Condominio sin el módulo de rifas

- **WHEN** el condominio no tiene contratado el módulo `rifas` y el administrador de rifas invoca un endpoint de rifas
- **THEN** el sistema responde `403` con el detalle del módulo no habilitado

### Requirement: Acceso a la administración de rifas desde el cliente

El cliente web DEBE (SHALL) mantener la pantalla de inicio del comunero con el permiso y ofrecerle, desde sus pantallas, un acceso a la administración de rifas (`/rifas`). Desde la administración de rifas DEBE (SHALL) poder volver a sus pantallas de comunero. Las pantallas `/rifas` y `/rifas/:id` DEBEN (SHALL) mostrarle las acciones de administración, salvo eliminar, y un bloque con los pagos en línea de rifas por revisar.

#### Scenario: Entra a administrar rifas

- **WHEN** un comunero con el permiso inicia sesión
- **THEN** llega a su pantalla de comunero y ve un acceso «Administrar rifas» que lo lleva a `/rifas`

#### Scenario: Comunero sin el permiso abre /rifas

- **WHEN** un comunero sin el permiso abre `/rifas`
- **THEN** el cliente lo redirige a su pantalla de inicio
