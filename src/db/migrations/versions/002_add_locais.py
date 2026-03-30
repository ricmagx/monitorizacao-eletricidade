"""Adiciona tabela locais e UniqueConstraint em comparacoes.

Revision ID: 002
Revises: 001
Create Date: 2026-03-30
"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'locais',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('cpe', sa.String(64), nullable=False, unique=True),
        sa.Column('current_supplier', sa.String(128)),
        sa.Column('current_plan_contains', sa.String(128)),
        sa.Column('power_label', sa.String(32)),
        sa.Column('created_at', sa.DateTime),
    )
    op.create_unique_constraint(
        'uq_comparacao_loc_month', 'comparacoes', ['location_id', 'year_month']
    )


def downgrade():
    op.drop_constraint('uq_comparacao_loc_month', 'comparacoes')
    op.drop_table('locais')
