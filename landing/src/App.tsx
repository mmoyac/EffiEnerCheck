import { useEffect, useState } from 'react'
import { obtenerSitio } from './api'
import { aplicarTema } from './tema'
import type { SitioPublico } from './types'
import { Cabecera, type Enlace } from './secciones/Cabecera'
import { Portada } from './secciones/Portada'
import { Administracion, Avisos, Comunidad, Contacto, Documentos, Espacios, Pie } from './secciones/Secciones'

/** Nombre comercial de la plataforma (mismo valor que frontend/src/config/marca.ts) */
const PLATAFORMA = 'EnerCheck'

function fijarMeta(nombre: string, valor: string, atributo: 'name' | 'property' = 'name') {
  let meta = document.querySelector<HTMLMetaElement>(`meta[${atributo}="${nombre}"]`)
  if (!meta) {
    meta = document.createElement('meta')
    meta.setAttribute(atributo, nombre)
    document.head.appendChild(meta)
  }
  meta.content = valor
}

/** Título, descripción y vista previa al compartir, desde el contenido del condominio */
function aplicarMetadatos(sitio: SitioPublico) {
  const { condominio, portada } = sitio
  document.title = condominio.lema ? `${condominio.nombre} · ${condominio.lema}` : condominio.nombre
  fijarMeta('description', condominio.descripcion_corta)
  fijarMeta('og:title', condominio.nombre, 'property')
  fijarMeta('og:description', condominio.descripcion_corta, 'property')
  const imagen = portada.imagen_url ?? condominio.logo_url
  if (imagen) fijarMeta('og:image', new URL(imagen, location.origin).href, 'property')
}

/** Enlaces de navegación: solo las secciones que vienen con contenido */
function enlacesDe(s: SitioPublico): Enlace[] {
  return [
    s.comunidad && { id: 'comunidad', texto: 'Comunidad' },
    s.avisos.length > 0 && { id: 'avisos', texto: 'Avisos' },
    s.espacios.length > 0 && { id: 'espacios', texto: 'Espacios' },
    s.administracion && { id: 'administracion', texto: 'Administración' },
    s.documentos.length > 0 && { id: 'documentos', texto: 'Documentos' },
    { id: 'contacto', texto: 'Contacto' },
  ].filter(Boolean) as Enlace[]
}

export default function App() {
  const [sitio, setSitio] = useState<SitioPublico | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    obtenerSitio()
      .then((s) => { aplicarTema(s.condominio.color_primario); aplicarMetadatos(s); setSitio(s) })
      .catch(() => setError(true))
  }, [])

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center px-6 text-center">
        <div>
          <h1 className="font-titulo text-3xl font-bold text-slate-900">Sitio no disponible</h1>
          <p className="mt-3 text-slate-600">No pudimos cargar el sitio en este momento. Intenta nuevamente más tarde.</p>
        </div>
      </main>
    )
  }

  if (!sitio) {
    return <div className="flex min-h-screen items-center justify-center"><div className="h-10 w-10 animate-spin rounded-full border-4 border-marca-200 border-t-marca-600" /></div>
  }

  return (
    <>
      <Cabecera sitio={sitio} enlaces={enlacesDe(sitio)} />
      <main>
        <Portada sitio={sitio} />
        {sitio.comunidad && <Comunidad comunidad={sitio.comunidad} />}
        {sitio.avisos.length > 0 && <Avisos avisos={sitio.avisos} />}
        {sitio.espacios.length > 0 && <Espacios espacios={sitio.espacios} />}
        {sitio.administracion && <Administracion adm={sitio.administracion} />}
        {sitio.documentos.length > 0 && <Documentos documentos={sitio.documentos} />}
        <Contacto contacto={sitio.contacto} ubicacion={sitio.ubicacion} />
      </main>
      <Pie sitio={sitio} plataforma={PLATAFORMA} />
    </>
  )
}
