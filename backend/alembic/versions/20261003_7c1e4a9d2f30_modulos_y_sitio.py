"""modulos_y_sitio

Plataforma por módulos y parametrización comercial de cada condominio:
condominio_modulos (sitio, portal, energia, rifas), condominio_dominios (dominios de la landing),
portal_url, logo_url y color_primario en condominios, y menus.modulo.

Los condominios existentes quedan con los cuatro módulos (no pierden funciones) y los menús
existentes se etiquetan por path. El seed de menús omite filas existentes, por eso el etiquetado
va aquí.

Revision ID: 7c1e4a9d2f30
Revises: 2b55e98811e4
Create Date: 2026-10-03 13:40:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '7c1e4a9d2f30'
down_revision: Union[str, None] = '2b55e98811e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'condominio_modulos',
        sa.Column('condominio_id', sa.Integer(), nullable=False),
        sa.Column('modulo', sa.String(length=20), nullable=False),
        sa.CheckConstraint("modulo IN ('sitio', 'portal', 'energia', 'rifas')", name='ck_condominio_modulos_modulo'),
        sa.ForeignKeyConstraint(['condominio_id'], ['condominios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('condominio_id', 'modulo'),
    )
    op.create_table(
        'condominio_dominios',
        sa.Column('dominio', sa.String(length=253), nullable=False),
        sa.Column('condominio_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['condominio_id'], ['condominios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('dominio'),
    )
    op.create_index('ix_condominio_dominios_condominio_id', 'condominio_dominios', ['condominio_id'])

    op.add_column('condominios', sa.Column('portal_url', sa.String(), nullable=True))
    op.add_column('condominios', sa.Column('logo_url', sa.String(), nullable=True))
    op.add_column('condominios', sa.Column('color_primario', sa.String(length=7), nullable=True))
    op.create_check_constraint('ck_condominios_color_primario', 'condominios', "color_primario ~ '^#[0-9A-F]{6}$'")

    op.add_column('menus', sa.Column('modulo', sa.String(length=20), nullable=True))

    # --- datos ---
    op.execute(
        "INSERT INTO condominio_modulos (condominio_id, modulo) "
        "SELECT c.id, m.modulo FROM condominios c "
        "CROSS JOIN (VALUES ('sitio'), ('portal'), ('energia'), ('rifas')) AS m(modulo)"
    )
    op.execute("UPDATE menus SET modulo = 'energia' WHERE path IN ('/boletas', '/lecturas', '/liquidaciones')")
    op.execute("UPDATE menus SET modulo = 'rifas' WHERE path = '/rifas'")


def downgrade() -> None:
    op.drop_column('menus', 'modulo')
    op.drop_constraint('ck_condominios_color_primario', 'condominios', type_='check')
    op.drop_column('condominios', 'color_primario')
    op.drop_column('condominios', 'logo_url')
    op.drop_column('condominios', 'portal_url')
    op.drop_index('ix_condominio_dominios_condominio_id', table_name='condominio_dominios')
    op.drop_table('condominio_dominios')
    op.drop_table('condominio_modulos')
