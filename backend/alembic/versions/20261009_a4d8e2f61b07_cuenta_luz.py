"""cuenta_luz

Cuenta corriente de luz por parcela (cambio cobranza-energia): movimientos (saldo inicial y abonos, nunca
se borran: se anulan con motivo) y monto abonado de cada liquidación, derivado por imputación a la deuda
más antigua.

Revision ID: a4d8e2f61b07
Revises: f7c3a1e58b29
Create Date: 2026-10-09 12:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'a4d8e2f61b07'
down_revision: Union[str, None] = 'f7c3a1e58b29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'movimientos_luz',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('condominio_id', sa.Integer(), sa.ForeignKey('condominios.id'), nullable=False),
        sa.Column('parcela_id', sa.Integer(), sa.ForeignKey('parcelas.id'), nullable=False),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('monto', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('nota', sa.Text(), nullable=True),
        sa.Column('boleta_id', sa.Integer(), sa.ForeignKey('boletas_maestras.id'), nullable=True),
        sa.Column('creado_por', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('anulado', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('anulado_por', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('anulado_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('motivo_anulacion', sa.Text(), nullable=True),
        sa.CheckConstraint("tipo IN ('saldo_inicial', 'abono')", name='ck_movimientos_luz_tipo'),
        sa.CheckConstraint('monto > 0', name='ck_movimientos_luz_monto'),
    )
    op.create_index('ix_movimientos_luz_condominio_id', 'movimientos_luz', ['condominio_id'])
    op.create_index('ix_movimientos_luz_parcela_id', 'movimientos_luz', ['parcela_id'])
    op.add_column('liquidaciones_parcelas',
                  sa.Column('monto_abonado', sa.Integer(), nullable=False, server_default='0'))
    # Pagos marcados con la regla anterior: pasan a ser abonos reales de la cuenta (si no, el primer
    # recálculo los perdería), por el total de la liquidación y con su fecha de pago.
    op.execute("""
        INSERT INTO movimientos_luz (condominio_id, parcela_id, tipo, monto, fecha, nota, creado_por)
        SELECT b.condominio_id, l.parcela_id, 'abono', l.total_pagar_mes,
               COALESCE(l.fecha_pago, now())::date,
               'Pago marcado antes de la cuenta corriente de luz', b.creado_por
          FROM liquidaciones_parcelas l
          JOIN boletas_maestras b ON b.id = l.boleta_id
         WHERE l.pagado AND COALESCE(l.total_pagar_mes, 0) > 0
    """)
    op.execute("UPDATE liquidaciones_parcelas SET monto_abonado = COALESCE(total_pagar_mes, 0) WHERE pagado")


def downgrade() -> None:
    op.drop_column('liquidaciones_parcelas', 'monto_abonado')
    op.drop_index('ix_movimientos_luz_parcela_id', table_name='movimientos_luz')
    op.drop_index('ix_movimientos_luz_condominio_id', table_name='movimientos_luz')
    op.drop_table('movimientos_luz')
