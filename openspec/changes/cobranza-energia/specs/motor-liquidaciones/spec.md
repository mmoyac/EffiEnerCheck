# Spec Delta

## REMOVED Requirements

### Requirement: Registro del pago de una liquidación

**Reason**: El pago se marcaba a mano, como pagado o pendiente por mes, y solo antes de cerrar el período, cuando todavía no se le había cobrado a nadie. El cargo de luz se cobra en el gasto común después de publicar, y el comunero puede abonar a su deuda total.

**Migration**: Se elimina `PATCH /api/v1/liquidaciones/{id}/pago`. Los pagos se registran como abonos en la cuenta corriente de luz (`POST /api/v1/cuenta-luz/abonos`). La migración convierte cada liquidación ya marcada como pagada en un abono por su total y con su fecha de pago.

## ADDED Requirements

### Requirement: Estado de pago derivado de la cuenta corriente

El estado de pago de una liquidación (`monto_abonado`, `pagado`, `fecha_pago`) NO DEBE (SHALL NOT) marcarse a mano: DEBE (SHALL) derivarse de la imputación de los abonos de la cuenta corriente de luz de su parcela. Una liquidación de un período no publicado DEBE (SHALL) quedar sin abonos imputados.

#### Scenario: Liquidación cubierta por abonos

- **WHEN** los abonos de la parcela cubren por completo la liquidación de octubre
- **THEN** la liquidación queda con `pagado` en verdadero, `monto_abonado` igual a su total y `fecha_pago` igual a la del abono que la completó

#### Scenario: Liquidación cubierta en parte

- **WHEN** los abonos cubren solo una parte de la liquidación
- **THEN** la liquidación queda con `pagado` en falso y `monto_abonado` con lo cubierto
