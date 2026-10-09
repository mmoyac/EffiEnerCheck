# Proposal

## Why

En el detalle de un período aparecen a la vez varios botones (Cerrar lecturas, Calcular, Corroborar…) y solo el color sugiere un orden, que además no siempre coincide con el orden real. En la prueba de octubre, el botón verde era «Calcular» y el siguiente paso correcto, «Cerrar lecturas», estaba en gris. Un administrador que opera una vez al mes no debería tener que recordar el ciclo.

## What Changes

- **Barra de pasos del período** en el detalle, con ✓ en los pasos hechos y el actual resaltado:
  1. Datos de la boleta;
  2. Corroborar desglose;
  3. Lecturas (con avance «X de N»);
  4. Calcular;
  5. Cerrar período;
  6. Publicar.
- **«Siguiente paso»**, una línea con la acción que corresponde y por qué. Si el paso depende del lector, muestra el avance y no ofrece acción.
- **Un solo botón destacado (verde): el del siguiente paso.** Las demás acciones permitidas (reabrir, recalcular, cerrar lecturas antes de tiempo) quedan en gris.
- Si faltan los datos de la boleta, aparece el botón **«Ingresar datos de la boleta»**.
- En la **lectura inicial**, la barra muestra sus propios pasos: lecturas de partida → cerrar lecturas → lista para la primera boleta.
- **Lista de Boletas sin atajos del ciclo:** se quitan los íconos de cerrar lecturas, calcular y publicar de cada fila, porque no seguían la guía (por ejemplo, ofrecían calcular cuando ya estaba calculado). Cada período en curso muestra **«Continuar»**, que lleva al detalle con la barra de pasos. Se mantienen *Ver*, *Eliminar* (mientras se pueda) y la carga desde Excel de la lectura inicial.
- **App del lector:** cuando las lecturas del período están cerradas, un aviso explica por qué las parcelas aparecen deshabilitadas y qué hacer para corregir una.
- **Liquidaciones siempre al día:** mientras el período no esté cerrado, reabrir lecturas, editar el desglose, reprocesar la boleta o registrar, corregir o sincronizar una lectura **descarta las liquidaciones calculadas**. Así no se puede cerrar ni publicar un período con montos que no corresponden a los datos vigentes: la guía vuelve a pedir «Calcular». La auditoría informa cuántas se descartaron.
- Fuera de lo anterior, no cambia ninguna regla del ciclo, solo la presentación.

## Capabilities

### New Capabilities

_(ninguna)_

### Modified Capabilities

- `consola-administrativa`: guía de pasos del período y botón destacado para el siguiente paso.
- `lecturas-remarcadores`: aviso de lecturas cerradas en la app del lector.
- `ciclo-periodo`: las liquidaciones calculadas se descartan cuando cambian sus insumos.

## Impact

- **Frontend:**
  - `pages/admin/BoletaDetalle.tsx`, con la barra de pasos y las variantes de los botones;
  - `utils/pasosPeriodo.ts`, el cálculo del siguiente paso, en un solo lugar.
- **Docs:** `docs/ayuda-energia.md` (la barra de pasos como hilo de la ayuda del administrador).
