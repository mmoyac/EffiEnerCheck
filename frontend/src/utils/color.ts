/**
 * Escala de tonos (50–950) a partir del color institucional de un condominio (design.md D11).
 * El tono 500 es el color dado; el resto conserva el matiz y ajusta la luminosidad, como la escala
 * de Tailwind. La landing tiene su propia copia (landing/src/color.ts): no comparten código.
 */
export type Tono = 50 | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900 | 950
export const TONOS: Tono[] = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]

type Rgb = [number, number, number]
type Hsl = [number, number, number]

// Luminosidad de la escala verde de Tailwind; 500 ≈ 45
const L_REFERENCIA: Record<Tono, number> = {
  50: 97, 100: 93, 200: 87, 300: 77, 400: 62, 500: 45, 600: 37, 700: 30, 800: 25, 900: 20, 950: 10,
}

export function hexARgb(hex: string): Rgb {
  const n = parseInt(hex.replace('#', ''), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

export function rgbAHex([r, g, b]: Rgb): string {
  return '#' + [r, g, b].map((v) => Math.round(v).toString(16).padStart(2, '0')).join('').toUpperCase()
}

function rgbAHsl([r, g, b]: Rgb): Hsl {
  r /= 255; g /= 255; b /= 255
  const max = Math.max(r, g, b), min = Math.min(r, g, b)
  const l = (max + min) / 2
  if (max === min) return [0, 0, l * 100]
  const d = max - min
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
  const h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4
  return [h * 60, s * 100, l * 100]
}

function hslARgb([h, s, l]: Hsl): Rgb {
  s /= 100; l /= 100
  const k = (n: number) => (n + h / 30) % 12
  const a = s * Math.min(l, 1 - l)
  const f = (n: number) => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)))
  return [f(0) * 255, f(8) * 255, f(4) * 255]
}

function luminancia([r, g, b]: Rgb): number {
  const c = [r, g, b].map((v) => {
    v /= 255
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
}

export function contraste(a: Rgb, b: Rgb): number {
  const [x, y] = [luminancia(a), luminancia(b)].sort((m, n) => n - m)
  return (x + 0.05) / (y + 0.05)
}

const BLANCO: Rgb = [255, 255, 255]
const OSCURO: Rgb = [15, 23, 42] // slate-900, el fondo del portal

/** Texto legible sobre el color: blanco o casi negro, el de mayor contraste (WCAG). */
export function textoSobre(hex: string): '#FFFFFF' | '#0F172A' {
  const rgb = hexARgb(hex)
  return contraste(rgb, BLANCO) >= contraste(rgb, OSCURO) ? '#FFFFFF' : '#0F172A'
}

/** Mueve la luminosidad hasta alcanzar `minimo` de contraste contra `fondo`. */
function conContraste([h, s, l]: Hsl, fondo: Rgb, minimo: number, paso: number): Hsl {
  let actual = l
  for (let i = 0; i < 100 && contraste(hslARgb([h, s, actual]), fondo) < minimo; i++) {
    actual = Math.max(0, Math.min(100, actual + paso))
  }
  return [h, s, actual]
}

export function escalaDesde(hex: string): Record<Tono, Rgb> {
  const [h, s, l0] = rgbAHsl(hexARgb(hex))
  const escala = {} as Record<Tono, Rgb>
  for (const tono of TONOS) {
    const ref = L_REFERENCIA[tono]
    let l: number
    if (tono === 500) l = l0
    else if (ref > 45) l = l0 + ((ref - 45) / (97 - 45)) * (97 - l0) // hacia el blanco
    else l = l0 * (ref / 45)                                        // hacia el negro
    const sat = tono <= 100 || tono >= 900 ? s * 0.88 : s
    let hsl: Hsl = [h, sat, l]
    // El portal es oscuro: 600 lleva texto blanco encima (botones) y 300–400 son texto sobre slate-900.
    // 600 exige 3:1 (WCAG para componentes de interfaz): es lo que ya tiene el verde histórico.
    if (tono === 600) hsl = conContraste(hsl, BLANCO, 3, -1)
    if (tono === 400) hsl = conContraste(hsl, OSCURO, 4.5, +1)
    if (tono === 300) hsl = conContraste(hsl, OSCURO, 7, +1)
    escala[tono] = hslARgb(hsl)
  }
  return escala
}

/**
 * ¿Hubo que oscurecer los botones? El tono 600 que sale de la escala no alcanza 3:1 con texto blanco,
 * así que el portal usa uno más oscuro que el natural (aviso informativo en Condominios).
 */
export function bajoContraste(hex: string): boolean {
  const [h, s, l0] = rgbAHsl(hexARgb(hex))
  return contraste(hslARgb([h, s, l0 * (L_REFERENCIA[600] / 45)]), BLANCO) < 3
}
