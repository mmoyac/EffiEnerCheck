from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.schemas.sitio import SitioPublico
from app.services.sitio import obtener_sitio

router = APIRouter(prefix="/sitio", tags=["sitio"])


@router.get("", response_model=SitioPublico, response_model_exclude_none=True)
async def get_sitio(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Contenido de la landing del condominio dueño del dominio de la petición. Público, sin login:
    lo consume la aplicación landing/. El nginx compartido envía el host en X-Forwarded-Host y Host.
    """
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    sitio = await obtener_sitio(host.split(",")[0], db)
    if sitio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sitio no encontrado")
    response.headers["Cache-Control"] = "public, max-age=300"
    return sitio
