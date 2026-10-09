"""
Cuenta corriente de luz por parcela (cambio cobranza-energia).

Cargos: el saldo inicial (onboarding) y las liquidaciones de los períodos PUBLICADOS.
Abonos: pagos de cualquier monto registrados por la administración (los anulados no cuentan).
Saldo = cargos − abonos (negativo = saldo a favor).

Los abonos se imputan a la deuda más antigua: primero el saldo inicial, luego los meses en orden.
De esa imputación salen, para cada liquidación, `monto_abonado`, `pagado` y `fecha_pago` (la fecha del abono
que la terminó de cubrir). Nunca se marcan a mano: `recalcular()` los rehace cada vez que cambia la cuenta.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.boleta import BoletaMaestra
from app.models.cuenta_luz import MovimientoLuz
from app.models.liquidacion import LiquidacionParcela

SALDO_INICIAL = "saldo_inicial"
ABONO = "abono"


@dataclass
class Cargo:
    tipo: str                    # saldo_inicial | mes
    fecha: date                  # fecha del saldo inicial o mes del período
    monto: int
    cubierto: int = 0
    fecha_pago: date | None = None
    liquidacion: LiquidacionParcela | None = None
    movimiento: MovimientoLuz | None = None
    boleta_id: int | None = None

    @property
    def estado(self) -> str:
        if self.cubierto >= self.monto:
            return "pagado"
        return "parcial" if self.cubierto > 0 else "pendiente"


@dataclass
class Cuenta:
    parcela_id: int
    cargos: list[Cargo] = field(default_factory=list)
    abonos: list[MovimientoLuz] = field(default_factory=list)          # vigentes, en orden
    anulados: list[MovimientoLuz] = field(default_factory=list)

    @property
    def total_cargos(self) -> int:
        return sum(c.monto for c in self.cargos)

    @property
    def total_abonos(self) -> int:
        return sum(a.monto for a in self.abonos)

    @property
    def saldo(self) -> int:
        return self.total_cargos - self.total_abonos


async def cuentas(db: AsyncSession, parcela_ids: list[int]) -> dict[int, Cuenta]:
    """Arma la cuenta de cada parcela e imputa los abonos (no escribe nada)."""
    resultado = {pid: Cuenta(parcela_id=pid) for pid in parcela_ids}
    if not parcela_ids:
        return resultado

    movimientos = (await db.execute(
        select(MovimientoLuz).where(MovimientoLuz.parcela_id.in_(parcela_ids))
        .order_by(MovimientoLuz.fecha, MovimientoLuz.id)
    )).scalars().all()
    liquidaciones = (await db.execute(
        select(LiquidacionParcela, BoletaMaestra)
        .join(BoletaMaestra, LiquidacionParcela.boleta_id == BoletaMaestra.id)
        .where(LiquidacionParcela.parcela_id.in_(parcela_ids), BoletaMaestra.boleta_visible_usuarios == True)  # noqa: E712
        .order_by(BoletaMaestra.periodo_mes)
    )).all()

    for m in movimientos:
        cuenta = resultado[m.parcela_id]
        if m.anulado:
            cuenta.anulados.append(m)
        elif m.tipo == SALDO_INICIAL:
            cuenta.cargos.append(Cargo(tipo=SALDO_INICIAL, fecha=m.fecha, monto=m.monto, movimiento=m, boleta_id=m.boleta_id))
        else:
            cuenta.abonos.append(m)
    for liq, boleta in liquidaciones:
        resultado[liq.parcela_id].cargos.append(Cargo(
            tipo="mes", fecha=boleta.periodo_mes, monto=liq.total_pagar_mes or 0, liquidacion=liq, boleta_id=boleta.id))

    for cuenta in resultado.values():
        # El saldo inicial va primero (es la deuda más antigua), luego los meses en orden
        cuenta.cargos.sort(key=lambda c: (c.tipo != SALDO_INICIAL, c.fecha))
        _imputar(cuenta)
    return resultado


def _imputar(cuenta: Cuenta) -> None:
    """Reparte los abonos, en orden, sobre los cargos más antiguos primero."""
    abonos = iter(cuenta.abonos)
    actual, disponible = None, 0
    for cargo in cuenta.cargos:
        while cargo.cubierto < cargo.monto:
            if disponible == 0:
                actual = next(abonos, None)
                if actual is None:
                    return
                disponible = actual.monto
            tomado = min(disponible, cargo.monto - cargo.cubierto)
            cargo.cubierto += tomado
            disponible -= tomado
            if cargo.cubierto >= cargo.monto:
                cargo.fecha_pago = actual.fecha


async def recalcular(db: AsyncSession, parcela_ids: list[int]) -> dict[int, Cuenta]:
    """Rehace monto_abonado / pagado / fecha_pago de las liquidaciones publicadas según la imputación."""
    resultado = await cuentas(db, parcela_ids)
    for cuenta in resultado.values():
        for cargo in cuenta.cargos:
            liq = cargo.liquidacion
            if liq is None:
                continue
            liq.monto_abonado = cargo.cubierto
            liq.pagado = cargo.monto == 0 or cargo.cubierto >= cargo.monto
            liq.fecha_pago = (datetime.combine(cargo.fecha_pago, time(12), tzinfo=timezone.utc)
                              if liq.pagado and cargo.fecha_pago else None)
    await db.flush()
    return resultado


async def recalcular_periodo(db: AsyncSession, boleta_id: int) -> None:
    """Al publicar un período sus liquidaciones pasan a ser cargos: se reimputan los abonos (p. ej. saldo a favor)."""
    ids = (await db.execute(
        select(LiquidacionParcela.parcela_id).where(LiquidacionParcela.boleta_id == boleta_id))).scalars().all()
    await recalcular(db, list(ids))
