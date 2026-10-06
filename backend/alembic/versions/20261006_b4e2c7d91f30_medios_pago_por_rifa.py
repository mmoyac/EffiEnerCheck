"""medios_pago_por_rifa

Cada rifa define qué formas de pago acepta (al menos una). Las rifas existentes quedan con las tres,
como funcionaban hasta ahora; las compras ya hechas conservan su forma de pago.

Revision ID: b4e2c7d91f30
Revises: a6738843cca6
Create Date: 2026-10-06 20:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b4e2c7d91f30'
down_revision: Union[str, None] = 'a6738843cca6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('rifas', sa.Column(
        'medios_pago', sa.ARRAY(sa.String()), nullable=False,
        server_default=sa.text("'{efectivo,transferencia,gasto_comun}'"),
    ))
    op.create_check_constraint(
        'ck_rifas_medios_pago', 'rifas',
        "cardinality(medios_pago) > 0 AND medios_pago <@ ARRAY['efectivo','transferencia','gasto_comun']::varchar[]",
    )


def downgrade() -> None:
    op.drop_constraint('ck_rifas_medios_pago', 'rifas', type_='check')
    op.drop_column('rifas', 'medios_pago')
