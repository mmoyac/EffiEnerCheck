from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import registrar_auditoria
from app.core.dependencies import AdminRequired, AnyRoleRequired, TenantId, get_db
from app.models.boleta import BoletaMaestra
from app.models.liquidacion import LiquidacionParcela
from app.models.parcela import Parcela
from app.models.usuario import Usuario
from app.schemas.liquidacion import LiquidacionParcelaResponse
from app.services.periodos import exigir_periodo_regular

router = APIRouter(prefix="/liquidaciones", tags=["liquidaciones"])

DB = Annotated[AsyncSession, Depends(get_db)]


async def _get_boleta(boleta_id: int, db: AsyncSession) -> BoletaMaestra:
    result = await db.execute(select(BoletaMaestra).where(BoletaMaestra.id == boleta_id))
    boleta = result.scalar_one_or_none()
    if not boleta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Boleta no encontrada")
    return boleta


@router.get("/", response_model=list[LiquidacionParcelaResponse])
async def list_liquidaciones(
    current_user: Annotated[Usuario, Depends(AnyRoleRequired)],
    tenant_id: TenantId,
    boleta_id: int | None = None,
    db: DB = None,
):
    stmt = select(LiquidacionParcela).join(Parcela, LiquidacionParcela.parcela_id == Parcela.id)
    if tenant_id is not None:
        stmt = stmt.where(Parcela.condominio_id == tenant_id)
    if boleta_id:
        stmt = stmt.where(LiquidacionParcela.boleta_id == boleta_id)

    # Comunero: solo ve sus liquidaciones Y solo cuando el período está publicado (cerrar no basta:
    # antes de publicar las liquidaciones aún pueden reabrirse y cambiar)
    if current_user.rol.nombre == "comunero":
        ids = [p.id for p in current_user.parcelas]
        stmt = stmt.where(LiquidacionParcela.parcela_id.in_(ids))
        stmt = stmt.join(BoletaMaestra, LiquidacionParcela.boleta_id == BoletaMaestra.id)
        stmt = stmt.where(BoletaMaestra.boleta_visible_usuarios == True)  # noqa: E712

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{liquidacion_id}", response_model=LiquidacionParcelaResponse)
async def get_liquidacion(
    liquidacion_id: int,
    current_user: Annotated[Usuario, Depends(AnyRoleRequired)],
    tenant_id: TenantId,
    db: DB,
):
    result = await db.execute(
        select(LiquidacionParcela)
        .join(Parcela, LiquidacionParcela.parcela_id == Parcela.id)
        .where(LiquidacionParcela.id == liquidacion_id)
    )
    liq = result.scalar_one_or_none()
    if not liq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liquidación no encontrada")

    parcela_result = await db.execute(select(Parcela).where(Parcela.id == liq.parcela_id))
    parcela = parcela_result.scalar_one_or_none()
    if tenant_id is not None and parcela.condominio_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a esta liquidación")

    if current_user.rol.nombre == "comunero":
        if liq.parcela_id not in [p.id for p in current_user.parcelas]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a esta liquidación")
        boleta = await _get_boleta(liq.boleta_id, db)
        if not boleta.boleta_visible_usuarios:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La liquidación aún no está publicada.",
            )

    return liq


@router.post("/calcular/{boleta_id}", response_model=list[LiquidacionParcelaResponse])
async def calcular_liquidaciones(
    boleta_id: int,
    current_user: Annotated[Usuario, Depends(AdminRequired)],
    tenant_id: TenantId,
    db: DB,
):
    """Dispara el Motor EnerCheck. Las lecturas pueden estar abiertas (permite recalcular tras correcciones)."""
    boleta = await _get_boleta(boleta_id, db)
    exigir_periodo_regular(boleta)

    if boleta.liquidaciones_cerradas:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El período ya está cerrado. No se puede recalcular.",
        )

    # El cálculo exige que el admin ya haya juzgado qué ítems entran al reparto.
    if boleta.estado != "validada":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Debes corroborar el desglose antes de calcular. Revisa los ítems de la "
                "boleta y confirma cuáles entran al reparto."
            ),
        )

    from app.services.enercheck import EnerCheckError, calcular_liquidaciones_boleta  # noqa: PLC0415

    try:
        liquidaciones = await calcular_liquidaciones_boleta(boleta_id, tenant_id, current_user, db)
    except EnerCheckError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    await registrar_auditoria(
        db, usuario_id=current_user.id, condominio_id=tenant_id,
        accion="CALCULAR_LIQUIDACIONES",
        detalles={"boleta_id": boleta_id, "total_parcelas": len(liquidaciones)},
    )
    await db.commit()
    return liquidaciones
