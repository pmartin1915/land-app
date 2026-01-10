"""
Add first deal tracking columns to property_interactions

Revision ID: 007_first_deal
Revises: 006_frontend_polish
Create Date: 2025-01-10
"""

from alembic import op
import sqlalchemy as sa

revision = '007_first_deal'
down_revision = '006_frontend_polish'
branch_labels = None
depends_on = None


def upgrade():
    """Add first deal tracking columns to property_interactions."""
    with op.batch_alter_table('property_interactions') as batch_op:
        batch_op.add_column(sa.Column('is_first_deal', sa.Boolean(),
                                       server_default='0', nullable=False))
        batch_op.add_column(sa.Column('first_deal_stage', sa.String(20),
                                       nullable=True))
        batch_op.add_column(sa.Column('first_deal_assigned_at', sa.DateTime(),
                                       nullable=True))
        batch_op.add_column(sa.Column('first_deal_updated_at', sa.DateTime(),
                                       nullable=True))


def downgrade():
    """Remove first deal tracking columns."""
    with op.batch_alter_table('property_interactions') as batch_op:
        batch_op.drop_column('first_deal_updated_at')
        batch_op.drop_column('first_deal_assigned_at')
        batch_op.drop_column('first_deal_stage')
        batch_op.drop_column('is_first_deal')
