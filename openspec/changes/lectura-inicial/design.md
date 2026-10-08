# Design

## Context

- **Crear una boleta** (`POST /boletas/`):
  - genera una `LecturaParcela` por **cada parcela del condominio**;
  - la lectura anterior es la `lectura_actual` de la última lectura de esa parcela, ordenada por `periodo_mes`, y si no hay ninguna queda en 0;
  - copia los ítems de la última boleta;
  - pone como mes el siguiente al de la última boleta, o el mes en curso si no hay ninguna.
- **Para crear una boleta**, ninguna otra del condominio puede tener `liquidaciones_cerradas` en falso.
- **La app del lector** (con y sin conexión, con foto) trabaja sobre las lecturas del período con lecturas abiertas: `prepararRecorrido()` toma la última boleta sin `lecturas_cerradas`. Cerrar las lecturas exige que todas tengan `fecha_toma`.
- **`PATCH /lecturas/{id}`** hoy acepta `lectura_anterior` sin restricción, aunque la consola solo edita la lectura actual.

## Goals / Non-Goals

**Goals**
- La lectura de partida se toma con exactamente las mismas garantías que una lectura mensual: sin conexión, con foto, sin pisar cambios ajenos y con auditoría.
- La primera boleta obtiene su lectura anterior por el mecanismo de siempre, sin una segunda fuente de verdad.

**Non-Goals**
- Cambio de medidor en parcelas con historial.
- Importación desde planillas.
- Corregir que las lecturas se generen también para parcelas inactivas. Es un comportamiento existente y aquí se mantiene igual en ambos tipos de período.

## Decisions

### 1. La lectura inicial es un período (`boletas_maestras.tipo = 'lectura_inicial'`)

Se agrega `tipo` (`regular` | `lectura_inicial`) a `boletas_maestras`. El período de lectura inicial es una boleta sin datos de la compañía cuyas lecturas guardan, en `lectura_actual`, el valor de partida, con `lectura_anterior` en 0.

**Por qué:** todo lo difícil ya existe sobre «lecturas de un período»:
- recorrido sin conexión;
- foto del medidor;
- sincronización por lotes con detección de conflictos;
- revisión;
- corrección en la consola;
- cierre como certificación;
- auditoría.

Además, la primera boleta toma la lectura anterior de «la última lectura de la parcela», que pasa a ser la inicial **sin tocar ese código**.

**Alternativa descartada:** columnas `lectura_inicial*` en `parcelas`, con su propio endpoint y su modo en la app. Duplicaría la cola sin conexión, la foto, los conflictos y la pantalla de captura, y crearía una segunda fuente para la lectura anterior.

### 2. Dónde se distingue el tipo

- **Backend:** un helper `_exigir_periodo_regular(boleta)` (409 «El período de lectura inicial no se liquida») en:
  - `liquidaciones/calcular`;
  - `validar-items`;
  - `imagen`;
  - `procesar-ocr`;
  - `detalles`;
  - `cerrar-liquidaciones`;
  - el `PATCH` que publica.
- **Regla de período abierto:** pasa a ser `liquidaciones_cerradas = false AND NOT (tipo = 'lectura_inicial' AND lecturas_cerradas)`.
- **`reabrir-lecturas` de una lectura inicial:** además, 409 si existe una boleta del condominio con `periodo_mes` posterior. Su lectura anterior ya se copió y quedaría desfasada.
- **Arrastre de ítems:** sin cambios. La lectura inicial no tiene ítems, así que la primera boleta no copia nada.
- **Mes:** la lectura inicial lleva el mes en que se toma (obligatorio, primer día). La primera boleta, sin `periodo_mes`, toma el mes siguiente, como hoy.
- **Frontend:** `tipo` viaja en la boleta y en el `Recorrido` de IndexedDB (`boleta.tipo`). Un recorrido descargado antes del cambio no lo trae, y se trata como `regular`.

### 3. Sin ceros silenciosos al crear una boleta

Antes de crear, el endpoint calcula qué parcelas no tienen ninguna lectura previa. Si hay alguna y la petición no trae `aceptar_sin_lectura_anterior: true`, responde 409 con:
- `detail`: «N parcelas no tienen lectura anterior»;
- `parcelas`: `[{id, numero_parcela}]`.

El frontend muestra la lista y ofrece dos caminos:
- si el condominio no tiene boletas, «Comenzar con lectura inicial»;
- en cualquier caso, «Crear igual: ingresaré su lectura anterior».

*Alternativa descartada:* un aviso informativo sin bloqueo en el servidor. Un cliente que lo ignore volvería a dejar ceros silenciosos.

### 4. Lectura anterior editable solo sin historial

- **`PATCH /lecturas/{id}` con `lectura_anterior`:**
  - 409 si la parcela tiene alguna lectura en una boleta del condominio con `periodo_mes` menor;
  - 409 si el período es de lectura inicial, donde la anterior es siempre 0.
- **`GET /lecturas?boleta_id=` agrega `lectura_anterior_editable`** con una consulta: las parcelas con lectura en períodos anteriores.
- **La consola** muestra la lectura anterior editable solo en esas filas. El contador no regresivo se sigue validando.

Con esto se cubre la parcela agregada después de la lectura inicial, sin un mecanismo aparte.

### 5. Pantallas

- **`Boletas.tsx`:**
  - sin boletas, muestra el botón «Comenzar con lectura inicial» (elige el mes);
  - la fila del período muestra «Lectura inicial · mes» en lugar de los montos.
- **`BoletaDetalle.tsx`, para `tipo = lectura_inicial`:**
  - sin KPIs de la compañía;
  - solo la pestaña *Lecturas*, con la columna «Lectura inicial» (`lectura_actual`) y sin anterior ni consumo;
  - botonera: Cerrar lecturas y Reabrir lecturas.
- **`Dashboard.tsx`:** si el período más reciente es una lectura inicial, no muestra KPIs de facturación; muestra el avance de la lectura inicial.
- **`LectorDashboard`:** muestra «Lectura inicial · mes» en lugar del período.
- **`CapturarLectura`:** se titula «Lectura inicial», oculta la lectura anterior y el consumo, y mantiene la foto.

### 6. Carga masiva desde Excel (solo lectura inicial)

**Plantilla.** `GET /boletas/{id}/lecturas-iniciales/plantilla` genera un `.xlsx` con `openpyxl`:
- columnas *Parcela*, *Propietario* y *Lectura inicial*;
- una fila por lectura del período, en orden natural;
- la lectura prellenada si ya se tomó.

Partir de la plantilla evita el problema más común: nombres de parcela que no calzan.

**Importación.** `POST /boletas/{id}/lecturas-iniciales/importar?aplicar=false|true` (multipart):
- **Lectura del archivo:** ≤ 2 MB, firma ZIP (`PK`), `load_workbook(read_only, data_only)` y primera hoja. Se busca la fila de encabezados que tenga «Parcela» o «Unidad» y «Lectura inicial» o «Lectura», con encabezados normalizados (minúsculas, sin tildes), igual que `cargar_residentes`.
- **Cruce de parcelas:** la parcela se cruza con `numero_parcela`, normalizado (minúsculas, sin espacios, sin el prefijo «parcela», y `23.0` → `23`).
- **Valor:** si la celda es numérica se usa tal cual. Si es texto, se aceptan formatos chilenos: «15.230» es miles y «15.230,5» es decimal. La vista previa muestra los valores interpretados, para que el administrador los revise antes de aplicar.
- **Respuesta:** `{a_aplicar: [{parcela_id, numero_parcela, valor, valor_actual, reemplaza}], sin_cambio, vacias, errores: [{fila, mensaje}], aplicadas}`.
- **Con `aplicar=true`:**
  - si hay errores, 422 con el mismo cuerpo;
  - sin errores, actualiza `lectura_actual`, `kwh_consumidos`, `fecha_toma` (el momento de la importación) y `lector_id` (el administrador), en una transacción, con auditoría `IMPORTAR_LECTURAS_INICIALES` (`{boleta_id, aplicadas, cambios: [{parcela_id, antes, despues}]}`).
- **Si el período no es una lectura inicial o tiene las lecturas cerradas:** 409.

**Todo o nada.** Aplicar una planilla a medias deja al administrador sin saber qué entró. Por eso, con errores no se aplica nada y se corrige la planilla.

**Convivencia con la app del lector.** La importación cambia la `fecha_toma`. Si un lector tenía esa parcela pendiente en su celular, su sincronización queda en *conflicto* (la base ya no coincide) y no pisa lo importado: es la detección de conflictos que ya existe.

*Alternativa descartada:* CSV. Excel es lo que usa la administración, y `openpyxl` ya está en el backend. Un CSV exige elegir separador y codificación, una fuente de errores para usuarios no técnicos.

## Risks / Trade-offs

- **[Las lecturas iniciales se toman en un día distinto al que la compañía lee el medidor general]** Habrá un diferencial mayor en la primera boleta. Mitigación: la guía del lector recomienda tomarlas el mismo día. El Motor ya reparte el diferencial como cuota fija.
- **[Un administrador crea la primera boleta aceptando lecturas anteriores en 0]** Es una decisión explícita y queda registrada. Puede corregir después la lectura anterior de cada parcela sin historial en el período abierto.
- **[BREAKING en `PATCH /lecturas` con `lectura_anterior`]** Ninguna pantalla actual lo envía, solo `lectura_actual`. Los tests que lo usen se ajustan.
- **[Texto ambiguo en la planilla, como «120.500»]** Se interpreta como miles (120500). Mitigación: la vista previa muestra cada valor antes de aplicar, y la plantilla trae celdas numéricas.
- **[Producción ya tiene boletas operadas]** La lectura inicial solo se abre en condominios sin boletas. En uno con historial, las parcelas sin lectura previa se resuelven con la lectura anterior editable.

## Migration Plan

1. Migración: `tipo VARCHAR NOT NULL DEFAULT 'regular'` con `CHECK (tipo IN ('regular','lectura_inicial'))`. Las boletas existentes quedan como `regular`. La reversa elimina la columna, y no puede haber lecturas iniciales al revertir: la migración de bajada falla si existe alguna.
2. Despliegue normal. No requiere cambios de infraestructura.
