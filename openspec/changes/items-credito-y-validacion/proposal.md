## Why

El desglose de la boleta puede quedar mal repartido sin que nadie lo note. El OCR descarta en silencio toda línea que no reconozca contra los ítems del mes anterior, y su prompt no contempla los montos negativos (descuentos, notas de crédito, abonos), por lo que devuelve su valor absoluto. Como el motor despeja `valor_kwh` desde `monto_total_emision`, el total liquidado **cuadra igual** aunque falten ítems o tengan el signo invertido: la plata se diluye en el componente de energía y se cobra proporcional al consumo en vez de repartirse según corresponde.

En una boleta de energía eléctrica el administrador es, cada mes, **el juez de qué entra y qué no entra** al cálculo de los gastos comunes de los parceleros. Los cargos de la compañía varían de período en período y no todos deben repartirse. Hoy nada obliga a ejercer ese juicio: el estado `validada` está declarado en el modelo, en los schemas y en los tipos del frontend, pero ningún endpoint lo asigna. El paso de corroboración quedó diseñado y sin implementar, y el cálculo se puede disparar sin que nadie haya mirado el desglose.

## What Changes

- El prompt del OCR reconoce e informa montos negativos para descuentos, notas de crédito, abonos y devoluciones, preservando el signo.
- El OCR deja de descartar líneas no reconocidas: las crea como ítems **pendientes de clasificar** en lugar de perderlas.
- Se introduce el `tipo_calculo` `pendiente` para los ítems que el OCR creó y el administrador aún no clasificó. Un ítem `pendiente` no participa del reparto.
- **BREAKING**: `POST /liquidaciones/calcular/{boleta_id}` exige que la boleta esté en estado `validada`. Las boletas en `borrador` son rechazadas con `409`.
- Se implementa la transición a `validada` mediante un endpoint nuevo de corroboración del desglose, restringido a roles administrativos. La transición exige que ningún ítem quede en `pendiente`, y constituye el acto formal por el cual el administrador declara qué entra y qué no entra al reparto del período.
- La corroboración se audita con una **instantánea del desglose completo** —descripción, monto y `tipo_calculo` de cada ítem— de modo que quede registro verificable de qué decidió el administrador, cuándo y sobre qué cifras.
- El `tipo_calculo` `informativo` queda establecido como el mecanismo explícito de exclusión: un ítem informativo es visible en el desglose pero **no entra** al reparto.
- Los ítems arrastrados del mes anterior llegan con su clasificación previa como propuesta, no como decisión tomada: el administrador la corrobora o la cambia cada período.
- Reprocesar el OCR o editar los detalles de una boleta ya validada la devuelve a `borrador`, forzando una nueva corroboración sobre las cifras nuevas.
- La consola distingue visualmente cargos de abonos, deja legible por ítem si entra o no al reparto, destaca los pendientes de clasificar y ofrece la acción de corroborar el desglose.
- Se documenta la semántica de los montos negativos en el motor. **No se modifican las fórmulas**: el motor ya reparte correctamente los negativos según su `tipo_calculo` y `valor_kwh` no se ve afectado por ellos.

Fuera de alcance: `monto_saldo_anterior` permanece informativo y sin efecto en el cálculo.

## Capabilities

### New Capabilities

Ninguna. El cambio modifica capacidades existentes.

### Modified Capabilities

- `ocr-boletas`: el prompt preserva el signo de los montos negativos; las líneas sin coincidencia se crean como ítems pendientes en lugar de descartarse.
- `boletas-maestras`: nuevo `tipo_calculo` `pendiente`; el arrastre mensual deja de ser un catálogo cerrado; editar detalles revierte la validación.
- `ciclo-periodo`: el estado `validada` se incorpora a la máquina de estados como paso previo obligatorio al cálculo, con su transición y su reverso.
- `motor-liquidaciones`: el cálculo exige estado `validada`; se documenta el tratamiento de montos negativos y la exclusión del reparto de los ítems `pendiente` e `informativo`.
- `consola-administrativa`: distinción visual cargo/abono, legibilidad de qué entra al reparto, aviso de ítems pendientes y acción de corroborar el desglose.
- `auditoria`: nueva acción `VALIDAR_ITEMS` con instantánea del desglose corroborado.

## Impact

**Backend**

- `app/schemas/boleta.py` — `TipoCalculo` incorpora `pendiente`.
- `app/services/ocr.py` — prompt con signo negativo y clasificación de créditos.
- `app/api/v1/endpoints/boletas.py` — el emparejamiento difuso crea los ítems sin coincidencia como `pendiente`; endpoint nuevo de confirmación; reversión a `borrador` al reprocesar OCR o editar detalles.
- `app/api/v1/endpoints/liquidaciones.py` — guarda de estado `validada` en `calcular`.
- `app/services/enercheck.py` — los ítems `pendiente` se excluyen de las sumas; docstring con la semántica de negativos.

**Frontend**

- `pages/admin/ModalEditDetalles.tsx` — selector con la opción `pendiente`, distinción visual de montos negativos.
- `pages/admin/BoletaDetalle.tsx` — aviso de ítems pendientes y botón de confirmar desglose.
- `types/index.ts` — `tipo_calculo` incorpora `pendiente`.

**Base de datos**

Sin migración. `tipo_calculo` y `estado` ya son columnas de texto libre; los valores nuevos no alteran el esquema.

**Compatibilidad**

Las boletas históricas en `publicada` o con el período cerrado no se ven afectadas. Las boletas abiertas en `borrador` con liquidaciones ya calculadas requerirán una confirmación de ítems antes del próximo recálculo.
