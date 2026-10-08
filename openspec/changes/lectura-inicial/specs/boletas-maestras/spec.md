# Spec Delta

## ADDED Requirements

### Requirement: Período de lectura inicial

El sistema DEBE (SHALL) exponer `POST /api/v1/boletas/lectura-inicial`, restringido a roles administrativos, que abre un período de tipo **lectura inicial** para registrar la lectura de partida de cada medidor. El sistema DEBE (SHALL) permitirlo solo cuando el condominio no tiene ninguna boleta. El período DEBE (SHALL) crearse con el `periodo_mes` indicado (primer día del mes), sin totales ni ítems de la compañía, y con una lectura en blanco por cada parcela del condominio, con `lectura_anterior` en cero. La creación DEBE (SHALL) registrarse como `CREATE_LECTURA_INICIAL`. Toda boleta DEBE (SHALL) informar su `tipo` (`regular` o `lectura_inicial`).

#### Scenario: Apertura de la lectura inicial

- **WHEN** un administrador abre la lectura inicial de un condominio sin boletas
- **THEN** el sistema crea el período de tipo `lectura_inicial` con una lectura en blanco por parcela y lo registra en la auditoría

#### Scenario: Condominio con boletas

- **WHEN** se intenta abrir la lectura inicial en un condominio que ya tiene alguna boleta
- **THEN** el sistema responde `409` y no crea nada

#### Scenario: Primera boleta tras la lectura inicial

- **WHEN** se crea la primera boleta después de cerrar las lecturas del período de lectura inicial
- **THEN** cada parcela parte con `lectura_anterior` igual a su lectura inicial, el período se asigna al mes siguiente y no se copian ítems

### Requirement: Carga masiva de lecturas iniciales desde una planilla

Para un período de lectura inicial, el sistema DEBE (SHALL) permitir a los roles administrativos:
- descargar una plantilla Excel con una fila por parcela del período (número de parcela, propietario y lectura inicial ya registrada, si la hay);
- subir una planilla Excel (`.xlsx`, máximo 2 MB, verificada por su contenido) con las columnas «Parcela» (o «Unidad») y «Lectura inicial» (o «Lectura»).

La subida DEBE (SHALL) funcionar en dos pasos:
1. **Vista previa**, sin modificar nada: informa las lecturas a aplicar, cuáles reemplazan una lectura ya tomada, las filas sin cambios, las filas vacías omitidas y los errores por fila (parcela que no está en el período, parcela repetida, valor no numérico o negativo).
2. **Aplicación**: el sistema NO DEBE (SHALL NOT) aplicar nada si la planilla tiene errores. Sin errores, registra cada valor como lectura tomada y deja constancia en la auditoría como `IMPORTAR_LECTURAS_INICIALES`, con el valor anterior y el nuevo de cada parcela.

La importación NO DEBE (SHALL NOT) estar disponible en períodos regulares ni con las lecturas cerradas.

#### Scenario: Vista previa de una planilla correcta

- **WHEN** el administrador sube una planilla válida en modo vista previa
- **THEN** el sistema informa cuántas lecturas aplicaría y cuáles reemplazan una ya tomada, sin modificar ninguna lectura

#### Scenario: Planilla con errores

- **WHEN** la planilla incluye una parcela que no existe en el período o un valor negativo
- **THEN** el sistema informa cada error con su número de fila y no aplica ninguna lectura, aunque se pida aplicar

#### Scenario: Aplicación

- **WHEN** el administrador aplica una planilla sin errores
- **THEN** cada parcela queda con su lectura inicial tomada y la importación queda registrada en la auditoría

#### Scenario: Celda vacía

- **WHEN** una fila de la planilla tiene la lectura vacía
- **THEN** el sistema la omite y no modifica la lectura de esa parcela

#### Scenario: Período regular o cerrado

- **WHEN** se intenta importar en un período regular o en una lectura inicial con las lecturas cerradas
- **THEN** el sistema responde `409` y no modifica nada

#### Scenario: Archivo que no es una planilla

- **WHEN** el archivo subido no es un `.xlsx` válido o supera 2 MB
- **THEN** el sistema responde `422` y no modifica nada

## MODIFIED Requirements

### Requirement: Un solo período abierto por condominio

El sistema NO DEBE (SHALL NOT) permitir crear una nueva boleta maestra mientras exista otra del mismo condominio cuyas liquidaciones no estén cerradas. Un período de lectura inicial DEBE (SHALL) considerarse cerrado una vez cerradas sus lecturas, porque no tiene liquidaciones.

#### Scenario: Período anterior sin cerrar

- **WHEN** un administrador intenta crear una boleta y ya existe una con `liquidaciones_cerradas` en falso
- **THEN** el sistema responde `409` indicando la etiqueta del período pendiente y que debe cerrarse antes de cargar una nueva boleta

#### Scenario: Lectura inicial cerrada

- **WHEN** un administrador crea una boleta y el único período previo es una lectura inicial con las lecturas cerradas
- **THEN** el sistema permite crear la boleta

#### Scenario: Lectura inicial abierta

- **WHEN** un administrador intenta crear una boleta mientras la lectura inicial tiene las lecturas abiertas
- **THEN** el sistema responde `409` indicando que la lectura inicial debe cerrarse primero

### Requirement: Generación automática de lecturas del período

Al crear una boleta maestra, el sistema DEBE (SHALL) generar una lectura en blanco por cada parcela del condominio, arrastrando como `lectura_anterior` el valor de `lectura_actual` de la última lectura registrada para esa parcela. Si alguna parcela no tiene ninguna lectura previa, el sistema NO DEBE (SHALL NOT) crear la boleta salvo que la petición lo acepte explícitamente con `aceptar_sin_lectura_anterior`. Si no lo acepta, DEBE (SHALL) responder `409` con la lista de esas parcelas.

#### Scenario: Parcela con historial previo

- **WHEN** se crea una boleta y una parcela ya tiene lecturas de períodos anteriores
- **THEN** el sistema crea su lectura del nuevo período con `lectura_anterior` igual a la `lectura_actual` más reciente, `lectura_actual` en cero, `kwh_consumidos` en cero y `fecha_toma` sin informar

#### Scenario: Parcela sin historial no aceptada

- **WHEN** se crea una boleta sin `aceptar_sin_lectura_anterior` y alguna parcela no tiene ninguna lectura previa
- **THEN** el sistema responde `409` con el detalle de las parcelas sin lectura previa y no crea la boleta

#### Scenario: Parcela sin historial

- **WHEN** se crea una boleta con `aceptar_sin_lectura_anterior` y alguna parcela no tiene ninguna lectura previa
- **THEN** el sistema crea la boleta y la lectura de esa parcela con `lectura_anterior` en cero
