import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import engine
from app.services.sitio import cargar_contenidos

# En producción la documentación interactiva no se publica (el repositorio y el sitio son públicos)
_docs = not settings.es_produccion



@asynccontextmanager
async def lifespan(_: FastAPI):
    # Falla temprano si un archivo de contenido de la landing no cumple el esquema
    cargar_contenidos()
    yield


app = FastAPI(
    lifespan=lifespan,
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs" if _docs else None,
    redoc_url="/api/redoc" if _docs else None,
    openapi_url="/openapi.json" if _docs else None,
)

app.include_router(api_router)

UPLOADS_DIR = "/app/uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


@app.get("/health", tags=["infra"])
async def health_check():
    """Sano solo si llega a PostgreSQL: lo usa el HEALTHCHECK del contenedor y el deploy."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        return JSONResponse(status_code=503, content={"status": "sin base de datos"})
    return {"status": "ok", "version": settings.APP_VERSION}
