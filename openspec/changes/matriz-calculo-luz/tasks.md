# Tasks

## 1. Backend

- [x] 1.1 Columnas `condominios.matriz_calculo_luz` y `boletas_maestras.matriz_calculo` (CHECK, default `fijo_y_variable`) + migración.
- [x] 1.2 Motor: con `cargo_fijo`, los ítems `variable` se reparten parejo como los `fijo`.
- [x] 1.3 Condominio: crear/editar/responder la matriz por defecto; auditoría en `UPDATE_CONDOMINIO`; copia desde desarrollo.
- [x] 1.4 Boleta: copia la matriz al crearse; `PUT /boletas/{id}/matriz-calculo` (solo super_admin, 409 si cerrada, descarta liquidaciones, `CAMBIAR_MATRIZ_CALCULO`).
- [x] 1.5 PDF del período: matriz aplicada y nota del criterio.
- [x] 1.6 Tests: ejemplo de la planilla de junio, cuadre al peso, guardas del endpoint.

## 2. Frontend

- [x] 2.1 Condominios: selector de matriz por defecto.
- [x] 2.2 Detalle del período: matriz aplicada, selector para super_admin, liquidaciones en dos componentes con `cargo_fijo`.
- [x] 2.3 Comunero: desglose «Cargo fijo» y «Consumo (kWh × $/kWh)» con `cargo_fijo`.

## 3. Documentación

- [x] 3.1 `CLAUDE.md`, `docs/flujo-periodo.md`, recorrido de Energía. Verificar con `openspec validate matriz-calculo-luz --strict`.
