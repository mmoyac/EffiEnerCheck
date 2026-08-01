from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.condominio import Condominio

CONDOMINIOS = [
    {
        "id": 1,
        "nombre": "Santa Laura",
        "rut_comunidad": "1-9",
        "direccion": None,
        "plan_suscripcion": "premium",
        "activo": True,
    },
]


async def seed_condominios(db: AsyncSession) -> None:
    for data in CONDOMINIOS:
        existe = await db.execute(select(Condominio).where(Condominio.id == data["id"]))
        if existe.scalar_one_or_none():
            continue
        db.add(Condominio(**data))

    await db.commit()
    print(f"  ✓ condominios: {len(CONDOMINIOS)} registros cargados")
