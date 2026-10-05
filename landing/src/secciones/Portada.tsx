import { LogIn } from 'lucide-react'
import type { SitioPublico } from '../types'

export function Portada({ sitio }: { sitio: SitioPublico }) {
  const { portada, condominio, portal_url } = sitio
  return (
    <section id="inicio" className="relative isolate overflow-hidden bg-marca-950">
      {portada.imagen_url && (
        <img src={portada.imagen_url} alt="" className="absolute inset-0 -z-10 h-full w-full object-cover object-[50%_60%]" />
      )}
      {/* Velo para que el texto se lea sobre cualquier imagen: parejo en celular (el texto ocupa todo el
          ancho) y degradado desde la izquierda en pantallas anchas */}
      <div className="absolute inset-0 -z-10 bg-slate-950/55 md:bg-transparent md:bg-gradient-to-r md:from-slate-950/80 md:via-slate-950/45 md:to-slate-950/5" />

      <div className="mx-auto flex min-h-[70vh] max-w-6xl flex-col justify-center px-4 py-20 sm:px-6 lg:min-h-[78vh]">
        <div className="max-w-xl">
          {condominio.logo_url && (
            <img src={condominio.logo_url} alt={`Logo de ${condominio.nombre}`}
              className="mb-6 h-20 w-20 rounded-2xl bg-white/95 object-contain p-2 shadow-lg" />
          )}
          {condominio.lema && (
            <p className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-marca-200">{condominio.lema}</p>
          )}
          <h1 className="font-titulo text-4xl font-bold leading-tight text-white sm:text-5xl lg:text-6xl">
            {portada.titulo}
          </h1>
          {portada.subtitulo && (
            <p className="mt-5 text-lg text-slate-100/90 sm:text-xl">{portada.subtitulo}</p>
          )}
          {portal_url && (
            <a href={portal_url} className="boton-marca mt-8 !px-7 !py-3.5 !text-base">
              <LogIn className="h-5 w-5" />
              {portada.cta_texto}
            </a>
          )}
        </div>
      </div>
    </section>
  )
}
