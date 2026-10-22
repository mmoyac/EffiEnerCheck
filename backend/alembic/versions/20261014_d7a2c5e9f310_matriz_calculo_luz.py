"""matriz_calculo_luz

Matriz de cálculo de la luz (cambio matriz-calculo-luz): la del condominio por defecto y la de cada período.
Todo lo existente queda en `fijo_y_variable`, la matriz con que se liquidaba.

Revision ID: d7a2c5e9f310
Revises: c3f9a1d27e54
Create Date: 2026-10-14 10:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'd7a2c5e9f310'
down_revision: Union[str, None] = 'c3f9a1d27e54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CHECK = "{col} IN ('fijo_y_variable', 'cargo_fijo')"


def upgrade() -> None:
    op.add_column('condominios', sa.Column(
        'matriz_calculo_luz', sa.String(20), nullable=False, server_default='fijo_y_variable'))
    op.create_check_constraint('ck_condominios_matriz_calculo_luz', 'condominios',
                               CHECK.format(col='matriz_calculo_luz'))
    op.add_column('boletas_maestras', sa.Column(
        'matriz_calculo', sa.String(20), nullable=False, server_default='fijo_y_variable'))
    op.create_check_constraint('ck_boletas_maestras_matriz_calculo', 'boletas_maestras',
                               CHECK.format(col='matriz_calculo'))


def downgrade() -> None:
    op.drop_constraint('ck_boletas_maestras_matriz_calculo', 'boletas_maestras', type_='check')
    op.drop_column('boletas_maestras', 'matriz_calculo')
    op.drop_constraint('ck_condominios_matriz_calculo_luz', 'condominios', type_='check')
    op.drop_column('condominios', 'matriz_calculo_luz')
