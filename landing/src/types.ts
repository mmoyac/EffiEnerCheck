/**
 * Contrato de GET /api/v1/sitio. Espejo de backend/app/schemas/sitio.py (la fuente de verdad):
 * si cambias un campo allá, cámbialo aquí. Todos los textos son texto plano.
 */
export type Icono =
  | 'piscina' | 'quincho' | 'cancha' | 'juegos' | 'sendero' | 'porteria' | 'seguridad' | 'estacionamiento'
  | 'areas-verdes' | 'sede' | 'agua' | 'luz' | 'internet' | 'mascotas' | 'bicicleta' | 'arbol'

export interface SitioPublico {
  version_esquema: 1
  condominio: {
    nombre: string
    lema?: string
    descripcion_corta: string
    logo_url?: string
    color_primario?: string
  }
  /** Solo viene si el condominio contrató el portal: sin él no hay "Acceso propietarios" */
  portal_url?: string
  portada: { titulo: string; subtitulo?: string; imagen_url?: string; cta_texto: string }
  comunidad?: {
    titulo: string
    parrafos: string[]
    imagenes: string[]
    datos_clave: { etiqueta: string; valor: string }[]
  }
  avisos: { titulo: string; fecha: string; cuerpo: string; destacado: boolean }[]
  espacios: { nombre: string; descripcion: string; icono?: Icono; imagen_url?: string }[]
  administracion?: {
    empresa?: string
    directiva: { cargo: string; nombre: string }[]
    horario_atencion?: string
  }
  documentos: { titulo: string; descripcion?: string; url: string }[]
  contacto: {
    telefonos: { etiqueta: string; numero: string }[]
    correo?: string
    whatsapp?: string
    horarios: string[]
  }
  ubicacion?: { direccion: string; comuna: string; region: string; mapa_url?: string }
  pie: { texto?: string; enlaces: { texto: string; url: string }[] }
}
