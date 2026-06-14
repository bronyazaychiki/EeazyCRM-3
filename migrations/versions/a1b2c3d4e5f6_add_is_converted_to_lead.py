"""add is_converted and converted_date to lead

Revision ID: a1b2c3d4e5f6
Revises: 56a0ecfd603a
Create Date: 2026-06-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '56a0ecfd603a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('lead', sa.Column('is_converted', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('lead', sa.Column('converted_date', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('lead', 'converted_date')
    op.drop_column('lead', 'is_converted')
