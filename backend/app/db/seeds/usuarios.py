from sqlalchemy import insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.usuario import Usuario
from app.models.usuario_parcela import usuario_parcelas

_PWD = hash_password("admin123")

# parcela_id lookup (ver seeds/parcelas.py):
#   id 12 = "13 A"  |  id 13 = "13 B"  |  id 24 = "23"
USUARIOS = [
    {
        "id": 1,
        "nombre": "Marcelo Moya",
        "email": "mmoyainfo@gmail.com",
        "password_hash": _PWD,
        "rol_id": 1,        # super_admin
        "condominio_id": None,
    },
    {
        "id": 2,
        "nombre": "Henry Hernández",
        "email": "hhernandez@santalaura.cl",
        "password_hash": _PWD,
        "rol_id": 2,        # admin_condominio
        "condominio_id": 1,
    },
    {
        "id": 3,
        "nombre": "Claudio Portero",
        "email": "cportero@santalaura.cl",
        "password_hash": _PWD,
        "rol_id": 3,        # lector
        "condominio_id": 1,
    },
    {
        "id": 4,
        "nombre": "Marcelo Moya",
        # Alias Gmail: llega a mmoyainfo@gmail.com pero es técnicamente distinto
        "email": "mmoyainfo+parcela@gmail.com",
        "password_hash": _PWD,
        "rol_id": 4,        # comunero
        "condominio_id": 1,
    },
    {
        "id": 5,
        "nombre": "German Chacon",
        "email": "gchacon@santalaura.cl",
        "password_hash": _PWD,
        "rol_id": 4,        # comunero
        "condominio_id": 1,
    },
]

# Sin id fijo: en bases con usuarios cargados después del seed, un id fijo chocaría.
# Se identifican por email.
USUARIOS_POR_EMAIL = [
    {
        # Cuenta compartida por los turnos de portería (rifas solidarias)
        "nombre": "Portería Santa Laura",
        "email": "porteria@santalaura.cl",
        "password_hash": _PWD,
        "rol_id": 5,        # porteria
        "condominio_id": 1,
    },
]

USUARIO_PARCELAS = [
    {"usuario_id": 4, "parcela_id": 24},   # Marcelo Moya  → parcela "23"
    {"usuario_id": 5, "parcela_id": 12},   # German Chacon → parcela "13 A"
    {"usuario_id": 5, "parcela_id": 13},   # German Chacon → parcela "13 B"
]


async def seed_usuarios(db: AsyncSession) -> None:
    for data in USUARIOS:
        existe = await db.execute(select(Usuario).where(Usuario.id == data["id"]))
        if existe.scalar_one_or_none():
            continue
        db.add(Usuario(**data))

    await db.flush()

    # Los inserts con id explícito no avanzan la secuencia
    await db.execute(text("SELECT setval('usuarios_id_seq', (SELECT max(id) FROM usuarios))"))
    for data in USUARIOS_POR_EMAIL:
        existe = await db.execute(select(Usuario).where(Usuario.email == data["email"]))
        if existe.scalar_one_or_none():
            continue
        db.add(Usuario(**data))

    await db.flush()

    # Asignar parcelas (ignorar duplicados)
    for rel in USUARIO_PARCELAS:
        existe = await db.execute(
            select(usuario_parcelas).where(
                usuario_parcelas.c.usuario_id == rel["usuario_id"],
                usuario_parcelas.c.parcela_id == rel["parcela_id"],
            )
        )
        if existe.first():
            continue
        await db.execute(insert(usuario_parcelas).values(**rel))

    await db.commit()
    print(f"  ✓ usuarios: {len(USUARIOS) + len(USUARIOS_POR_EMAIL)} registros | {len(USUARIO_PARCELAS)} asignaciones de parcelas")
