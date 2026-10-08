# Proposal

## Why

Al crear una boleta, la lectura anterior de cada parcela se toma del período anterior y, si no lo hay, queda en **0**. Hoy no existe ninguna forma de cargar la lectura de partida de los medidores. Por eso el primer período de un condominio, en desarrollo y también en producción, que se cargó sin datos operativos, cobraría a cada comunero el número completo de su medidor como si fuera el consumo de un mes. Sin una lectura inicial confiable, la primera liquidación real sale absurda.

## What Changes

- **Período de lectura inicial.** Un condominio sin boletas puede abrir un período especial, **«Lectura inicial»**, cuyo único fin es registrar la lectura de partida de cada medidor:
  - no tiene boleta de la compañía, ni ítems, ni OCR, ni liquidaciones;
  - nunca se publica a los comuneros;
  - se cierra con **Cerrar lecturas**, igual que un período normal.
- **El lector lo toma en terreno con la app que ya existe**: sin conexión, con foto del medidor y con sincronización y detección de conflictos. Conviene hacerlo el día en que la compañía lee el medidor general, porque desde ahí se cuenta el primer período. La pantalla de captura muestra **«Lectura inicial»**, sin lectura anterior ni consumo.
- **La administración puede ingresar o corregir los valores** desde la pestaña *Lecturas* de ese período, con auditoría, por ejemplo con las lecturas del proceso manual anterior a la plataforma.
- **Carga masiva desde Excel.** En la lectura inicial, la administración descarga una **plantilla** con las parcelas del período (y los valores ya tomados), la completa y la sube. El sistema muestra una **vista previa**:
  - lecturas a aplicar;
  - cuáles reemplazan una ya tomada;
  - errores por fila: parcela desconocida o repetida, valor inválido o negativo.

  Solo aplica si la planilla no tiene errores, y lo deja en la auditoría.
- **La primera boleta parte de la lectura inicial.** Toma esos valores como lectura anterior por el mecanismo de siempre (el último período), y su mes se encadena al siguiente.
- **Sin ceros silenciosos.** Crear una boleta cuando alguna parcela no tiene lectura previa responde `409` con la lista de parcelas afectadas. Solo se crea si el administrador lo confirma explícitamente (`aceptar_sin_lectura_anterior`).
- **Lectura anterior editable solo donde no hay historial.** La lectura anterior de una parcela sin período previo (por ejemplo, una parcela agregada después) se puede ingresar en el período abierto. La de una parcela con historial viene del período anterior y **no** se edita. **BREAKING:** `PATCH /lecturas/{id}` deja de aceptar cambios de `lectura_anterior` cuando la parcela tiene un período previo (409).
- **Candados propios del período de lectura inicial:**
  - no se puede calcular, corroborar, cargar imagen ni OCR, cerrar liquidaciones ni publicar (409);
  - una vez cerradas sus lecturas, cuenta como cerrado y permite crear la primera boleta;
  - no se puede reabrir si ya existe un período posterior, que tomó sus lecturas como base.

Fuera de alcance:
- cambio de medidor en una parcela con historial;
- importación desde Excel en períodos regulares. Por decisión del producto, la carga desde Excel es solo para el **onboarding** del condominio (la lectura inicial, una sola vez). Las lecturas mensuales se toman siempre con la app del lector, con foto y trazabilidad.

## Capabilities

### New Capabilities

_(ninguna)_

### Modified Capabilities

- `boletas-maestras`:
  - nuevo período de tipo lectura inicial;
  - la generación de lecturas ya no deja ceros silenciosos para parcelas sin historial;
  - el período de lectura inicial cerrado no bloquea la creación de la primera boleta.
- `ciclo-periodo`: candados del período de lectura inicial y reapertura bloqueada si existe un período posterior.
- `lecturas-remarcadores`:
  - la lectura anterior solo se corrige en parcelas sin historial;
  - la captura del lector distingue la lectura inicial.

## Impact

- **Base de datos:** migración que agrega `boletas_maestras.tipo` (`regular` | `lectura_inicial`, por defecto `regular`, con `CHECK`). `schema.dbml`.
- **Backend:**
  - `endpoints/boletas.py`:
    - `POST /boletas/lectura-inicial`;
    - `aceptar_sin_lectura_anterior` en la creación;
    - guarda de período regular en calcular, `validar-items`, imagen, OCR, `cerrar-liquidaciones` y publicación;
    - regla de período abierto;
    - reapertura.
  - `endpoints/liquidaciones.py` (calcular).
  - `endpoints/lecturas.py`: regla de `lectura_anterior` y `lectura_anterior_editable` en el listado.
  - Plantilla e importación de lecturas iniciales (`GET .../lecturas-iniciales/plantilla`, `POST .../lecturas-iniciales/importar`) con `openpyxl`, que ya es dependencia del backend.
  - Auditoría `IMPORTAR_LECTURAS_INICIALES`.
  - Schemas: `tipo` en la respuesta de la boleta.
  - Auditoría `CREATE_LECTURA_INICIAL`.
- **Frontend:**
  - `Boletas.tsx`: «Comenzar con lectura inicial» cuando no hay boletas, etiqueta del período y confirmación de las parcelas sin lectura previa;
  - `BoletaDetalle.tsx`: vista reducida para el período de lectura inicial, con **Descargar plantilla** y **Cargar desde Excel** (vista previa y aplicar), y lectura anterior editable donde corresponde;
  - `Dashboard.tsx`: no lo trata como período facturado;
  - `offline/lecturas.ts`, `LectorDashboard.tsx` y `CapturarLectura.tsx`: tipo del período en el recorrido y textos de lectura inicial;
  - `types/index.ts`.
- **Portal del comunero:** sin cambios. El período de lectura inicial nunca se publica.
- **Tests:** los que crean boletas por la API y no tienen historial deben enviar la confirmación.
- **Docs:** `docs/flujo-periodo.md` (paso 0: lectura inicial), `docs/lecturas-sin-conexion.md`, `CLAUDE.md`. El centro de capacitación tiene Energía como «próximamente»; cuando se complete, debe incluir este paso.
