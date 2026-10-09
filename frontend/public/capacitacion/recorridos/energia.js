/*
 * Módulo Energía (EnerCheck): de la lectura de los medidores al cobro de la luz de cada parcela.
 *
 * Cinco recorridos: incorporación del condominio (administración), toma de lecturas (lector), el ciclo del
 * mes (administración), cobranza de la luz (administración) y la consulta del comunero.
 * Formato de cada paso: ver recorridos/rifas.js. Datos ficticios (condominio Los Aromos).
 *
 * Si cambia un flujo real de energía, se actualiza aquí en el mismo cambio (spec capacitacion-plataforma).
 * Fuente del contenido: docs/ayuda-energia.md.
 */
;(function (C) {
  const ui = C.ui
  const { clp, icono, badge } = ui

  // ---- Piezas propias de Energía ---------------------------------------------------------------
  const PASOS_MES = ['Datos de la boleta', 'Corroborar desglose', 'Lecturas', 'Calcular', 'Cerrar período', 'Publicar']
  const PASOS_INICIAL = ['Lecturas de partida', 'Cerrar lecturas', 'Lista para la primera boleta']

  /** Guía de pasos del período: ✓ los hechos, resaltado el actual y la línea «Siguiente paso». */
  function guia(pasos, actual, siguiente, detalle = {}) {
    return `
      <div class="s-guia">
        <ol class="s-guia-pasos">${pasos.map((p, i) => `
          <li class="${i < actual ? 'hecho' : i === actual ? 'actual' : ''}"><i>${i < actual ? '✓' : i + 1}</i>${p}${detalle[i] ? ` <small>(${detalle[i]})</small>` : ''}</li>`).join('')}
        </ol>
        <p class="s-guia-sig">${siguiente}</p>
      </div>`
  }

  /** Encabezado de un período con sus botones (el verde es siempre el siguiente paso). */
  function cabPeriodo(titulo, sellos, botones) {
    return `
      <div class="s-entre">
        <div><p class="s-h1">${titulo}</p><p>${sellos.map(([t, c]) => badge(t, c)).join(' ')}</p></div>
        <div class="s-acciones">${botones}</div>
      </div>`
  }
  const boton = (texto, { prim = false, t = '', ic = '' } = {}) =>
    `<span class="s-btn ${prim ? 's-btn-prim' : 's-btn-sec'} s-btn-sm" ${t ? `data-t="${t}"` : ''}>${ic ? icono(ic) : ''} ${texto}</span>`

  const fotoMedidor = (parcela, cifras, fecha) => `
    <div class="s-foto"><div class="s-foto-img"><span>${cifras}</span></div>
      <p class="s-foto-franja">Parcela ${parcela} · ${fecha}</p></div>`

  // ---- Recorrido 1: incorporación del condominio ------------------------------------------------
  const listaBoletasVacia = `
    <div class="s-entre"><div><p class="s-h1">Boletas</p><p class="s-muted">0 períodos registrados</p></div>
      <div class="s-acciones">${boton('Comenzar con lectura inicial', { prim: true, t: 'lectura-inicial', ic: 'medidor' })}${boton('Generar período', { ic: 'mas' })}</div></div>
    <div class="s-aviso">${icono('medidor', 's-verde')}<p class="s-chico s-flex1">Antes de la primera boleta, registra la <b>lectura inicial</b> de cada medidor: es el punto de partida del primer consumo.</p></div>`

  const detalleInicial = ({ tomadas = 0, cerrada = false, capas = '' } = {}) => ui.escritorio({
    activo: 'Boletas',
    capas,
    contenido: `
      ${cabPeriodo('Lectura inicial · Sep. 2026', [[cerrada ? 'Lecturas cerradas' : 'En toma', cerrada ? 'verde' : 'amarillo']],
        cerrada ? boton('Reabrir lecturas') : boton('Cerrar lecturas', { prim: tomadas === 53, t: 'cerrar-lecturas', ic: 'candado' }))}
      ${guia(PASOS_INICIAL, cerrada ? 3 : tomadas === 53 ? 1 : 0,
        cerrada ? 'Lectura inicial cerrada. Ya puedes generar la primera boleta desde Boletas.'
          : tomadas === 53 ? '<b>Siguiente paso:</b> están las 53 lecturas de partida. Ciérralas para dejar lista la primera boleta.'
            : `<b>Siguiente paso:</b> registra la lectura de partida de cada medidor (${tomadas} de 53): con la app del lector o desde Excel.`,
        { 0: `${tomadas} de 53` })}
      ${cerrada ? '' : `<div class="s-acciones">${boton('Descargar plantilla', { t: 'plantilla', ic: 'descargar' })}${boton('Cargar desde Excel', { prim: true, t: 'excel', ic: 'planilla' })}</div>`}
      <div class="s-lista">
        <div><span><b>Parcela 1</b></span><span class="s-mono">${tomadas ? '15.230' : '—'}</span></div>
        <div><span><b>Parcela 2</b></span><span class="s-mono">${tomadas ? '8.804' : '—'}</span></div>
        <div><span><b>Parcela 3</b></span><span class="s-mono">${tomadas ? '21.117' : '—'}</span></div>
      </div>`,
  })

  const vistaPrevia = `
    <div class="s-velo"><div class="s-modal">
      <p class="s-h2">Cargar lecturas iniciales desde Excel</p>
      <div class="s-voucher ok">${icono('planilla')} lecturas-iniciales-2026-09.xlsx</div>
      <div class="s-kpis">
        <div class="s-kpi"><p class="s-chico">Lecturas / saldos</p><p class="s-kpi-valor">53 / 12</p></div>
        <div class="s-kpi"><p class="s-chico">Errores</p><p class="s-kpi-valor">0</p></div>
      </div>
      <p class="s-mini-titulo">Cambios por parcela</p>
      <div class="s-lista">
        <div><b>Parcela 1</b><span class="s-mono s-chico">Lectura — → 15.230<br>Saldo luz — → $45.000</span></div>
        <div><b>Parcela 2</b><span class="s-mono s-chico">Lectura — → 8.804</span></div>
        <div><b>Parcela 3</b><span class="s-mono s-chico">Lectura — → 21.117</span></div>
      </div>
      <div class="s-acciones"><span class="s-btn s-btn-ghost">Cancelar</span><span class="s-btn s-btn-prim" data-t="aplicar">${icono('subir')} Aplicar 53 lecturas y 12 saldos</span></div>
    </div></div>`

  const recorridoParcelas = (ordenado) => ui.escritorio({
    activo: 'Parcelas',
    contenido: `
      <div class="s-entre"><div><p class="s-h1">Parcelas</p><p class="s-muted">53 activas de 53</p></div>
        <div class="s-acciones">${boton('Orden del recorrido', { t: 'orden', ic: 'ruta' })}${boton('Nueva parcela', { prim: true, ic: 'mas' })}</div></div>
      ${ordenado ? `
      <div class="s-velo"><div class="s-modal">
        <p class="s-h2">Orden del recorrido del lector</p>
        <p class="s-chico">Ordena las parcelas como las camina el lector (arrastra o usa las flechas). La app de lecturas las mostrará en este orden, también sin señal.</p>
        <div class="s-lista">
          ${['6', '5', '4', '3', '13 A', '13 B'].map((n, i) => `<div><span>${i + 1}. <b>Parcela ${n}</b></span><span class="s-chico">▲ ▼</span></div>`).join('')}
        </div>
        <div class="s-acciones"><span class="s-btn s-btn-ghost">Quitar recorrido</span><span class="s-btn s-btn-prim" data-t="guardar-orden">Guardar recorrido</span></div>
      </div></div>` : ''}`,
  })

  const incorporacion = {
    id: 'incorporacion',
    rol: 'Administración',
    icono: 'maletin',
    titulo: 'Incorporación del condominio',
    resumen: 'Se hace una sola vez: la lectura de partida de cada medidor y la deuda de luz anterior, desde una planilla Excel.',
    dispositivo: 'escritorio',
    pasos: [
      {
        titulo: 'Comenzar con lectura inicial',
        texto: 'Un condominio nuevo parte sin boletas. En <b>Boletas</b>, el botón verde es <b>Comenzar con lectura inicial</b>: registra el número de partida de cada medidor, para que el primer consumo sea real.',
        pantalla: () => ui.escritorio({ activo: 'Boletas', contenido: listaBoletasVacia }),
        toque: 'lectura-inicial',
      },
      {
        titulo: 'Elegir el mes',
        texto: 'Elige el mes en que se toman las lecturas; la <b>primera boleta será la del mes siguiente</b>. Lo ideal es tomarlas el mismo día en que la compañía lee el medidor general.',
        pantalla: () => ui.escritorio({
          activo: 'Boletas', contenido: listaBoletasVacia,
          capas: `<div class="s-velo"><div class="s-modal"><p class="s-h2">Lectura inicial de los medidores</p>
            <p class="s-chico">Se abre un período especial, sin boleta de la compañía, para registrar la lectura de partida de cada medidor.</p>
            ${ui.campo({ label: 'Mes en que se toman las lecturas', id: 'mes', valor: 'septiembre de 2026' })}
            <p class="s-chico">La primera boleta quedará en el mes siguiente.</p>
            <div class="s-acciones"><span class="s-btn s-btn-ghost">Cancelar</span><span class="s-btn s-btn-prim" data-t="abrir">Abrir lectura inicial</span></div></div></div>`,
        }),
        toque: 'abrir',
      },
      {
        titulo: 'Descargar la plantilla',
        texto: 'La guía de arriba muestra los pasos. Si ya tienes las lecturas del proceso anterior, descarga la <b>plantilla Excel</b>: trae las parcelas con las columnas <b>Lectura inicial</b> y <b>Saldo luz</b> (lo que cada uno debía por luz antes de la plataforma).',
        pantalla: () => detalleInicial(),
        toque: 'plantilla',
      },
      {
        titulo: 'Cargar desde Excel',
        texto: 'Completa la planilla y súbela con <b>Cargar desde Excel</b>. Una celda vacía no cambia nada; un saldo en 0 deja la parcela sin deuda. La carga desde Excel existe <b>solo en la incorporación</b>: las lecturas mensuales se toman siempre con la app.',
        pantalla: () => detalleInicial(),
        toque: 'excel',
      },
      {
        titulo: 'Revisar la vista previa',
        texto: 'Antes de guardar ves los <b>cambios por parcela</b> y los <b>errores con su fila</b> (parcela que no existe, repetida, número negativo). Si hay errores no se aplica nada: corriges la planilla y la subes de nuevo.',
        pantalla: () => detalleInicial({ capas: vistaPrevia }),
        toque: 'aplicar',
      },
      {
        titulo: 'Cerrar las lecturas',
        texto: 'Con las 53 lecturas de partida, el siguiente paso es <b>Cerrar lecturas</b> (botón verde). El saldo inicial de luz queda como el primer cargo de la cuenta de cada parcela.',
        pantalla: () => detalleInicial({ tomadas: 53 }),
        toque: 'cerrar-lecturas',
      },
      {
        titulo: 'Lista para la primera boleta',
        texto: 'La lectura inicial queda cerrada. Desde ahora, cada mes se genera un período con su boleta y cada parcela parte de su lectura inicial.',
        pantalla: () => detalleInicial({ tomadas: 53, cerrada: true }),
      },
      {
        titulo: 'Orden del recorrido (opcional)',
        texto: 'En <b>Parcelas → Orden del recorrido</b> ordenas las parcelas como las camina el lector. Su app las mostrará en ese orden: la próxima parcela pendiente siempre arriba. Sin recorrido, usa el orden numérico.',
        pantalla: () => recorridoParcelas(true),
        toque: 'guardar-orden',
      },
    ],
  }

  // ---- Recorrido 2: el lector en terreno ----------------------------------------------------------
  const PARCELAS_RUTA = [['6', 'Rosa Vidal'], ['5', 'Juan Pérez'], ['4', 'Ana Soto'], ['3', 'Pedro Muñoz'], ['13 A', 'Carla Díaz']]
  const appLector = ({ conexion = true, pendientes = 0, fotos = 0, leidas = 0, revisar = false, cerrado = false } = {}) => ui.celular({
    rol: 'Lector',
    contenido: `
      <div class="s-banda ${conexion ? '' : 's-banda-amarilla'}">${icono(conexion ? 'mundo' : 'nube')}
        <span class="s-flex1">${conexion ? 'Con conexión' : 'Sin conexión: las lecturas se guardan en el celular'}${pendientes ? ` · <b>${pendientes} sin sincronizar</b>` : ''}${fotos ? ` · <b>${fotos} fotos por subir</b>` : ''}</span>
        ${conexion && (pendientes || fotos) ? `<span class="s-btn s-btn-prim s-btn-sm" data-t="sincronizar">${icono('subir')} Sincronizar</span>` : ''}</div>
      <div class="s-entre"><p class="s-chico">OCT. 2026</p><p class="s-link" data-t="preparar">${icono('descargar')} Recorrido de las 08:10</p></div>
      <div class="s-avance"><span style="width:${(leidas / 53) * 100}%"></span></div>
      <p class="s-chico s-der"><b>${leidas}/53</b></p>
      ${cerrado ? `<div class="s-banda">${icono('candado')}<span>Las lecturas de Oct. 2026 están <b>cerradas</b>: ya no se pueden modificar. Si hay que corregir una, pide a la administración que las reabra.</span></div>` : ''}
      ${ui.pestanas([['pendientes', 'Pendientes'], ['todas', 'Todas'], ...(revisar ? [['revisar', 'Revisar (1)']] : [])], revisar ? 'revisar' : 'pendientes')}
      <div class="s-lista">
        ${(revisar ? [PARCELAS_RUTA[2]] : PARCELAS_RUTA.slice(leidas)).map(([n, nombre]) => `
          <div data-t="parcela-${n}"><span><b>Parcela ${n}</b><br><span class="s-chico">${nombre}</span>
            ${revisar ? `<br><span class="s-chico s-amarillo">Tu lectura 18.340 no se aplicó: cambió en el servidor después de preparar el recorrido</span>` : ''}</span>
            <span>${revisar ? '<span class="s-btn s-btn-sec s-btn-sm">Descartar</span>' : icono('der')}</span></div>`).join('')}
      </div>`,
  })

  const captura = ({ valor = '', foto = false } = {}) => ui.celular({
    rol: 'Lector',
    contenido: `
      <p class="s-link">${icono('izq')} Volver</p>
      <p class="s-mini-titulo s-centro">Registrar lectura</p>
      <p class="s-h1 s-centro">Parcela 6</p>
      <p class="s-muted s-centro">Rosa Vidal</p>
      <div class="s-caja s-centro"><p class="s-chico">Lectura anterior</p><p class="s-num-grande" style="font-size:22px">12.405</p></div>
      ${ui.campo({ label: 'Lectura actual', id: 'lectura', valor, tipo: 's-num-grande' })}
      <div class="s-caja s-centro" data-revelar><p class="s-chico">Consumo del período</p><p class="s-num-grande s-verde" style="font-size:22px">${valor ? '312 kWh' : '312 kWh'}</p></div>
      ${foto ? fotoMedidor('6', '12.717', '30-10-2026 10:35') : `<span class="s-btn s-btn-sec s-btn-full" data-t="foto">${icono('camara')} Tomar foto del medidor <small>(opcional)</small></span>`}
      <span class="s-btn s-btn-prim s-btn-full" data-t="confirmar-lectura">Confirmar lectura</span>`,
  })

  const lector = {
    id: 'lector',
    rol: 'Lector',
    icono: 'medidor',
    titulo: 'Toma de lecturas en terreno',
    resumen: 'El lector recorre las parcelas con su celular, incluso sin señal, y toma la lectura y la foto de cada medidor.',
    dispositivo: 'celular',
    pasos: [
      {
        titulo: 'Preparar el recorrido',
        texto: 'Con señal, antes de salir: abre la app (conviene <b>instalarla</b> en la pantalla de inicio) y toca <b>Preparar recorrido</b>. Se descargan al celular las parcelas y sus lecturas anteriores para trabajar <b>sin señal</b>. No cambia el orden: el orden lo define la administración.',
        pantalla: () => appLector(),
        toque: 'preparar',
      },
      {
        titulo: 'La próxima parcela, arriba',
        texto: 'Las parcelas aparecen en el <b>orden del recorrido</b> y la pestaña <b>Pendientes</b> deja arriba la próxima. Toca la parcela donde estás.',
        pantalla: () => appLector(),
        toque: 'parcela-6',
      },
      {
        titulo: 'Escribir la lectura',
        texto: 'Ves la <b>lectura anterior</b>. Escribe el número que marca el medidor: la app calcula al instante los <b>kWh consumidos</b>. Si es menor que la anterior se pone en rojo y no deja guardar.',
        pantalla: () => captura(),
        escribir: [{ campo: 'lectura', texto: '12717' }],
        toque: 'foto',
      },
      {
        titulo: 'Foto del medidor',
        texto: 'Toma la foto con la cámara del celular (opcional, recomendada): que se lean los dígitos. Queda con una franja con la <b>parcela, la fecha y la hora</b> en que se sacó, como evidencia. Puedes retomarla o quitarla.',
        pantalla: () => captura({ valor: '12717', foto: true }),
        toque: 'confirmar-lectura',
      },
      {
        titulo: 'Sin señal: se guarda en el celular',
        texto: 'Sin señal la app sigue funcionando: aparece la barra amarilla y la lectura y la foto quedan <b>guardadas en el celular</b>. No se pierden aunque se cierre la app, se apague el teléfono o venza la sesión.',
        pantalla: () => appLector({ conexion: false, pendientes: 3, fotos: 3, leidas: 3 }),
      },
      {
        titulo: 'Vuelve la señal: sincronizar',
        texto: 'Al volver la señal se sincroniza solo, o con el botón <b>Sincronizar</b>: primero las lecturas y después las fotos. Una lectura no se borra del celular hasta que el servidor la confirma.',
        pantalla: () => appLector({ pendientes: 3, fotos: 3, leidas: 3 }),
        toque: 'sincronizar',
      },
      {
        titulo: 'Revisar',
        texto: 'Si alguien corrigió una lectura mientras estabas sin señal, la tuya <b>no pisa</b> la del servidor: queda en <b>Revisar</b> con el motivo. Vuelve a capturarla si corresponde, o <b>Descarta</b> la tuya.',
        pantalla: () => appLector({ leidas: 3, revisar: true }),
      },
      {
        titulo: 'Lecturas cerradas',
        texto: 'Cuando están las 53 y la administración cierra las lecturas, la app lo avisa y ya no permite cambios. Para corregir una, la administración debe reabrirlas.',
        pantalla: () => appLector({ leidas: 5, cerrado: true }),
      },
    ],
  }

  // ---- Recorrido 3: el ciclo del mes (administración) -------------------------------------------
  const KPIS_BOLETA = (vacio) => `
    <div class="s-kpis s-kpis-4">
      <div class="s-kpi"><p class="s-chico">kWh compañía</p><p class="s-kpi-valor">${vacio ? '—' : '18.000'}</p></div>
      <div class="s-kpi"><p class="s-chico">Monto neto</p><p class="s-kpi-valor">${vacio ? '—' : clp(3000000)}</p></div>
      <div class="s-kpi"><p class="s-chico">Total emisión</p><p class="s-kpi-valor">${vacio ? '—' : clp(3600000)}</p></div>
      <div class="s-kpi"><p class="s-chico">Saldo anterior</p><p class="s-kpi-valor">—</p></div>
    </div>`
  const CONCEPTOS = [['Cargo fijo', 'Fijo', 60000], ['Transporte de electricidad', 'Variable', 540000], ['Interés / saldo anterior', 'Informativo', 12000]]

  const periodo = ({ paso, botones, sellos = [], vacio = false, tab = 'resumen', capas = '', siguiente, detalleLect = '53 de 53' }) => ui.escritorio({
    activo: 'Boletas',
    capas,
    contenido: `
      ${cabPeriodo('Boleta Oct. 2026', sellos, botones)}
      ${guia(PASOS_MES, paso, siguiente, { 2: detalleLect })}
      ${KPIS_BOLETA(vacio)}
      ${ui.pestanas([['resumen', 'Resumen'], ['lecturas', 'Lecturas'], ['liquidaciones', 'Liquidaciones (53)'], ['boleta', 'Boleta']], tab)}
      ${tab === 'liquidaciones' ? `
        <div class="s-lista">
          <div><span><b>Parcela 6</b> · 312 kWh</span><span class="s-mono">Energía ${clp(52004)} · Variable ${clp(11003)} · Fijo ${clp(9582)} = <b>${clp(72589)}</b></span></div>
          <div><span><b>Parcela 5</b> · 210 kWh</span><span class="s-mono">Energía ${clp(35001)} · Variable ${clp(7406)} · Fijo ${clp(9582)} = <b>${clp(51989)}</b></span></div>
          <div><span><b>TOTAL (53 parcelas)</b></span><span class="s-mono s-verde"><b>${clp(3600000)}</b> · exacto, al peso</span></div>
        </div>`
        : vacio ? `<div class="s-card s-centro"><p>Este período aún no tiene los datos de la boleta.</p>
            <p class="s-chico">Lo mínimo para liquidar son 3 totales: kWh compañía, monto neto y total emisión. Los conceptos son opcionales y pueden cambiar mes a mes.</p>
            <div class="s-acciones">${boton('Ingresar a mano', { ic: 'documento' })}${boton('Usar conceptos sugeridos', { prim: true, t: 'sugeridos' })}</div></div>`
        : `<div class="s-lista">${CONCEPTOS.map(([d, t, m]) => `<div><span><b>${d}</b> · <span class="s-chico">${t}</span></span><span class="s-mono">${clp(m)}</span></div>`).join('')}</div>`}`,
  })

  const editarValores = `
    <div class="s-velo"><div class="s-modal">
      <p class="s-h2">Editar totales e ítems</p>
      ${ui.campo({ label: 'kWh compañía', id: 'kwh', valor: '' })}
      ${ui.campo({ label: 'Monto neto', id: 'neto', valor: '' })}
      ${ui.campo({ label: 'Total emisión', id: 'emision', valor: '' })}
      <div class="s-lista">${CONCEPTOS.map(([d, t, m]) => `<div><span>${d}</span><span class="s-chico">${t} · ${clp(m)}</span></div>`).join('')}</div>
      <p class="s-chico">Los montos son los de la <b>boleta completa del condominio</b>, no de una parcela.</p>
      <div class="s-acciones"><span class="s-btn s-btn-ghost">Cancelar</span><span class="s-btn s-btn-prim" data-t="guardar">Guardar</span></div>
    </div></div>`

  const ciclo = {
    id: 'ciclo',
    rol: 'Administración',
    icono: 'maletin',
    titulo: 'El ciclo del mes',
    resumen: 'De la boleta de la compañía a la liquidación de cada parcela: datos, corroborar, cerrar lecturas, calcular, cerrar y publicar.',
    dispositivo: 'escritorio',
    pasos: [
      {
        titulo: 'Generar el período',
        texto: 'En <b>Boletas → Generar período</b> se crea el mes siguiente. Cada parcela parte con su <b>lectura anterior</b> y se proponen los conceptos del mes pasado en $0. Arriba, la <b>guía de pasos</b>: el botón verde es siempre el siguiente paso.',
        pantalla: () => periodo({ paso: 0, vacio: true, botones: boton('Ingresar datos de la boleta', { prim: true, t: 'datos', ic: 'documento' }), siguiente: '<b>Siguiente paso:</b> ingresa los 3 totales de la boleta: súbela en la pestaña Boleta o ingrésala a mano.', detalleLect: '0 de 53' }),
        toque: 'datos',
      },
      {
        titulo: 'Datos de la boleta',
        texto: 'Sube la boleta y procésala con IA, o ingrésala a mano: <b>no hace falta la boleta física</b>. Lo mínimo son <b>kWh compañía, monto neto y total emisión</b>. Clasifica cada concepto: <b>fijo</b> (partes iguales), <b>variable</b> (según consumo) o <b>informativo</b> (no se reparte).',
        pantalla: () => periodo({ paso: 0, vacio: true, botones: boton('Ingresar datos de la boleta', { prim: true, ic: 'documento' }), siguiente: '<b>Siguiente paso:</b> ingresa los 3 totales de la boleta.', detalleLect: '0 de 53', capas: editarValores }),
        escribir: [{ campo: 'kwh', texto: '18.000' }, { campo: 'neto', texto: '3.000.000' }, { campo: 'emision', texto: '3.600.000' }],
        toque: 'guardar',
      },
      {
        titulo: 'Corroborar el desglose',
        texto: 'Revisa que los conceptos y su tipo estén bien y toca <b>Corroborar desglose</b>: es tu firma, queda en la auditoría. Si después cambias una cifra, vuelve a borrador y hay que corroborar de nuevo.',
        pantalla: () => periodo({ paso: 1, botones: boton('Cerrar lecturas') + boton('Corroborar desglose', { prim: true, t: 'corroborar', ic: 'check' }), siguiente: '<b>Siguiente paso:</b> revisa los conceptos y su tipo y confírmalos con «Corroborar desglose».', detalleLect: '41 de 53' }),
        toque: 'corroborar',
      },
      {
        titulo: 'Esperar las lecturas',
        texto: 'Mientras el lector toma las lecturas, la guía muestra el avance y <b>no destaca ningún botón</b>: no hay nada que hacer todavía. Si cambia una lectura o una cifra, las liquidaciones ya calculadas se descartan solas.',
        pantalla: () => periodo({ paso: 2, sellos: [['Desglose corroborado', 'morado']], botones: boton('Cerrar lecturas') + boton('Calcular liquidaciones'), siguiente: '<b>Siguiente paso:</b> el lector está tomando las lecturas: 41 de 53. Cuando estén todas, ciérralas.', detalleLect: '41 de 53' }),
      },
      {
        titulo: 'Cerrar las lecturas',
        texto: 'Con las 53 tomadas, el botón verde es <b>Cerrar lecturas</b>: certifica el recorrido y bloquea los cambios (para el lector y la administración).',
        pantalla: () => periodo({ paso: 2, sellos: [['Desglose corroborado', 'morado']], botones: boton('Cerrar lecturas', { prim: true, t: 'cerrar', ic: 'candado' }) + boton('Calcular liquidaciones'), siguiente: '<b>Siguiente paso:</b> las 53 lecturas están tomadas. Ciérralas para certificar el recorrido.' }),
        toque: 'cerrar',
      },
      {
        titulo: 'Calcular',
        texto: 'Toca <b>Calcular liquidaciones</b>. Cada parcela paga su energía, su parte variable (que incluye el diferencial: lo que la compañía cobró y ningún medidor registró) y la cuota fija.',
        pantalla: () => periodo({ paso: 3, sellos: [['Desglose corroborado', 'morado'], ['Lecturas cerradas', 'amarillo']], botones: boton('Reabrir lecturas') + boton('Calcular liquidaciones', { prim: true, t: 'calcular', ic: 'calculadora' }), siguiente: '<b>Siguiente paso:</b> calcula cuánto paga cada parcela. Puedes recalcular las veces que necesites.' }),
        toque: 'calcular',
      },
      {
        titulo: 'Revisar y cerrar el período',
        texto: 'En la pestaña <b>Liquidaciones</b> la suma es <b>exactamente el total de emisión</b>, al peso. Si todo está bien, <b>Cerrar período</b>. Todavía se puede reabrir si hay que corregir.',
        pantalla: () => periodo({ paso: 4, tab: 'liquidaciones', sellos: [['Desglose corroborado', 'morado'], ['Lecturas cerradas', 'amarillo']], botones: boton('Reabrir lecturas') + boton('Recalcular') + boton('Cerrar período', { prim: true, t: 'cerrar-periodo', ic: 'candado' }), siguiente: '<b>Siguiente paso:</b> revisa las liquidaciones en su pestaña y cierra el período.' }),
        toque: 'cerrar-periodo',
      },
      {
        titulo: 'Publicar',
        texto: 'Toca <b>Publicar</b>: desde ese momento cada comunero ve su liquidación y su cargo entra a la cobranza. <b>No se puede deshacer</b>.',
        pantalla: () => periodo({ paso: 5, tab: 'liquidaciones', sellos: [['Período cerrado', 'gris']], botones: boton('Reabrir período') + boton('Publicar', { prim: true, t: 'publicar', ic: 'mundo' }), siguiente: '<b>Siguiente paso:</b> publica para que cada comunero vea su liquidación. Después ya no se puede reabrir.' }),
        toque: 'publicar',
      },
    ],
  }

  // ---- Recorrido 4: cobranza de la luz ------------------------------------------------------------
  const DEUDORES = [
    ['3', 'Pedro Muñoz', 117589, ['Saldo inicial', 'Oct. 2026']],
    ['5', 'Juan Pérez', 51989, ['Oct. 2026']],
    ['6', 'Rosa Vidal', 72589, ['Oct. 2026']],
  ]
  const cobranza = ({ capas = '', abonado = false } = {}) => ui.escritorio({
    activo: 'Cobranza',
    capas,
    contenido: `
      <p class="s-h1">Liquidaciones y cobranza</p>
      <p class="s-muted">Cuánto deben los comuneros por luz. Los abonos se imputan a la deuda más antigua.</p>
      <div class="s-kpis s-kpis-4">
        <div class="s-kpi"><p class="s-chico">Cargos emitidos</p><p class="s-kpi-valor">${clp(4140000)}</p></div>
        <div class="s-kpi"><p class="s-chico">Abonado</p><p class="s-kpi-valor s-verde">${clp(abonado ? 2970000 : 2930000)}</p></div>
        <div class="s-kpi"><p class="s-chico">Por cobrar</p><p class="s-kpi-valor s-rojo">${clp(abonado ? 1170000 : 1210000)}</p></div>
        <div class="s-kpi"><p class="s-chico">Saldo a favor</p><p class="s-kpi-valor">${clp(0)}</p></div>
      </div>
      <p class="s-mini-titulo">Cobranza por período</p>
      <div class="s-lista">
        <div><span><b>Oct. 2026</b> · 37/53 pagados</span><span class="s-mono">Emitido ${clp(3600000)} · Pendiente ${clp(abonado ? 670000 : 710000)}</span></div>
        <div><span><b>Saldo inicial</b> · 4/12 pagados</span><span class="s-mono">Emitido ${clp(540000)} · Pendiente ${clp(500000)}</span></div>
      </div>
      <div class="s-entre"><p class="s-mini-titulo">Deudores</p><div class="s-acciones">${boton('Pagar saldo (2)', { prim: true, t: 'masivo', ic: 'billetera' })}${boton('CSV', { t: 'csv', ic: 'descargar' })}</div></div>
      <div class="s-lista">
        ${DEUDORES.map(([n, nombre, saldo, meses], i) => `
          <div><span>☑ <b>Parcela ${n}</b> · <span class="s-chico">${nombre}</span><br>${meses.map((m) => badge(abonado && n === '3' && m === 'Saldo inicial' ? 'Saldo inicial · pagado' : abonado && n === '3' ? `${m} · parcial` : m, abonado && n === '3' && m !== 'Saldo inicial' ? 'amarillo' : 'gris')).join(' ')}</span>
            <span><b class="s-mono s-rojo">${clp(abonado && n === '3' ? saldo - 40000 : saldo)}</b> ${boton('Abonar', { t: i === 0 ? 'abonar' : '', ic: 'billetera' })}${boton('Cuenta', { t: i === 0 ? 'cuenta' : '' })}</span></div>`).join('')}
      </div>`,
  })
  const modalAbono = `
    <div class="s-velo"><div class="s-modal">
      <p class="s-h2">Abono · Parcela 3</p>
      <p class="s-chico">Saldo actual: <b>${clp(117589)}</b>. Puede ser un abono parcial: se aplica a la deuda más antigua.</p>
      ${ui.campo({ label: 'Monto del abono', id: 'monto', valor: '' })}
      ${ui.campo({ label: 'Fecha del pago', id: 'fecha', valor: '15-11-2026' })}
      ${ui.campo({ label: 'Nota (opcional)', id: 'nota', valor: '' })}
      <p class="s-chico">Queda registrado para auditoría; si te equivocas, se anula con un motivo (no se borra).</p>
      <div class="s-acciones"><span class="s-btn s-btn-ghost">Cancelar</span><span class="s-btn s-btn-prim" data-t="registrar">Registrar abono</span></div>
    </div></div>`
  const modalCuenta = (anulado) => `
    <div class="s-velo"><div class="s-modal">
      <p class="s-h2">Cuenta de luz · Parcela 3</p>
      <div class="s-tres"><div><p class="s-chico">Cargos</p><p class="s-mono">${clp(157589)}</p></div><div><p class="s-chico">Abonos</p><p class="s-mono s-verde">${clp(anulado ? 0 : 40000)}</p></div><div><p class="s-chico">Saldo</p><p class="s-mono s-rojo">${clp(anulado ? 157589 : 117589)}</p></div></div>
      <div class="s-lista">
        <div><span>Saldo inicial (deuda anterior)<br><span class="s-chico">01-09-2026</span></span><span class="s-mono">${clp(45000)} ${badge(anulado ? 'Pendiente' : 'Pagado', anulado ? 'gris' : 'verde')}</span></div>
        <div><span>Luz Oct. 2026</span><span class="s-mono">${clp(112589)} ${badge('Pendiente', 'gris')}</span></div>
        <div><span style="${anulado ? 'text-decoration:line-through;opacity:.5' : ''}">Abono · gasto común noviembre<br><span class="s-chico">15-11-2026</span>${anulado ? '<br><span class="s-chico s-amarillo">Anulado: registrado en la parcela equivocada</span>' : ''}</span>
          <span class="s-mono s-verde">− ${clp(40000)} ${anulado ? '' : '<span class="s-link" data-t="anular">Anular</span>'}</span></div>
      </div>
    </div></div>`

  const cobro = {
    id: 'cobranza',
    rol: 'Administración',
    icono: 'billetera',
    titulo: 'Cobranza de la luz',
    resumen: 'La luz se cobra en el gasto común: registra los abonos, sigue a los deudores y lleva la cuenta corriente de cada parcela.',
    dispositivo: 'escritorio',
    pasos: [
      {
        titulo: 'Menú Cobranza',
        texto: 'En <b>Cobranza</b> ves lo emitido (incluido el saldo inicial), lo abonado y lo <b>por cobrar</b>, la cobranza de cada período y los <b>deudores</b>. Solo cuentan los períodos <b>publicados</b>.',
        pantalla: () => cobranza(),
        toque: 'abonar',
      },
      {
        titulo: 'Registrar un abono',
        texto: 'El comunero puede <b>abonar cualquier monto</b>. Indica el monto, la fecha del pago y una nota (por ejemplo, el comprobante del gasto común).',
        pantalla: () => cobranza({ capas: modalAbono }),
        escribir: [{ campo: 'monto', texto: '40.000' }, { campo: 'nota', texto: 'Gasto común noviembre' }],
        toque: 'registrar',
      },
      {
        titulo: 'Se aplica a lo más antiguo',
        texto: 'El abono cubre primero la <b>deuda más antigua</b>: el saldo inicial queda pagado y octubre, <b>parcial</b>. Los estados Pagado / Parcial / Pendiente se calculan solos; nadie los marca a mano.',
        pantalla: () => cobranza({ abonado: true }),
        toque: 'cuenta',
      },
      {
        titulo: 'La cuenta de la parcela',
        texto: 'En <b>Cuenta</b> ves todos los movimientos: cargos con su estado y abonos con su fecha. Si un abono se registró por error, se <b>anula con un motivo</b>.',
        pantalla: () => cobranza({ abonado: true, capas: modalCuenta(false) }),
        toque: 'anular',
      },
      {
        titulo: 'Anular sin borrar',
        texto: 'El abono anulado <b>no se borra</b>: queda tachado, con su motivo, quién y cuándo, para auditorías futuras. El saldo vuelve a su valor anterior.',
        pantalla: () => cobranza({ capas: modalCuenta(true) }),
      },
      {
        titulo: 'Pagos del gasto común, de una vez',
        texto: 'Al recibir el informe de pagos del gasto común, selecciona las parcelas que pagaron y toca <b>Pagar saldo</b>: se registra el saldo completo de cada una con la misma fecha. Con <b>CSV</b> exportas los deudores para Excel.',
        pantalla: () => cobranza(),
        toque: 'masivo',
      },
    ],
  }

  // ---- Recorrido 5: el comunero ---------------------------------------------------------------------
  const detalleComunero = ({ estado = 'Pendiente', color = 'amarillo', foto = false } = {}) => ui.celular({
    rol: 'Comunero',
    contenido: `
      <p class="s-link">${icono('izq')} Volver a mis liquidaciones</p>
      <p class="s-h1">Sep. 2026</p>
      <div class="s-card">
        <div class="s-entre"><p class="s-mini-titulo">Parcela 14</p>${badge(estado, color)}</div>
        <div class="s-caja"><p class="s-mini-titulo">Tu consumo del período</p>
          <div class="s-tres"><div><p class="s-chico">Anterior</p><p class="s-mono">8.120</p></div><div><p class="s-chico">Actual</p><p class="s-mono">8.346</p></div><div><p class="s-chico">Consumo</p><p class="s-mono s-verde"><b>226 kWh</b></p></div></div>
          <p class="s-chico s-centro">Medidor leído el 30-09-2026 10:12</p></div>
        <div class="s-resumen">
          <p><span>Energía (kWh)</span><b class="s-mono">${clp(26140)}</b></p>
          <p><span>Prorrateo variable</span><b class="s-mono">${clp(5528)}</b></p>
          <p><span>Cuota fija</span><b class="s-mono">${clp(6782)}</b></p>
          <p><span>Total a pagar</span><b class="s-total">${clp(38450)}</b></p>
        </div>
        <p class="s-chico ${color === 'verde' ? 's-verde' : 's-amarillo'}">${estado === 'Pendiente' ? 'Pago pendiente — se paga con tu gasto común' : estado}</p>
        <p class="s-link" data-t="foto">${icono('camara')} Ver foto del medidor</p>
      </div>
      ${foto ? fotoMedidor('14', '8.346', '30-09-2026 10:12') : ''}`,
  })

  const comunero = {
    id: 'comunero',
    rol: 'Comunero',
    icono: 'casa',
    titulo: 'Tu liquidación de luz',
    resumen: 'Cada comunero ve, desde su celular, cuánto consumió, cuánto paga, la foto de su medidor y su cuenta de luz.',
    dispositivo: 'celular',
    pasos: [
      {
        titulo: 'Entrar al portal',
        texto: 'Entra con tu <b>correo</b> y la <b>clave</b> que creaste con tu invitación.',
        pantalla: () => ui.celular({ sinCabecera: true, contenido: ui.login() }),
        escribir: [{ campo: 'correo', texto: 'ana.soto@ejemplo.cl' }, { campo: 'clave', texto: '••••••••••' }],
        toque: 'ingresar',
      },
      {
        titulo: 'Tu saldo de luz',
        texto: 'Arriba ves si <b>debes algo por luz</b>, si estás al día o si tienes saldo a favor. Abajo, los <b>períodos publicados</b>: solo aparecen cuando la administración los publica.',
        pantalla: () => ui.celular({ rol: 'Comunero', contenido: ui.misLiquidaciones({ conRifa: false }) }),
        toque: 'periodo-0',
      },
      {
        titulo: 'Tu consumo y tu cobro',
        texto: 'En el detalle ves <b>tu consumo</b> (lectura anterior, actual y kWh, y cuándo se leyó) y el <b>desglose</b>: energía, parte variable y cuota fija.',
        pantalla: () => detalleComunero(),
        toque: 'foto',
      },
      {
        titulo: 'La foto de tu medidor',
        texto: 'Si el lector tomó la foto, la ves con la <b>fecha y hora</b> en que se sacó. Así puedes comparar lo que se te cobra con lo que marca tu medidor.',
        pantalla: () => detalleComunero({ foto: true }),
      },
      {
        titulo: 'Pagado o parcial',
        texto: 'La luz se paga con tu <b>gasto común</b>. Cuando la administración registra tu pago, el mes queda <b>Pagado</b>; si pagaste una parte, queda <b>Parcial</b> con lo abonado.',
        pantalla: () => detalleComunero({ estado: 'Parcial · $20.000 de $38.450', color: 'amarillo' }),
      },
      {
        titulo: 'Tu cuenta de luz',
        texto: 'Al tocar tu saldo ves tu <b>cuenta</b>: el saldo inicial (si debías antes de la plataforma), cada mes con su estado y tus abonos con su fecha.',
        pantalla: () => ui.celular({
          rol: 'Comunero',
          contenido: `
            <p class="s-h2">Cuenta de luz · Parcela 14</p>
            <div class="s-tres"><div><p class="s-chico">Cargos</p><p class="s-mono">${clp(124430)}</p></div><div><p class="s-chico">Abonos</p><p class="s-mono s-verde">${clp(85980)}</p></div><div><p class="s-chico">Saldo</p><p class="s-mono s-rojo">${clp(38450)}</p></div></div>
            <div class="s-lista">
              <div><span>Luz Jul. 2026</span><span class="s-mono">${clp(44780)} ${badge('Pagado', 'verde')}</span></div>
              <div><span>Abono · gasto común agosto<br><span class="s-chico">10-08-2026</span></span><span class="s-mono s-verde">− ${clp(44780)}</span></div>
              <div><span>Luz Ago. 2026</span><span class="s-mono">${clp(41200)} ${badge('Pagado', 'verde')}</span></div>
              <div><span>Abono · gasto común septiembre<br><span class="s-chico">12-09-2026</span></span><span class="s-mono s-verde">− ${clp(41200)}</span></div>
              <div><span>Luz Sep. 2026</span><span class="s-mono">${clp(38450)} ${badge('Pendiente', 'gris')}</span></div>
            </div>`,
        }),
      },
    ],
  }

  C.modulos.push({
    id: 'energia',
    orden: 2,
    nombre: 'Energía (EnerCheck)',
    icono: 'energia',
    estado: 'disponible',
    resumen: 'De la lectura de los medidores al cobro de la luz de cada parcela: incorporación, lecturas, cálculo, publicación, cobranza y consulta del comunero.',
    intro: `La compañía eléctrica cobra al condominio una sola <b>boleta</b>. EFFIComunidad la reparte entre las parcelas según lo que marca
      el <b>medidor de cada una</b>: la suma de las liquidaciones es exactamente el total de la boleta, al peso. Cada mes: la administración
      carga la boleta, el <b>lector</b> toma las lecturas en terreno (incluso sin señal, con foto), se calcula, se cierra y se <b>publica</b>.
      La luz se cobra en el gasto común y cada parcela tiene su <b>cuenta corriente</b> de luz.`,
    caminosTitulo: 'Los recorridos del módulo, en orden',
    recorridos: [incorporacion, lector, ciclo, cobro, comunero],
  })
})(window.Capacitacion)
