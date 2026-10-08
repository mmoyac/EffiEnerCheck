"""foto_medidor

Foto del medidor asociada a la lectura (cambio foto-medidor). El archivo vive en /app/privado/lecturas;
aquí solo su nombre, su sha256 y la toma que documenta (`foto_fecha_toma`, que puede quedar distinta de
`fecha_toma` si después se corrige el valor: la foto es la evidencia de esa corrección).

Revision ID: d3a8f5b61c72
Revises: c7f1a2e93d40
Create Date: 2026-10-07 12:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'd3a8f5b61c72'
down_revision: Union[str, None] = 'c7f1a2e93d40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('lecturas_parcelas', sa.Column('foto_archivo', sa.String(length=64), nullable=True))
    op.add_column('lecturas_parcelas', sa.Column('foto_sha256', sa.String(length=64), nullable=True))
    op.add_column('lecturas_parcelas', sa.Column('foto_fecha_toma', sa.DateTime(timezone=True), nullable=True))
    op.add_column('lecturas_parcelas', sa.Column('foto_subida_en', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('lecturas_parcelas', 'foto_subida_en')
    op.drop_column('lecturas_parcelas', 'foto_fecha_toma')
    op.drop_column('lecturas_parcelas', 'foto_sha256')
    op.drop_column('lecturas_parcelas', 'foto_archivo')
