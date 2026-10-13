"""
Rota la clave maestra de las credenciales de las pasarelas de pago.

    python -m app.db.rotar_clave_pagos --nueva <clave en base64>

Lee las credenciales con la clave actual (PAGOS_CLAVE_MAESTRA), las recifra con la nueva en una sola
transacción y no muestra ningún valor. Después hay que reemplazar PAGOS_CLAVE_MAESTRA por la nueva en el
Environment de Dokploy y reiniciar el backend (DEPLOY.md). Generar una clave:

    python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"
"""
import argparse
import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, engine
from app.models.pago import PasarelaPago
from app.services.pagos.cifrado import ClaveMaestraInvalida, aad, cifrar, descifrar, leer_clave

import app.db.base  # noqa: F401 — registra todos los modelos


async def rotar(db: AsyncSession, actual: bytes, nueva: bytes, solo_ids: list[int] | None = None) -> int:
    """Recifra las credenciales (todas, o las de `solo_ids`); no hace commit. Devuelve cuántas cambió."""
    stmt = select(PasarelaPago).where(PasarelaPago.credenciales_cifradas.is_not(None)).with_for_update()
    if solo_ids is not None:
        stmt = stmt.where(PasarelaPago.id.in_(solo_ids))
    pasarelas = (await db.execute(stmt)).scalars().all()
    for p in pasarelas:
        dato = aad(p.condominio_id, p.id)
        p.credenciales_cifradas = cifrar(descifrar(p.credenciales_cifradas, dato, actual), dato, nueva)
    await db.flush()
    return len(pasarelas)


async def main(nueva_b64: str) -> None:
    actual = leer_clave()
    nueva = leer_clave(nueva_b64)
    async with AsyncSessionLocal() as db:
        cantidad = await rotar(db, actual, nueva)
        await db.commit()
    await engine.dispose()
    print(f"  ✓ {cantidad} pasarela(s) recifradas. Ahora reemplaza PAGOS_CLAVE_MAESTRA por la clave nueva.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rota PAGOS_CLAVE_MAESTRA")
    parser.add_argument("--nueva", required=True, help="Clave nueva: 32 bytes en base64")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.nueva))
    except ClaveMaestraInvalida as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
