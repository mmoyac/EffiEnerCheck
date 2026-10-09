"""menu_cobranza

La opción «Liquidaciones» del menú de la administración pasa a «Cobranza» (/cobranza): /liquidaciones queda
solo para el comunero, que no usa el menú lateral (cambio cobranza-energia).

Revision ID: b6e1f3a92c40
Revises: a4d8e2f61b07
Create Date: 2026-10-09 16:00:00

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'b6e1f3a92c40'
down_revision: Union[str, None] = 'a4d8e2f61b07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE menus SET label = 'Cobranza', path = '/cobranza' WHERE id = 7 AND path = '/liquidaciones'")


def downgrade() -> None:
    op.execute("UPDATE menus SET label = 'Liquidaciones', path = '/liquidaciones' WHERE id = 7 AND path = '/cobranza'")
