# Módulo Energía: base para la ayuda y la capacitación

Este documento es la **fuente para escribir la ayuda** del módulo Energía: los recorridos del centro de capacitación (`frontend/public/capacitacion/recorridos/energia.js`, hoy marcado «próximamente» en `recorridos/plataforma.js`) y cualquier material para administración, lector y comunero.

Describe el comportamiento real del portal al 08-10-2026, validado en desarrollo con un recorrido completo. Las reglas formales están en la spec [`proceso-energia`](../openspec/changes/proceso-energia/specs/proceso-energia/spec.md) y en las specs de detalle que esa spec enlaza. El detalle técnico (endpoints y códigos) está en [flujo-periodo.md](flujo-periodo.md).

> **Regla del centro de capacitación:** datos ficticios, sin llamadas a `/api/` y sin nombres ni teléfonos reales (spec `capacitacion-plataforma`). Los ejemplos de este documento ya son ficticios.

---

## 1. El proceso en una página

```
INCORPORACIÓN (una sola vez)          CADA MES
───────────────────────────           ───────────────────────────────────────────────────────────
Admin: abre la Lectura inicial   ──►  Admin: Generar período (boleta del mes)
Lector o Excel: lectura de             Admin: datos de la boleta (IA o a mano) + conceptos
  partida de cada medidor              Admin: Corroborar desglose
Admin: Cerrar lecturas                 Lector: toma las lecturas en terreno (app, sin señal, foto)
(Opcional) Admin: Orden del            Lector/Admin: Cerrar lecturas
  recorrido del lector                 Admin: Calcular liquidaciones → revisar
                                       Admin: Cerrar período → Publicar
                                       Comunero: ve su liquidación y la foto de su medidor
```

**Roles:**

| Rol | Qué hace en Energía | Dispositivo típico |
|---|---|---|
| Administración (`admin_condominio`) | Lectura inicial, boleta, conceptos, corroborar, calcular, cerrar, publicar, orden del recorrido | Computador |
| Lector | Toma las lecturas en terreno con la app (también sin señal), con foto del medidor | Celular (app instalada) |
| Comunero | Consulta su liquidación publicada | Celular o computador |

---

## 2. Glosario para la ayuda

| Término | Explicación para usuarios |
|---|---|
| **Período** | Un mes de la boleta eléctrica del condominio. En pantalla: «Boleta Oct. 2026». |
| **Lectura inicial** | Período especial, **solo en la incorporación**, para anotar el número de partida de cada medidor. No tiene boleta ni cobro y nunca se publica. En pantalla: «Lectura inicial · Sept. 2026». |
| **Lectura anterior / actual** | El número del medidor el mes pasado y el de hoy. La anterior la pone el sistema; la actual la toma el lector. |
| **kWh consumidos** | Actual − anterior. La app los calcula al escribir la lectura actual. |
| **kWh compañía** | El consumo total que la compañía le cobra al condominio (el medidor general). |
| **Diferencial** | Los kWh que la compañía cobró y que ningún medidor de parcela registró (pérdidas, áreas comunes). Se reparte en partes iguales, dentro de la cuota fija. |
| **Concepto / ítem** | Cada línea de la boleta de la compañía: cargo fijo, transporte, intereses… Son **montos del condominio completo**, no por parcela. |
| **Fijo / variable / informativo** | Fijo: se divide en partes iguales. Variable: según el consumo de cada parcela. Informativo: se muestra, pero no se cobra aparte (su monto queda dentro del total). |
| **Corroborar desglose** | El administrador confirma que los conceptos y su tipo están bien. Sin esto no se puede calcular. |
| **Cerrar lecturas** | Certifica que se tomaron todas. Exige el 100 % de las parcelas. |
| **Cerrar período** | Fija las liquidaciones. Todavía se puede reabrir. |
| **Publicar** | Hace visible el período a los comuneros. **No se puede deshacer.** |
| **Preparar recorrido** | Descarga al celular las parcelas y lecturas para trabajar sin señal. **No define el orden.** |
| **Orden del recorrido** | El orden en que el lector camina las parcelas (por ejemplo 6, 5, 4, 3, 13 A…). Lo define la administración. Si no existe, la app usa el orden numérico. |

---

## 3. Administración: incorporación del condominio (una sola vez)

### 3.1 Abrir la lectura inicial

1. **Boletas**. Si el condominio no tiene boletas, aparece un aviso azul y el botón **«Comenzar con lectura inicial»**.
2. Elegir el **mes en que se toman las lecturas**. La primera boleta quedará en el **mes siguiente**.
   - *Para la ayuda:* «Si tu primera boleta es la de octubre, abre la lectura inicial en **septiembre**».
   - Lo ideal es tomar las lecturas **el mismo día en que la compañía lee el medidor general**: desde ahí corre el primer período.
3. Queda la fila **«Lectura inicial · Sept. 2026»** con el estado **«En toma»**.

*Si se eligió un mes equivocado:* mientras esté abierta, se elimina con el basurero de la fila y se abre de nuevo.

### 3.2 Registrar las lecturas de partida (dos formas)

**A. Con la app del lector**, en terreno: igual que una toma mensual (sección 5). La pantalla dice «Lectura inicial» y pide solo el valor del medidor, **sin lectura anterior ni consumo**.

**B. Desde Excel**, si ya existen las lecturas del proceso manual anterior. **Solo existe en la incorporación.**
1. En la fila de la lectura inicial, ícono de **planilla verde**, o en el detalle → pestaña *Lecturas* → **Descargar plantilla**. Columnas: *Parcela*, *Propietario*, *Lectura inicial*; una fila por parcela, en orden.
2. Completar la columna *Lectura inicial*. Las celdas vacías se omiten. Se aceptan números escritos a la chilena (`15.230` o `8.800,5`).
3. **Cargar desde Excel** → elegir el archivo, **cerrado en Excel**. Aparece la **vista previa**:
   - *A aplicar*: cuántas lecturas se cargarán;
   - *Reemplazan una tomada* (en amarillo): parcelas que ya tenían lectura;
   - *Sin cambio / vacías*;
   - *Errores*, con el número de fila: parcela que no existe, parcela repetida, valor negativo o que no es número.
4. **Aplicar N lecturas**. Queda bloqueado mientras haya errores: **se aplica todo o nada**.

### 3.3 Cerrar la lectura inicial

- **Continuar** (en la fila) → **Cerrar lecturas**, el botón verde del detalle. Exige todas las parcelas con lectura (las cargadas por Excel cuentan como tomadas).
- Cerrada, queda lista para generar la primera boleta.
- Se puede **reabrir** para corregir **solo mientras no exista la primera boleta**. Después, ya no.

### 3.4 (Opcional) Orden del recorrido del lector

1. **Parcelas → «Orden del recorrido»**.
2. Ordenar las parcelas como se caminan: **arrastrar** en el computador o **flechas ↑ ↓** en el celular.
3. **Guardar recorrido**. **Quitar recorrido** vuelve al orden numérico.
- Las parcelas nuevas aparecen **al final**, marcadas «sin ubicar», hasta que se las ubique.
- El lector recibe el orden nuevo al abrir la app con señal o al presionar **Preparar recorrido**.

---

## 4. Administración: cada mes

**Desde la lista de Boletas**, cada período en curso tiene **«Continuar»**, que abre su detalle; las acciones del ciclo se hacen ahí.

**Guía de pasos:** el detalle de cada período muestra arriba la barra **Datos de la boleta → Corroborar desglose → Lecturas (X de N) → Calcular → Cerrar período → Publicar**, con ✓ en lo hecho y una línea **«Siguiente paso»** que explica qué hacer. **El botón verde siempre es el siguiente paso**; los grises son acciones posibles pero no las que tocan ahora. Mientras el lector toma las lecturas, la guía muestra el avance y no destaca ningún botón. En la lectura inicial, la barra es: Lecturas de partida → Cerrar lecturas → Lista para la primera boleta.

### 4.1 Generar el período

**Boletas → Generar período**. El sistema:
- crea el mes siguiente al último;
- pone a cada parcela su **lectura anterior** (la del mes pasado, o la lectura inicial la primera vez);
- copia los **conceptos del mes anterior** con su tipo y **monto en $0**, como propuesta. La primera vez no hay conceptos que copiar.

*Aviso posible:* «N parcelas no tienen lectura anterior y partirían en 0». Ocurre si falta la lectura inicial o hay una parcela nueva. Opciones: **Comenzar con lectura inicial** (si no hay boletas) o **Crear igual**, y después ingresar su lectura anterior en la pestaña *Lecturas*: aparece en amarillo, con un lápiz, solo en esas parcelas.

### 4.2 Datos de la boleta (con o sin boleta física)

**Con la boleta:** pestaña *Boleta* → subir la imagen o el PDF → **Procesar con IA**. El sistema lee los totales y los conceptos. Los conceptos nuevos quedan **sin clasificar** y hay que asignarles un tipo.

**Sin la boleta física** (no es impedimento): pestaña *Resumen* → **Ingresar a mano** o **Usar conceptos sugeridos** (Cargo fijo – fijo, Transporte de electricidad – variable, Interés / saldo anterior – informativo).

**Lo mínimo para liquidar son 3 totales:**

| Campo | Para qué |
|---|---|
| **kWh compañía** | El consumo total del medidor general. Conviene que sea mayor que la suma de los consumos de las parcelas; si no, el diferencial sale negativo y rebaja la cuota fija. |
| **Monto neto** | Requisito del cálculo. |
| **Total emisión** | **Lo que se reparte.** La suma de las liquidaciones da exactamente este monto, al peso. |

Los conceptos son opcionales y **pueden cambiar mes a mes**: agregar, quitar, reclasificar o usar montos negativos (descuentos y notas de crédito).

**Error frecuente para la ayuda:** los montos de los conceptos son los de **la boleta completa del condominio**, no los de una parcela. Ejemplo ficticio coherente: kWh compañía 18.000, monto neto $3.000.000, total emisión $3.600.000; Cargo fijo $60.000 (fijo), Transporte $540.000 (variable), Interés $12.000 (informativo). Valor del kWh resultante: (3.600.000 − 60.000 − 540.000) ÷ 18.000 = $166,67.

### 4.3 Corroborar el desglose

**Corroborar desglose**, el botón verde. Habilita **Calcular liquidaciones**.
- Si después se editan cifras o se reprocesa con IA, vuelve a **«borrador»** y hay que corroborar de nuevo. Es deliberado.

### 4.4 Lecturas del mes

Las toma el lector (sección 5). Aquí, la pestaña *Lecturas* muestra el avance, el lector y la **foto** (ícono de cámara). Arriba aparece el conteo «N lecturas tomadas sin foto».
- Una lectura se puede corregir con el lápiz mientras las lecturas estén abiertas. La foto se conserva como evidencia, con el aviso «Foto de la toma del …».
- **Cerrar lecturas** exige todas las parcelas: «Faltan lecturas por ingresar».

### 4.5 Calcular, revisar, cerrar y publicar

1. **Calcular liquidaciones**. Cada parcela recibe energía + transporte (variable) + cuota fija. Se puede recalcular las veces que haga falta mientras el período no esté cerrado.
2. Revisar la pestaña *Liquidaciones*. La suma es **exactamente** el total de emisión.
3. **Cerrar período**. Se puede **Reabrir período** para corregir.
4. **Publicar**. Desde ese momento los comuneros lo ven, y **ya no se puede reabrir**.

**Liquidaciones siempre al día:** si antes de cerrar el período reabres las lecturas, cambias montos o conceptos, o se corrige una lectura, las liquidaciones calculadas **se descartan solas** y la guía vuelve a pedir **Calcular**. No se puede cerrar ni publicar con montos viejos.

*Ejemplo ficticio por parcela* (300 kWh, con los totales de 4.2 y unos 15.900 kWh en el condominio): energía ≈ $50.000 + transporte ≈ $10.190 + cuota fija ≈ $7.740 = **≈ $67.930**.

---

## 5. Lector: la app en terreno (celular)

### 5.1 Antes de salir (con señal)
1. **Instalar la app**, una vez. Chrome: menú ⋮ → *Agregar a pantalla de inicio*. iPhone (Safari): Compartir → *Agregar a inicio*. **En iPhone es importante**: sin instalar, Safari puede borrar los datos guardados.
2. Abrir la app e ingresar con el correo y la clave.
3. **Preparar recorrido**: descarga el período, las parcelas y las lecturas anteriores. Arriba aparece «Recorrido de las hh:mm». Con señal se actualiza solo al abrir la app.

### 5.2 Tomar una lectura
1. Tocar la parcela. Aparecen en orden de recorrido, si existe; si no, en orden numérico. La pestaña **Pendientes** muestra las que faltan.
2. Ver la **lectura anterior**, escribir la **lectura actual** y ver los **kWh consumidos**. En rojo si es menor que la anterior; en ese caso no deja guardar.
3. **Tomar foto del medidor** (opcional, recomendada): abre la cámara. Permite **Retomar** y **Quitar**. Que se lean bien los dígitos. La foto queda con una franja abajo: «Parcela 23 · 09-10-2026 10:35», con la fecha y hora en que se sacó.
4. **Confirmar lectura** muestra «¡Lectura guardada!», o «Guardada en el celular» si no hay señal.

*Parcela ya leída sin foto:* entrar, tomar la foto y confirmar **sin cambiar el número**. Solo se agrega la foto.

*Revisar una foto ya subida:* en la parcela aparece «Esta lectura ya tiene foto en el servidor» y el botón **Ver foto**, que solo funciona con señal. Una vez que el servidor confirma la subida, la foto se borra del celular para no ocupar memoria.

### 5.3 Sin señal
- Barra amarilla: «Sin conexión: las lecturas se guardan en el celular · N sin sincronizar · N fotos por subir».
- Todo queda en el celular aunque se cierre la app, se apague el teléfono o venza la sesión. **No borrar los datos del navegador** con cosas pendientes.
- Al volver la señal se sincroniza solo, o con el botón **Sincronizar**. Primero suben las lecturas y después las fotos, una por una.

### 5.4 Pestaña «Revisar» (⚠️)
| Mensaje | Qué pasó | Qué hacer |
|---|---|---|
| «cambió en el servidor después de preparar el recorrido» | Alguien la corrigió mientras el lector estaba sin señal | Volver a capturarla si corresponde, o **Descartar** para quedarse con la del servidor (también se descarta su foto) |
| «las lecturas del período ya están cerradas» | Se cerraron antes de sincronizar | Avisar a la administración |
| «La foto no se subió: … ya no está vigente» | La lectura cambió y la foto era de la toma anterior | Retomar la foto o **Descartar foto** |
| Sesión vencida | Venció la sesión con cosas pendientes | Ingresar de nuevo: se sincroniza solo y no se pierde nada |

### 5.5 Lectura inicial (solo en la incorporación)
Misma app. Arriba dice «Lectura inicial · mes». La pantalla pide solo **«Lectura del medidor»**, sin anterior ni consumo, y con foto.

---

## 5b. Administración: cobranza de la luz

La luz se cobra **dentro del gasto común**. Menú **Cobranza** (`/cobranza`) → **Liquidaciones y cobranza**:

- **Indicadores:** cargos emitidos (incluye el saldo inicial), abonado, **por cobrar** y saldo a favor.
- **Cobranza por período:** emitido, cubierto, pendiente y cuántos pagaron. Solo cuentan los períodos **publicados**.
- **Deudores:** cada parcela con deuda, sus meses adeudados (con «parcial» cuando corresponde), su último abono y su saldo.
  - **Abonar:** un pago de **cualquier monto**, con fecha y nota (por ejemplo, «gasto común octubre, comprobante 1234»).
  - **Registrar pago del saldo:** se seleccionan varias parcelas y se registra el saldo completo de cada una, con la misma fecha.
  - **Cuenta:** todos los movimientos de la parcela. Un abono equivocado se **anula con un motivo**; no se borra y sigue visible tachado.
  - **Exportar CSV:** la lista de deudores para Excel.
- **Cómo se aplica un abono:** primero a la **deuda más antigua** (el saldo inicial y luego los meses en orden). Por eso un mes puede quedar **Parcial**.
- **El saldo inicial** (la deuda por luz anterior a la plataforma) se carga una vez, en el onboarding, en la columna **«Saldo luz»** de la planilla de la lectura inicial.
- **Todo queda en la auditoría:** quién registró o anuló cada abono, cuándo y el saldo antes y después.

*Ejemplo ficticio:* la parcela 2 debe un saldo inicial de $5.000, octubre $10.000 y noviembre $11.000, un total de $26.000. Abona $12.000: el saldo inicial queda pagado, octubre parcial ($7.000 de $10.000), y debe $14.000.

## 6. Comunero: su liquidación

1. Entrar al portal → **Mis liquidaciones**: la lista de **períodos publicados**.
2. Tocar el período para ver, por cada parcela suya:
   - **Tu consumo del período:** lectura anterior, lectura actual, kWh consumidos y cuándo se leyó el medidor;
   - **Energía (kWh)**, **Prorrateo variable**, **Cuota fija** y **Total a pagar**;
   - estado **Pagado / Parcial / Pendiente**, según sus abonos;
   - **Ver foto del medidor**, si el lector la tomó;
   - la **boleta de la compañía**: totales e imagen, si se subió.
- Arriba ve su **saldo de luz**: «Debes $X por luz», «Estás al día» o «Tienes $X a favor». Al tocarlo, ve su **cuenta**: saldo inicial, cada mes con su estado y sus abonos con fecha.
- Solo ve **sus** parcelas y solo **lo publicado**. Un período cerrado pero no publicado no se ve. La lectura inicial nunca se ve.

---

## 7. Preguntas frecuentes (surgidas en las pruebas)

| Pregunta | Respuesta |
|---|---|
| «Creé el período y el resumen está vacío.» | Es la primera boleta: no hay un mes anterior del cual copiar conceptos. Usa **Usar conceptos sugeridos** o **Ingresar a mano**. Lo mínimo son 3 totales. |
| «No tengo la boleta física.» | No es impedimento: ingresa los 3 totales a mano. La imagen se puede subir después. |
| «¿Qué monto pongo en cada concepto?» | El de la boleta **del condominio completo**. El sistema lo reparte entre las parcelas. |
| «Corroboré con conceptos en $0.» | Es válido, pero no tienen efecto: todo se reparte por consumo más el diferencial. Edítalos y vuelve a corroborar. |
| «En la lectura inicial no aparece la lectura anterior ni los kWh.» | Es correcto: es el punto de partida. La lectura anterior y los kWh aparecen desde la primera boleta. |
| «Pude cerrar la lectura inicial sin que el lector tomara ninguna.» | Las lecturas cargadas por Excel cuentan como tomadas. |
| «¿Para qué sirve “Preparar recorrido”?» | Para descargar los datos al celular y trabajar sin señal. El orden se define en Parcelas → Orden del recorrido. |
| «¿Puedo cargar las lecturas mensuales por Excel?» | No. Excel es **solo para la incorporación**. Las mensuales se toman con la app, con foto y registro de quién las tomó. |
| «La suma de las liquidaciones no da la emisión.» | Debe dar exacto, al peso. Si no da, revisa que se calculó después del último cambio de cifras. |
| «La lectura actual sale en rojo.» | Es menor que la anterior. Revisa el número; el sistema no la acepta. |
| «Me equivoqué de mes en la lectura inicial.» | Mientras esté abierta y sin boletas, elimínala con el basurero y ábrela de nuevo. |

---

## 8. Mensajes del sistema (para textos de ayuda)

| Mensaje | Cuándo |
|---|---|
| «La lectura inicial (…) aún tiene las lecturas abiertas. Ciérralas antes de cargar la primera boleta.» | Generar período con la lectura inicial abierta |
| «N parcela(s) no tienen lectura anterior y partirían en 0» | Generar período con parcelas sin historial |
| «El período de lectura inicial no se liquida» | Calcular, corroborar, subir boleta o publicar en la lectura inicial |
| «La lectura inicial ya es la base de un período posterior y no se puede reabrir» | Reabrir la lectura inicial cuando ya existe la primera boleta |
| «Debes corroborar el desglose antes de calcular…» | Calcular sin corroborar |
| «Faltan lecturas por ingresar…» | Cerrar lecturas incompletas |
| «La boleta no tiene 'monto_total_emision' definido» | Calcular sin total emisión |
| «La planilla tiene N error(es): corrígelos antes de aplicar» | Aplicar un Excel con errores |
| «La carga desde Excel solo está disponible en la lectura inicial» | Intentar Excel en un período mensual |
| «La liquidación aún no está publicada.» | El comunero consulta antes de la publicación |

---

## 9. Recorridos sugeridos para `recorridos/energia.js`

Siguiendo el formato de `recorridos/rifas.js`: un recorrido por rol, con pasos de *título + texto + pantalla simulada + toque*.

**Administración: incorporación** (computador)
1. Boletas sin períodos → aviso y «Comenzar con lectura inicial».
2. Elegir el mes (el anterior a la primera boleta).
3. Descargar la plantilla Excel.
4. Cargar el Excel → vista previa (a aplicar, reemplazos, errores).
5. Aplicar.
6. Continuar → Cerrar lecturas (botón verde del detalle).
7. Parcelas → Orden del recorrido → ordenar → Guardar.

**Administración: el mes** (computador)
1. Generar período → «Boleta Oct. 2026».
2. Pestaña Boleta → subir → Procesar con IA (o, en Resumen, «Usar conceptos sugeridos»).
3. Editar valores: 3 totales + conceptos con su tipo.
4. Corroborar desglose.
5. Pestaña Lecturas: avance, foto del medidor.
6. Cerrar lecturas.
7. Calcular → pestaña Liquidaciones.
8. Cerrar período.
9. Publicar.

**Lector: la toma** (celular)
1. Instalar la app.
2. Preparar recorrido.
3. Lista en orden de recorrido → tocar la parcela.
4. Lectura anterior → escribir la actual → kWh.
5. Tomar foto.
6. Confirmar.
7. Sin señal: barra amarilla y pendientes.
8. Vuelve la señal → Sincronizar.
9. Pestaña Revisar.

**Comunero: la consulta** (celular)
1. Mis liquidaciones (períodos publicados).
2. Abrir el período → desglose y total.
3. Estado de pago.
4. Ver foto del medidor.
5. Boleta de la compañía.

Al terminar, quitar la entrada «próximamente» de Energía en `recorridos/plataforma.js` (regla de la spec `capacitacion-plataforma`).

---

## 10. Estado al 08-10-2026 y pendientes

**Cambios OpenSpec del proceso:**

| Cambio | Estado |
|---|---|
| `cuadre-al-peso` | Completo |
| `proceso-energia` | Completo |
| `lectura-inicial` | Faltan las pruebas en el navegador |
| `foto-medidor` | Faltan las pruebas en el navegador y en celulares Android e iPhone |
| `lecturas-sin-conexion` | Faltan las pruebas en el navegador |
| `orden-recorrido` | Faltan las pruebas en el navegador |
| `items-credito-y-validacion` | Por cerrar |

Orden de archivado: los de detalle → `proceso-energia` → `ajustes-post-presentacion`. El detalle está en la propuesta de `proceso-energia`.

**Avance de la prueba en desarrollo:**
- Lectura inicial de septiembre 2026: cargada por Excel con **valores de prueba del 1 al 53** y cerrada.
- Boleta de octubre 2026: generada, con totales y conceptos de prueba (sección 4.2).
- **Siguiente paso:** corroborar → lecturas de octubre (actual > anterior) → cerrar → calcular → cerrar → publicar → vista del comunero.
- Antes de producción, cargar la lectura inicial **real** de Santa Laura.

**Desarrollo:** el portal corre con `npm run dev` (recarga en caliente, http://localhost:3000). El modo sin conexión y la foto en el celular se prueban con el contenedor (`docker-compose --profile contenedor up --build -d frontend`), porque Vite no activa el service worker.
