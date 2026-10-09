# Spec Delta

## ADDED Requirements

### Requirement: Saldo y cuenta de luz del comunero

El portal DEBE (SHALL) mostrar al comunero, en *Mis liquidaciones*, el saldo de luz de cada una de sus parcelas («Debes $X por luz», al día, o saldo a favor). También DEBE (SHALL) permitirle ver su cuenta: el saldo inicial, cada mes publicado con su estado (pagado, parcial o pendiente) y sus abonos con fecha. En el detalle de cada período, el estado de pago DEBE (SHALL) reflejar si el mes está pagado, parcial (con lo abonado) o pendiente.

#### Scenario: Comunero con deuda

- **WHEN** el comunero debe $20.486 por luz
- **THEN** ve «Debes $20.486 por luz» y puede abrir su cuenta para ver los cargos y abonos

#### Scenario: Comunero al día

- **WHEN** el saldo de su parcela es cero
- **THEN** ve que está al día con la luz

#### Scenario: Mes con abono parcial

- **WHEN** el comunero abre un período publicado cuya liquidación está cubierta en parte
- **THEN** el estado indica «Parcial» y cuánto se ha abonado
