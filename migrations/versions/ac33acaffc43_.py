"""empty message

Revision ID: ac33acaffc43
Revises: c77e1c657728
Create Date: 2019-03-06 16:01:05.685608

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ac33acaffc43'
down_revision = 'c77e1c657728'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users', 'blocked',
               existing_type=sa.BOOLEAN(),
               nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users', 'blocked',
               existing_type=sa.BOOLEAN(),
               nullable=True)
    # ### end Alembic commands ###
