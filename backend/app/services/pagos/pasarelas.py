"""Pasarelas de un condominio: credenciales, prueba vigente y las que se ofrecen al pagador."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.pago import PasarelaPago
from app.services.pagos import cifrado
from app.services.pagos.comision import total_con_comision
from app.services.pagos.proveedores import REGISTRO, adaptador
from app.services.pagos.proveedores.base import PasarelaEnUso


class CredencialesInvalidas(ValueError):
    pass


def ahora() -> datetime:
    return datetime.now(timezone.utc)


def validar_credenciales(proveedor: str, credenciales: dict[str, str]) -> dict[str, str]:
    """Exactamente los campos del proveedor, todos con valor. Devuelve solo esos campos."""
    campos = [c.nombre for c in adaptador(proveedor).campos_credenciales]
    faltan = [c.etiqueta for c in adaptador(proveedor).campos_credenciales if not credenciales.get(c.nombre)]
    if faltan:
        raise CredencialesInvalidas(f"Faltan credenciales: {', '.join(faltan)}")
    return {c: credenciales[c] for c in campos}


def guardar_credenciales(pasarela: PasarelaPago, credenciales: dict[str, str]) -> None:
    """Cifra y reemplaza las credenciales (la pasarela ya debe tener id). Desactiva la pasarela."""
    pasarela.credenciales_cifradas = cifrado.cifrar(
        validar_credenciales(pasarela.proveedor, credenciales), cifrado.aad(pasarela.condominio_id, pasarela.id)
    )
    pasarela.credenciales_at = ahora()
    pasarela.activa = False


def en_uso(pasarela: PasarelaPago) -> PasarelaEnUso:
    """Descifra las credenciales en memoria. Lanza cifrado.CredencialesIlegibles o ClaveMaestraInvalida."""
    credenciales = cifrado.descifrar(
        pasarela.credenciales_cifradas or b"", cifrado.aad(pasarela.condominio_id, pasarela.id)
    )
    return PasarelaEnUso(id=pasarela.id, ambiente=pasarela.ambiente, credenciales=credenciales)


def prueba_vigente(pasarela: PasarelaPago) -> bool:
    return bool(
        pasarela.prueba_ok and pasarela.prueba_at and pasarela.credenciales_at
        and pasarela.prueba_at > pasarela.credenciales_at
    )


def ofrecible(pasarela: PasarelaPago) -> bool:
    """Activa, de un proveedor conocido y, en producción, nunca de ambiente integración."""
    if not pasarela.activa or pasarela.proveedor not in REGISTRO or not pasarela.credenciales_cifradas:
        return False
    return not (settings.es_produccion and pasarela.ambiente != "produccion")


async def pasarelas_ofrecibles(db: AsyncSession, condominio_id: int) -> list[PasarelaPago]:
    filas = (
        await db.execute(
            select(PasarelaPago)
            .where(PasarelaPago.condominio_id == condominio_id, PasarelaPago.activa == True)  # noqa: E712
            .order_by(PasarelaPago.orden, PasarelaPago.id)
        )
    ).scalars().all()
    return [p for p in filas if ofrecible(p)]


def cotizar(pasarela: PasarelaPago, monto: int) -> tuple[int, int, str | None]:
    """(comisión, total, motivo de exclusión). Hay motivo si el total no alcanza el mínimo del proveedor."""
    total = total_con_comision(monto, pasarela.comision_porcentaje, pasarela.comision_fija)
    minimo = adaptador(pasarela.proveedor).monto_minimo
    motivo = None
    if total < minimo:
        motivo = f"{pasarela.nombre_visible} exige un pago mínimo de ${minimo:,}".replace(",", ".")
    return total - monto, total, motivo


async def hay_pasarela_para(db: AsyncSession, condominio_id: int, monto: int) -> bool:
    return any(cotizar(p, monto)[2] is None for p in await pasarelas_ofrecibles(db, condominio_id))
