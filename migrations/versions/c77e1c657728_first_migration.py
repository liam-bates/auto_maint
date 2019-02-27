"""First Migration

Revision ID: c77e1c657728
Revises: 
Create Date: 2019-02-26 23:25:14.041170

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c77e1c657728'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=256), nullable=False),
    sa.Column('password_hash', sa.String(length=93), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('failed_logins', sa.SmallInteger(), nullable=False),
    sa.Column('blocked', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('user_id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('vehicles',
    sa.Column('vehicle_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('vehicle_name', sa.String(length=128), nullable=False),
    sa.Column('vehicle_built', sa.Date(), nullable=False),
    sa.Column('last_notification', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
    sa.PrimaryKeyConstraint('vehicle_id')
    )
    op.create_table('maintenance',
    sa.Column('maintenance_id', sa.Integer(), nullable=False),
    sa.Column('vehicle_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=True),
    sa.Column('description', sa.String(length=256), nullable=True),
    sa.Column('freq_miles', sa.Integer(), nullable=True),
    sa.Column('freq_months', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.vehicle_id'], ),
    sa.PrimaryKeyConstraint('maintenance_id')
    )
    op.create_table('odometers',
    sa.Column('reading_id', sa.Integer(), nullable=False),
    sa.Column('vehicle_id', sa.Integer(), nullable=False),
    sa.Column('reading', sa.Integer(), nullable=False),
    sa.Column('reading_date', sa.Date(), nullable=False),
    sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.vehicle_id'], ),
    sa.PrimaryKeyConstraint('reading_id')
    )
    op.create_table('logs',
    sa.Column('log_id', sa.Integer(), nullable=False),
    sa.Column('maintenance_id', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('mileage', sa.Integer(), nullable=True),
    sa.Column('notes', sa.String(length=256), nullable=True),
    sa.ForeignKeyConstraint(['maintenance_id'], ['maintenance.maintenance_id'], ),
    sa.PrimaryKeyConstraint('log_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('logs')
    op.drop_table('odometers')
    op.drop_table('maintenance')
    op.drop_table('vehicles')
    op.drop_table('users')
    # ### end Alembic commands ###
