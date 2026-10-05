import { useState } from 'react'
import { LogIn, Menu, X } from 'lucide-react'
import type { SitioPublico } from '../types'

export interface Enlace { id: string; texto: string }

export function Cabecera({ sitio, enlaces }: { sitio: SitioPublico; enlaces: Enlace[] }) {
  const [abierto, setAbierto] = useState(false)
  const { condominio, portal_url, portada } = sitio

  return (
    <header className="sticky top-0 z-40 border-b border-stone-200/70 bg-stone-50/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <a href="#inicio" className="flex min-w-0 items-center gap-2.5">
          {condominio.logo_url && (
            <img src={condominio.logo_url} alt="" className="h-9 w-9 flex-shrink-0 object-contain" />
          )}
          <span className="truncate font-titulo text-base font-bold text-slate-900 sm:text-lg">{condominio.nombre}</span>
        </a>

        <nav className="hidden items-center gap-6 lg:flex" aria-label="Secciones">
          {enlaces.map((e) => (
            <a key={e.id} href={`#${e.id}`} className="text-sm font-medium text-slate-600 hover:text-marca-700">
              {e.texto}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          {portal_url && (
            <a href={portal_url} className="boton-marca !px-4 !py-2">
              <LogIn className="h-4 w-4" />
              <span className="hidden sm:inline">{portada.cta_texto}</span>
              <span className="sm:hidden">Acceso</span>
            </a>
          )}
          {enlaces.length > 0 && (
            <button
              type="button"
              onClick={() => setAbierto((v) => !v)}
              className="rounded-lg p-2 text-slate-700 hover:bg-stone-200 lg:hidden"
              aria-label={abierto ? 'Cerrar menú' : 'Abrir menú'}
              aria-expanded={abierto}
            >
              {abierto ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          )}
        </div>
      </div>

      {abierto && (
        <nav className="border-t border-stone-200 bg-stone-50 px-4 py-2 lg:hidden" aria-label="Secciones">
          {enlaces.map((e) => (
            <a key={e.id} href={`#${e.id}`} onClick={() => setAbierto(false)}
              className="block rounded-lg px-3 py-2.5 text-sm font-medium text-slate-700 hover:bg-stone-200">
              {e.texto}
            </a>
          ))}
        </nav>
      )}
    </header>
  )
}
