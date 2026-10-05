from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.rol import Rol

ROLES = [
    {"id": 1, "nombre": "super_admin",        "descripcion": "Llena las tablas maestras"},
    {"id": 2, "nombre": "admin_condominio",   "descripcion": "Carga boletas y realiza los cálculos"},
    {"id": 3, "nombre": "lector",             "descripcion": "Toma lecturas de remarcadores por parcela"},
    {"id": 4, "nombre": "parcelero",          "descripcion": "Visualiza sus liquidaciones"},
    {"id": 5, "nombre": "porteria",           "descripcion": "Vende números de rifas solidarias"},
]


async def seed_roles(db: AsyncSession) -> None:
    for data in ROLES:
        existe = await db.execute(select(Rol).where(Rol.id == data["id"]))
        if existe.scalar_one_or_none():
            continue
        db.add(Rol(**data))

    await db.commit()
    print(f"  ✓ roles: {len(ROLES)} registros cargados")
