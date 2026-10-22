"""administra_rifas

Permiso de un comunero para administrar las rifas (cambio admin-rifas). Nadie lo tiene al migrar.

Revision ID: e5b8d1c4a703
Revises: d7a2c5e9f310
Create Date: 2026-10-22 10:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'e5b8d1c4a703'
down_revision: Union[str, None] = 'd7a2c5e9f310'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column(
        'administra_rifas', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column('usuarios', 'administra_rifas')
