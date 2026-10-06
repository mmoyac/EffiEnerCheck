from fastapi import APIRouter, Depends

from app.api.v1.endpoints import (
    auth,
    boletas,
    condominios,
    lecturas,
    liquidaciones,
    menus,
    parcelas,
    rifas,
    portal,
    sitio,
    usuarios,
)
from app.core.dependencies import modulo_requerido

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(usuarios.router)
api_router.include_router(condominios.router)
api_router.include_router(parcelas.router)
api_router.include_router(menus.router)
api_router.include_router(sitio.router)  # público: landing (sin login)
api_router.include_router(portal.router)  # público: marca y manifiesto de la app según el dominio

# Módulos del portal: todo router de un módulo se incluye con su guarda (spec modulos-plataforma)
_energia = [Depends(modulo_requerido("energia"))]
api_router.include_router(boletas.router, dependencies=_energia)
api_router.include_router(lecturas.router, dependencies=_energia)
api_router.include_router(liquidaciones.router, dependencies=_energia)
api_router.include_router(rifas.router, dependencies=[Depends(modulo_requerido("rifas"))])
