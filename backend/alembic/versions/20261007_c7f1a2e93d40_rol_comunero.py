"""rol_comunero

El rol `parcelero` pasa a llamarse `comunero`, el término que usa la comunidad. Se renombra la fila
existente (id 4): los usuarios conservan su rol, sus parcelas y sus sesiones.

Revision ID: c7f1a2e93d40
Revises: b4e2c7d91f30
Create Date: 2026-10-07 10:00:00

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'c7f1a2e93d40'
down_revision: Union[str, None] = 'b4e2c7d91f30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE roles SET nombre = 'comunero', "
        "descripcion = 'Vecino de una parcela: consulta sus liquidaciones y compra rifas' "
        "WHERE id = 4 AND nombre = 'parcelero'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE roles SET nombre = 'parcelero', descripcion = 'Visualiza sus liquidaciones' "
        "WHERE id = 4 AND nombre = 'comunero'"
    )
