/*
 * Piezas del portal simulado para los recorridos de capacitación.
 *
 * Imitan las pantallas reales del portal (tema oscuro, acento verde) con datos ficticios. No llaman a
 * la API ni leen nada del navegador. Cuando cambia una pantalla real, se ajusta aquí su imitación.
 *
 * Convenciones que usa el motor (motor.js):
 *   data-t="<id>"        elemento que el puntero puede tocar en un paso (paso.toque)
 *   data-escribe="<id>"  campo donde el motor "escribe" texto (paso.escribir)
 *   data-revelar         aparece recién cuando termina la escritura del paso
 */
window.Capacitacion = window.Capacitacion || { modulos: [], plataforma: null }

;(function (C) {
  // ---- Íconos (trazos de lucide, MIT) ---------------------------------------------------------
  const TRAZOS = {
    ticket: '<path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/><path d="M13 5v2"/><path d="M13 17v2"/><path d="M13 11v2"/>',
    comunidad: '<path d="M18 21a8 8 0 0 0-16 0"/><circle cx="10" cy="8" r="5"/><path d="M22 20c0-3.37-2-6.5-4-8a5 5 0 0 0-.45-8.3"/>',
    energia: '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>',
    escudo: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
    casa: '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    celular: '<rect width="14" height="20" x="5" y="2" rx="2"/><path d="M12 18h.01"/>',
    notebook: '<path d="M20 16V7a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v9m16 0H4m16 0 1.28 2.55a1 1 0 0 1-.9 1.45H3.62a1 1 0 0 1-.9-1.45L4 16"/>',
    play: '<polygon points="6 3 20 12 6 21 6 3"/>',
    pausa: '<rect x="14" y="4" width="4" height="16" rx="1"/><rect x="6" y="4" width="4" height="16" rx="1"/>',
    izq: '<path d="m15 18-6-6 6-6"/>',
    der: '<path d="m9 18 6-6-6-6"/>',
    reiniciar: '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
    check: '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    corazon: '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',
    reloj: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    boleta: '<path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/><path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/><path d="M12 17.5v-11"/>',
    banco: '<line x1="3" x2="21" y1="22" y2="22"/><line x1="6" x2="6" y1="18" y2="11"/><line x1="10" x2="10" y1="18" y2="11"/><line x1="14" x2="14" y1="18" y2="11"/><line x1="18" x2="18" y1="18" y2="11"/><polygon points="12 2 20 7 4 7"/>',
    billete: '<rect width="20" height="12" x="2" y="6" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/>',
    buscar: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    compartir: '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" x2="15.42" y1="13.51" y2="17.49"/><line x1="15.41" x2="8.59" y1="6.51" y2="10.49"/>',
    imprimir: '<path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 9V3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v6"/><rect x="6" y="14" width="12" height="8" rx="1"/>',
    mensaje: '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
    mas: '<path d="M5 12h14"/><path d="M12 5v14"/>',
    imagen: '<rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>',
    trofeo: '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
    ayuda: '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
    mundo: '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
    candado: '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    porteria: '<path d="M13 4h3a2 2 0 0 1 2 2v14"/><path d="M2 20h3"/><path d="M13 20h9"/><path d="M10 12v.01"/><path d="M13 4.562v16.157a1 1 0 0 1-1.242.97L5 20V5.562a2 2 0 0 1 1.515-1.94l4-1A2 2 0 0 1 13 4.561Z"/>',
    maletin: '<path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/><rect width="20" height="14" x="2" y="6" rx="2"/>',
    medidor: '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
    panel: '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
    documento: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    ubicacion: '<path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>',
    usuarios: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    camara: '<path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3"/>',
    nube: '<path d="m2 2 20 20"/><path d="M5.782 5.782A7 7 0 0 0 9 19h8.5a4.5 4.5 0 0 0 1.307-.193"/><path d="M21.532 16.5A4.5 4.5 0 0 0 17.5 10h-1.79A7.008 7.008 0 0 0 10 5.07"/>',
    subir: '<path d="M12 13v8"/><path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/><path d="m8 17 4-4 4 4"/>',
    descargar: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
    planilla: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M8 13h2"/><path d="M14 13h2"/><path d="M8 17h2"/><path d="M14 17h2"/>',
    ruta: '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
    billetera: '<path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1"/><path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/>',
    alerta: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    calculadora: '<rect width="16" height="20" x="4" y="2" rx="2"/><line x1="8" x2="16" y1="6" y2="6"/><line x1="16" x2="16" y1="14" y2="18"/><path d="M16 10h.01M12 10h.01M8 10h.01M12 14h.01M8 14h.01M12 18h.01M8 18h.01"/>',
  }
  /** Ícono en línea; decorativo salvo que se le dé un título. */
  function icono(nombre, clase = '', titulo = '') {
    const aria = titulo ? `role="img" aria-label="${titulo}"` : 'aria-hidden="true"'
    return `<svg class="ico ${clase}" ${aria} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${TRAZOS[nombre] || ''}</svg>`
  }

  const clp = (n) => '$' + Number(n).toLocaleString('es-CL')

  // ---- Datos ficticios compartidos -------------------------------------------------------------
  const DATOS = {
    condominio: 'Los Aromos',
    rifa: {
      nombre: 'Rifa solidaria familia Rojas',
      beneficiario: 'la familia Rojas',
      precio: 2000,
      cantidad: 30,
      vendidos: [2, 3, 5, 9, 11, 16, 18, 21, 22, 28],
      premios: ['Canasta familiar', 'Gift card de $30.000', 'Kit de jardinería'],
      transferencia: 'Banco Ejemplo · Cuenta vista 000-000-000\nComunidad Los Aromos · RUT 11.111.111-1\npagos@ejemplo.cl',
    },
  }

  // ---- Armazón de las pantallas ---------------------------------------------------------------
  function cabecera({ rol = 'Comunero', extra = '' } = {}) {
    return `
      <header class="s-cab">
        <div class="s-marca"><span class="s-logo">${icono('comunidad')}</span>
          <div><p class="s-marca-nombre">${DATOS.condominio}</p><p class="s-marca-sub">EFFIComunidad</p></div>
        </div>
        <div class="s-cab-der">${extra}<span class="s-badge s-badge-rol">${rol}</span><span class="s-ayuda">${icono('ayuda')}</span></div>
      </header>`
  }

  /** Pantalla de celular: cabecera + contenido desplazable + capas (barra fija, modal). */
  function celular({ rol, contenido, capas = '', cabExtra = '', sinCabecera = false }) {
    return `
      <div class="sim sim-cel">
        <div class="s-estado"><span>9:41</span><span class="s-estado-der">●●● ▮</span></div>
        ${sinCabecera ? '' : cabecera({ rol, extra: cabExtra })}
        <div class="s-scroll">${contenido}</div>
        ${capas}
      </div>`
  }

  const MENU_ADMIN = [
    { grupo: null, items: [['panel', 'Dashboard']] },
    { grupo: 'Energía', items: [['documento', 'Boletas'], ['medidor', 'Lecturas'], ['calculadora', 'Cobranza']] },
    { grupo: 'Comunidad', items: [['ticket', 'Rifas']] },
    { grupo: 'Administración', items: [['usuarios', 'Usuarios'], ['ubicacion', 'Parcelas']] },
  ]

  /** Pantalla de escritorio de la administración: menú lateral + contenido. */
  function escritorio({ activo, contenido, capas = '' }) {
    const menu = MENU_ADMIN.map(({ grupo, items }) => `
      <div class="s-side-grupo">
        ${grupo ? `<p class="s-side-titulo">${grupo}</p>` : ''}
        ${items.map(([ic, label]) => `
          <span class="s-side-item ${label === activo ? 'activo' : ''}" data-t="menu-${label.toLowerCase()}">${icono(ic)} ${label}</span>`).join('')}
      </div>`).join('')
    return `
      <div class="sim sim-esc">
        <aside class="s-side">
          <div class="s-marca"><span class="s-logo">${icono('comunidad')}</span>
            <div><p class="s-marca-nombre">${DATOS.condominio}</p><p class="s-marca-sub">EFFIComunidad</p></div>
          </div>
          ${menu}
        </aside>
        <div class="s-main">
          <header class="s-cab s-cab-esc"><span></span>
            <div class="s-cab-der"><span class="s-usuario">Administración</span><span class="s-badge s-badge-rol">Administrador</span><span class="s-ayuda">${icono('ayuda')}</span></div>
          </header>
          <div class="s-scroll">${contenido}</div>
        </div>
        ${capas}
      </div>`
  }

  // ---- Piezas -----------------------------------------------------------------------------------
  function campo({ label, id, valor = '', placeholder = '', tipo = '' }) {
    return `
      <div class="s-campo">
        <p class="s-label">${label}</p>
        <div class="s-input ${tipo}"><span data-escribe="${id}">${valor}</span><span class="s-placeholder">${valor ? '' : placeholder}</span></div>
      </div>`
  }

  function login() {
    return `
      <div class="s-login">
        <div class="s-login-logo">${icono('comunidad')}</div>
        <p class="s-login-nombre">EFFIComunidad</p>
        <p class="s-muted s-centro">Portal de la comunidad</p>
        <div class="s-card s-login-card">
          <p class="s-h2">Iniciar sesión</p>
          ${campo({ label: 'Correo electrónico', id: 'correo', placeholder: 'usuario@ejemplo.cl' })}
          ${campo({ label: 'Contraseña', id: 'clave', placeholder: '••••••••' })}
          <span class="s-btn s-btn-prim s-btn-full" data-t="ingresar">Ingresar</span>
          <p class="s-link s-centro">¿Olvidaste tu clave? ¿Primera vez?</p>
        </div>
      </div>`
  }

  function avisoRifa() {
    const r = DATOS.rifa
    return `
      <div class="s-aviso" data-t="aviso">
        ${icono('ticket', 's-verde')}
        <div class="s-flex1"><p class="s-fuerte">${r.nombre}</p><p class="s-chico">Rifa solidaria a beneficio de ${r.beneficiario} · Toca para comprar números</p></div>
        ${icono('der', 's-verde')}
      </div>`
  }

  /** Inicio del comunero: aviso de rifa, su saldo de luz y los períodos publicados. */
  function misLiquidaciones({ conRifa = true, saldo = 38450 } = {}) {
    const periodos = [['Sep. 2026', 38450, 'Pendiente', 'amarillo'], ['Ago. 2026', 41200, 'Pagado', 'verde'], ['Jul. 2026', 44780, 'Pagado', 'verde']]
    return `
      ${conRifa ? avisoRifa() : ''}
      <p class="s-h1">Mis liquidaciones</p>
      <p class="s-muted">Selecciona un período para ver el detalle</p>
      <div class="s-aviso ${saldo > 0 ? 's-aviso-amarillo' : ''}" data-t="saldo">
        ${icono('boleta', saldo > 0 ? 's-amarillo' : 's-verde')}
        <div class="s-flex1"><p class="s-fuerte">${saldo > 0 ? `Debes ${clp(saldo)} por luz` : 'Estás al día con la luz'}</p>
          <p class="s-chico">Toca para ver tu cuenta: cargos, abonos y estado de cada mes</p></div>
        ${icono('der')}
      </div>
      ${periodos.map(([p, m, e, color], i) => `
        <div class="s-fila-card" data-t="periodo-${i}"><div><p class="s-fuerte">${p}</p><p class="s-chico">Parcela 14</p></div>
          <div class="s-der"><p class="s-mono">${clp(m)}</p><span class="s-badge s-badge-${color}">${e}</span></div></div>`).join('')}`
  }

  function encabezadoRifa({ volver = 'Volver a rifas' } = {}) {
    const r = DATOS.rifa
    return `
      <p class="s-link">${icono('izq')} ${volver}</p>
      <div class="s-entre"><p class="s-h1">${r.nombre}</p><span class="s-badge s-badge-verde">● Abierta</span></div>
      <p class="s-texto">${icono('corazon', 's-verde')} A beneficio de ${r.beneficiario}</p>
      <p class="s-muted">${clp(r.precio)} por número · ${r.vendidos.length} de ${r.cantidad} vendidos</p>`
  }

  function premios() {
    return `
      <div class="s-card">
        <p class="s-fuerte">${icono('trofeo', 's-amarillo')} Premios</p>
        <ol class="s-premios">${DATOS.rifa.premios.map((p) => `<li>${p}</li>`).join('')}</ol>
      </div>`
  }

  /** Grilla de números: vendidos (no disponibles), de mi parcela y seleccionados. */
  function grilla({ seleccion = [], mios = [], vendidos = DATOS.rifa.vendidos, columnas = 6 } = {}) {
    let celdas = ''
    for (let n = 1; n <= DATOS.rifa.cantidad; n++) {
      const estado = seleccion.includes(n) ? 'sel' : mios.includes(n) ? 'mio' : vendidos.includes(n) ? 'vendido' : ''
      celdas += `<span class="s-num ${estado}" data-t="n-${n}">${n}</span>`
    }
    return `
      <div class="s-grilla" style="--cols:${columnas}">${celdas}</div>
      <div class="s-leyenda"><span><i class="s-num-mini"></i>Disponible</span><span><i class="s-num-mini sel"></i>Elegido</span><span><i class="s-num-mini mio"></i>De tu parcela</span><span><i class="s-num-mini vendido"></i>Vendido</span></div>`
  }

  const MEDIOS = {
    efectivo: ['billete', 'Efectivo', 'Pagado ahora'],
    transferencia: ['banco', 'Transferencia', 'A la cuenta de la comunidad'],
    gasto_comun: ['boleta', 'Gasto común', 'Se carga en el gasto común'],
  }
  function medios({ opciones, activo }) {
    return `
      <div class="s-campo">
        <p class="s-label">Forma de pago</p>
        <div class="s-medios" style="--cols:${opciones.length}">
          ${opciones.map((m) => {
            const [ic, nombre, ayuda] = MEDIOS[m]
            return `<span class="s-medio ${m === activo ? 'activo' : ''}" data-t="medio-${m}">${icono(ic)}<b>${nombre}</b><small>${ayuda}</small></span>`
          }).join('')}
        </div>
      </div>`
  }

  function datosTransferencia() {
    return `
      <div class="s-caja"><p class="s-mini-titulo">Datos para transferir</p><p class="s-pre">${DATOS.rifa.transferencia}</p></div>`
  }

  function voucher({ adjunto = false } = {}) {
    return adjunto
      ? `<div class="s-voucher ok">${icono('imagen')} voucher.jpg <span class="s-chico">· listo</span></div>`
      : `<div class="s-voucher" data-t="voucher">${icono('imagen')} Foto del voucher</div>`
  }

  /** Barra inferior con el resumen de la selección y el botón Confirmar. */
  function barra({ numeros, faltante = '' }) {
    if (!numeros.length) return ''
    const n = numeros.length
    return `
      <div class="s-barra">
        <div><p class="s-fuerte">${n} ${n === 1 ? 'número' : 'números'} · ${clp(n * DATOS.rifa.precio)}</p>
          <p class="s-chico">${faltante || numeros.join(', ')}</p></div>
        <span class="s-btn s-btn-prim" data-t="confirmar">${icono('ticket')} Confirmar</span>
      </div>`
  }

  function modalConfirmar({ parcela, numeros, medio, comprador = '', nota }) {
    const n = numeros.length
    return `
      <div class="s-velo">
        <div class="s-modal">
          <p class="s-h2">Confirmar compra</p>
          <div class="s-caja s-resumen">
            <p><span>Parcela</span><b>${parcela}</b></p>
            ${comprador ? `<p><span>Comprador</span><b>${comprador}</b></p>` : ''}
            <p><span>Números</span><b class="s-mono">${numeros.join(', ')}</b></p>
            <p><span>Pago</span><b>${MEDIOS[medio][1]}</b></p>
            <p><span>${n} × ${clp(DATOS.rifa.precio)}</span><b class="s-total">${clp(n * DATOS.rifa.precio)}</b></p>
          </div>
          <p class="s-chico">${nota}</p>
          <div class="s-acciones"><span class="s-btn s-btn-ghost">Cancelar</span><span class="s-btn s-btn-prim" data-t="comprar">Comprar</span></div>
        </div>
      </div>`
  }

  function tarjetaComprobante({ folio, numeros, parcela, medio, comprador = '', estado }) {
    const n = numeros.length
    return `
      <div class="s-comprobante">
        <p class="s-muted">${DATOS.rifa.nombre}</p>
        <p class="s-mini-titulo">Folio</p>
        <p class="s-folio">${folio}</p>
        <p class="s-mini-titulo">${n === 1 ? 'Número' : 'Números'}</p>
        <p class="s-numeros">${numeros.join(' · ')}</p>
        <div class="s-resumen">
          <p><span>Parcela</span><b>${parcela}</b></p>
          ${comprador ? `<p><span>Comprador</span><b>${comprador}</b></p>` : ''}
          <p><span>Monto</span><b class="s-mono">${clp(n * DATOS.rifa.precio)}</b></p>
          <p><span>Pago</span><b>${MEDIOS[medio][1]}</b></p>
          ${estado ? `<p class="s-centro s-chico">${estado}</p>` : ''}
        </div>
      </div>`
  }

  /** Pantalla de agradecimiento del comunero tras comprar desde su portal. */
  function agradecimiento({ folio, numeros, parcela, medio }) {
    const total = clp(numeros.length * DATOS.rifa.precio)
    const sigue = medio === 'gasto_comun'
      ? `<p class="s-texto">${icono('boleta', 's-verde')} No tienes que pagar nada ahora: ${total} se cargarán en un próximo gasto común de tu parcela, cuando se cierre la rifa.</p>`
      : `<p class="s-texto">${icono('banco', 's-verde')} Transfiere ${total} y guarda el comprobante de tu banco.</p>
         ${datosTransferencia()}
         <p class="s-texto s-amarillo">${icono('reloj')} Tu compra queda pendiente hasta que la administración confirme la transferencia.</p>`
    return `
      <div class="s-gracias">
        <div class="s-gracias-ico">${icono('corazon')}</div>
        <p class="s-h1 s-centro">¡Gracias por tu aporte!</p>
        <p class="s-muted s-centro">Tu compra ayuda a <b>${DATOS.rifa.beneficiario}</b>.</p>
      </div>
      ${tarjetaComprobante({ folio, numeros, parcela, medio })}
      <div class="s-card" data-t="que-sigue"><p class="s-fuerte">Qué sigue</p>${sigue}</div>
      <div class="s-botones">
        <span class="s-btn s-btn-sec" data-t="compartir">${icono('compartir')} Compartir</span>
        <span class="s-btn s-btn-sec">${icono('imprimir')} Guardar</span>
        <span class="s-btn s-btn-prim">${icono('mas')} Comprar más números</span>
        <span class="s-btn s-btn-ghost">${icono('izq')} Volver a rifas</span>
      </div>`
  }

  function pestanas(lista, activa) {
    return `<div class="s-tabs">${lista.map(([id, label]) => `<span class="s-tab ${id === activa ? 'activa' : ''}" data-t="tab-${id}">${label}</span>`).join('')}</div>`
  }

  function badge(texto, color) {
    return `<span class="s-badge s-badge-${color}">${texto}</span>`
  }

  C.ui = {
    icono, clp, DATOS, celular, escritorio, campo, login, avisoRifa, misLiquidaciones, encabezadoRifa, premios,
    grilla, medios, datosTransferencia, voucher, barra, modalConfirmar, tarjetaComprobante, agradecimiento,
    pestanas, badge,
  }
})(window.Capacitacion)
