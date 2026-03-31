"""Adiciona coluna detalhe_json a custos_reais.

Armazena breakdown detalhado de linhas de fatura (energia, potencia, impostos)
e custo real por kWh calculado com todos os custos fixos e impostos incluidos.

Revision ID: 003
Revises: 002
Create Date: 2026-03-31
"""
from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('custos_reais') as batch_op:
        batch_op.add_column(sa.Column('detalhe_json', sa.Text, nullable=True))


def downgrade():
    with op.batch_alter_table('custos_reais') as batch_op:
        batch_op.drop_column('detalhe_json')
