/*
 * Portada de la capacitación: qué es EFFIComunidad, sus productos, sus roles y los módulos que aún
 * no tienen recorridos ("próximamente").
 *
 * Para agregar un módulo nuevo: crea recorridos/<modulo>.js (ver rifas.js), cárgalo en index.html y
 * quita aquí su entrada "próximamente". Un módulo nuevo de la plataforma siempre aparece en esta
 * página, aunque sea como "próximamente".
 */
;(function (C) {
  C.plataforma = {
    nombre: 'EFFIComunidad',
    lema: 'La plataforma de tu comunidad',
    productos: [
      {
        icono: 'mundo',
        nombre: 'Sitio público',
        texto: 'La página web del condominio: quiénes son, avisos, espacios, documentos públicos y contacto. La ve cualquiera, sin iniciar sesión, y tiene el botón de acceso al portal.',
      },
      {
        icono: 'candado',
        nombre: 'Portal de la comunidad',
        texto: 'Donde cada persona entra con su correo y su clave. Muestra solo lo que le corresponde según su rol y los módulos que el condominio contrató.',
      },
    ],
    roles: [
      {
        icono: 'casa',
        nombre: 'Comunero',
        texto: 'Vecino de una o más parcelas. Consulta sus liquidaciones de energía y compra números de rifa desde su celular.',
        modulos: ['energia', 'rifas'],
      },
      {
        icono: 'maletin',
        nombre: 'Administración',
        texto: 'La administración del condominio, sea de la comunidad o externa. Carga las boletas, calcula y publica los cobros, gestiona rifas, usuarios y parcelas.',
        modulos: ['nucleo', 'energia', 'rifas'],
      },
      {
        icono: 'porteria',
        nombre: 'Portería',
        texto: 'Cuenta compartida por los turnos de la portería. Solo vende números de rifa y entrega el comprobante.',
        modulos: ['rifas'],
      },
      {
        icono: 'medidor',
        nombre: 'Lector',
        texto: 'Recorre las parcelas y registra la lectura de cada remarcador. Funciona incluso sin señal.',
        modulos: ['energia'],
      },
    ],
  }

  C.modulos.push(
    {
      id: 'nucleo',
      orden: 1,
      nombre: 'Acceso y cuentas',
      icono: 'candado',
      estado: 'proximamente',
      resumen: 'Crear tu clave con la invitación, recuperarla si la olvidas, y para la administración: usuarios y parcelas.',
    },
    {
      id: 'energia',
      orden: 2,
      nombre: 'Energía (EnerCheck)',
      icono: 'energia',
      estado: 'proximamente',
      resumen: 'De la boleta eléctrica al cobro de cada parcela: carga de la boleta, lecturas, cálculo, publicación y consulta del comunero.',
    },
  )
})(window.Capacitacion)
