from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.menu import Menu, menu_roles

MENUS = [
    {"id": 1, "label": "Dashboard",     "path": "/dashboard",     "icon": "home",        "orden": 1},
    {"id": 2, "label": "Condominios",   "path": "/condominios",   "icon": "building",    "orden": 2},
    {"id": 3, "label": "Usuarios",      "path": "/usuarios",      "icon": "users",       "orden": 3},
    {"id": 4, "label": "Parcelas",      "path": "/parcelas",      "icon": "map-pin",     "orden": 4},
    {"id": 5, "label": "Boletas",       "path": "/boletas",       "icon": "file-text",   "orden": 5},
    {"id": 6, "label": "Lecturas",      "path": "/lecturas",      "icon": "activity",    "orden": 6},
    {"id": 7, "label": "Liquidaciones", "path": "/liquidaciones", "icon": "calculator",  "orden": 7},
    {"id": 8, "label": "Auditoría",     "path": "/auditoria",     "icon": "shield",      "orden": 8},
]

# rol_id: 1=super_admin | 2=admin_condominio | 3=lector | 4=parcelero
MENU_ROLES = [
    # Dashboard — todos los roles
    {"menu_id": 1, "rol_id": 1}, {"menu_id": 1, "rol_id": 2},
    {"menu_id": 1, "rol_id": 3}, {"menu_id": 1, "rol_id": 4},
    # Condominios — solo super_admin
    {"menu_id": 2, "rol_id": 1},
    # Usuarios — super_admin y admin_condominio
    {"menu_id": 3, "rol_id": 1}, {"menu_id": 3, "rol_id": 2},
    # Parcelas — super_admin, admin_condominio, lector, parcelero
    {"menu_id": 4, "rol_id": 1}, {"menu_id": 4, "rol_id": 2},
    {"menu_id": 4, "rol_id": 3}, {"menu_id": 4, "rol_id": 4},
    # Boletas — todos los roles
    {"menu_id": 5, "rol_id": 1}, {"menu_id": 5, "rol_id": 2},
    {"menu_id": 5, "rol_id": 3}, {"menu_id": 5, "rol_id": 4},
    # Lecturas — super_admin, admin_condominio, lector
    {"menu_id": 6, "rol_id": 1}, {"menu_id": 6, "rol_id": 2},
    {"menu_id": 6, "rol_id": 3},
    # Liquidaciones — super_admin, admin_condominio, parcelero
    {"menu_id": 7, "rol_id": 1}, {"menu_id": 7, "rol_id": 2},
    {"menu_id": 7, "rol_id": 4},
    # Auditoría — solo super_admin
    {"menu_id": 8, "rol_id": 1},
]


async def seed_menus(db: AsyncSession) -> None:
    for data in MENUS:
        existe = await db.execute(select(Menu).where(Menu.id == data["id"]))
        if existe.scalar_one_or_none():
            continue
        db.add(Menu(**data))

    await db.flush()

    for rel in MENU_ROLES:
        existe = await db.execute(
            select(menu_roles).where(
                menu_roles.c.menu_id == rel["menu_id"],
                menu_roles.c.rol_id == rel["rol_id"],
            )
        )
        if existe.first():
            continue
        await db.execute(insert(menu_roles).values(**rel))

    await db.commit()
    print(f"  ✓ menus: {len(MENUS)} ítems | {len(MENU_ROLES)} asignaciones de roles")
