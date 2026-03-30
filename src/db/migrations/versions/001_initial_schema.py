"""Initial schema -- consumo_mensal, comparacoes, custos_reais.

Revision ID: 001
Revises:
Create Date: 2026-03-30
"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'consumo_mensal',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('location_id', sa.String(64), nullable=False),
        sa.Column('year_month', sa.String(7), nullable=False),
        sa.Column('total_kwh', sa.Float, nullable=False),
        sa.Column('vazio_kwh', sa.Float, nullable=False),
        sa.Column('fora_vazio_kwh', sa.Float, nullable=False),
        sa.UniqueConstraint('location_id', 'year_month', name='uq_consumo_loc_month'),
    )
    op.create_table(
        'comparacoes',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('location_id', sa.String(64), nullable=False),
        sa.Column('year_month', sa.String(7), nullable=False),
        sa.Column('top_3_json', sa.Text),
        sa.Column('current_supplier_result_json', sa.Text),
        sa.Column('generated_at', sa.String(32)),
        sa.Column('cached_at', sa.DateTime),
    )
    op.create_table(
        'custos_reais',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('location_id', sa.String(64), nullable=False),
        sa.Column('year_month', sa.String(7), nullable=False),
        sa.Column('custo_eur', sa.Float, nullable=False),
        sa.Column('source', sa.String(64)),
        sa.Column('created_at', sa.DateTime),
        sa.UniqueConstraint('location_id', 'year_month', name='uq_custos_loc_month'),
    )


def downgrade():
    op.drop_table('custos_reais')
    op.drop_table('comparacoes')
    op.drop_table('consumo_mensal')
