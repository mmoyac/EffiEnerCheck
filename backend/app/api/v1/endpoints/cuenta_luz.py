"""
Cuenta corriente de luz y cobranza (cambio cobranza-energia).

El cargo de luz se cobra en el gasto común. La administración registra abonos (de cualquier monto) y el
sistema los imputa a la deuda más antigua (services/cuenta_luz.py). Un movimiento nunca se borra: se anula
con motivo, y todo queda en la auditoría.
"""
from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import registrar_auditoria
from app.core.dependencies import AdminRequired, AnyRoleRequired, TenantId, get_db
from app.models.cuenta_luz import MovimientoLuz
from app.models.parcela import Parcela
from app.models.usuario import Usuario
from app.schemas.cuenta_luz import (
    AbonoOut, AnularAbonoRequest, CargoOut, CuentaOut, DeudorOut, PeriodoCobranza, RegistrarAbonosRequest,
    ResumenCobranza, TotalesCobranza,
)
from app.services import cuenta_luz
from app.services.cuenta_luz import ABONO, SALDO_INICIAL, Cargo, Cuenta

router = APIRouter(prefix="/cuenta-luz", tags=["cuenta-luz"])

DB = Annotated[AsyncSession, Depends(get_db)]
ROLES_ADMIN = ("super_admin", "admin_condominio")


def _orden_natural(numero: str):
    digitos = "".join(ch for ch in numero if ch.isdigit())
    return (int(digitos) if digitos else 0, numero)


def _cargo_out(c: Cargo) -> CargoOut:
    return CargoOut(tipo=c.tipo, fecha=c.fecha, boleta_id=c.boleta_id, monto=c.monto, cubierto=c.cubierto,
                    estado=c.estado, fecha_pago=c.fecha_pago)


def _cuenta_out(parcela: Parcela, cuenta: Cuenta) -> CuentaOut:
    abonos = sorted(cuenta.abonos + cuenta.anulados, key=lambda m: (m.fecha, m.id))
    return CuentaOut(
        parcela_id=parcela.id, numero_parcela=parcela.numero_parcela, propietario_nombre=parcela.propietario_nombre,
        total_cargos=cuenta.total_cargos, total_abonos=cuenta.total_abonos, saldo=cuenta.saldo,
        cargos=[_cargo_out(c) for c in cuenta.cargos],
        abonos=[AbonoOut(id=m.id, fecha=m.fecha, monto=m.monto, nota=m.nota, creado_por=m.creado_por,
                         creado_en=m.creado_en, anulado=m.anulado, anulado_en=m.anulado_en,
                         motivo_anulacion=m.motivo_anulacion) for m in abonos if m.tipo == ABONO],
    )


async def _parcela_o_404(parcela_id: int, tenant_id: int | None, db: AsyncSession) -> Parcela:
    parcela = await db.get(Parcela, parcela_id)
    if not parcela or (tenant_id is not None and parcela.condominio_id != tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcela no encontrada")
    return parcela


@router.get("/resumen", response_model=ResumenCobranza)
async def resumen(
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
    condominio_id: int | None = None,
):
    """Cobranza del condominio: totales, por período (y saldo inicial) y deudores."""
    cid = tenant_id if tenant_id is not None else condominio_id
    if cid is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debe especificar condominio_id")
    parcelas = (await db.execute(select(Parcela).where(Parcela.condominio_id == cid))).scalars().all()
    todas = await cuenta_luz.cuentas(db, [p.id for p in parcelas])

    periodos: dict[tuple, PeriodoCobranza] = {}
    deudores: list[DeudorOut] = []
    for p in parcelas:
        cuenta = todas[p.id]
        for c in cuenta.cargos:
            clave = (c.tipo, c.boleta_id if c.tipo == "mes" else None)
            per = periodos.setdefault(clave, PeriodoCobranza(
                tipo=c.tipo, boleta_id=clave[1], fecha=c.fecha, emitido=0, cubierto=0, pendiente=0, cargos=0, pagados=0))
            per.emitido += c.monto
            per.cubierto += c.cubierto
            per.pendiente += c.monto - c.cubierto
            per.cargos += 1
            per.pagados += c.estado == "pagado"
        if cuenta.saldo > 0:
            deudores.append(DeudorOut(
                parcela_id=p.id, numero_parcela=p.numero_parcela, propietario_nombre=p.propietario_nombre,
                saldo=cuenta.saldo, pendientes=[_cargo_out(c) for c in cuenta.cargos if c.estado != "pagado"],
                ultimo_abono=max((a.fecha for a in cuenta.abonos), default=None)))

    saldo_inicial = sum(c.monto for cu in todas.values() for c in cu.cargos if c.tipo == SALDO_INICIAL)
    cargos = sum(cu.total_cargos for cu in todas.values())
    return ResumenCobranza(
        totales=TotalesCobranza(
            saldo_inicial=saldo_inicial, emitido=cargos - saldo_inicial, cargos=cargos,
            abonado=sum(cu.total_abonos for cu in todas.values()),
            por_cobrar=sum(cu.saldo for cu in todas.values() if cu.saldo > 0),
            a_favor=-sum(cu.saldo for cu in todas.values() if cu.saldo < 0)),
        # Lo más reciente primero; el saldo inicial (lo más antiguo) al final
        periodos=sorted(periodos.values(), key=lambda x: (x.tipo == "mes", x.fecha), reverse=True),
        deudores=sorted(deudores, key=lambda d: _orden_natural(d.numero_parcela)),
    )


@router.get("/parcelas/{parcela_id}", response_model=CuentaOut)
async def cuenta_de_parcela(
    parcela_id: int,
    current_user: Annotated[Usuario, Depends(AnyRoleRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """Movimientos y saldo de una parcela. Administración: cualquiera del condominio; comunero: solo las suyas."""
    rol = current_user.rol.nombre
    if rol not in ROLES_ADMIN and not (rol == "comunero" and parcela_id in [p.id for p in current_user.parcelas]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcela no encontrada")
    parcela = await _parcela_o_404(parcela_id, tenant_id, db)
    return _cuenta_out(parcela, (await cuenta_luz.cuentas(db, [parcela.id]))[parcela.id])


@router.post("/abonos", response_model=list[CuentaOut], status_code=status.HTTP_201_CREATED)
async def registrar_abonos(
    data: RegistrarAbonosRequest,
    request: Request,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """Registra uno o varios abonos (todo o nada). Cada uno queda en la auditoría con el saldo antes y después."""
    if data.fecha > date.today():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La fecha del abono no puede ser futura")
    ids = [i.parcela_id for i in data.items]
    if len(set(ids)) != len(ids):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Hay parcelas repetidas")
    parcelas = {pid: await _parcela_o_404(pid, tenant_id, db) for pid in ids}
    antes = await cuenta_luz.cuentas(db, ids)

    for item in data.items:
        db.add(MovimientoLuz(condominio_id=parcelas[item.parcela_id].condominio_id, parcela_id=item.parcela_id,
                             tipo=ABONO, monto=item.monto, fecha=data.fecha, nota=data.nota, creado_por=current_user.id))
    await db.flush()
    despues = await cuenta_luz.recalcular(db, ids)
    ip = request.client.host if request.client else None
    for item in data.items:
        await registrar_auditoria(
            db, usuario_id=current_user.id, condominio_id=parcelas[item.parcela_id].condominio_id,
            accion="REGISTRAR_ABONO_LUZ", ip_address=ip,
            detalles={"parcela_id": item.parcela_id, "monto": item.monto, "fecha": data.fecha.isoformat(),
                      "nota": data.nota, "saldo_antes": antes[item.parcela_id].saldo,
                      "saldo_despues": despues[item.parcela_id].saldo})
    await db.commit()
    return [_cuenta_out(parcelas[pid], (await cuenta_luz.cuentas(db, [pid]))[pid]) for pid in ids]


@router.post("/abonos/{movimiento_id}/anular", response_model=CuentaOut)
async def anular_abono(
    movimiento_id: int,
    data: AnularAbonoRequest,
    request: Request,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """Anula un abono registrado por error. No se borra: queda con su motivo, quién y cuándo."""
    mov = await db.get(MovimientoLuz, movimiento_id)
    if not mov or (tenant_id is not None and mov.condominio_id != tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Abono no encontrado")
    if mov.tipo != ABONO:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="El saldo inicial se corrige desde la planilla de la lectura inicial")
    if mov.anulado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El abono ya está anulado")
    antes = (await cuenta_luz.cuentas(db, [mov.parcela_id]))[mov.parcela_id].saldo
    mov.anulado = True
    mov.anulado_por = current_user.id
    mov.anulado_en = datetime.now(timezone.utc)
    mov.motivo_anulacion = data.motivo
    await db.flush()
    despues = (await cuenta_luz.recalcular(db, [mov.parcela_id]))[mov.parcela_id]
    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=mov.condominio_id, accion="ANULAR_ABONO_LUZ",
        ip_address=request.client.host if request.client else None,
        detalles={"movimiento_id": mov.id, "parcela_id": mov.parcela_id, "monto": mov.monto,
                  "fecha": mov.fecha.isoformat(), "motivo": data.motivo, "saldo_antes": antes,
                  "saldo_despues": despues.saldo})
    await db.commit()
    parcela = await db.get(Parcela, mov.parcela_id)
    return _cuenta_out(parcela, (await cuenta_luz.cuentas(db, [mov.parcela_id]))[mov.parcela_id])

