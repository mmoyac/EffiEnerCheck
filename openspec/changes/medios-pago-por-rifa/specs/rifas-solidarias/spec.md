# Spec Delta

## ADDED Requirements

### Requirement: Formas de pago aceptadas por rifa

Cada rifa DEBE (SHALL) definir qué formas de pago acepta, entre `efectivo`, `transferencia` y `gasto_comun`, con al menos una. Por omisión, las acepta todas. El sistema DEBE (SHALL) rechazar con `422` una compra con una forma de pago no aceptada por la rifa, y las pantallas de venta DEBEN (SHALL) ofrecer solo las aceptadas. Las compras ya registradas conservan su forma de pago aunque la rifa deje de aceptarla.

#### Scenario: Rifa solo con transferencia

- **WHEN** una rifa acepta solo transferencia y la portería intenta registrar una venta en efectivo
- **THEN** el sistema responde `422` con el detalle "Esta rifa no acepta pagos con efectivo" y no registra la venta

#### Scenario: Rifa sin formas de pago

- **WHEN** se crea o se edita una rifa sin ninguna forma de pago
- **THEN** el sistema responde `422` y no guarda el cambio
