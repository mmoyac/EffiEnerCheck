"""acceso_por_invitacion

Cada usuario crea su propia clave con un enlace de un solo uso (spec acceso-por-enlace):
- usuarios.password_hash admite NULL = cuenta pendiente (no inicia sesión hasta crear su clave);
- usuarios.clave_cambiada_en: los JWT emitidos antes de esa hora dejan de valer;
- enlaces_acceso: invitaciones y recuperaciones, guardando solo el sha256 del token.

Revision ID: a6738843cca6
Revises: 7c1e4a9d2f30
Create Date: 2026-10-06 14:11:25.753867

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a6738843cca6'
down_revision: Union[str, None] = '7c1e4a9d2f30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('enlaces_acceso',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.Column('token_hash', sa.CHAR(length=64), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('expira_en', sa.DateTime(timezone=True), nullable=False),
    sa.Column('usado_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('anulado_en', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("tipo IN ('invitacion', 'recuperacion')", name='ck_enlaces_acceso_tipo'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_index('ix_enlaces_acceso_usuario_tipo', 'enlaces_acceso', ['usuario_id', 'tipo'], unique=False)
    op.add_column('usuarios', sa.Column('clave_cambiada_en', sa.DateTime(timezone=True), nullable=True))
    op.alter_column('usuarios', 'password_hash',
               existing_type=sa.VARCHAR(),
               nullable=True)


def downgrade() -> None:
    # Volver a NOT NULL exige que no haya cuentas pendientes: se falla con un mensaje claro
    pendientes = op.get_bind().execute(sa.text("SELECT count(*) FROM usuarios WHERE password_hash IS NULL")).scalar()
    if pendientes:
        raise RuntimeError(f"Hay {pendientes} cuenta(s) sin clave: no se puede volver a password_hash NOT NULL")
    op.alter_column('usuarios', 'password_hash',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.drop_column('usuarios', 'clave_cambiada_en')
    op.drop_index('ix_enlaces_acceso_usuario_tipo', table_name='enlaces_acceso')
    op.drop_table('enlaces_acceso')
