import { useEffect } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { PLATAFORMA } from '../../config/marca'
import { escalaDesde, TONOS } from '../../utils/color'

/**
 * Aplica el color institucional del condominio del usuario a la escala `primary` (variables CSS que
 * usa tailwind.config.ts). Sin condominio, sin color o con el color por defecto, quita las variables
 * y vuelve al verde histórico definido en index.css, tal cual.
 */
export function TemaCondominio() {
  const { user } = useAuth()
  const color = user?.condominio?.color_primario ?? null

  useEffect(() => {
    const raiz = document.documentElement.style
    const meta = document.querySelector('meta[name="theme-color"]')
    if (!color || color.toUpperCase() === PLATAFORMA.colorPorDefecto) {
      TONOS.forEach((t) => raiz.removeProperty(`--primary-${t}`))
      meta?.setAttribute('content', '#16a34a')
      return
    }
    const escala = escalaDesde(color)
    TONOS.forEach((t) => raiz.setProperty(`--primary-${t}`, escala[t].map(Math.round).join(' ')))
    meta?.setAttribute('content', `rgb(${escala[600].map(Math.round).join(',')})`)
  }, [color])

  return null
}
