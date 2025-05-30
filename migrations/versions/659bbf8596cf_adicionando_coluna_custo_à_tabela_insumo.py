"""Adicionando coluna custo à tabela insumo

Revision ID: 659bbf8596cf
Revises: 714148255ee6
Create Date: 2025-04-25 16:14:38.599444

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '659bbf8596cf'
down_revision = '714148255ee6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('insumo', schema=None) as batch_op:
        batch_op.add_column(sa.Column('custo', sa.Float(), nullable=False))
        batch_op.alter_column('unidade',
               existing_type=sa.VARCHAR(length=20),
               nullable=False)
        batch_op.alter_column('quantidade',
               existing_type=sa.INTEGER(),
               type_=sa.Float(),
               existing_nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('insumo', schema=None) as batch_op:
        batch_op.alter_column('quantidade',
               existing_type=sa.Float(),
               type_=sa.INTEGER(),
               existing_nullable=False)
        batch_op.alter_column('unidade',
               existing_type=sa.VARCHAR(length=20),
               nullable=True)
        batch_op.drop_column('custo')

    # ### end Alembic commands ###
