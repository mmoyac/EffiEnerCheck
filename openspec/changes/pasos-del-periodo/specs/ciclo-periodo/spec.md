# Spec Delta

## ADDED Requirements

### Requirement: Liquidaciones descartadas cuando cambian sus insumos

Mientras el período no esté cerrado, el sistema DEBE (SHALL) descartar las liquidaciones calculadas cuando cambia algo de lo que las produjo:
- se reabren las lecturas;
- se edita el desglose (totales o conceptos) o se reprocesa la boleta;
- se registra, corrige o sincroniza una lectura.

La acción auditada DEBE (SHALL) informar cuántas liquidaciones se descartaron. Un reintento de sincronización que no modifica ninguna lectura NO DEBE (SHALL NOT) descartarlas. Así, cerrar el período exige recalcular con los datos vigentes.

#### Scenario: Reabrir lecturas después de calcular

- **WHEN** el administrador reabre las lecturas de un período ya calculado
- **THEN** las liquidaciones se descartan y, al volver a cerrar las lecturas, el período no puede cerrarse hasta recalcular

#### Scenario: Editar el desglose después de calcular

- **WHEN** el administrador cambia los totales o los conceptos de un período ya calculado
- **THEN** el desglose vuelve a borrador y las liquidaciones se descartan

#### Scenario: Corregir una lectura después de una vista previa

- **WHEN** se corrige o sincroniza una lectura de un período con liquidaciones calculadas y las lecturas abiertas
- **THEN** las liquidaciones se descartan
