# Tasks

## 1. Base de datos

- [x] 1.1 Migración Alembic:
  - `boletas_maestras.tipo` (`VARCHAR NOT NULL DEFAULT 'regular'`, `CHECK` `regular|lectura_inicial`);
  - reversa que falla si existe alguna lectura inicial;
  - modelo `BoletaMaestra` y `schema.dbml` actualizados.

  Verificar con `alembic upgrade head`, `alembic downgrade -1` y de nuevo `upgrade`.

## 2. Backend

- [x] 2.1 `POST /boletas/lectura-inicial` (`AdminRequired`, `periodo_mes` obligatorio):
  - 409 si el condominio tiene boletas;
  - una lectura en blanco por parcela con anterior en 0;
  - auditoría `CREATE_LECTURA_INICIAL`;
  - `tipo` en `BoletaMaestraResponse`.

  Verificar con pytest: apertura, condominio con boletas y tenant.
- [x] 2.2 Helper `_exigir_periodo_regular` en:
  - calcular;
  - `validar-items`;
  - imagen;
  - `procesar-ocr`;
  - `detalles`;
  - `cerrar-liquidaciones`;
  - el `PATCH` de publicación.

  `cerrar-lecturas` sin cambios. Verificar con pytest que cada uno responde 409 sobre una lectura inicial.
- [x] 2.3 Regla de período abierto (la lectura inicial con lecturas cerradas no bloquea) y `reabrir-lecturas` de la lectura inicial (409 si existe una boleta posterior). Verificar con pytest:
  - la lectura inicial abierta bloquea la creación;
  - cerrada, la permite;
  - la primera boleta hereda la lectura inicial como `lectura_anterior`, toma el mes siguiente y no copia ítems;
  - la reapertura se bloquea con un período posterior.
- [x] 2.4 `aceptar_sin_lectura_anterior` en `POST /boletas/`: 409 con `parcelas` sin lectura previa si no se acepta. Ajustar los tests existentes que crean boletas por la API sin historial. Verificar con pytest los dos escenarios y la suite completa en verde.
- [x] 2.5 `PATCH /lecturas/{id}`: rechazar `lectura_anterior` con historial o en una lectura inicial (409). `GET /lecturas` informa `lectura_anterior_editable`. Verificar con pytest:
  - la parcela sin historial se edita y recalcula el consumo;
  - la parcela con historial responde 409;
  - el flag es correcto.

- [x] 2.6 Plantilla e importación de lecturas iniciales:
  - `GET /boletas/{id}/lecturas-iniciales/plantilla` (xlsx);
  - `POST /boletas/{id}/lecturas-iniciales/importar?aplicar=` con vista previa, todo o nada, auditoría `IMPORTAR_LECTURAS_INICIALES` y 409/422 según la spec.

  Verificar con pytest:
  - la plantilla se puede leer de vuelta;
  - vista previa sin cambios;
  - errores (parcela desconocida, repetida, negativa, texto);
  - celdas vacías;
  - formatos chilenos;
  - aplicar;
  - período regular o cerrado;
  - archivo inválido.

## 3. Frontend

- [x] 3.1 `types/index.ts` (`tipo`, `lectura_anterior_editable`), `api/boletas.ts` (`crearLecturaInicial`, `aceptar_sin_lectura_anterior`) y `Recorrido.boleta.tipo` en `offline/lecturas.ts` (por defecto `regular`). Verificar con `npm run build`.
- [ ] 3.2 `Boletas.tsx`:
  - botón «Comenzar con lectura inicial» cuando no hay boletas;
  - fila del período «Lectura inicial · mes»;
  - ante el 409 de parcelas sin lectura previa, modal con la lista y las opciones «Comenzar con lectura inicial» (si no hay boletas) o «Crear igual».

  Verificar en el navegador con la base de desarrollo vacía de boletas.
- [ ] 3.3 `BoletaDetalle.tsx`:
  - vista de la lectura inicial (sin KPIs, solo *Lecturas* con la columna «Lectura inicial», botonera Cerrar y Reabrir lecturas);
  - en períodos regulares, lectura anterior editable solo donde `lectura_anterior_editable`.

  Verificar en el navegador.
- [ ] 3.5 `BoletaDetalle.tsx` (lectura inicial): botones **Descargar plantilla** y **Cargar desde Excel**. El modal muestra la vista previa (a aplicar, reemplazos, vacías, errores por fila) y **Aplicar N lecturas**, deshabilitado si hay errores. Verificar en el navegador con una planilla descargada y editada.
- [ ] 3.4 `Dashboard.tsx` no muestra KPIs de facturación para una lectura inicial. `LectorDashboard` y `CapturarLectura` muestran «Lectura inicial», sin anterior ni consumo, con foto. Verificar en el navegador, también con DevTools en *Offline*.

## 4. Documentación

- [x] 4.1 Documentación:
  - `docs/flujo-periodo.md`: paso 0 «Lectura inicial», sus candados, la carga desde Excel y `aceptar_sin_lectura_anterior`;
  - `docs/lecturas-sin-conexion.md`: cómo tomar la lectura inicial y por qué el mismo día que la compañía;
  - `CLAUDE.md`: el tipo de período y sus candados.

  Verificar con `openspec validate lectura-inicial --strict`.

## 5. Integración

- [ ] 5.1 Recorrido completo en desarrollo, desde un condominio sin boletas:
  1. lectura inicial con el lector, con una parte sin conexión y con foto;
  2. cierre;
  3. primera boleta con OCR, que hereda la lectura inicial;
  4. lecturas del mes;
  5. cálculo, cierre y publicación;
  6. vista del comunero.

  Verificar que los consumos de la liquidación son la diferencia entre la lectura del mes y la inicial.
