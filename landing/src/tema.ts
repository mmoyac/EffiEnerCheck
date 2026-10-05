import { escalaDesde, textoSobre, TONOS, hexARgb } from './color'

const POR_DEFECTO = '#22C55E' // el verde histórico de la plataforma

/** Aplica el color institucional del condominio a las variables `--marca-*` (tailwind.config.ts). */
export function aplicarTema(color?: string) {
  const hex = color && /^#[0-9A-Fa-f]{6}$/.test(color) ? color : POR_DEFECTO
  const raiz = document.documentElement.style
  const escala = escalaDesde(hex)
  TONOS.forEach((t) => raiz.setProperty(`--marca-${t}`, escala[t].map(Math.round).join(' ')))
  // Botones con el color tal cual: el texto se elige por contraste
  raiz.setProperty('--marca-base', hexARgb(hex).join(' '))
  raiz.setProperty('--sobre-marca', hexARgb(textoSobre(hex)).join(' '))
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', hex)
}
