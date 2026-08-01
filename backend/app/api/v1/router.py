from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    boletas,
    condominios,
    lecturas,
    liquidaciones,
    menus,
    parcelas,
    usuarios,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(usuarios.router)
api_router.include_router(condominios.router)
api_router.include_router(parcelas.router)
api_router.include_router(boletas.router)
api_router.include_router(lecturas.router)
api_router.include_router(liquidaciones.router)
api_router.include_router(menus.router)
