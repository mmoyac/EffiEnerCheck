"""
Sitio público (landing) de cada condominio — spec sitio-publico, design.md D6.

- Resolución: host de la petición → condominio_dominios → condominio activo con el módulo `sitio`.
  Si el dominio no está registrado, se usa SITIO_POR_DEFECTO (RUT de la comunidad), si existe.
- Contenido editorial: hoy, un archivo JSON por condominio en app/sitio/contenido/ (validado al
  arrancar). Mañana saldrá de la tabla sitio_contenido, editado desde el portal: solo cambia
  `_contenido_por_rut`; el contrato (SitioPublico) y la landing quedan iguales.
- Parametrización (logo, color y portal_url): siempre desde la base, nunca del archivo.
"""
import json
import logging
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.condominio import Condominio
from app.models.condominio_modulo import CondominioDominio
from app.schemas.sitio import ArchivoSitio, SitioPublico
from app.utils.dominio import normalizar_host

log = logging.getLogger(__name__)

CONTENIDO_DIR = Path(__file__).resolve().parent.parent / "sitio" / "contenido"


class ContenidoSitioInvalido(Exception):
    pass


@lru_cache(maxsize=1)
def cargar_contenidos() -> dict[str, SitioPublico]:
    """Lee y valida todos los archivos de contenido. Un archivo inválido detiene el arranque."""
    contenidos: dict[str, SitioPublico] = {}
    for ruta in sorted(CONTENIDO_DIR.glob("*.json")):
        try:
            archivo = ArchivoSitio.model_validate(json.loads(ruta.read_text(encoding="utf-8")))
        except Exception as exc:  # noqa: BLE001 — se reporta con el nombre del archivo
            raise ContenidoSitioInvalido(f"{ruta.name}: {exc}") from exc
        for rut in archivo.ruts_comunidad:
            if rut in contenidos:
                raise ContenidoSitioInvalido(f"{ruta.name}: el RUT {rut} ya está en otro archivo")
            contenidos[rut] = archivo.sitio
    return contenidos


def _contenido_por_rut(rut: str) -> SitioPublico | None:
    return cargar_contenidos().get(rut)


async def _condominio_del_host(host: str, db: AsyncSession) -> Condominio | None:
    stmt = select(Condominio).options(selectinload(Condominio.modulos))
    condominio = (await db.execute(
        stmt.join(CondominioDominio).where(CondominioDominio.dominio == normalizar_host(host))
    )).scalar_one_or_none()
    if condominio is None and settings.SITIO_POR_DEFECTO:
        condominio = (await db.execute(
            stmt.where(Condominio.rut_comunidad == settings.SITIO_POR_DEFECTO)
        )).scalar_one_or_none()
    return condominio


async def obtener_sitio(host: str, db: AsyncSession) -> SitioPublico | None:
    condominio = await _condominio_del_host(host, db)
    if condominio is None or not condominio.activo:
        return None
    modulos = condominio.modulos_habilitados
    if "sitio" not in modulos:
        return None
    contenido = _contenido_por_rut(condominio.rut_comunidad)
    if contenido is None:
        log.warning("El condominio %s tiene el módulo sitio pero no tiene archivo de contenido", condominio.id)
        return None

    sitio = contenido.model_copy(deep=True)
    sitio.condominio.logo_url = condominio.logo_url
    sitio.condominio.color_primario = condominio.color_primario
    sitio.portal_url = condominio.portal_url if "portal" in modulos else None
    return sitio
