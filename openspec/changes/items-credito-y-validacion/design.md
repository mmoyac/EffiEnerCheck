## Context

El desglose de la boleta eléctrica es la base sobre la que se reparten los gastos comunes del condominio. Cada mes la compañía emite líneas de cargo que varían, y el administrador es quien decide cuáles se reparten entre los parceleros y cuáles no. Hoy ese juicio no está representado en el sistema.

Tres hechos del código actual definen el problema:

1. **El OCR descarta lo que no reconoce.** El emparejamiento difuso compara la descripción extraída contra los ítems arrastrados del mes anterior con umbral 0,6; si no encuentra coincidencia, ejecuta `continue`. La línea se pierde sin dejar rastro.
2. **El prompt no contempla el signo.** Pide `"monto_neto_clp": <entero>` sin mencionar descuentos ni créditos, por lo que el modelo devuelve el valor absoluto de una nota de crédito.
3. **El cálculo cuadra igual con el desglose mal armado.** Como `valor_kwh` se despeja desde `monto_total_emision`, cualquier ítem faltante o mal clasificado no rompe el cuadre: la plata se absorbe en el componente de energía y se reparte proporcional al consumo. El error es silencioso por construcción.

Existe además un vestigio revelador: `estado` admite `borrador`, `validada` y `publicada` en el modelo, en los schemas y en los tipos del frontend, pero **ningún endpoint asigna `validada`**. El paso de corroboración fue previsto en el diseño original y quedó sin implementar.

Restricción de fondo: el motor no puede dejar de cuadrar. La identidad `Σ total_pagar = monto_total_emision` es el argumento del sistema frente a la comunidad y ninguna decisión de este diseño puede debilitarla.

## Goals / Non-Goals

**Goals:**

- Que ninguna línea de la boleta se pierda en silencio, incluidas las que restan.
- Que el juicio mensual del administrador sobre qué entra al reparto sea un acto explícito, obligatorio y auditable.
- Que el juicio no pueda quedar desacoplado de las cifras que lo sustentan.
- Que un crédito de la compañía se reparta según su naturaleza y no diluido en el consumo.
- Cero cambios en las fórmulas del motor y cero riesgo para el cuadre.

**Non-Goals:**

- Modificar la aritmética de distribución. Se verificó que el motor ya trata correctamente los montos negativos.
- Dar uso a `monto_saldo_anterior`, que permanece informativo.
- Resolver el doble conteo latente del ítem "Diferencial" cuando se clasifica como `fijo` o `variable`. Es un defecto distinto, identificado durante este análisis, que merece su propio cambio.
- Migrar datos históricos. Las boletas ya publicadas o con período cerrado no se tocan.

## Decisions

### Sobrecargar `tipo_calculo` en vez de agregar un campo de inclusión

Se agrega el valor `pendiente` al conjunto existente (`fijo`, `variable`, `informativo`) y se establece `informativo` como el mecanismo de exclusión deliberada.

*Alternativa descartada:* un booleano `incluido` separado de `tipo_calculo`. Sería semánticamente más limpio —separa "cómo se reparte" de "si se reparte"— pero exige migración Alembic, duplica estados representables (`informativo` + `incluido=true` no significa nada) y obliga a revisar todo consumidor del campo. `informativo` ya significa exactamente "no entra al reparto" y el motor ya lo respeta. Sobrecargar es la opción de menor riesgo.

*Consecuencia:* `tipo_calculo` y `estado` son columnas `String` sin restricción en base de datos, por lo que **este cambio no requiere migración**. La validación de valores admitidos vive en el `Literal` de Pydantic.

### Reutilizar el estado `validada` en lugar de un candado booleano nuevo

La corroboración se representa con la transición `borrador → validada`, no con un cuarto booleano junto a `lecturas_cerradas`, `liquidaciones_cerradas` y `boleta_visible_usuarios`.

*Razón:* el estado ya existe en las tres capas y fue previsto para esto. Agregar un booleano crearía dos representaciones del mismo hecho y dejaría `validada` como código muerto indefinidamente.

*Trade-off aceptado:* `estado` pasa a tener dos responsabilidades —el avance del ciclo y la visibilidad pública, dado que `publicada` se asigna al activar `boleta_visible_usuarios`—. Es acoplamiento preexistente que este cambio no empeora.

### La corroboración es un endpoint propio, no un `PATCH` de estado

Se expone `POST /boletas/{id}/validar-items` en lugar de permitir `PATCH {estado: "validada"}`.

*Razón:* la transición tiene precondiciones (sin ítems `pendiente`, período abierto, boleta en `borrador`) y un efecto secundario obligatorio (la instantánea de auditoría). Un `PATCH` genérico invita a saltarse ambas cosas. Además queda consistente con las cuatro transiciones de ciclo que ya son `POST` con verbo explícito.

### La reversión es automática, no una acción del administrador

Reprocesar el OCR o editar los detalles devuelve la boleta a `borrador` sin preguntar.

*Razón:* la alternativa —advertir y dejar que el administrador decida— permite que el estado `validada` sobreviva a un cambio de las cifras que se validaron, que es exactamente el fallo silencioso que este cambio busca eliminar. La fricción de volver a corroborar es baja; el costo de un juicio desactualizado es alto.

*Se conservan las liquidaciones existentes* al revertir, para no destruir trabajo. El cierre del período ya exige liquidaciones calculadas, y el recálculo exige `validada`, de modo que el flujo empuja naturalmente al recálculo sin necesidad de borrar nada.

### La instantánea de auditoría se guarda completa, no como diferencia

El registro `VALIDAR_ITEMS` guarda el desglose entero en `detalles`, no solo lo que cambió.

*Razón:* el propósito no es rastrear ediciones sino **poder demostrar meses después** qué decidió el administrador y sobre qué cifras. Una diferencia obliga a reconstruir el estado recorriendo la historia; una instantánea responde sola. El campo `detalles` es `JSONB` y el volumen es despreciable —una boleta tiene del orden de quince ítems y hay una corroboración por período.

### Los ítems arrastrados llegan clasificados, no en `pendiente`

El arrastre mensual conserva el `tipo_calculo` del período anterior. Solo los ítems que el OCR crea por primera vez nacen `pendiente`.

*Alternativa descartada:* forzar todo a `pendiente` cada mes para obligar a reclasificar. Se descartó porque convierte la corroboración en reingreso de quince ítems, invita a clasificar mecánicamente para salir del paso y degrada el juicio que se busca proteger.

*Cómo se preserva igualmente el juicio mensual:* la boleta nace en `borrador` aunque ningún ítem esté `pendiente`, de modo que la corroboración es obligatoria todos los meses. La clasificación heredada es una propuesta que el administrador confirma o corrige, no una decisión heredada automáticamente.

### El prompt del OCR clasifica el signo, no la naturaleza del ítem

Se instruye al modelo para devolver negativos en descuentos, notas de crédito, abonos, devoluciones y bonificaciones. **No** se le pide que asigne `tipo_calculo`.

*Razón:* el signo es un hecho legible en el documento; la clasificación es un juicio que corresponde al administrador. Pedirle al modelo que decida qué se reparte y cómo trasladaría a la IA una responsabilidad que este cambio busca justamente formalizar en una persona.

## Risks / Trade-offs

**El modelo puede no respetar el signo de forma consistente** → La instrucción es explícita y enumera los conceptos afectados, pero un crédito mal extraído como positivo seguirá siendo posible. Mitigación real: la corroboración obligatoria pone un humano frente al desglose antes de cada cálculo, que es la última línea de defensa. La consola destaca los negativos para que un cargo que debería ser abono resalte por omisión.

**Los ítems nuevos creados por el OCR podrían proliferar** → Si el modelo varía la redacción de una misma línea entre meses y no supera el umbral de 0,6, creará un duplicado en `pendiente` en lugar de actualizar el existente. Mitigación: el duplicado es visible y bloquea la corroboración hasta ser resuelto, en vez de corromper el cálculo en silencio. El administrador puede eliminarlo desde el modal de detalles. Conviene vigilar la frecuencia con que aparecen para calibrar el umbral en un cambio posterior.

**El paso obligatorio agrega fricción al cierre mensual** → Es fricción deliberada y acotada: una acción por período, no por ítem. Se mitiga permitiendo corroborar en un solo acto cuando no hay pendientes.

**Boletas abiertas al momento del despliegue quedan en `borrador`** → Cualquier período en curso con liquidaciones ya calculadas requerirá una corroboración antes del próximo recálculo. No rompe nada —las liquidaciones existentes se conservan y el período puede cerrarse— pero conviene avisarlo. Ver plan de despliegue.

**`informativo` pasa a tener dos lecturas** → "dato de referencia de la compañía" y "el administrador lo excluyó a propósito". Ambas comparten el efecto —no entra al reparto— pero se distinguen solo por la descripción del ítem. Se acepta a cambio de evitar la migración; si la distinción llega a importar, se separa en un cambio posterior.

## Migration Plan

Sin migración de base de datos: `tipo_calculo` y `estado` son columnas de texto libre y los valores nuevos no alteran el esquema.

**Despliegue:**

1. Backend primero. Mientras el frontend viejo siga desplegado, `calcular` empezará a rechazar boletas en `borrador` con `409`; el mensaje del error indica qué hacer.
2. Frontend a continuación, que incorpora la acción de corroborar y el manejo del nuevo `409`.
3. Reconstruir el contenedor con `docker-compose up --build -d backend`. Un `restart` no basta.

**Datos existentes:** ninguna boleta histórica queda en un estado inválido. Las publicadas y las de período cerrado conservan su comportamiento. Las abiertas quedan en `borrador` y requieren una corroboración antes del próximo recálculo, que es el comportamiento buscado.

**Rollback:** revertir el código. No hay estructura de datos que deshacer. Los ítems que hayan quedado en `tipo_calculo = "pendiente"` serían el único residuo; con el código anterior el motor los ignoraría al sumar por `fijo` y `variable`, de modo que se comportarían como `informativo` y el cuadre se mantendría. El único registro de auditoría nuevo, `VALIDAR_ITEMS`, es inocuo para el código viejo.

## Open Questions

- ¿El umbral de similitud de 0,6 sigue siendo adecuado ahora que un fallo de emparejamiento crea un ítem en vez de descartar la línea? El costo del falso negativo cambió: antes se perdía plata en silencio, ahora aparece un duplicado visible. Puede convenir subirlo para reducir falsos positivos, pero conviene decidirlo con datos reales de un par de períodos.
- ¿Debe la consola ofrecer al administrador fusionar un ítem `pendiente` con uno existente, en lugar de obligarlo a corregir la descripción y reprocesar? Fuera de alcance aquí; depende de cuánto ocurra en la práctica.
- El doble conteo del ítem "Diferencial" clasificado como `fijo` o `variable` queda pendiente de un cambio propio.
