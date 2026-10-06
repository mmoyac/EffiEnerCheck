from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import registrar_auditoria
from app.core.dependencies import AnyRoleRequired, LectorRequired, TenantId, get_db
from app.models.boleta import BoletaMaestra
from app.models.lectura import LecturaParcela
from app.models.parcela import Parcela
from app.models.usuario import Usuario
from app.schemas.lectura import (
    LecturaParcelaCreate, LecturaParcelaResponse, LecturaParcelaUpdate,
    ResultadoSincronizacion, SincronizarLecturasRequest, SincronizarLecturasResponse,
)

router = APIRouter(prefix="/lecturas", tags=["lecturas"])

DB = Annotated[AsyncSession, Depends(get_db)]


async def _verificar_boleta_abierta(boleta_id: int, db: AsyncSession) -> BoletaMaestra:
    """Lanza 409 si las lecturas del período ya fueron cerradas."""
    result = await db.execute(select(BoletaMaestra).where(BoletaMaestra.id == boleta_id))
    boleta = result.scalar_one_or_none()
    if not boleta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Boleta no encontrada")
    if boleta.lecturas_cerradas:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Las lecturas de este período están cerradas y no se pueden modificar",
        )
    return boleta


@router.get("/", response_model=list[LecturaParcelaResponse])
async def list_lecturas(
    current_user: Annotated[Usuario, Depends(AnyRoleRequired)],
    tenant_id: TenantId,
    boleta_id: int | None = None,
    db: DB = None,
):
    stmt = select(LecturaParcela).join(Parcela, LecturaParcela.parcela_id == Parcela.id)
    if tenant_id is not None:
        stmt = stmt.where(Parcela.condominio_id == tenant_id)
    if boleta_id:
        stmt = stmt.where(LecturaParcela.boleta_id == boleta_id)
    if current_user.rol.nombre == "parcelero":
        ids = [p.id for p in current_user.parcelas]
        stmt = stmt.where(LecturaParcela.parcela_id.in_(ids))

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=LecturaParcelaResponse, status_code=status.HTTP_201_CREATED)
async def crear_lectura(
    data: LecturaParcelaCreate,
    current_user: Annotated[Usuario, Depends(LectorRequired)],
    tenant_id: TenantId,
    db: DB,
):
    await _verificar_boleta_abierta(data.boleta_id, db)

    parcela_result = await db.execute(select(Parcela).where(Parcela.id == data.parcela_id))
    parcela = parcela_result.scalar_one_or_none()
    if not parcela:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcela no encontrada")
    if tenant_id is not None and parcela.condominio_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Parcela no pertenece a su condominio")

    lectura = LecturaParcela(
        parcela_id=data.parcela_id,
        boleta_id=data.boleta_id,
        lectura_anterior=data.lectura_anterior,
        lectura_actual=data.lectura_actual,
        kwh_consumidos=data.kwh_consumidos,
        lector_id=current_user.id,
        fecha_toma=data.fecha_toma,
    )
    db.add(lectura)
    await db.flush()

    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=parcela.condominio_id,
        accion="CREATE_LECTURA",
        detalles={"lectura_id": lectura.id, "parcela_id": data.parcela_id, "kwh_consumidos": lectura.kwh_consumidos},
    )
    await db.commit()
    await db.refresh(lectura)
    return lectura


@router.patch("/{lectura_id}", response_model=LecturaParcelaResponse)
async def actualizar_lectura(
    lectura_id: int,
    data: LecturaParcelaUpdate,
    current_user: Annotated[Usuario, Depends(LectorRequired)],
    tenant_id: TenantId,
    db: DB,
):
    result = await db.execute(
        select(LecturaParcela).join(Parcela, LecturaParcela.parcela_id == Parcela.id)
        .where(LecturaParcela.id == lectura_id)
    )
    lectura = result.scalar_one_or_none()
    if not lectura:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lectura no encontrada")

    await _verificar_boleta_abierta(lectura.boleta_id, db)

    parcela_result = await db.execute(select(Parcela).where(Parcela.id == lectura.parcela_id))
    parcela = parcela_result.scalar_one_or_none()
    if tenant_id is not None and parcela.condominio_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a esta lectura")

    cambios = data.model_dump(exclude_unset=True)
    nueva_actual = cambios.get("lectura_actual", lectura.lectura_actual)
    nueva_anterior = cambios.get("lectura_anterior", lectura.lectura_anterior)
    if nueva_actual < nueva_anterior:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La lectura actual ({nueva_actual}) no puede ser menor que la anterior ({nueva_anterior})",
        )

    estado_anterior = {k: getattr(lectura, k) for k in cambios}
    estado_anterior["lector_id"] = lectura.lector_id

    for campo, valor in cambios.items():
        setattr(lectura, campo, valor)
    if "lectura_anterior" in cambios or "lectura_actual" in cambios:
        lectura.kwh_consumidos = lectura.lectura_actual - lectura.lectura_anterior

    lectura.lector_id = current_user.id
    cambios["lector_id"] = current_user.id

    audit_before = {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in estado_anterior.items()}
    audit_after = {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in cambios.items()}

    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=parcela.condominio_id,
        accion="UPDATE_LECTURA", detalles={"before": audit_before, "after": audit_after},
    )
    await db.commit()
    await db.refresh(lectura)
    return lectura


# ---- Sincronización de lecturas tomadas sin conexión (cambio lecturas-sin-conexion) ----------------------

def _mismo_instante(a: datetime | None, b: datetime | None) -> bool:
    """Igualdad al milisegundo: el navegador guarda la hora con milisegundos y la base con microsegundos."""
    if a is None or b is None:
        return a is b
    return abs((a - b).total_seconds()) < 0.001


def _mismo_valor(a: float, b: float) -> bool:
    return abs(a - b) < 1e-9


@router.post("/sincronizar", response_model=SincronizarLecturasResponse)
async def sincronizar_lecturas(
    data: SincronizarLecturasRequest,
    current_user: Annotated[Usuario, Depends(LectorRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """
    Aplica un lote de lecturas tomadas sin conexión. Cada una se resuelve por separado (savepoint propio):
    - aplicada: coincidía con la base descargada (o ya estaba aplicada: reintento idempotente);
    - conflicto: alguien la cambió en el servidor después de la descarga; no se pisa;
    - rechazada: período cerrado, contador regresivo u otro condominio.
    """
    resultados: list[ResultadoSincronizacion] = []
    for item in data.items:
        lectura = (await db.execute(
            select(LecturaParcela).where(LecturaParcela.id == item.lectura_id)
        )).scalar_one_or_none()
        if lectura is None:
            resultados.append(ResultadoSincronizacion(lectura_id=item.lectura_id, estado="rechazada",
                                                      motivo="La lectura no existe"))
            continue
        parcela = await db.get(Parcela, lectura.parcela_id)
        if tenant_id is not None and parcela.condominio_id != tenant_id:
            resultados.append(ResultadoSincronizacion(lectura_id=item.lectura_id, estado="rechazada",
                                                      motivo="La lectura no pertenece a su condominio"))
            continue
        vigente = LecturaParcelaResponse.model_validate(lectura)

        # Reintento: ya está exactamente lo que se envía
        if _mismo_valor(lectura.lectura_actual, item.lectura_actual) and _mismo_instante(lectura.fecha_toma, item.fecha_toma):
            resultados.append(ResultadoSincronizacion(lectura_id=lectura.id, estado="aplicada", lectura=vigente))
            continue

        boleta = await db.get(BoletaMaestra, lectura.boleta_id)
        if boleta.lecturas_cerradas:
            resultados.append(ResultadoSincronizacion(lectura_id=lectura.id, estado="rechazada", lectura=vigente,
                                                      motivo="Las lecturas del período ya están cerradas"))
            continue
        if not (_mismo_valor(lectura.lectura_actual, item.base.lectura_actual)
                and _mismo_instante(lectura.fecha_toma, item.base.fecha_toma)):
            resultados.append(ResultadoSincronizacion(
                lectura_id=lectura.id, estado="conflicto", lectura=vigente,
                motivo="La lectura cambió en el servidor después de preparar el recorrido"))
            continue
        if item.lectura_actual < lectura.lectura_anterior:
            resultados.append(ResultadoSincronizacion(
                lectura_id=lectura.id, estado="rechazada", lectura=vigente,
                motivo=f"La lectura actual ({item.lectura_actual:g}) no puede ser menor que la anterior "
                       f"({lectura.lectura_anterior:g})"))
            continue

        async with db.begin_nested():
            antes = {"lectura_actual": lectura.lectura_actual,
                     "fecha_toma": lectura.fecha_toma.isoformat() if lectura.fecha_toma else None,
                     "lector_id": lectura.lector_id}
            lectura.lectura_actual = item.lectura_actual
            lectura.fecha_toma = item.fecha_toma
            lectura.kwh_consumidos = lectura.lectura_actual - lectura.lectura_anterior
            lectura.lector_id = current_user.id
            await registrar_auditoria(
                db, usuario_id=current_user.id, condominio_id=parcela.condominio_id, accion="UPDATE_LECTURA",
                detalles={"before": antes, "origen": "sin_conexion",
                          "after": {"lectura_actual": item.lectura_actual, "fecha_toma": item.fecha_toma.isoformat(),
                                    "lector_id": current_user.id}},
            )
        await db.flush()
        resultados.append(ResultadoSincronizacion(lectura_id=lectura.id, estado="aplicada",
                                                  lectura=LecturaParcelaResponse.model_validate(lectura)))
    await db.commit()
    return SincronizarLecturasResponse(resultados=resultados)
