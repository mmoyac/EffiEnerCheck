# Spec Delta

## Purpose

Llevar la cuenta corriente de luz de cada parcela, porque el cargo de luz se cobra dentro del gasto común y el comunero puede abonar a su deuda: cargos (saldo inicial y liquidaciones publicadas), abonos de cualquier monto con trazabilidad completa para auditorías, y la cobranza del condominio por período y por deudor.

## ADDED Requirements

### Requirement: Cuenta corriente de luz

Cada parcela DEBE (SHALL) tener una cuenta corriente de luz:
- sus **cargos** son el saldo inicial vigente y las liquidaciones de los períodos **publicados**;
- sus **abonos** son los no anulados;
- su **saldo** es cargos menos abonos (si es negativo, es saldo a favor).

Las liquidaciones de períodos no publicados NO DEBEN (SHALL NOT) ser cargos. El sistema DEBE (SHALL) exponer `GET /api/v1/cuenta-luz/parcelas/{parcela_id}` con los cargos (monto, cubierto y estado), los abonos (incluidos los anulados, marcados) y el saldo. La administración DEBE (SHALL) poder consultar cualquier parcela de su condominio; el comunero, solo las suyas.

#### Scenario: Saldo de una parcela

- **WHEN** una parcela tiene un saldo inicial de $5.000 y liquidaciones publicadas de $10.000 y $11.000, sin abonos
- **THEN** su saldo es $26.000

#### Scenario: Comunero consulta otra parcela

- **WHEN** un comunero pide la cuenta de una parcela que no es suya
- **THEN** el sistema responde `404`

### Requirement: Imputación de abonos a la deuda más antigua

Los abonos DEBEN (SHALL) imputarse en orden de fecha a los cargos más antiguos primero: el saldo inicial y después los meses en orden. Cada cargo DEBE (SHALL) quedar **pagado** (cubierto por completo, con la fecha del abono que lo completó), **parcial** o **pendiente**. El monto abonado, el estado pagado y la fecha de pago de cada liquidación DEBEN (SHALL) derivarse de esta imputación y recalcularse cuando se registra o anula un abono, cambia el saldo inicial o se publica un período.

#### Scenario: Abono parcial

- **WHEN** la parcela debe un saldo inicial de $5.000 y octubre $10.000, y abona $12.000
- **THEN** el saldo inicial queda pagado, octubre queda parcial con $7.000 cubiertos y el saldo es $3.000 más los meses siguientes

#### Scenario: Saldo a favor al publicar

- **WHEN** una parcela tiene $9.000 a favor y se publica un período donde le corresponden $12.000
- **THEN** esa liquidación queda parcial con $9.000 cubiertos

### Requirement: Registro de abonos

El sistema DEBE (SHALL) exponer `POST /api/v1/cuenta-luz/abonos`, restringido a roles administrativos, para registrar uno o varios abonos (todo o nada) con fecha (no futura), nota opcional y monto mayor que cero por parcela. El sistema DEBE (SHALL) rechazar parcelas de otro condominio y parcelas repetidas. Cada abono DEBE (SHALL) guardar quién lo registró y cuándo, y registrarse en la auditoría como `REGISTRAR_ABONO_LUZ`, con el monto, la fecha, la nota y el saldo antes y después.

#### Scenario: Abonos del gasto común

- **WHEN** el administrador registra los abonos de varias parcelas con la fecha del pago del gasto común
- **THEN** cada abono queda en la cuenta de su parcela y en la auditoría, con el saldo antes y después

#### Scenario: Fecha futura

- **WHEN** se intenta registrar un abono con fecha futura
- **THEN** el sistema responde `422` y no registra nada

### Requirement: Anulación de abonos sin borrado

Un abono NO DEBE (SHALL NOT) borrarse. El sistema DEBE (SHALL) exponer `POST /api/v1/cuenta-luz/abonos/{id}/anular`, restringido a roles administrativos, con un motivo obligatorio. El abono anulado DEBE (SHALL) dejar de contar en el saldo, conservarse visible con su motivo, quién lo anuló y cuándo, y registrarse en la auditoría como `ANULAR_ABONO_LUZ`. No se puede anular dos veces ni anular un saldo inicial por esta vía.

#### Scenario: Abono registrado por error

- **WHEN** el administrador anula un abono indicando el motivo
- **THEN** el saldo vuelve a su valor anterior y el abono sigue visible en la cuenta como anulado, con su motivo

### Requirement: Saldo inicial de luz en el onboarding

La planilla de la lectura inicial DEBE (SHALL) aceptar una columna opcional «Saldo luz» con la deuda por luz anterior a la plataforma, y la plantilla DEBE (SHALL) incluirla con el saldo vigente.
- Una celda vacía no cambia el saldo; 0 lo deja sin deuda; un valor negativo es un error de fila.
- La vista previa DEBE (SHALL) informar los saldos que cambian.
- Al aplicar, el saldo vigente DEBE (SHALL) anularse con motivo, nunca sobrescribirse, y registrarse el nuevo.
- Eliminar la lectura inicial DEBE (SHALL) anular sus saldos, sin borrarlos.

#### Scenario: Carga del saldo inicial

- **WHEN** la planilla de la lectura inicial trae «45.000» en el saldo de luz de la parcela 1
- **THEN** la vista previa lo informa y, al aplicar, la cuenta de la parcela 1 parte con $45.000 de deuda

#### Scenario: Corrección del saldo inicial

- **WHEN** se vuelve a cargar la planilla con otro saldo para la parcela 1
- **THEN** el saldo anterior queda anulado con su motivo y rige el nuevo

### Requirement: Resumen de cobranza

El sistema DEBE (SHALL) exponer `GET /api/v1/cuenta-luz/resumen`, restringido a roles administrativos y acotado al condominio, con:
- los totales: saldo inicial, emitido en períodos publicados, cargos, abonado, por cobrar y a favor;
- la cobranza por período y del saldo inicial: emitido, cubierto, pendiente y cargos pagados;
- los deudores: cada parcela con saldo positivo, con sus cargos pendientes o parciales y la fecha de su último abono.

#### Scenario: Totales de cobranza

- **WHEN** se emitieron $87.000 en cargos y se abonaron $66.000, con todos los saldos deudores sumando $21.000
- **THEN** el resumen informa cargos $87.000, abonado $66.000 y por cobrar $21.000

### Requirement: Pantalla de liquidaciones y cobranza

La consola DEBE (SHALL) ofrecer a la administración una pantalla de cobranza con:
- los indicadores;
- la cobranza por período;
- los deudores, con registro de abonos individual (cualquier monto) o masivo (el saldo de cada parcela seleccionada) con fecha y nota;
- la cuenta de cada parcela, con sus movimientos y la anulación con motivo;
- la exportación de los deudores a un CSV legible en Excel.

#### Scenario: Registrar los pagos del gasto común

- **WHEN** el administrador selecciona las parcelas que pagaron y registra sus abonos con la fecha
- **THEN** los saldos se actualizan, las parcelas al día salen de la lista de deudores y los indicadores cambian

#### Scenario: Exportar deudores

- **WHEN** el administrador exporta los deudores
- **THEN** obtiene un archivo con cada parcela, su propietario, los meses adeudados y su saldo
