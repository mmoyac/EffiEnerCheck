from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.core.modulos import MODULOS
from app.models.condominio import Condominio
from app.models.condominio_modulo import CondominioModulo

CONDOMINIOS = [
    {
        "id": 1,
        "nombre": "Santa Laura",
        "rut_comunidad": "1-9",
        "direccion": None,
        "plan_suscripcion": "premium",
        "activo": True,
        # Parametrización de DESARROLLO: el verde actual del portal y el portal local
        "color_primario": "#22C55E",
        "portal_url": "http://localhost:3000",
    },
]


async def seed_condominios(db: AsyncSession) -> None:
    for data in CONDOMINIOS:
        existe = (await db.execute(select(Condominio).where(Condominio.id == data["id"]))).scalar_one_or_none()
        if existe:
            # Bases creadas antes de la parametrización: completa lo que falte sin pisar cambios
            for campo in ("color_primario", "portal_url"):
                if getattr(existe, campo) is None:
                    setattr(existe, campo, data[campo])
        else:
            db.add(Condominio(**data))
        await db.flush()
        tiene = (await db.execute(
            select(CondominioModulo).where(CondominioModulo.condominio_id == data["id"])
        )).first()
        if not tiene:
            db.add_all(CondominioModulo(condominio_id=data["id"], modulo=m) for m in MODULOS)

    # Los inserts con id explícito no avanzan la secuencia
    await db.execute(text("SELECT setval(pg_get_serial_sequence('condominios', 'id'), (SELECT max(id) FROM condominios))"))
    await db.commit()
    print(f"  ✓ condominios: {len(CONDOMINIOS)} registros cargados")
