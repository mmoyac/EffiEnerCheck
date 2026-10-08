"""lectura_inicial

Tipo de período (cambio lectura-inicial): `regular` o `lectura_inicial`. La lectura inicial es un período sin
boleta de la compañía que solo registra la lectura de partida de cada medidor; la primera boleta la toma
como lectura anterior.

Revision ID: e5b2c9d47a18
Revises: d3a8f5b61c72
Create Date: 2026-10-08 10:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'e5b2c9d47a18'
down_revision: Union[str, None] = 'd3a8f5b61c72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('boletas_maestras',
                  sa.Column('tipo', sa.String(length=20), nullable=False, server_default='regular'))
    op.create_check_constraint('ck_boletas_maestras_tipo', 'boletas_maestras',
                               "tipo IN ('regular', 'lectura_inicial')")


def downgrade() -> None:
    hay = op.get_bind().execute(
        sa.text("SELECT count(*) FROM boletas_maestras WHERE tipo = 'lectura_inicial'")).scalar()
    if hay:
        raise RuntimeError(f"Hay {hay} período(s) de lectura inicial: no se puede quitar la columna tipo sin perderlos")
    op.drop_constraint('ck_boletas_maestras_tipo', 'boletas_maestras', type_='check')
    op.drop_column('boletas_maestras', 'tipo')
