"""Adiciona precos de tarifario (vazio e fora de vazio) ao local.

Revision ID: 004
Revises: 003
Create Date: 2026-04-05
"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('locais') as batch_op:
        batch_op.add_column(sa.Column('preco_vazio_kwh', sa.Float, nullable=True))
        batch_op.add_column(sa.Column('preco_fora_vazio_kwh', sa.Float, nullable=True))


def downgrade():
    with op.batch_alter_table('locais') as batch_op:
        batch_op.drop_column('preco_fora_vazio_kwh')
        batch_op.drop_column('preco_vazio_kwh')
