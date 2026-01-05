"""Add indexes for frequently filtered columns

Revision ID: 005_filter_indexes
Revises: 004_acreage_lineage
Create Date: 2025-01-05

Improves query performance for common filter operations like
county, year_sold, created_at, and investment_score filtering.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_filter_indexes'
down_revision: Union[str, None] = '004_acreage_lineage'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Single-column indexes for common filters
    with op.batch_alter_table('properties', schema=None) as batch_op:
        batch_op.create_index('ix_properties_county', ['county'])
        batch_op.create_index('ix_properties_year_sold', ['year_sold'])
        batch_op.create_index('ix_properties_created_at', ['created_at'])
        batch_op.create_index('ix_properties_investment_score', ['investment_score'])
        batch_op.create_index('ix_properties_amount', ['amount'])
        batch_op.create_index('ix_properties_acreage', ['acreage'])
        batch_op.create_index('ix_properties_is_deleted', ['is_deleted'])

        # Composite indexes for common query patterns
        # State + County (multi-state filtering)
        batch_op.create_index('ix_properties_state_county', ['state', 'county'])

        # Active properties sorted by score (most common listing query)
        batch_op.create_index('ix_properties_active_by_score', ['is_deleted', 'investment_score'])

        # Period filtering (created_at with is_deleted)
        batch_op.create_index('ix_properties_active_by_date', ['is_deleted', 'created_at'])


def downgrade() -> None:
    with op.batch_alter_table('properties', schema=None) as batch_op:
        batch_op.drop_index('ix_properties_active_by_date')
        batch_op.drop_index('ix_properties_active_by_score')
        batch_op.drop_index('ix_properties_state_county')
        batch_op.drop_index('ix_properties_is_deleted')
        batch_op.drop_index('ix_properties_acreage')
        batch_op.drop_index('ix_properties_amount')
        batch_op.drop_index('ix_properties_investment_score')
        batch_op.drop_index('ix_properties_created_at')
        batch_op.drop_index('ix_properties_year_sold')
        batch_op.drop_index('ix_properties_county')
