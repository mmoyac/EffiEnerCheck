"""rifas_porteria_pagos_voucher

Premios, datos de transferencia y folio en la rifa; canal, comprador, teléfono, forma de pago,
pago y voucher en las compras; cobros_rifa → imputaciones_rifa; teléfono en usuarios.

Las compras existentes se migran: folio correlativo por fecha de creación, canal desde
registrada_por_admin y forma de pago `gasto_comun` (la versión anterior cobraba todo al cierre).

Revision ID: 2b55e98811e4
Revises: efa24b43f91a
Create Date: 2026-10-02 18:53:00.675988

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '2b55e98811e4'
down_revision: Union[str, None] = 'efa24b43f91a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- rifas ---
    op.add_column('rifas', sa.Column('premios', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False))
    op.add_column('rifas', sa.Column('datos_transferencia', sa.Text(), nullable=True))
    op.add_column('rifas', sa.Column('ultimo_folio', sa.Integer(), server_default='0', nullable=False))

    # --- compras_rifa: columnas nuevas, primero nulables para migrar los datos ---
    op.add_column('compras_rifa', sa.Column('folio', sa.Integer(), nullable=True))
    op.add_column('compras_rifa', sa.Column('canal', sa.String(), nullable=True))
    op.add_column('compras_rifa', sa.Column('comprador_nombre', sa.String(), nullable=True))
    op.add_column('compras_rifa', sa.Column('telefono', sa.String(), nullable=True))
    op.add_column('compras_rifa', sa.Column('medio_pago', sa.String(), nullable=True))
    op.add_column('compras_rifa', sa.Column('pagada', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('compras_rifa', sa.Column('pagada_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('compras_rifa', sa.Column('pago_confirmado_por_id', sa.Integer(), nullable=True))
    op.add_column('compras_rifa', sa.Column('voucher_archivo', sa.String(), nullable=True))
    op.add_column('compras_rifa', sa.Column('voucher_mime', sa.String(), nullable=True))

    op.execute("""
        UPDATE compras_rifa c SET folio = n.rn
        FROM (SELECT id, row_number() OVER (PARTITION BY rifa_id ORDER BY created_at, id) AS rn
              FROM compras_rifa) n
        WHERE c.id = n.id
    """)
    op.execute("UPDATE compras_rifa SET canal = CASE WHEN registrada_por_admin THEN 'administracion' ELSE 'portal' END")
    op.execute("UPDATE compras_rifa SET medio_pago = 'gasto_comun'")
    op.execute("""
        UPDATE rifas r SET ultimo_folio = COALESCE((SELECT max(folio) FROM compras_rifa c WHERE c.rifa_id = r.id), 0)
    """)

    op.alter_column('compras_rifa', 'folio', nullable=False)
    op.alter_column('compras_rifa', 'canal', nullable=False)
    op.alter_column('compras_rifa', 'medio_pago', nullable=False)
    op.create_unique_constraint('uq_compra_rifa_folio', 'compras_rifa', ['rifa_id', 'folio'])
    op.create_foreign_key(
        'compras_rifa_pago_confirmado_por_id_fkey', 'compras_rifa', 'usuarios', ['pago_confirmado_por_id'], ['id']
    )
    op.drop_column('compras_rifa', 'registrada_por_admin')

    # --- cobros_rifa → imputaciones_rifa (cargada en el sistema de gasto común) ---
    op.create_table('imputaciones_rifa',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rifa_id', sa.Integer(), nullable=False),
        sa.Column('parcela_id', sa.Integer(), nullable=False),
        sa.Column('cantidad_numeros', sa.Integer(), nullable=False),
        sa.Column('monto', sa.Integer(), nullable=False),
        sa.Column('cargada', sa.Boolean(), nullable=False),
        sa.Column('cargada_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['parcela_id'], ['parcelas.id']),
        sa.ForeignKeyConstraint(['rifa_id'], ['rifas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rifa_id', 'parcela_id', name='uq_imputacion_rifa_parcela'),
    )
    op.execute("""
        INSERT INTO imputaciones_rifa (rifa_id, parcela_id, cantidad_numeros, monto, cargada, cargada_at)
        SELECT rifa_id, parcela_id, cantidad_numeros, monto, pagado, fecha_pago FROM cobros_rifa
    """)
    op.drop_table('cobros_rifa')

    # --- usuarios ---
    op.add_column('usuarios', sa.Column('telefono', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('usuarios', 'telefono')

    op.create_table('cobros_rifa',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rifa_id', sa.Integer(), nullable=False),
        sa.Column('parcela_id', sa.Integer(), nullable=False),
        sa.Column('cantidad_numeros', sa.Integer(), nullable=False),
        sa.Column('monto', sa.Integer(), nullable=False),
        sa.Column('pagado', sa.Boolean(), nullable=False),
        sa.Column('fecha_pago', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['parcela_id'], ['parcelas.id']),
        sa.ForeignKeyConstraint(['rifa_id'], ['rifas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rifa_id', 'parcela_id', name='uq_cobro_rifa_parcela'),
    )
    op.execute("""
        INSERT INTO cobros_rifa (rifa_id, parcela_id, cantidad_numeros, monto, pagado, fecha_pago)
        SELECT rifa_id, parcela_id, cantidad_numeros, monto, cargada, cargada_at FROM imputaciones_rifa
    """)
    op.drop_table('imputaciones_rifa')

    op.add_column('compras_rifa', sa.Column('registrada_por_admin', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.execute("UPDATE compras_rifa SET registrada_por_admin = (canal <> 'portal')")
    op.drop_constraint('compras_rifa_pago_confirmado_por_id_fkey', 'compras_rifa', type_='foreignkey')
    op.drop_constraint('uq_compra_rifa_folio', 'compras_rifa', type_='unique')
    for col in ('voucher_mime', 'voucher_archivo', 'pago_confirmado_por_id', 'pagada_at', 'pagada',
                'medio_pago', 'telefono', 'comprador_nombre', 'canal', 'folio'):
        op.drop_column('compras_rifa', col)

    op.drop_column('rifas', 'ultimo_folio')
    op.drop_column('rifas', 'datos_transferencia')
    op.drop_column('rifas', 'premios')
