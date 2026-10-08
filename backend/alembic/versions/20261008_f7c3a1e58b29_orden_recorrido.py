"""orden_recorrido

Posición de cada parcela en el recorrido del lector (cambio orden-recorrido). NULL = sin posición: la app del
lector la muestra después de las ordenadas, en orden numérico. Sin ninguna posición, el orden de siempre.

Revision ID: f7c3a1e58b29
Revises: e5b2c9d47a18
Create Date: 2026-10-08 18:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'f7c3a1e58b29'
down_revision: Union[str, None] = 'e5b2c9d47a18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('parcelas', sa.Column('orden_recorrido', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('parcelas', 'orden_recorrido')
