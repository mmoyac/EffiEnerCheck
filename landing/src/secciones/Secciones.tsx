import {
  Bike, Car, CalendarDays, Clock, Dog, Droplets, ExternalLink, FileText, Flame, Mail, MapPin, MessageCircle,
  Phone, Shield, ShieldCheck, Sparkles, Trees, TreePine, Trophy, Users, Waves, Wifi, Zap, Footprints, Home,
  type LucideIcon,
} from 'lucide-react'
import type { Icono, SitioPublico } from '../types'

const ICONOS: Record<Icono, LucideIcon> = {
  piscina: Waves, quincho: Flame, cancha: Trophy, juegos: Sparkles, sendero: Footprints, porteria: ShieldCheck,
  seguridad: Shield, estacionamiento: Car, 'areas-verdes': Trees, sede: Home, agua: Droplets, luz: Zap,
  internet: Wifi, mascotas: Dog, bicicleta: Bike, arbol: TreePine,
}

/** Solo dígitos (y + inicial): los datos sin confirmar no generan enlaces rotos */
const soloDigitos = (v: string) => v.replace(/[^\d+]/g, '')
const esTelefono = (v: string) => soloDigitos(v).replace('+', '').length >= 8
const esCorreo = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)

function fechaLarga(iso: string) {
  const [a, m, d] = iso.split('-').map(Number)
  return new Date(a, m - 1, d).toLocaleDateString('es-CL', { day: 'numeric', month: 'long', year: 'numeric' })
}

export function Comunidad({ comunidad }: { comunidad: NonNullable<SitioPublico['comunidad']> }) {
  return (
    <section id="comunidad" className="seccion">
      <div className="grid gap-12 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <h2 className="titulo-seccion">{comunidad.titulo}</h2>
          <div className="mt-6 space-y-4 text-lg leading-relaxed text-slate-600">
            {comunidad.parrafos.map((p, i) => <p key={i}>{p}</p>)}
          </div>
        </div>
        {comunidad.datos_clave.length > 0 && (
          <dl className="grid grid-cols-1 gap-4 self-start min-[400px]:grid-cols-2 lg:col-span-2">
            {comunidad.datos_clave.map((d) => (
              <div key={d.etiqueta} className="rounded-2xl border border-marca-100 bg-white p-5 shadow-sm">
                <dt className="text-sm text-slate-500">{d.etiqueta}</dt>
                <dd className="mt-1 break-words font-titulo text-xl font-bold text-marca-800 sm:text-2xl">{d.valor}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
      {comunidad.imagenes.length > 0 && (
        <div className="mt-10 grid grid-cols-2 gap-4 md:grid-cols-3">
          {comunidad.imagenes.map((src) => (
            <img key={src} src={src} alt="" loading="lazy" className="aspect-[4/3] w-full rounded-2xl object-cover" />
          ))}
        </div>
      )}
    </section>
  )
}

export function Avisos({ avisos }: { avisos: SitioPublico['avisos'] }) {
  const ordenados = [...avisos].sort((a, b) => Number(b.destacado) - Number(a.destacado) || b.fecha.localeCompare(a.fecha))
  return (
    <section id="avisos" className="bg-white">
      <div className="seccion">
        <h2 className="titulo-seccion">Avisos</h2>
        <div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {ordenados.map((a) => (
            <article key={a.titulo + a.fecha}
              className={`rounded-2xl border p-6 ${a.destacado ? 'border-marca-300 bg-marca-50' : 'border-stone-200 bg-stone-50'}`}>
              <p className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                <CalendarDays className="h-3.5 w-3.5" /> {fechaLarga(a.fecha)}
                {a.destacado && <span className="ml-auto rounded-full bg-marca-600 px-2 py-0.5 text-[11px] font-semibold text-white">Destacado</span>}
              </p>
              <h3 className="mt-3 text-lg font-semibold text-slate-900">{a.titulo}</h3>
              <p className="mt-2 text-slate-600">{a.cuerpo}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

export function Espacios({ espacios }: { espacios: SitioPublico['espacios'] }) {
  return (
    <section id="espacios" className="seccion">
      <h2 className="titulo-seccion">Espacios y servicios</h2>
      <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {espacios.map((e) => {
          const Icon = e.icono ? ICONOS[e.icono] : Sparkles
          return (
            <div key={e.nombre} className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm">
              {e.imagen_url && <img src={e.imagen_url} alt="" loading="lazy" className="aspect-[16/9] w-full object-cover" />}
              <div className="p-6">
                <div className="mb-4 inline-flex rounded-xl bg-marca-100 p-2.5 text-marca-700">
                  <Icon className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900">{e.nombre}</h3>
                <p className="mt-1.5 text-slate-600">{e.descripcion}</p>
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

export function Administracion({ adm }: { adm: NonNullable<SitioPublico['administracion']> }) {
  return (
    <section id="administracion" className="bg-marca-950 text-white">
      <div className="seccion">
        <h2 className="font-titulo text-3xl font-bold sm:text-4xl">Administración y directiva</h2>
        <div className="mt-8 grid gap-8 lg:grid-cols-3">
          <div className="space-y-4">
            {adm.empresa && (
              <p className="flex items-start gap-3 text-marca-100">
                <Users className="mt-0.5 h-5 w-5 flex-shrink-0 text-marca-300" /> {adm.empresa}
              </p>
            )}
            {adm.horario_atencion && (
              <p className="flex items-start gap-3 text-marca-100">
                <Clock className="mt-0.5 h-5 w-5 flex-shrink-0 text-marca-300" /> {adm.horario_atencion}
              </p>
            )}
          </div>
          {adm.directiva.length > 0 && (
            <ul className="grid gap-4 sm:grid-cols-3 lg:col-span-2">
              {adm.directiva.map((c) => (
                <li key={c.cargo} className="rounded-2xl bg-white/5 p-5 ring-1 ring-white/10">
                  <p className="text-xs font-semibold uppercase tracking-wider text-marca-300">{c.cargo}</p>
                  <p className="mt-1.5 font-medium">{c.nombre}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  )
}

export function Documentos({ documentos }: { documentos: SitioPublico['documentos'] }) {
  return (
    <section id="documentos" className="seccion">
      <h2 className="titulo-seccion">Documentos</h2>
      <ul className="mt-8 divide-y divide-stone-200 rounded-2xl border border-stone-200 bg-white">
        {documentos.map((d) => (
          <li key={d.url}>
            <a href={d.url} target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-4 p-5 transition hover:bg-stone-50">
              <FileText className="h-6 w-6 flex-shrink-0 text-marca-600" />
              <span className="min-w-0 flex-1">
                <span className="block font-medium text-slate-900">{d.titulo}</span>
                {d.descripcion && <span className="block text-sm text-slate-500">{d.descripcion}</span>}
              </span>
              <ExternalLink className="h-4 w-4 flex-shrink-0 text-slate-400" />
            </a>
          </li>
        ))}
      </ul>
    </section>
  )
}

export function Contacto({ contacto, ubicacion }: {
  contacto: SitioPublico['contacto']; ubicacion?: SitioPublico['ubicacion']
}) {
  const fila = 'flex items-start gap-3 rounded-xl p-3 text-slate-700'
  return (
    <section id="contacto" className="bg-white">
      <div className="seccion grid gap-10 lg:grid-cols-2">
        <div>
          <h2 className="titulo-seccion">Contacto</h2>
          <div className="mt-6 space-y-1">
            {contacto.telefonos.map((t) => (
              esTelefono(t.numero) ? (
                <a key={t.etiqueta} href={`tel:${soloDigitos(t.numero)}`} className={`${fila} hover:bg-stone-100`}>
                  <Phone className="mt-0.5 h-5 w-5 text-marca-600" />
                  <span><span className="block text-sm text-slate-500">{t.etiqueta}</span>{t.numero}</span>
                </a>
              ) : (
                <p key={t.etiqueta} className={fila}>
                  <Phone className="mt-0.5 h-5 w-5 text-marca-600" />
                  <span><span className="block text-sm text-slate-500">{t.etiqueta}</span>{t.numero}</span>
                </p>
              )
            ))}
            {contacto.correo && (
              esCorreo(contacto.correo) ? (
                <a href={`mailto:${contacto.correo}`} className={`${fila} hover:bg-stone-100`}>
                  <Mail className="mt-0.5 h-5 w-5 text-marca-600" /> {contacto.correo}
                </a>
              ) : (
                <p className={fila}><Mail className="mt-0.5 h-5 w-5 text-marca-600" /> {contacto.correo}</p>
              )
            )}
            {contacto.horarios.map((h) => (
              <p key={h} className={fila}><Clock className="mt-0.5 h-5 w-5 text-marca-600" /> {h}</p>
            ))}
          </div>
          {contacto.whatsapp && esTelefono(contacto.whatsapp) && (
            <a href={`https://wa.me/${soloDigitos(contacto.whatsapp).replace('+', '')}`} target="_blank"
              rel="noopener noreferrer" className="boton-marca mt-6">
              <MessageCircle className="h-4 w-4" /> Escríbenos por WhatsApp
            </a>
          )}
        </div>

        {ubicacion && (
          <div id="ubicacion" className="self-start rounded-2xl bg-marca-50 p-8 ring-1 ring-marca-100">
            <MapPin className="h-8 w-8 text-marca-600" />
            <h3 className="mt-4 font-titulo text-2xl font-bold text-slate-900">Cómo llegar</h3>
            <p className="mt-2 text-slate-700">{ubicacion.direccion}</p>
            <p className="text-slate-500">{ubicacion.comuna}, {ubicacion.region}</p>
            {ubicacion.mapa_url && (
              <a href={ubicacion.mapa_url} target="_blank" rel="noopener noreferrer"
                className="mt-5 inline-flex items-center gap-1.5 font-medium text-marca-700 hover:underline">
                Ver en el mapa <ExternalLink className="h-4 w-4" />
              </a>
            )}
          </div>
        )}
      </div>
    </section>
  )
}

export function Pie({ sitio, plataforma }: { sitio: SitioPublico; plataforma: string }) {
  const { pie, condominio, portal_url, portada } = sitio
  return (
    <footer className="border-t border-stone-200 bg-stone-100">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="font-titulo text-lg font-bold text-slate-900">{condominio.nombre}</p>
          {pie.texto && <p className="text-sm text-slate-500">{pie.texto}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
          {pie.enlaces.map((e) => (
            <a key={e.url} href={e.url} className="text-slate-600 hover:text-marca-700">{e.texto}</a>
          ))}
          {portal_url && <a href={portal_url} className="font-medium text-marca-700 hover:underline">{portada.cta_texto}</a>}
        </div>
      </div>
      <p className="pb-6 text-center text-xs text-slate-400">Plataforma {plataforma}</p>
    </footer>
  )
}
