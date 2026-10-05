"""
Cambia la clave de una cuenta desde la consola del servidor (la pide por teclado).

    python -m app.db.cambiar_clave --email <correo>
    python -m app.db.cambiar_clave --expuestas      # lista las cuentas con la clave pública del seed

Sirve cuando no se puede entrar a la aplicación: el super admin perdió su clave, o el backend
no arranca porque alguna cuenta conserva la clave pública del seed (app/arranque.py).
"""
import argparse
import asyncio
import getpass
import sys

from sqlalchemy import select

from app.arranque import CLAVES_CONOCIDAS, usuarios_con_clave_conocida
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.usuario import Usuario

import app.db.base  # noqa: F401 — registra todos los modelos (relaciones por nombre)

LARGO_MINIMO_CLAVE = 10


async def listar_expuestas() -> None:
    async with AsyncSessionLocal() as db:
        expuestos = await usuarios_con_clave_conocida(db)
    await engine.dispose()
    print(f"{len(expuestos)} cuenta(s) con la clave pública del seed")
    for email in expuestos:
        print(f"  {email}")


async def cambiar(email: str) -> None:
    async with AsyncSessionLocal() as db:
        usuario = (await db.execute(select(Usuario).where(Usuario.email == email))).scalar_one_or_none()
        if usuario is None:
            raise ValueError(f"No existe la cuenta {email}")
        clave = getpass.getpass(f"Nueva clave para {email}: ")
        if len(clave) < LARGO_MINIMO_CLAVE or clave in CLAVES_CONOCIDAS:
            raise ValueError(f"La clave debe tener al menos {LARGO_MINIMO_CLAVE} caracteres y no ser una clave conocida")
        if getpass.getpass("Repite la clave: ") != clave:
            raise ValueError("Las claves no coinciden")
        usuario.password_hash = hash_password(clave)
        await db.commit()
    await engine.dispose()
    print(f"Clave actualizada: {email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cambia la clave de una cuenta desde la consola del servidor")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--email")
    grupo.add_argument("--expuestas", action="store_true")
    args = parser.parse_args()
    try:
        asyncio.run(listar_expuestas() if args.expuestas else cambiar(args.email.strip().lower()))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
