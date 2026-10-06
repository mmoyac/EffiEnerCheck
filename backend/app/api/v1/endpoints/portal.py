"""
Marca pública del portal por dominio y manifiesto de la app instalable (cambio app-instalable-por-condominio).

El condominio se identifica por el dominio con que se entra al portal, comparado con su `portal_url`.
Se lee de la base en cada petición: cambiar el nombre o el color del condominio no exige desplegar.
Solo se expone lo que ya es público en el portal: nombre y color.
"""
import json
from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.models.condominio import Condominio
from app.utils.dominio import normalizar_host

router = APIRouter(prefix="/portal", tags=["portal"])

PLATAFORMA = "EFFIComunidad"
LEMA = "Portal de la comunidad"
COLOR_PLATAFORMA = "#16A34A"
FONDO = "#0F172A"


class MarcaPortal(BaseModel):
    nombre: str            # bajo el ícono de la app
    nombre_completo: str   # al instalar y en el selector de apps
    color: str
    condominio: bool       # False = marca de la plataforma (dominio sin condominio)


async def _marca(request: Request, db: AsyncSession) -> MarcaPortal:
    host = normalizar_host((request.headers.get("x-forwarded-host") or request.headers.get("host") or "").split(",")[0])
    filas = (await db.execute(
        select(Condominio.nombre, Condominio.color_primario, Condominio.portal_url)
        .where(Condominio.activo.is_(True), Condominio.portal_url.is_not(None))
    )).all()
    for nombre, color, portal_url in filas:
        if host and normalizar_host(urlparse(portal_url).netloc or portal_url) == host:
            return MarcaPortal(nombre=nombre, nombre_completo=f"{nombre} · {PLATAFORMA}",
                               color=color or COLOR_PLATAFORMA, condominio=True)
    return MarcaPortal(nombre=PLATAFORMA, nombre_completo=f"{PLATAFORMA} · {LEMA}", color=COLOR_PLATAFORMA,
                       condominio=False)


@router.get("/marca", response_model=MarcaPortal)
async def marca_portal(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    return await _marca(request, db)


@router.get("/manifest")
async def manifest(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    """Manifiesto de la PWA con el nombre y el color del condominio del dominio."""
    m = await _marca(request, db)
    cuerpo = {
        "name": m.nombre_completo,
        "short_name": m.nombre,
        "description": f"Portal de la comunidad {m.nombre}" if m.condominio else LEMA,
        "lang": "es-CL",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "theme_color": m.color,
        "background_color": FONDO,
        "icons": [
            {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    return Response(json.dumps(cuerpo, ensure_ascii=False), media_type="application/manifest+json",
                    headers={"Cache-Control": "no-cache"})
