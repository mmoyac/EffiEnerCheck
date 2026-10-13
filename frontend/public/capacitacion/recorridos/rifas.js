/*
 * Módulo Rifas: los tres caminos para comprar un número.
 *
 * Cada paso declara:
 *   titulo     nombre corto en la lista de pasos
 *   texto      explicación (HTML de confianza: solo lo escribimos nosotros)
 *   pantalla   () => HTML de la pantalla simulada (piezas en pantallas.js)
 *   escribir   [{ campo, texto }] que el motor teclea antes del toque (opcional)
 *   toque      data-t del elemento que el puntero toca al final (opcional)
 *   enfoque    data-t de un elemento que se lleva a la vista, sin tocarlo (opcional)
 *
 * Si cambia un flujo real de rifas, se actualiza aquí en el mismo cambio (spec capacitacion-plataforma).
 */
;(function (C) {
  const ui = C.ui
  const { DATOS, clp } = ui
  const PRECIO = DATOS.rifa.precio

  // ---- Camino 3: el comunero desde su portal ---------------------------------------------------
  const MEDIOS_PORTAL = ['en_linea', 'gasto_comun']
  const detalleComunero = ({ seleccion = [], medio = null, pasarela = null, capas = '' } = {}) =>
    ui.celular({
      rol: 'Comunero',
      cabExtra: `<span class="s-chip">${ui.icono('ticket')} Rifas</span>`,
      contenido: `
        ${ui.encabezadoRifa()}
        ${ui.premios()}
        <div class="s-card">
          <p class="s-fuerte">Elige tus números</p>
          ${ui.grilla({ seleccion, mios: [6] })}
          ${seleccion.length > 1 ? ui.medios({ opciones: MEDIOS_PORTAL, activo: medio }) : ''}
          ${medio === 'en_linea' ? ui.pasarelas({ numeros: seleccion, elegida: pasarela }) : ''}
        </div>`,
      capas: ui.barra({
        numeros: seleccion,
        faltante: seleccion.length > 1 && !medio ? 'Elige la forma de pago' : medio === 'en_linea' && !pasarela ? 'Elige cómo pagar' : '',
      }) + capas,
    })

  const comunero = {
    id: 'comunero',
    rol: 'Comunero',
    icono: 'casa',
    titulo: 'Desde tu portal',
    resumen: 'El propio comunero entra al portal con su correo y su clave y compra a nombre de su parcela.',
    dispositivo: 'celular',
    pagos: MEDIOS_PORTAL,
    pasos: [
      {
        titulo: 'Entrar al portal',
        texto: 'Abre el portal de tu comunidad e ingresa con tu <b>correo</b> y la <b>clave</b> que creaste con tu enlace de invitación. Si no la recuerdas, toca «¿Olvidaste tu clave?».',
        pantalla: () => ui.celular({ sinCabecera: true, contenido: ui.login() }),
        escribir: [{ campo: 'correo', texto: 'ana.soto@ejemplo.cl' }, { campo: 'clave', texto: '••••••••••' }],
        toque: 'ingresar',
      },
      {
        titulo: 'Aviso de rifa abierta',
        texto: 'Cuando hay una rifa abierta, aparece un aviso arriba de tus liquidaciones. Tócalo para ver la rifa. También puedes entrar desde <b>Rifas</b>, en la cabecera.',
        pantalla: () => ui.celular({ rol: 'Comunero', cabExtra: `<span class="s-chip">${ui.icono('ticket')} Rifas</span>`, contenido: ui.misLiquidaciones() }),
        toque: 'aviso',
      },
      {
        titulo: 'Ver premios y números',
        texto: 'Revisa el beneficiario y los premios. En la grilla, los números <b>grises</b> ya están vendidos y los de <b>contorno verde</b> son de tu parcela. Toca un número libre para elegirlo.',
        pantalla: () => detalleComunero(),
        toque: 'n-7',
      },
      {
        titulo: 'Elegir varios números',
        texto: 'Puedes elegir los que quieras. Abajo ves cuántos llevas y el total a pagar.',
        pantalla: () => detalleComunero({ seleccion: [7] }),
        toque: 'n-12',
      },
      {
        titulo: 'Forma de pago',
        texto: 'Elige cómo pagar: <b>pago en línea</b> (tarjeta, Webpay o transferencia desde tu banco, con un costo adicional) o <b>gasto común</b>, que se cobra después junto a tu gasto común. El pago en línea aparece <b>solo si tu comunidad decidió usarlo</b>, y cada rifa define qué formas acepta.',
        pantalla: () => detalleComunero({ seleccion: [7, 12] }),
        toque: 'medio-en_linea',
      },
      {
        titulo: 'Elegir con qué pagar',
        texto: 'Si tu comunidad tiene más de una pasarela, ves cada una con su <b>comisión</b> y su <b>total</b>: la comisión la cobra la pasarela y se suma al valor de los números. Si hay una sola, al tocar «Pago en línea» pasas directo al resumen.',
        pantalla: () => detalleComunero({ seleccion: [7, 12], medio: 'en_linea' }),
        toque: 'pasarela-tarjeta',
      },
      {
        titulo: 'Confirmar',
        texto: 'Con los números y la forma de pago elegidos, toca <b>Confirmar</b>.',
        pantalla: () => detalleComunero({ seleccion: [7, 12], medio: 'en_linea', pasarela: 'tarjeta' }),
        toque: 'confirmar',
      },
      {
        titulo: 'Revisar e ir a pagar',
        texto: 'Revisa los números, la comisión y el <b>total a pagar</b>. Al tocar <b>Ir a pagar</b>, tus números quedan <b>reservados 15 minutos</b> y pasas a la página de la pasarela.',
        pantalla: () => detalleComunero({
          seleccion: [7, 12], medio: 'en_linea', pasarela: 'tarjeta',
          capas: ui.modalConfirmar({ parcela: '14', numeros: [7, 12], medio: 'en_linea', pasarela: 'tarjeta', nota: 'Te llevaremos a Tarjeta o Webpay para pagar. Si no completas el pago en 15 minutos, los números se liberan.' }),
        }),
        toque: 'comprar',
      },
      {
        titulo: 'Pago aprobado',
        texto: 'Pagas en la pasarela y vuelves solo al portal. Ves el <b>resultado</b> con el número de operación. Si la pasarela todavía no confirma (una transferencia puede tardar unos minutos), la pantalla se actualiza sola.',
        pantalla: () => ui.celular({ rol: 'Comunero', contenido: ui.resultadoPago({ numeros: [7, 12] }) }),
        toque: 'ver-compras',
      },
      {
        titulo: 'Si eliges gasto común',
        texto: 'Con gasto común no pagas nada ahora: ves tu <b>folio</b>, tus números y <b>qué sigue</b>. Puedes <b>compartir</b> el comprobante por WhatsApp o guardarlo.',
        pantalla: () => ui.celular({ rol: 'Comunero', contenido: ui.agradecimiento({ folio: 'R1-015', numeros: [7, 12], parcela: '14', medio: 'gasto_comun' }) }),
        toque: 'compartir',
      },
      {
        titulo: 'Si no hay pago en línea',
        texto: 'Si tu comunidad <b>no usa pago en línea</b> (o la pasarela no está disponible en ese momento), en su lugar aparece <b>transferencia</b>: transfieres a la cuenta de la comunidad y adjuntas la <b>foto del voucher</b>. La compra queda <b>pendiente</b> hasta que la administración confirme que llegó el dinero.',
        pantalla: () => ui.celular({ rol: 'Comunero', contenido: ui.agradecimiento({ folio: 'R1-015', numeros: [7, 12], parcela: '14', medio: 'transferencia' }) }),
        enfoque: 'que-sigue',
      },
    ],
  }

  // ---- Camino 1: la portería -------------------------------------------------------------------
  const MEDIOS_STAFF = ['efectivo', 'transferencia', 'gasto_comun']
  const TABS_PORTERIA = [['vender', 'Vender'], ['buscar', 'Buscar compra'], ['caja', 'Caja']]
  const parcelaElegida = (numero, nombre) => `
    <div class="s-elegida">${ui.icono('ubicacion', 's-verde')}<div class="s-flex1"><p class="s-fuerte">Parcela ${numero}</p><p class="s-chico">${nombre}</p></div><span class="s-link">Cambiar</span></div>`
  const telefonos = (activo) => `
    <div class="s-campo">
      <p class="s-label">Teléfono para el comprobante (WhatsApp)</p>
      <div class="s-chips">
        <span class="s-chip ${activo ? 'activo' : ''}" data-t="tel-1">Pedro · 9 0000 0000</span>
        <span class="s-chip">Sin teléfono</span>
      </div>
      <div class="s-input"><span>${activo ? '9 0000 0000' : ''}</span><span class="s-placeholder">${activo ? '' : 'Ej: 9 1234 5678 (opcional)'}</span></div>
    </div>`
  const vendidosPorteria = [...DATOS.rifa.vendidos, 6, 7, 12]
  const ventaPorteria = ({ seleccion = [24], medio = null, tel = false, capas = '' } = {}) =>
    ui.celular({
      rol: 'Portería',
      contenido: `
        <p class="s-h1">${DATOS.rifa.nombre}</p>
        ${ui.pestanas(TABS_PORTERIA, 'vender')}
        <p class="s-paso">1. Parcela</p>${parcelaElegida(27, 'Pedro Muñoz')}
        <p class="s-paso">2. Números</p>${ui.grilla({ seleccion, vendidos: vendidosPorteria })}
        <p class="s-paso">3. Comprador y pago</p>
        ${ui.campo({ label: 'Nombre del comprador', id: 'comprador', valor: 'Pedro Muñoz' })}
        ${ui.medios({ opciones: MEDIOS_STAFF, activo: medio })}
        ${telefonos(tel)}`,
      capas: ui.barra({ numeros: seleccion }) + capas,
    })

  const porteria = {
    id: 'porteria',
    rol: 'Portería',
    icono: 'porteria',
    titulo: 'En la portería',
    resumen: 'Quien está de turno en la portería registra la venta con la cuenta de portería y entrega el comprobante.',
    dispositivo: 'celular',
    pagos: MEDIOS_STAFF,
    pasos: [
      {
        titulo: 'Buscar la parcela',
        texto: 'La portería entra con su cuenta compartida y llega directo a <b>Vender</b>. Escribe el número de la parcela o el nombre del propietario.',
        pantalla: () => ui.celular({
          rol: 'Portería',
          contenido: `
            <p class="s-h1">${DATOS.rifa.nombre}</p>
            ${ui.pestanas(TABS_PORTERIA, 'vender')}
            <p class="s-paso">1. Parcela</p>
            <div class="s-input s-input-buscar">${ui.icono('buscar')}<span data-escribe="parcela"></span><span class="s-placeholder">Número de parcela o propietario</span></div>
            <div class="s-resultados" data-revelar>
              <span class="s-resultado" data-t="parcela-27"><b>Parcela 27</b> — Pedro Muñoz</span>
              <span class="s-resultado"><b>Parcela 27-B</b> — Rosa Vidal</span>
            </div>`,
        }),
        escribir: [{ campo: 'parcela', texto: '27' }],
        toque: 'parcela-27',
      },
      {
        titulo: 'Elegir números',
        texto: 'Toca los números que pide el comprador. Los grises ya están vendidos: el sistema no deja vender dos veces el mismo número.',
        pantalla: () => ventaPorteria({ seleccion: [24] }),
        toque: 'n-25',
      },
      {
        titulo: 'Comprador y forma de pago',
        texto: 'Se propone al propietario como comprador, pero puede ser cualquiera, incluso alguien de fuera. <b>Efectivo</b>: recibe el dinero y queda pagado. <b>Transferencia</b>: toma la foto del voucher (obligatoria en portería). <b>Gasto común</b>: se carga a la parcela.',
        pantalla: () => ventaPorteria({ seleccion: [24, 25] }),
        toque: 'medio-efectivo',
      },
      {
        titulo: 'Teléfono para el comprobante',
        texto: 'Se sugieren los teléfonos registrados de la parcela. Elige uno para enviar el comprobante por WhatsApp, o «Sin teléfono».',
        pantalla: () => ventaPorteria({ seleccion: [24, 25], medio: 'efectivo' }),
        toque: 'tel-1',
      },
      {
        titulo: 'Confirmar',
        texto: 'Revisa el total abajo y toca <b>Confirmar</b>.',
        pantalla: () => ventaPorteria({ seleccion: [24, 25], medio: 'efectivo', tel: true }),
        toque: 'confirmar',
      },
      {
        titulo: 'Recibir el dinero y vender',
        texto: 'Con efectivo, <b>recibe el dinero antes de confirmar</b>. Luego toca <b>Comprar</b>.',
        pantalla: () => ventaPorteria({
          seleccion: [24, 25], medio: 'efectivo', tel: true,
          capas: ui.modalConfirmar({ parcela: '27', comprador: 'Pedro Muñoz', numeros: [24, 25], medio: 'efectivo', nota: 'Recibe el dinero antes de confirmar.' }),
        }),
        toque: 'comprar',
      },
      {
        titulo: 'Comprobante por WhatsApp',
        texto: 'El <b>folio</b> queda en grande. Toca <b>Enviar</b> y se abre WhatsApp con el mensaje listo: solo falta enviarlo. Sin teléfono, anota el folio en un papel o imprime el comprobante.',
        pantalla: () => ui.celular({
          rol: 'Portería',
          contenido: `
            <p class="s-ok">${ui.icono('check')} Venta registrada</p>
            ${ui.tarjetaComprobante({ folio: 'R1-016', numeros: [24, 25], parcela: '27', comprador: 'Pedro Muñoz', medio: 'efectivo', estado: 'Pagado' })}
            <div class="s-botones">
              <span class="s-btn s-btn-wsp" data-t="whatsapp">${ui.icono('mensaje')} Enviar a +56 9 0000 0000</span>
              <span class="s-btn s-btn-sec">${ui.icono('imprimir')} Imprimir</span>
              <span class="s-btn s-btn-prim">${ui.icono('mas')} Nueva venta</span>
            </div>`,
        }),
        toque: 'whatsapp',
      },
      {
        titulo: 'Caja del turno',
        texto: 'En <b>Caja</b> la portería ve lo vendido y el <b>efectivo</b> recibido, para entregarlo a la administración. La portería no anula ventas: si hubo un error, avisa a la administración.',
        pantalla: () => ui.celular({
          rol: 'Portería',
          contenido: `
            <p class="s-h1">${DATOS.rifa.nombre}</p>
            ${ui.pestanas(TABS_PORTERIA, 'caja')}
            <div class="s-kpis">
              <div class="s-kpi"><p class="s-chico">Efectivo recibido</p><p class="s-kpi-valor">${clp(14 * PRECIO)}</p></div>
              <div class="s-kpi"><p class="s-chico">Ventas</p><p class="s-kpi-valor">6</p></div>
              <div class="s-kpi"><p class="s-chico">Transferencias por confirmar</p><p class="s-kpi-valor">${clp(4 * PRECIO)}</p></div>
              <div class="s-kpi"><p class="s-chico">A gasto común</p><p class="s-kpi-valor">${clp(6 * PRECIO)}</p></div>
            </div>`,
        }),
      },
    ],
  }

  // ---- Camino 2: la administración -------------------------------------------------------------
  const TABS_ADMIN = [['compras', 'Compras (12)'], ['registrar', 'Registrar venta'], ['imputaciones', 'Gasto común (0)'], ['caja', 'Caja']]
  const kpisAdmin = (porConfirmar) => `
    <div class="s-kpis s-kpis-4">
      <div class="s-kpi"><p class="s-chico">Vendidos</p><p class="s-kpi-valor">14 / 30 · ${clp(14 * PRECIO)}</p></div>
      <div class="s-kpi"><p class="s-chico">Cobrado (efectivo y transferencias)</p><p class="s-kpi-valor">${clp(8 * PRECIO)}</p></div>
      <div class="s-kpi"><p class="s-chico">Transferencias por confirmar</p><p class="s-kpi-valor">${clp(porConfirmar * PRECIO)}</p></div>
      <div class="s-kpi"><p class="s-chico">A cargar en gasto común</p><p class="s-kpi-valor">${clp(4 * PRECIO)}</p></div>
    </div>`
  const cabeceraRifaAdmin = (porConfirmar, tab) => `
    <p class="s-link">${ui.icono('izq')} Rifas</p>
    <div class="s-entre"><div><p class="s-h1">${DATOS.rifa.nombre}</p><p class="s-muted">A beneficio de ${DATOS.rifa.beneficiario} · ${clp(PRECIO)} por número</p></div>
      <span class="s-btn s-btn-sec">${ui.icono('candado')} Cerrar rifa</span></div>
    ${kpisAdmin(porConfirmar)}
    ${ui.pestanas(TABS_ADMIN.map(([id, l]) => [id, id === 'compras' && porConfirmar ? `${l} · ${porConfirmar / 2} por confirmar` : l]), tab)}`
  const vendidosAdmin = [...vendidosPorteria, 24, 25]
  const registrarAdmin = (capas = '') => ui.escritorio({
    activo: 'Rifas',
    contenido: `
      ${cabeceraRifaAdmin(0, 'registrar')}
      <div class="s-columnas">
        <div>
          <p class="s-paso">1. Parcela</p>${parcelaElegida(8, 'Carla Díaz')}
          <p class="s-paso">2. Números</p>${ui.grilla({ seleccion: [10, 14], vendidos: vendidosAdmin, columnas: 10 })}
        </div>
        <div>
          <p class="s-paso">3. Comprador y pago</p>
          ${ui.campo({ label: 'Nombre del comprador', id: 'comprador', valor: 'Carla Díaz' })}
          ${ui.medios({ opciones: MEDIOS_STAFF, activo: 'transferencia' })}
          ${ui.voucher({ adjunto: true })}
          ${ui.barra({ numeros: [10, 14] }).replace('s-barra', 's-barra s-barra-linea')}
        </div>
      </div>`,
    capas,
  })
  const filaCompra = ({ folio, parcela, numeros, medio, estado, color, acciones = '' }) => `
    <div class="s-compra">
      <div class="s-flex1"><p class="s-fuerte"><span class="s-mono">${folio}</span> · Parcela ${parcela}</p>
        <p class="s-chico">Números ${numeros.join(', ')} · ${medio}</p>${ui.badge(estado, color)}</div>
      <div class="s-der"><p class="s-mono">${clp(numeros.length * PRECIO)}</p><div class="s-acciones">${acciones}</div></div>
    </div>`
  const comprasAdmin = (confirmada) => ui.escritorio({
    activo: 'Rifas',
    contenido: `
      ${cabeceraRifaAdmin(confirmada ? 2 : 4, 'compras')}
      ${filaCompra({
        folio: 'R1-017', parcela: 8, numeros: [10, 14], medio: 'Carla Díaz',
        estado: confirmada ? '● Transferencia · pagada' : '● Transferencia por confirmar',
        color: confirmada ? 'verde' : 'amarillo',
        acciones: confirmada ? `<span class="s-btn s-btn-ghost s-btn-sm">${ui.icono('imagen')} Voucher</span>`
          : `<span class="s-btn s-btn-sec s-btn-sm">${ui.icono('imagen')} Voucher</span><span class="s-btn s-btn-prim s-btn-sm" data-t="confirmar-pago">${ui.icono('check')} Confirmar pago</span>`,
      })}
      ${filaCompra({ folio: 'R1-016', parcela: 27, numeros: [24, 25], medio: 'Pedro Muñoz · Portería', estado: '● Efectivo · pagada', color: 'verde' })}
      ${filaCompra({ folio: 'R1-015', parcela: 14, numeros: [7, 12], medio: 'Ana Soto · Portal', estado: 'Gasto común', color: 'morado' })}`,
  })

  const administracion = {
    id: 'administracion',
    rol: 'Administración',
    icono: 'maletin',
    titulo: 'En la administración',
    resumen: 'La administración registra la compra desde su menú de Rifas, confirma los pagos por transferencia y revisa los pagos en línea.',
    dispositivo: 'escritorio',
    pagos: MEDIOS_STAFF,
    pasos: [
      {
        titulo: 'Menú Rifas',
        texto: 'En el menú lateral, dentro de <b>Comunidad</b>, entra a <b>Rifas</b>.',
        pantalla: () => ui.escritorio({
          activo: 'Dashboard',
          contenido: `<p class="s-h1">Dashboard</p><p class="s-muted">Resumen del período</p>
            <div class="s-kpis s-kpis-4">
              <div class="s-kpi"><p class="s-chico">Período</p><p class="s-kpi-valor">Sep. 2026</p></div>
              <div class="s-kpi"><p class="s-chico">Lecturas</p><p class="s-kpi-valor">53 / 53</p></div>
              <div class="s-kpi"><p class="s-chico">Total boleta</p><p class="s-kpi-valor">${clp(2148300)}</p></div>
              <div class="s-kpi"><p class="s-chico">Rifas abiertas</p><p class="s-kpi-valor">1</p></div>
            </div>`,
        }),
        toque: 'menu-rifas',
      },
      {
        titulo: 'Elegir la rifa',
        texto: 'Aquí están todas las rifas del condominio. Abre la que está en curso.',
        pantalla: () => ui.escritorio({
          activo: 'Rifas',
          contenido: `<div class="s-entre"><p class="s-h1">Rifas solidarias</p><span class="s-btn s-btn-prim">${ui.icono('mas')} Nueva rifa</span></div>
            <div class="s-tabla">
              <p class="s-tabla-cab"><span>Rifa</span><span>Vendidos</span><span>Recaudado</span><span>Estado</span></p>
              <p class="s-tabla-fila" data-t="rifa-1"><span><b>${DATOS.rifa.nombre}</b></span><span>14 / 30</span><span class="s-mono">${clp(14 * PRECIO)}</span><span>${ui.badge('● Abierta', 'verde')}</span></p>
              <p class="s-tabla-fila"><span>Rifa día del niño</span><span>100 / 100</span><span class="s-mono">${clp(150000)}</span><span>${ui.badge('Cerrada', 'gris')}</span></p>
            </div>`,
        }),
        toque: 'rifa-1',
      },
      {
        titulo: 'Registrar venta',
        texto: 'Arriba ves lo vendido, lo cobrado y lo pendiente. Para registrar una compra (alguien que llamó o vino a la oficina), usa la pestaña <b>Registrar venta</b>.',
        pantalla: () => ui.escritorio({ activo: 'Rifas', contenido: cabeceraRifaAdmin(0, 'compras') + filaCompra({ folio: 'R1-016', parcela: 27, numeros: [24, 25], medio: 'Pedro Muñoz · Portería', estado: '● Efectivo · pagada', color: 'verde' }) }),
        toque: 'tab-registrar',
      },
      {
        titulo: 'Parcela, números y pago',
        texto: 'Es el mismo panel de la portería: <b>parcela</b>, <b>números</b>, comprador y <b>forma de pago</b>. Con transferencia puedes adjuntar la foto del voucher. Luego toca <b>Confirmar</b>.',
        pantalla: () => registrarAdmin(),
        toque: 'confirmar',
      },
      {
        titulo: 'Comprar',
        texto: 'Revisa el resumen y toca <b>Comprar</b>. La compra queda a nombre de la parcela.',
        pantalla: () => registrarAdmin(ui.modalConfirmar({ parcela: '8', comprador: 'Carla Díaz', numeros: [10, 14], medio: 'transferencia', nota: 'Queda pendiente hasta que la administración confirme la transferencia.' })),
        toque: 'comprar',
      },
      {
        titulo: 'Confirmar transferencias',
        texto: 'Las transferencias quedan <b>por confirmar</b>, también las que hacen los comuneros desde su portal. Revisa el voucher y, cuando el dinero llegue a la cuenta, toca <b>Confirmar pago</b>.',
        pantalla: () => comprasAdmin(false),
        toque: 'confirmar-pago',
      },
      {
        titulo: 'Pago confirmado',
        texto: 'La compra queda <b>pagada</b>. Al <b>cerrar la rifa</b>, las compras con gasto común generan un cargo por parcela para cargar en Comunidad Feliz. El sorteo se hace fuera del sistema, con la lista de compradores.',
        pantalla: () => comprasAdmin(true),
      },
      {
        titulo: 'Pago en línea: lo decide la comunidad',
        texto: `El pago en línea es <b>opcional</b> y se usa <b>solo si la comunidad lo decide</b> (por ejemplo, en asamblea o por acuerdo del comité).
          La pasarela es una cuenta <b>de la propia comunidad</b> en Flow, Khipu u otro proveedor, con su contrato y su comisión, que paga el comunero
          que elige pagar así. Si la comunidad no lo aprueba, todo sigue funcionando con efectivo, transferencia y gasto común.
          Con el acuerdo y la cuenta abierta, pide al equipo de EFFIComunidad que la configure.`,
        pantalla: () => ui.escritorio({
          activo: 'Pasarelas de pago',
          contenido: `<p class="s-h1">${ui.icono('tarjeta', 's-verde')} Pasarelas de pago</p>
            <p class="s-muted">Las configura el equipo de la plataforma. Aquí ves cuáles están activas y su comisión.</p>
            <div class="s-caja" data-t="decision">
              <p class="s-fuerte">${ui.icono('usuarios', 's-verde')} Antes de usar pago en línea</p>
              <p class="s-texto">1. La comunidad decide usarlo y acepta que el comunero pague la comisión.</p>
              <p class="s-texto">2. La comunidad abre su cuenta en la pasarela (Flow, Khipu u otra).</p>
              <p class="s-texto">3. El equipo de EFFIComunidad la configura y la prueba.</p>
              <p class="s-texto">4. La administración marca <b>Pago en línea</b> en cada rifa que lo acepte.</p>
            </div>
            <p class="s-muted">Tu comunidad aún no tiene pasarelas de pago.</p>`,
        }),
        enfoque: 'decision',
      },
      {
        titulo: 'Activarlo en la rifa',
        texto: 'Con la pasarela lista, el pago en línea se habilita <b>rifa por rifa</b>: al crear o editar la rifa, marca <b>Pago en línea</b> en las formas de pago. Deja también los <b>datos para transferir</b>: si la pasarela no está disponible, el comunero verá la transferencia manual con voucher.',
        pantalla: () => ui.escritorio({
          activo: 'Rifas',
          contenido: `<p class="s-h1">Editar rifa</p>
            <div class="s-campo"><p class="s-label">Formas de pago aceptadas</p>
              <div class="s-chips">
                <span class="s-chip activo">${ui.icono('billete')} Efectivo</span>
                <span class="s-chip activo">${ui.icono('banco')} Transferencia</span>
                <span class="s-chip activo">${ui.icono('boleta')} Gasto común</span>
                <span class="s-chip" data-t="marcar-en-linea">${ui.icono('tarjeta')} Pago en línea</span>
              </div>
              <p class="s-chico">Pago en línea: el comunero paga desde el portal con las pasarelas activas de la comunidad (con costo adicional).</p>
            </div>
            <div class="s-campo"><p class="s-label">Datos para transferir</p><p class="s-pre s-caja">${DATOS.rifa.transferencia}</p></div>`,
        }),
        toque: 'marcar-en-linea',
      },
      {
        titulo: 'Pagos en línea',
        texto: 'Lo que los comuneros pagan <b>en línea</b> se confirma solo, sin voucher. En <b>Pasarelas de pago</b> ves las pasarelas de tu comunidad y su comisión (las configura el equipo de EFFIComunidad).',
        pantalla: () => ui.escritorio({
          activo: 'Pasarelas de pago',
          contenido: `<p class="s-h1">${ui.icono('tarjeta', 's-verde')} Pasarelas de pago</p>
            <p class="s-muted">Las configura el equipo de la plataforma. Aquí ves cuáles están activas y su comisión.</p>
            <div class="s-fila-card"><div><p class="s-fuerte">Tarjeta o Webpay</p><p class="s-chico">Flow · 3,8 %</p></div>
              <div class="s-der">${ui.badge('Producción', 'azul')} ${ui.badge('● Activa', 'verde')}</div></div>
            <div class="s-fila-card"><div><p class="s-fuerte">Transferencia bancaria</p><p class="s-chico">Khipu · 1,5 %</p></div>
              <div class="s-der">${ui.badge('Producción', 'azul')} ${ui.badge('● Activa', 'verde')}</div></div>`,
        }),
        enfoque: 'menu-pasarelas',
      },
      {
        titulo: 'Pagos por revisar',
        texto: 'Si una pasarela aprueba un pago que no se puede aplicar (por ejemplo, porque esos números ya se vendieron), aparece en <b>Pagos por revisar</b>. Resuélvelo con el comunero (otros números o la devolución en la pasarela) y toca <b>Marcar resuelto</b> con una nota.',
        pantalla: () => ui.escritorio({
          activo: 'Pasarelas de pago',
          contenido: `<p class="s-h1">${ui.icono('alerta', 's-amarillo')} Pagos por revisar</p>
            <div class="s-card"><div class="s-entre"><p class="s-fuerte">Ana Soto</p><b class="s-mono">${clp(ui.conComision(2 * PRECIO, 3.8))}</b></div>
              <p class="s-chico">${DATOS.rifa.nombre} – números 7, 12</p>
              <p class="s-texto s-amarillo">Pago aprobado sin aplicar: números ya vendidos a otra compra: 12</p>
              <div class="s-acciones"><span class="s-btn s-btn-sec s-btn-sm" data-t="resolver">Marcar resuelto</span></div></div>`,
        }),
        toque: 'resolver',
      },
    ],
  }

  C.modulos.push({
    id: 'rifas',
    orden: 3,
    nombre: 'Rifas solidarias',
    icono: 'ticket',
    estado: 'disponible',
    resumen: 'Colectas con rifa para ayudar a un vecino o a una causa de la comunidad: venta de números, pagos y cierre.',
    intro: `Una <b>rifa solidaria</b> reúne fondos para un vecino o una causa de la comunidad. Cada número queda a nombre de una
      <b>parcela</b> y recibe un <b>folio</b> (por ejemplo, <span class="mono">R1-015</span>) que sirve de comprobante. El sistema no deja vender dos veces el mismo número.`,
    caminosTitulo: 'Hay 3 maneras de comprar un número',
    pagos: [
      { medio: 'efectivo', nombre: 'Efectivo', quien: 'Portería y administración', estado: 'Queda pagado al momento.' },
      { medio: 'transferencia', nombre: 'Transferencia', quien: 'Portería y administración. El comunero, solo si no hay pago en línea', estado: 'Queda pendiente hasta que la administración confirma que llegó el dinero. Se exige la foto del voucher.' },
      { medio: 'gasto_comun', nombre: 'Gasto común', quien: 'Los tres caminos', estado: 'No se paga en el momento: al cerrar la rifa se carga en un próximo gasto común de la parcela.' },
      { medio: 'en_linea', nombre: 'Pago en línea', quien: 'El comunero desde su portal, solo si la comunidad decidió usarlo', estado: 'Con tarjeta, Webpay o transferencia desde el banco, más la comisión de la pasarela. Queda pagado en cuanto la pasarela lo confirma.' },
    ],
    notaPagos: 'Cada rifa define qué formas de pago acepta, así que puede que no las veas todas. El pago en línea es opcional: existe solo si la comunidad decide usarlo y abre su cuenta en una pasarela.',
    recorridos: [porteria, administracion, comunero],
  })
})(window.Capacitacion)
