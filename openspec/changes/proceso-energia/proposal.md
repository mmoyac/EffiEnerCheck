# Proposal

## Why

Las reglas del módulo de Energía están repartidas en varias specs por capacidad: boletas, ciclo del período, lecturas, motor y portal. Ninguna cuenta el **proceso completo** que vive un condominio, desde que se incorpora hasta que cada comunero ve lo que paga. Antes de salir a producción hace falta una referencia única de ese recorrido, que sirva para capacitar y para revisar, y que una prueba automática compruebe de punta a punta.

Al revisar ese recorrido apareció una inconsistencia. El portal le muestra al comunero solo los períodos **publicados**, pero la API le entrega sus liquidaciones apenas el período se **cierra**. Entre «Cerrar período» y «Publicar» las liquidaciones todavía se pueden reabrir y corregir, así que un comunero podría ver montos que después cambian.

## What Changes

- **Nueva capacidad `proceso-energia`.** Describe el proceso de punta a punta:
  1. **onboarding:** lectura inicial de los medidores, una sola vez, con la app del lector o desde Excel;
  2. **primera boleta:** hereda la lectura inicial; si no está la boleta física, bastan los tres totales;
  3. **toma mensual** en terreno: lectura anterior visible, kWh calculado, sin conexión, foto opcional;
  4. **desglose** corroborado;
  5. **cálculo** cuadrado al peso;
  6. **cierre y publicación**;
  7. **consulta del comunero:** solo lo suyo y solo lo publicado;
  8. **meses siguientes.**

  Cada requisito remite a la spec de detalle que lo norma.
- **Liquidaciones visibles para el comunero solo al publicar.** **BREAKING** para el rol comunero: `GET /liquidaciones` y `GET /liquidaciones/{id}` dejan de entregarle liquidaciones de un período cerrado pero no publicado (antes bastaba el cierre).
- **Prueba de aceptación** del proceso completo por la API: desde un condominio sin boletas hasta la consulta del comunero.

## Cambios relacionados

La spec `proceso-energia` resume el proceso. Sus reglas de detalle llegan a las specs por capacidad desde estos cambios. La spec enlaza a las specs y no a los cambios, porque los cambios se mueven a `archive/` al archivarse y las specs son la referencia permanente.

| Etapa | Cambio que aporta la regla | Spec de detalle |
|---|---|---|
| 0. Lectura inicial y carga desde Excel (solo onboarding) | `lectura-inicial` | `boletas-maestras`, `ciclo-periodo`, `lecturas-remarcadores` |
| 1. Primera boleta: lectura anterior heredada, sin ceros silenciosos | `lectura-inicial` | `boletas-maestras` |
| 1 y 3. Ítems negativos, pendientes, corroboración del desglose | `items-credito-y-validacion` | `boletas-maestras`, `ciclo-periodo`, `motor-liquidaciones`, `ocr-boletas` |
| 2. Toma sin conexión y sincronización | `lecturas-sin-conexion` | `lecturas-remarcadores` |
| 2. La app del lector sigue el orden del recorrido, si está definido | `orden-recorrido` | `gestion-parcelas`, `lecturas-remarcadores` |
| 2 y 6. Foto del medidor y acceso del comunero a ella | `foto-medidor` | `lecturas-remarcadores` |
| 4. Cálculo cuadrado al peso | `cuadre-al-peso` | `motor-liquidaciones` |
| 6. El comunero ve solo lo publicado | este cambio | `portal-parcelero` |
| Después de publicar: cobranza, cuenta corriente de luz y saldo inicial | `cobranza-energia` | `cobranza-energia`, `motor-liquidaciones`, `portal-parcelero` |
| Término «comunero» y renombre `portal-parcelero` → `portal-comunero` | `ajustes-post-presentacion` | todas |

**Orden de archivado:** primero los cambios de detalle (`items-credito-y-validacion`, `lecturas-sin-conexion`, `foto-medidor`, `lectura-inicial`, `cuadre-al-peso`, `orden-recorrido`, `pasos-del-periodo`, `cobranza-energia`), después este, y al final `ajustes-post-presentacion`. Ese último renombra `portal-parcelero`, y en su barrido terminológico debe actualizar también los enlaces de esta spec a `portal-parcelero`.

## Capabilities

### New Capabilities

- `proceso-energia`: el proceso de Energía de punta a punta (onboarding, primera boleta, toma, desglose, cálculo, cierre, publicación y consulta del comunero), como contrato verificable que remite a las specs de detalle.

### Modified Capabilities

- `portal-parcelero`: la visibilidad de las liquidaciones para el comunero queda condicionada a la **publicación** del período, no a su cierre. La spec pasa a llamarse `portal-comunero` al archivar `ajustes-post-presentacion`.

## Impact

- **Backend:** `endpoints/liquidaciones.py`, en el listado y en la consulta por id, para el rol comunero.
- **Tests:** `tests/test_proceso_energia.py` (aceptación de punta a punta) y ajuste de los tests que suponían la visibilidad al cierre, si los hay.
- **Frontend:** sin cambios. El portal ya listaba solo los períodos publicados.
- **Docs:** `docs/flujo-periodo.md` (paso 11: el comunero ve lo publicado) y `CLAUDE.md` (la referencia a la nueva spec).
