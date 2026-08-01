"""
Ejecutar desde la raíz del backend:
    python -m app.db.seeds.seeder
"""
import asyncio

from app.db.session import AsyncSessionLocal
from app.db.seeds.roles import seed_roles
from app.db.seeds.condominios import seed_condominios
from app.db.seeds.boleta_marzo_2025 import seed_boleta_marzo_2025
from app.db.seeds.lecturas_marzo_2025 import seed_lecturas_marzo_2025
from app.db.seeds.menus import seed_menus
from app.db.seeds.parcelas import seed_parcelas
from app.db.seeds.usuarios import seed_usuarios


async def run_all():
    async with AsyncSessionLocal() as db:
        print("Iniciando carga de datos semilla...")
        await seed_roles(db)
        await seed_condominios(db)
        await seed_parcelas(db)
        await seed_usuarios(db)
        await seed_menus(db)
        await seed_boleta_marzo_2025(db)
        await seed_lecturas_marzo_2025(db)
        print("Carga completada.")


if __name__ == "__main__":
    asyncio.run(run_all())
