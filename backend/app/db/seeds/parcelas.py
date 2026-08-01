from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parcela import Parcela

_numeros = (
    [str(n) for n in range(2, 13)]          # 2 – 12
    + ["13 A", "13 B", "14 A", "14 B"]      # fraccionadas
    + [str(n) for n in range(15, 53)]        # 15 – 52
)

PARCELAS = [
    {
        "id": idx + 1,
        "condominio_id": 1,
        "numero_parcela": num,
        "propietario_nombre": num,
        "activa": True,
    }
    for idx, num in enumerate(_numeros)
]


async def seed_parcelas(db: AsyncSession) -> None:
    for data in PARCELAS:
        existe = await db.execute(select(Parcela).where(Parcela.id == data["id"]))
        if existe.scalar_one_or_none():
            continue
        db.add(Parcela(**data))

    await db.commit()
    print(f"  ✓ parcelas: {len(PARCELAS)} registros cargados")
