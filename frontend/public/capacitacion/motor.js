/*
 * Motor del centro de capacitación: navegación por hash y reproductor de recorridos.
 *
 * Rutas:  #/                         portada (plataforma, roles, módulos)
 *         #/modulo/<id>              página del módulo (o "próximamente")
 *         #/modulo/<id>/<recorrido>  reproductor
 *         #/modulo/<id>/<recorrido>/<n>  reproductor detenido en el paso n (para enlazar un paso)
 *
 * No conoce ningún módulo en particular: todo sale de Capacitacion.modulos (recorridos/*.js).
 */
;(function (C) {
  const { icono } = C.ui
  const app = document.getElementById('app')
  const movimientoReducido = window.matchMedia('(prefers-reduced-motion: reduce)')
  const reducido = () => movimientoReducido.matches
  const modulos = () => [...C.modulos].sort((a, b) => a.orden - b.orden)
  const NOMBRE_PAGO = { efectivo: 'Efectivo', transferencia: 'Transferencia', gasto_comun: 'Gasto común' }
  const ICONO_PAGO = { efectivo: 'billete', transferencia: 'banco', gasto_comun: 'boleta' }

  const esperar = (ms) => new Promise((r) => setTimeout(r, ms))

  // ---- Navegación -------------------------------------------------------------------------------
  function ruta() {
    return location.hash.replace(/^#\/?/, '').split('/').filter(Boolean)
  }

  function render() {
    detener()
    const [seccion, moduloId, recorridoId, pasoN] = ruta()
    const modulo = seccion === 'modulo' ? C.modulos.find((m) => m.id === moduloId) : null
    if (!modulo) vistaInicio()
    else if (modulo.estado !== 'disponible') vistaProximamente(modulo)
    else {
      const recorrido = recorridoId && modulo.recorridos.find((r) => r.id === recorridoId)
      if (recorrido) vistaReproductor(modulo, recorrido, pasoN ? Number(pasoN) - 1 : null)
      else vistaModulo(modulo)
    }
    window.scrollTo(0, 0)
    const h1 = app.querySelector('h1')
    if (h1) { h1.setAttribute('tabindex', '-1'); h1.focus({ preventScroll: true }) }
  }

  const chipPago = (m) => `<span class="chip-pago">${icono(ICONO_PAGO[m])}${NOMBRE_PAGO[m]}</span>`
  const migas = (items) => `<nav class="migas" aria-label="Ruta">${items.map(([href, texto]) =>
    href ? `<a href="${href}">${texto}</a><span aria-hidden="true">/</span>` : `<span aria-current="page">${texto}</span>`).join('')}</nav>`

  // ---- Portada ----------------------------------------------------------------------------------
  function vistaInicio() {
    const p = C.plataforma
    const nombreModulo = (id) => C.modulos.find((m) => m.id === id)?.nombre.replace(/ \(.*\)$/, '') ?? id
    app.innerHTML = `
      <section class="hero">
        <p class="eyebrow">Centro de capacitación</p>
        <h1>Aprende a usar ${p.nombre}, paso a paso</h1>
        <p class="bajada">${p.lema}. Elige un módulo y mira cómo se hace cada tarea, con pantallas de ejemplo y datos ficticios.</p>
        <a class="btn btn-prim" href="#/modulo/rifas">${icono('play')} Empezar con Rifas</a>
      </section>

      <section class="bloque" aria-labelledby="t-plataforma">
        <h2 id="t-plataforma">Qué es ${p.nombre}</h2>
        <p class="sub">Dos productos que el condominio contrata por separado.</p>
        <div class="grid-2">
          ${p.productos.map((x) => `
            <article class="tarjeta"><span class="tarjeta-ico">${icono(x.icono)}</span>
              <h3>${x.nombre}</h3><p>${x.texto}</p></article>`).join('')}
        </div>
      </section>

      <section class="bloque" aria-labelledby="t-roles">
        <h2 id="t-roles">Quién hace qué</h2>
        <p class="sub">Cada persona entra al portal con un rol. El rol define qué ve y qué puede hacer.</p>
        <div class="grid-4">
          ${p.roles.map((r) => `
            <article class="tarjeta tarjeta-rol"><span class="tarjeta-ico">${icono(r.icono)}</span>
              <h3>${r.nombre}</h3><p>${r.texto}</p>
              <p class="etiquetas">${r.modulos.map((m) => `<span class="etiqueta">${nombreModulo(m)}</span>`).join('')}</p></article>`).join('')}
        </div>
      </section>

      <section class="bloque" aria-labelledby="t-modulos">
        <h2 id="t-modulos">Módulos</h2>
        <p class="sub">Elige uno para ver sus recorridos.</p>
        <div class="grid-3">
          ${modulos().map((m) => `
            <a class="tarjeta tarjeta-modulo ${m.estado}" href="#/modulo/${m.id}">
              <span class="tarjeta-ico">${icono(m.icono)}</span>
              <span class="estado">${m.estado === 'disponible' ? `${m.recorridos.length} recorridos` : 'Próximamente'}</span>
              <h3>${m.nombre}</h3><p>${m.resumen}</p>
              <span class="ir">${m.estado === 'disponible' ? 'Ver recorridos' : 'Ver qué incluirá'} ${icono('der')}</span>
            </a>`).join('')}
        </div>
      </section>`
  }

  function vistaProximamente(m) {
    app.innerHTML = `
      ${migas([['#/', 'Inicio'], [null, m.nombre]])}
      <section class="hero hero-chico">
        <span class="tarjeta-ico grande">${icono(m.icono)}</span>
        <p class="eyebrow">Próximamente</p>
        <h1>${m.nombre}</h1>
        <p class="bajada">${m.resumen}</p>
        <p class="bajada">Estamos preparando los recorridos de este módulo. Mientras tanto, revisa los que ya están disponibles.</p>
        <a class="btn btn-sec" href="#/">${icono('izq')} Volver a los módulos</a>
      </section>`
  }

  // ---- Página del módulo ------------------------------------------------------------------------
  function vistaModulo(m) {
    app.innerHTML = `
      ${migas([['#/', 'Inicio'], [null, m.nombre]])}
      <section class="hero hero-chico">
        <span class="tarjeta-ico grande">${icono(m.icono)}</span>
        <h1>${m.nombre}</h1>
        <p class="bajada">${m.intro ?? m.resumen}</p>
      </section>

      <section class="bloque" aria-labelledby="t-caminos">
        <h2 id="t-caminos">${m.caminosTitulo ?? 'Recorridos'}</h2>
        <ol class="caminos">
          ${m.recorridos.map((r, i) => `
            <li><a class="tarjeta camino" href="#/modulo/${m.id}/${r.id}">
              <span class="camino-num" aria-hidden="true">${i + 1}</span>
              <span class="tarjeta-ico">${icono(r.icono)}</span>
              <h3>${r.titulo}</h3>
              <p class="camino-rol">${icono(r.dispositivo === 'escritorio' ? 'notebook' : 'celular')} ${r.rol}</p>
              <p>${r.resumen}</p>
              <p class="etiquetas">${r.pagos.map(chipPago).join('')}</p>
              <span class="ir">${icono('play')} Ver recorrido · ${r.pasos.length} pasos</span>
            </a></li>`).join('')}
        </ol>
      </section>

      ${m.pagos ? `
      <section class="bloque" aria-labelledby="t-pagos">
        <h2 id="t-pagos">Formas de pago</h2>
        <div class="tabla-pagos" role="table">
          <div class="fila cab" role="row"><span role="columnheader">Forma</span><span role="columnheader">Quién la usa</span><span role="columnheader">Qué pasa con el pago</span></div>
          ${m.pagos.map((x) => `
            <div class="fila" role="row"><span role="cell">${chipPago(x.medio)}</span><span role="cell">${x.quien}</span><span role="cell">${x.estado}</span></div>`).join('')}
        </div>
        ${m.notaPagos ? `<p class="nota">${m.notaPagos}</p>` : ''}
      </section>` : ''}`
  }

  // ---- Reproductor ------------------------------------------------------------------------------
  let rep = null

  function detener() {
    if (!rep) return
    rep.token++
    clearTimeout(rep.temporizador)
    window.removeEventListener('resize', rep.alRedimensionar)
    document.removeEventListener('keydown', rep.alTeclear)
    rep = null
  }

  function vistaReproductor(m, r, pasoInicial) {
    const base = `#/modulo/${m.id}`
    app.innerHTML = `
      ${migas([['#/', 'Inicio'], [base, m.nombre], [null, r.titulo]])}
      <div class="rep-cab">
        <h1>${r.titulo}</h1>
        <nav class="rep-otros" aria-label="Otros recorridos">
          ${m.recorridos.map((x) => `<a href="${base}/${x.id}" ${x.id === r.id ? 'aria-current="page"' : ''}>${icono(x.icono)} ${x.rol}</a>`).join('')}
        </nav>
      </div>
      <div class="reproductor">
        <div class="escenario" id="escenario">
          <div class="dispositivo ${r.dispositivo}" id="dispositivo">
            <div class="pantalla" id="pantalla"></div>
            <div class="puntero" id="puntero" aria-hidden="true"><span class="onda"></span></div>
          </div>
        </div>
        <div class="panel">
          <div class="progreso" aria-hidden="true"><span id="barra-progreso"></span></div>
          <p class="paso-n" id="paso-n"></p>
          <h2 class="paso-titulo" id="paso-titulo"></h2>
          <p class="paso-texto" id="paso-texto" aria-live="polite"></p>
          <div class="controles" role="group" aria-label="Controles del recorrido">
            <button type="button" class="ctrl" id="c-reiniciar" title="Reiniciar">${icono('reiniciar', '', 'Reiniciar')}</button>
            <button type="button" class="ctrl" id="c-ant" title="Paso anterior (←)">${icono('izq', '', 'Paso anterior')}</button>
            <button type="button" class="ctrl ctrl-play" id="c-play"></button>
            <button type="button" class="ctrl" id="c-sig" title="Paso siguiente (→)">${icono('der', '', 'Paso siguiente')}</button>
          </div>
          <p class="ayuda-teclas">Teclado: ← → para moverte, espacio para pausar.</p>
          <ol class="lista-pasos" id="lista-pasos">
            ${r.pasos.map((p, i) => `<li><button type="button" data-paso="${i}">${p.titulo}</button></li>`).join('')}
          </ol>
          <div class="pagos-camino"><p>Formas de pago en este camino</p><p class="etiquetas">${r.pagos.map(chipPago).join('')}</p></div>
        </div>
      </div>
      <div class="fin" id="fin" hidden>
        <p>${icono('check')} Terminaste el recorrido <b>${r.titulo}</b>.</p>
        <div class="fin-acciones">
          <button type="button" class="btn btn-sec" id="f-repetir">${icono('reiniciar')} Repetir</button>
          ${m.recorridos.filter((x) => x.id !== r.id).map((x) => `<a class="btn btn-sec" href="${base}/${x.id}">${icono(x.icono)} ${x.titulo}</a>`).join('')}
          <a class="btn btn-prim" href="${base}">Volver a ${m.nombre}</a>
        </div>
      </div>`

    const $ = (id) => document.getElementById(id)
    rep = {
      r, i: 0, token: 0, temporizador: null, escala: 1,
      jugando: pasoInicial == null && !reducido(),
      pantalla: $('pantalla'), puntero: $('puntero'), dispositivo: $('dispositivo'), escenario: $('escenario'),
    }
    rep.alRedimensionar = () => { ajustarEscala(); posicionarPuntero(false) }
    rep.alTeclear = (e) => {
      if (e.target.closest('input, textarea, select')) return
      if (e.key === 'ArrowRight') { e.preventDefault(); ir(rep.i + 1) }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); ir(rep.i - 1) }
      else if (e.key === ' ' && !e.target.closest('button, a')) { e.preventDefault(); alternar() }
    }
    window.addEventListener('resize', rep.alRedimensionar)
    document.addEventListener('keydown', rep.alTeclear)
    $('c-reiniciar').onclick = () => { rep.jugando = !reducido(); ir(0) }
    $('c-ant').onclick = () => ir(rep.i - 1)
    $('c-sig').onclick = () => ir(rep.i + 1)
    $('c-play').onclick = alternar
    $('f-repetir').onclick = () => { rep.jugando = !reducido(); ir(0) }
    $('lista-pasos').onclick = (e) => {
      const b = e.target.closest('[data-paso]')
      if (b) ir(Number(b.dataset.paso))
    }
    ajustarEscala()
    ir(pasoInicial ?? 0)
  }

  /** Escala el dispositivo simulado para que quepa entero (ancho y alto) sin scroll horizontal. */
  function ajustarEscala() {
    if (!rep) return
    const d = rep.dispositivo
    const ancho = d.offsetWidth
    const alto = d.offsetHeight
    const disponible = rep.escenario.clientWidth
    const altoMax = Math.max(420, window.innerHeight - 140)
    rep.escala = Math.min(1, disponible / ancho, altoMax / alto)
    d.style.transform = `scale(${rep.escala})`
    rep.escenario.style.height = `${alto * rep.escala}px`
    d.style.left = `${Math.max(0, (disponible - ancho * rep.escala) / 2)}px`
  }

  function alternar() {
    rep.jugando = !rep.jugando
    actualizarControles()
    if (rep.jugando) {
      if (rep.i >= rep.r.pasos.length - 1 && rep.terminado) ir(0)
      else programarSiguiente()
    } else clearTimeout(rep.temporizador)
  }

  function ir(i) {
    if (!rep) return
    const max = rep.r.pasos.length - 1
    mostrar(Number.isFinite(i) ? Math.max(0, Math.min(max, i)) : 0)
  }

  function actualizarControles() {
    const play = document.getElementById('c-play')
    play.innerHTML = rep.jugando ? icono('pausa', '', 'Pausar') : icono('play', '', 'Reproducir')
    play.title = rep.jugando ? 'Pausar (espacio)' : 'Reproducir (espacio)'
    play.setAttribute('aria-pressed', String(rep.jugando))
    document.getElementById('c-ant').disabled = rep.i === 0
    document.getElementById('c-sig').disabled = rep.i === rep.r.pasos.length - 1
  }

  async function mostrar(i) {
    const tok = ++rep.token
    clearTimeout(rep.temporizador)
    rep.i = i
    rep.terminado = false
    const paso = rep.r.pasos[i]
    const total = rep.r.pasos.length

    // Panel
    document.getElementById('paso-n').textContent = `Paso ${i + 1} de ${total}`
    document.getElementById('paso-titulo').textContent = paso.titulo
    document.getElementById('paso-texto').innerHTML = paso.texto
    document.getElementById('barra-progreso').style.width = `${((i + 1) / total) * 100}%`
    document.querySelectorAll('#lista-pasos button').forEach((b, j) => {
      b.classList.toggle('hecho', j < i)
      if (j === i) b.setAttribute('aria-current', 'step')
      else b.removeAttribute('aria-current')
    })
    document.getElementById('fin').hidden = true
    actualizarControles()

    // Pantalla
    const p = rep.pantalla
    p.innerHTML = paso.pantalla()
    p.classList.remove('entra')
    if (!reducido()) { void p.offsetWidth; p.classList.add('entra') }
    rep.puntero.classList.remove('visible', 'toca')
    rep.puntero.style.transition = 'none'
    rep.puntero.style.transform = 'translate(-60px, 120%)'

    await esperar(reducido() ? 0 : 450)
    if (tok !== rep?.token) return

    for (const { campo, texto } of paso.escribir ?? []) {
      const el = p.querySelector(`[data-escribe="${campo}"]`)
      if (!el) continue
      const campoVisual = el.closest('.s-input')
      campoVisual?.classList.add('foco')
      campoVisual?.querySelector('.s-placeholder')?.replaceChildren()
      if (reducido()) el.textContent = texto
      else {
        for (const letra of texto) {
          el.textContent += letra
          await esperar(70)
          if (tok !== rep?.token) return
        }
      }
      campoVisual?.classList.remove('foco')
      await esperar(reducido() ? 0 : 250)
    }
    p.querySelectorAll('[data-revelar]').forEach((el) => el.classList.add('visible'))
    if (paso.escribir) await esperar(reducido() ? 0 : 400)
    if (tok !== rep?.token) return

    if (paso.toque) {
      await posicionarPuntero(true)
      if (tok !== rep?.token) return
    } else if (paso.enfoque) {
      const el = p.querySelector(`[data-t="${paso.enfoque}"]`)
      if (el) await llevarAVista(el, true)
      if (tok !== rep?.token) return
    }
    programarSiguiente()
  }

  /** Desplaza el contenido de la pantalla simulada para que el elemento quede a la vista. */
  async function llevarAVista(el, animar) {
    const scroll = el.closest('.s-scroll')
    if (!scroll) return
    const s = rep.escala
    const rs = scroll.getBoundingClientRect()
    const re = el.getBoundingClientRect()
    const margen = 40 * s
    let delta = 0
    if (re.bottom > rs.bottom - margen) delta = (re.bottom - rs.bottom + margen) / s
    else if (re.top < rs.top + margen) delta = (re.top - rs.top - margen) / s
    if (!delta) return
    const suave = animar && !reducido()
    scroll.scrollTo({ top: scroll.scrollTop + delta, behavior: suave ? 'smooth' : 'auto' })
    if (suave) await esperar(500)
  }

  /** Lleva el puntero al elemento del paso (desplazando la pantalla si hace falta) y lo "toca". */
  async function posicionarPuntero(animar) {
    if (!rep) return
    const paso = rep.r.pasos[rep.i]
    if (!paso.toque) return
    const tok = rep.token
    const el = rep.pantalla.querySelector(`[data-t="${paso.toque}"]`)
    if (!el) return
    const s = rep.escala
    await llevarAVista(el, animar)
    if (tok !== rep?.token) return

    const rd = rep.dispositivo.getBoundingClientRect()
    const re = el.getBoundingClientRect()
    const x = (re.left - rd.left + re.width / 2) / s
    const y = (re.top - rd.top + re.height / 2) / s
    const pt = rep.puntero
    const suave = animar && !reducido()
    pt.style.transition = suave ? 'transform 900ms cubic-bezier(.4,.1,.2,1), opacity 200ms' : 'none'
    pt.classList.add('visible')
    pt.style.transform = `translate(${x}px, ${y}px)`
    if (!animar) return
    await esperar(suave ? 1000 : 0)
    if (tok !== rep?.token) return
    pt.classList.add('toca')
    el.classList.add('s-tocado')
  }

  function programarSiguiente() {
    if (!rep || !rep.jugando) return
    const tok = rep.token
    const paso = rep.r.pasos[rep.i]
    const ultimo = rep.i === rep.r.pasos.length - 1
    // Tiempo de lectura: proporcional al texto, con un mínimo
    const lectura = Math.max(3200, paso.texto.replace(/<[^>]+>/g, '').length * 45)
    rep.temporizador = setTimeout(() => {
      if (tok !== rep?.token) return
      if (ultimo) {
        rep.jugando = false
        rep.terminado = true
        actualizarControles()
        const fin = document.getElementById('fin')
        fin.hidden = false
        fin.scrollIntoView({ behavior: reducido() ? 'auto' : 'smooth', block: 'nearest' })
      } else ir(rep.i + 1)
    }, lectura)
  }

  // ---- Tema claro/oscuro: sigue al sistema hasta que el visitante elige uno (se recuerda aquí) ----
  const botonTema = document.getElementById('tema')
  const temaGuardado = (() => { try { return localStorage.getItem('capacitacion-tema') } catch { return null } })()
  if (temaGuardado) document.documentElement.dataset.theme = temaGuardado
  botonTema.onclick = () => {
    const oscuro = document.documentElement.dataset.theme
      ? document.documentElement.dataset.theme === 'dark'
      : window.matchMedia('(prefers-color-scheme: dark)').matches
    const nuevo = oscuro ? 'light' : 'dark'
    document.documentElement.dataset.theme = nuevo
    try { localStorage.setItem('capacitacion-tema', nuevo) } catch { /* sin almacenamiento */ }
  }

  window.addEventListener('hashchange', render)
  render()
})(window.Capacitacion)
