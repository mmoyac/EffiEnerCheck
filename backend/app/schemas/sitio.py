"""
Contrato de la landing pública (spec sitio-publico, design.md D5).

`SitioPublico` es la fuente de verdad: landing/src/types.ts lo replica. Si cambias un campo,
cambia ambos y sube `version_esquema` si el cambio no es compatible.

Reglas: solo texto plano (la landing no interpreta HTML), íconos de una lista cerrada, URLs
https o rutas relativas, y ningún dato del padrón (solo contacto institucional y directiva).
"""
import re
from datetime import date
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

VERSION_ESQUEMA = 1

Icono = Literal[
    "piscina", "quincho", "cancha", "juegos", "sendero", "porteria", "seguridad", "estacionamiento",
    "areas-verdes", "sede", "agua", "luz", "internet", "mascotas", "bicicleta", "arbol",
]

_URL = re.compile(r"^(https://\S+|/\S*)$")


def _url(v: str) -> str:
    if not _URL.match(v):
        raise ValueError("Debe ser una URL https:// o una ruta relativa que empiece con /")
    return v


def _sin_html(v: str) -> str:
    if re.search(r"<\s*[a-zA-Z/!]", v):
        raise ValueError("El contenido del sitio es texto plano: no admite HTML")
    return v


Url = Annotated[str, AfterValidator(_url)]
Texto = Annotated[str, AfterValidator(_sin_html), Field(min_length=1)]


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DatoClave(_Estricto):
    etiqueta: Texto
    valor: Texto


class CondominioSitio(_Estricto):
    nombre: Texto
    lema: Texto | None = None
    descripcion_corta: Texto  # SEO y vistas previas
    # Los agrega el servicio desde la base (parametrización del super_admin); el archivo no los trae
    logo_url: str | None = None
    color_primario: str | None = None


class Portada(_Estricto):
    titulo: Texto
    subtitulo: Texto | None = None
    imagen_url: Url | None = None
    cta_texto: Texto = "Acceso propietarios"


class Comunidad(_Estricto):
    titulo: Texto
    parrafos: list[Texto]
    imagenes: list[Url] = []
    datos_clave: list[DatoClave] = []


class Aviso(_Estricto):
    titulo: Texto
    fecha: date
    cuerpo: Texto
    destacado: bool = False


class Espacio(_Estricto):
    nombre: Texto
    descripcion: Texto
    icono: Icono | None = None
    imagen_url: Url | None = None


class Cargo(_Estricto):
    cargo: Texto
    nombre: Texto


class Administracion(_Estricto):
    empresa: Texto | None = None
    directiva: list[Cargo] = []
    horario_atencion: Texto | None = None


class Documento(_Estricto):
    titulo: Texto
    descripcion: Texto | None = None
    url: Url


class Telefono(_Estricto):
    etiqueta: Texto
    numero: Texto


class Contacto(_Estricto):
    telefonos: list[Telefono] = []
    correo: Texto | None = None
    whatsapp: Texto | None = None  # solo dígitos con código de país: 569XXXXXXXX
    horarios: list[Texto] = []


class Ubicacion(_Estricto):
    direccion: Texto
    comuna: Texto
    region: Texto
    mapa_url: Url | None = None


class Enlace(_Estricto):
    texto: Texto
    url: Url


class Pie(_Estricto):
    texto: Texto | None = None
    enlaces: list[Enlace] = []


class SitioPublico(_Estricto):
    """Respuesta de GET /api/v1/sitio. Las secciones opcionales vacías no se dibujan."""
    version_esquema: Literal[1] = VERSION_ESQUEMA
    condominio: CondominioSitio
    portal_url: str | None = None  # lo agrega el servicio, solo si el condominio tiene `portal`
    portada: Portada
    comunidad: Comunidad | None = None
    avisos: list[Aviso] = []
    espacios: list[Espacio] = []
    administracion: Administracion | None = None
    documentos: list[Documento] = []
    contacto: Contacto
    ubicacion: Ubicacion | None = None
    pie: Pie = Pie()


class ArchivoSitio(_Estricto):
    """
    Archivo backend/app/sitio/contenido/<slug>.json: el contenido más los RUT de comunidad que lo
    asocian a un condominio (el de desarrollo, que es ficticio, y el real de producción).
    """
    ruts_comunidad: list[str] = Field(min_length=1)
    sitio: SitioPublico
