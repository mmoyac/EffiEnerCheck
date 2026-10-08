"""
Carga inicial de producción copiada desde la base de desarrollo, sin datos de prueba (ver DEPLOY.md).

  1. En desarrollo:  python -m app.db.copiar_desde_desarrollo exportar --condominio "Santa Laura" --salida /tmp/sl.carga.json
  2. En producción:  python -m app.db.copiar_desde_desarrollo importar /tmp/sl.carga.json \
                         --portal-url https://portal.comunidadsantalaura.cl --dominio comunidadsantalaura.cl [--simular]

El JSON lleva solo la configuración del condominio (módulos, color, dirección, plan), sus parcelas y sus
comuneros con teléfono y parcelas asignadas. Nunca claves: en producción todos quedan como cuentas
pendientes y cada uno crea su clave con su invitación (spec acceso-por-enlace). Quedan fuera los datos operativos (boletas, lecturas, liquidaciones,
rifas, auditoría), los otros condominios y las cuentas del seed (app/db/seeds/usuarios.py).

Importar es idempotente: no duplica nada ni toca las cuentas que ya existen. El JSON tiene datos personales:
nunca va al repositorio (*.carga.json está en .gitignore) y se borra después de importar.
"""
import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import registrar_auditoria
from app.core.modulos import MODULOS
from app.db.cargar_residentes import _orden_natural
from app.db.session import AsyncSessionLocal, engine
from app.models.condominio import Condominio
from app.models.condominio_modulo import CondominioDominio, CondominioModulo
from app.models.parcela import Parcela
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.models.usuario_parcela import usuario_parcelas
from app.utils.dominio import normalizar_dominio

import app.db.base  # noqa: F401 — registra todos los modelos (relaciones por nombre)

VERSION_FORMATO = 1


def emails_del_seed() -> set[str]:
    """Cuentas de prueba: nunca pasan a producción. Import diferido: el seed calcula hashes al importarse."""
    from app.db.seeds.usuarios import USUARIOS, USUARIOS_POR_EMAIL
    return {u["email"].lower() for u in USUARIOS + USUARIOS_POR_EMAIL}


# ---- Exportar (base de desarrollo) ----------------------------------------------------------------------

async def exportar(db: AsyncSession, condominio_nombre: str) -> dict:
    condominio = (await db.execute(
        select(Condominio).options(selectinload(Condominio.modulos)).where(Condominio.nombre == condominio_nombre)
    )).scalar_one_or_none()
    if condominio is None:
        raise ValueError(f"No existe el condominio '{condominio_nombre}'")

    parcelas = (await db.execute(
        select(Parcela).where(Parcela.condominio_id == condominio.id)
    )).scalars().all()
    numero_por_id = {p.id: p.numero_parcela for p in parcelas}

    excluidos = emails_del_seed()
    comuneros = (await db.execute(
        select(Usuario).options(selectinload(Usuario.parcelas)).join(Rol)
        .where(Usuario.condominio_id == condominio.id, Rol.nombre == "comunero")
        .order_by(Usuario.email)
    )).scalars().all()

    return {
        "version": VERSION_FORMATO,
        "condominio": {
            "nombre": condominio.nombre,
            "rut_comunidad": condominio.rut_comunidad,
            "direccion": condominio.direccion,
            "plan_suscripcion": condominio.plan_suscripcion,
            "color_primario": condominio.color_primario,
            "modulos": sorted(m.modulo for m in condominio.modulos),
        },
        "parcelas": [
            {"numero_parcela": p.numero_parcela, "propietario_nombre": p.propietario_nombre, "activa": p.activa}
            for p in sorted(parcelas, key=lambda p: _orden_natural(p.numero_parcela))
        ],
        "residentes": [
            {
                "nombre": u.nombre,
                "email": u.email.lower(),
                "telefono": u.telefono,
                "parcelas": sorted((numero_por_id[p.id] for p in u.parcelas if p.id in numero_por_id),
                                   key=_orden_natural),
            }
            for u in comuneros if u.email.lower() not in excluidos
        ],
    }


# ---- Importar (base de producción) ---------------------------------------------------------------------

@dataclass
class Resumen:
    condominio_creado: bool = False
    modulos_agregados: int = 0
    dominios_agregados: int = 0
    parcelas_creadas: int = 0
    usuarios_creados: int = 0
    asignaciones_creadas: int = 0
    avisos: list[str] = field(default_factory=list)


async def importar(
    db: AsyncSession,
    datos: dict,
    *,
    portal_url: str | None,
    dominios: list[str],
) -> Resumen:
    """Aplica la carga en la sesión, sin commit: quien llama confirma o descarta."""
    if datos.get("version") != VERSION_FORMATO:
        raise ValueError(f"Formato de exportación no soportado: {datos.get('version')}")
    resumen = Resumen()
    c = datos["condominio"]
    # dict.fromkeys: www.x.cl y x.cl son el mismo dominio una vez normalizados.
    dominios = list(dict.fromkeys(normalizar_dominio(d) for d in dominios))
    modulos_invalidos = set(c["modulos"]) - set(MODULOS)
    if modulos_invalidos:
        raise ValueError(f"Módulos desconocidos: {sorted(modulos_invalidos)}")

    # ---- Condominio: se crea completo; si ya existe solo se completa lo que falte ----------------------
    condominio = (await db.execute(
        select(Condominio).options(selectinload(Condominio.modulos), selectinload(Condominio.dominios_sitio))
        .where(Condominio.rut_comunidad == c["rut_comunidad"])
    )).scalar_one_or_none()
    if condominio is None:
        condominio = Condominio(
            nombre=c["nombre"],
            rut_comunidad=c["rut_comunidad"],
            direccion=c["direccion"],
            plan_suscripcion=c["plan_suscripcion"],
            color_primario=c["color_primario"],
            portal_url=portal_url,
            activo=True,
            modulos=[],
            dominios_sitio=[],
        )
        db.add(condominio)
        resumen.condominio_creado = True
    else:
        condominio.portal_url = condominio.portal_url or portal_url
        condominio.color_primario = condominio.color_primario or c["color_primario"]

    actuales = {m.modulo for m in condominio.modulos}
    for modulo in c["modulos"]:
        if modulo not in actuales:
            condominio.modulos.append(CondominioModulo(modulo=modulo))
            resumen.modulos_agregados += 1

    propios = {d.dominio for d in condominio.dominios_sitio}
    for dominio in dominios:
        if dominio in propios:
            continue
        ajeno = (await db.execute(
            select(CondominioDominio).where(CondominioDominio.dominio == dominio)
        )).scalar_one_or_none()
        if ajeno is not None:
            resumen.avisos.append(f"el dominio {dominio} ya es de otro condominio; no se asigna")
            continue
        condominio.dominios_sitio.append(CondominioDominio(dominio=dominio))
        propios.add(dominio)
        resumen.dominios_agregados += 1
    await db.flush()

    # ---- Parcelas ------------------------------------------------------------------------------------
    parcelas = {
        p.numero_parcela: p
        for p in (await db.execute(select(Parcela).where(Parcela.condominio_id == condominio.id))).scalars()
    }
    for p in datos["parcelas"]:
        if p["numero_parcela"] in parcelas:
            continue
        parcela = Parcela(
            condominio_id=condominio.id,
            numero_parcela=p["numero_parcela"],
            propietario_nombre=p["propietario_nombre"],
            activa=p["activa"],
        )
        db.add(parcela)
        parcelas[p["numero_parcela"]] = parcela
        resumen.parcelas_creadas += 1
    await db.flush()

    # ---- Comuneros y asignaciones -------------------------------------------------------------------
    excluidos = emails_del_seed()
    rol_comunero = (await db.execute(select(Rol).where(Rol.nombre == "comunero"))).scalar_one()
    for r in datos["residentes"]:
        email = r["email"].lower()
        if email in excluidos:
            resumen.avisos.append(f"{email}: es una cuenta de prueba del seed; se omite")
            continue
        usuario = (await db.execute(
            select(Usuario).options(selectinload(Usuario.rol)).where(Usuario.email == email)
        )).scalar_one_or_none()
        if usuario is None:
            usuario = Usuario(
                nombre=r["nombre"],
                email=email,
                password_hash=None,   # pendiente: crea su clave con la invitación
                rol_id=rol_comunero.id,
                condominio_id=condominio.id,
                telefono=r["telefono"],
            )
            db.add(usuario)
            await db.flush()
            resumen.usuarios_creados += 1
        elif usuario.rol.nombre != "comunero" or usuario.condominio_id != condominio.id:
            resumen.avisos.append(f"{email}: ya es una cuenta {usuario.rol.nombre} de otro condominio o rol; "
                                  "no se asignan parcelas")
            continue

        for numero in r["parcelas"]:
            parcela = parcelas.get(numero)
            if parcela is None:
                resumen.avisos.append(f"{email}: la parcela {numero} no está en la exportación")
                continue
            asignada = (await db.execute(select(usuario_parcelas).where(
                usuario_parcelas.c.usuario_id == usuario.id,
                usuario_parcelas.c.parcela_id == parcela.id,
            ))).first()
            if not asignada:
                await db.execute(insert(usuario_parcelas).values(usuario_id=usuario.id, parcela_id=parcela.id))
                resumen.asignaciones_creadas += 1

    super_admin_id = (await db.execute(
        select(Usuario.id).join(Rol).where(Rol.nombre == "super_admin").order_by(Usuario.id).limit(1)
    )).scalar_one_or_none()
    if super_admin_id is not None:
        await registrar_auditoria(
            db,
            usuario_id=super_admin_id,
            condominio_id=condominio.id,
            accion="CARGA_INICIAL",
            detalles={
                "condominio_creado": resumen.condominio_creado,
                "modulos_agregados": resumen.modulos_agregados,
                "dominios_agregados": resumen.dominios_agregados,
                "parcelas_creadas": resumen.parcelas_creadas,
                "usuarios_creados": resumen.usuarios_creados,
                "asignaciones_creadas": resumen.asignaciones_creadas,
            },
        )
    return resumen


# ---- Consola ------------------------------------------------------------------------------------------

async def main_exportar(args: argparse.Namespace) -> None:
    async with AsyncSessionLocal() as db:
        datos = await exportar(db, args.condominio)
    await engine.dispose()
    salida = Path(args.salida)
    salida.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    salida.chmod(0o600)
    print(f"Exportado {salida}: {len(datos['parcelas'])} parcelas, {len(datos['residentes'])} comuneros, "
          f"módulos {', '.join(datos['condominio']['modulos'])}. Tiene datos personales: bórralo al terminar.")


async def main_importar(args: argparse.Namespace) -> None:
    datos = json.loads(Path(args.archivo).read_text(encoding="utf-8"))
    print(f"Archivo: {datos['condominio']['nombre']}, {len(datos['parcelas'])} parcelas, "
          f"{len(datos['residentes'])} comuneros")
    async with AsyncSessionLocal() as db:
        resumen = await importar(db, datos, portal_url=args.portal_url, dominios=args.dominio)
        if args.simular:
            await db.rollback()
        else:
            await db.commit()
    await engine.dispose()

    print(("SIMULACIÓN (no se guardó nada) — " if args.simular else "") +
          f"condominio {'creado' if resumen.condominio_creado else 'existente'} | "
          f"módulos nuevos: {resumen.modulos_agregados} | dominios nuevos: {resumen.dominios_agregados} | "
          f"parcelas nuevas: {resumen.parcelas_creadas} | usuarios nuevos: {resumen.usuarios_creados} | "
          f"asignaciones nuevas: {resumen.asignaciones_creadas}")
    for aviso in resumen.avisos:
        print(f"  AVISO {aviso}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga inicial de producción copiada desde desarrollo")
    sub = parser.add_subparsers(dest="orden", required=True)

    p_exp = sub.add_parser("exportar", help="Exporta un condominio de la base de desarrollo a JSON")
    p_exp.add_argument("--condominio", required=True, help='Nombre del condominio, p. ej. "Santa Laura"')
    p_exp.add_argument("--salida", required=True, help="Ruta del JSON (*.carga.json)")

    p_imp = sub.add_parser("importar", help="Importa el JSON en la base de producción")
    p_imp.add_argument("archivo", help="Ruta del JSON exportado")
    p_imp.add_argument("--portal-url", help="URL del portal del condominio, p. ej. https://portal.dominio.cl")
    p_imp.add_argument("--dominio", action="append", default=[], help="Dominio de la landing (repetible)")
    p_imp.add_argument("--simular", action="store_true", help="Muestra el resumen sin guardar")

    args = parser.parse_args()
    try:
        asyncio.run(main_exportar(args) if args.orden == "exportar" else main_importar(args))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
