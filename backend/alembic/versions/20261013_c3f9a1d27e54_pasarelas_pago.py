"""pasarelas_pago

Pagos en línea (cambio pasarelas-pago): pasarelas por condominio, intenciones de pago, la forma de pago
`en_linea` de las rifas y la opción «Pasarelas de pago» del menú.

Revision ID: c3f9a1d27e54
Revises: b6e1f3a92c40
Create Date: 2026-10-13 10:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = 'c3f9a1d27e54'
down_revision: Union[str, None] = 'b6e1f3a92c40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEDIOS_ANTES = "ARRAY['efectivo','transferencia','gasto_comun']::varchar[]"
MEDIOS_AHORA = "ARRAY['efectivo','transferencia','gasto_comun','en_linea']::varchar[]"


def upgrade() -> None:
    op.create_table(
        'pasarelas_pago',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('condominio_id', sa.Integer(), sa.ForeignKey('condominios.id'), nullable=False),
        sa.Column('proveedor', sa.String(20), nullable=False),
        sa.Column('nombre_visible', sa.String(), nullable=False),
        sa.Column('ambiente', sa.String(12), nullable=False),
        sa.Column('credenciales_cifradas', sa.LargeBinary()),
        sa.Column('credenciales_at', sa.DateTime(timezone=True)),
        sa.Column('comision_porcentaje', sa.Numeric(7, 4), nullable=False, server_default='0'),
        sa.Column('comision_fija', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('orden', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('activa', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('prueba_at', sa.DateTime(timezone=True)),
        sa.Column('prueba_ok', sa.Boolean()),
        sa.Column('prueba_mensaje', sa.String()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("ambiente IN ('integracion','produccion')", name='ck_pasarelas_pago_ambiente'),
        sa.CheckConstraint('comision_porcentaje >= 0 AND comision_porcentaje < 50', name='ck_pasarelas_pago_comision'),
        sa.CheckConstraint('comision_fija >= 0', name='ck_pasarelas_pago_comision_fija'),
    )
    op.create_index('ix_pasarelas_pago_condominio_id', 'pasarelas_pago', ['condominio_id'])

    op.create_table(
        'intenciones_pago',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('condominio_id', sa.Integer(), sa.ForeignKey('condominios.id'), nullable=False),
        sa.Column('pasarela_id', sa.Integer(), sa.ForeignKey('pasarelas_pago.id'), nullable=False),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('concepto', sa.String(30), nullable=False),
        sa.Column('referencia_id', sa.Integer(), nullable=False),
        sa.Column('descripcion', sa.String(), nullable=False),
        sa.Column('monto', sa.Integer(), nullable=False),
        sa.Column('comision', sa.Integer(), nullable=False),
        sa.Column('total', sa.Integer(), nullable=False),
        sa.Column('estado', sa.String(12), nullable=False, server_default='INICIADO'),
        sa.Column('vence_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('orden_comercio', sa.String(26), nullable=False, unique=True),
        sa.Column('token_proveedor', sa.String()),
        sa.Column('transaccion_proveedor', sa.String()),
        sa.Column('email_pagador', sa.String()),
        sa.Column('autorizacion', sa.String()),
        sa.Column('ultimos_digitos', sa.String(4)),
        sa.Column('medio', sa.String()),
        sa.Column('monto_confirmado', sa.Integer()),
        sa.Column('respuesta_proveedor', postgresql.JSONB()),
        sa.Column('motivo', sa.Text()),
        sa.Column('consultado_at', sa.DateTime(timezone=True)),
        sa.Column('confirmado_at', sa.DateTime(timezone=True)),
        sa.Column('resuelta_at', sa.DateTime(timezone=True)),
        sa.Column('resuelta_por_id', sa.Integer(), sa.ForeignKey('usuarios.id')),
        sa.Column('nota_resolucion', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "estado IN ('INICIADO','CONFIRMADO','RECHAZADO','EXPIRADO','EN_REVISION')",
            name='ck_intenciones_pago_estado',
        ),
    )
    op.create_index('ix_intenciones_pago_condominio_id', 'intenciones_pago', ['condominio_id'])
    op.create_index('ix_intenciones_pago_pasarela_id', 'intenciones_pago', ['pasarela_id'])
    op.create_index('ix_intenciones_pago_estado', 'intenciones_pago', ['estado'])
    op.create_index('ix_intenciones_pago_token_proveedor', 'intenciones_pago', ['token_proveedor'])
    op.create_index('ix_intenciones_pago_transaccion_proveedor', 'intenciones_pago', ['transaccion_proveedor'])

    op.add_column('compras_rifa', sa.Column(
        'intencion_pago_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('intenciones_pago.id'),
    ))
    op.create_index('ix_compras_rifa_intencion_pago_id', 'compras_rifa', ['intencion_pago_id'])

    op.drop_constraint('ck_rifas_medios_pago', 'rifas', type_='check')
    op.create_check_constraint(
        'ck_rifas_medios_pago', 'rifas', f"cardinality(medios_pago) > 0 AND medios_pago <@ {MEDIOS_AHORA}",
    )

    op.execute(
        "INSERT INTO menus (id, label, path, icon, orden, activo, modulo) "
        "VALUES (10, 'Pasarelas de pago', '/pasarelas', 'credit-card', 10, true, NULL) ON CONFLICT (id) DO NOTHING"
    )
    op.execute(
        "INSERT INTO menu_roles (menu_id, rol_id) SELECT 10, r.id FROM roles r "
        "WHERE r.nombre IN ('super_admin', 'admin_condominio') ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DELETE FROM menu_roles WHERE menu_id = 10")
    op.execute("DELETE FROM menus WHERE id = 10")
    op.execute("UPDATE rifas SET medios_pago = array_remove(medios_pago, 'en_linea')")
    op.drop_constraint('ck_rifas_medios_pago', 'rifas', type_='check')
    op.create_check_constraint(
        'ck_rifas_medios_pago', 'rifas', f"cardinality(medios_pago) > 0 AND medios_pago <@ {MEDIOS_ANTES}",
    )
    op.drop_index('ix_compras_rifa_intencion_pago_id', 'compras_rifa')
    op.drop_column('compras_rifa', 'intencion_pago_id')
    op.drop_table('intenciones_pago')
    op.drop_table('pasarelas_pago')
