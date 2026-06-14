"""add is_active and display_order to config models

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
    # LeadSource: add is_active and display_order
    op.add_column('lead_source', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('lead_source', sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'))

    # LeadStatus: add is_active and display_order
    op.add_column('lead_status', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('lead_status', sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'))

    # DealStage: add is_active (already has display_order)
    op.add_column('deal_stage', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))

    # Set display_order for existing lead_source rows based on id ordering
    op.execute("UPDATE lead_source SET display_order = id")

    # Set display_order for existing lead_status rows based on id ordering
    op.execute("UPDATE lead_status SET display_order = id")

    # deal_stage already has correct display_order values from install


def downgrade():
    op.drop_column('deal_stage', 'is_active')
    op.drop_column('lead_status', 'display_order')
    op.drop_column('lead_status', 'is_active')
    op.drop_column('lead_source', 'display_order')
    op.drop_column('lead_source', 'is_active')
