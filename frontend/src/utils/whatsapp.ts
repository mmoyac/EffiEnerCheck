/** Abre WhatsApp (app o web) con el destinatario y el mensaje listos; el envío lo confirma la persona. */
export function urlWhatsApp(telefono: string, mensaje: string): string {
  return `https://wa.me/${telefono}?text=${encodeURIComponent(mensaje)}`
}

/** Mensaje de invitación al portal: mismo enlace que el correo (vence en 7 días, un solo uso). */
export function mensajeInvitacion(nombre: string, condominio: string, enlace: string): string {
  return [
    `Hola ${nombre}:`,
    '',
    `Te invitamos al portal de *${condominio}*, donde podrás revisar tus cobros y participar en las actividades de la comunidad.`,
    '',
    'Crea tu clave en este enlace (vence en 7 días y sirve una sola vez):',
    enlace,
    '',
    'Tu usuario es tu correo electrónico.',
  ].join('\n')
}
