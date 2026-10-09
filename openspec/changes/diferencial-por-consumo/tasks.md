# Tasks

## 1. Motor

- [x] 1.1 `services/enercheck.py`: el diferencial se prorratea por consumo con los variables; sin consumo registrado, diferencial y variables van a la cuota fija. Verificar con pytest: el resultado por parcela es `kWh × (emisión − fijos) / Σ kWh + fijos / n` (±1), una parcela sin consumo paga solo los fijos, el caso sin consumo cuadra y la suite completa queda en verde.
- [x] 1.2 Cargar el período de septiembre 2026 de la planilla en desarrollo y comparar parcela por parcela.

## 2. Documentación

- [x] 2.1 `CLAUDE.md`, `AGENTS.md`, `README.md`, `docs/flujo-periodo.md` y `.html`, `docs/ayuda-energia.md`, `docs/presentacion-comunidad.md` y `recorridos/energia.js`. Verificar con `openspec validate diferencial-por-consumo --strict`.
