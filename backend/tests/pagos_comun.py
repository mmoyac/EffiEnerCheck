"""Apoyo de las pruebas de pagos en línea (no es un archivo de pruebas)."""
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import create_access_token
from app.models.usuario import Usuario

SUPER = "mmoyainfo@gmail.com"
ADMIN = "hhernandez@santalaura.cl"
COMUNERO = "mmoyainfo+parcela@gmail.com"
PORTERIA = "porteria@santalaura.cl"
SECRETO = "secreto-que-no-debe-salir"
FLOW = {"proveedor": "flow", "nombre_visible": "Tarjeta o Webpay", "ambiente": "integracion",
        "credenciales": {"api_key": "API-KEY-123", "secret_key": SECRETO},
        "comision_porcentaje": "3.8", "comision_fija": 0}


async def usuario(s, email) -> Usuario:
    return (await s.execute(
        select(Usuario).options(selectinload(Usuario.rol), selectinload(Usuario.parcelas)).where(Usuario.email == email)
    )).scalar_one()


async def cabecera(s, email) -> dict[str, str]:
    """Token emitido directo: las claves de desarrollo pueden haber cambiado."""
    u = await usuario(s, email)
    return {"Authorization": f"Bearer {create_access_token(user_id=u.id, rol=u.rol.nombre, condominio_id=u.condominio_id)}"}


async def crear_pasarela(c, cab, condominio_id=1, **extra):
    return await c.post("/api/v1/pasarelas/", headers=cab, json={**FLOW, "condominio_id": condominio_id, **extra})


def sin_secretos(texto: str) -> None:
    assert SECRETO not in texto and "API-KEY-123" not in texto
