"""Add acreage data lineage columns

Revision ID: 004_acreage_lineage
Revises: 003_multistate_scores
Create Date: 2025-01-04

Adds columns to track where acreage data came from (API vs parsed)
and confidence level for better data quality management.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_acreage_lineage'
down_revision: Union[str, None] = '003_multistate_scores'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add acreage lineage columns to properties table
    with op.batch_alter_table('properties', schema=None) as batch_op:
        batch_op.add_column(sa.Column('acreage_source', sa.String(20), nullable=True,
                                       comment='Source: api, parsed_explicit, parsed_plss, parsed_dimensions'))
        batch_op.add_column(sa.Column('acreage_confidence', sa.String(10), nullable=True,
                                       comment='Confidence: high, medium, low'))
        batch_op.add_column(sa.Column('acreage_raw_text', sa.String(200), nullable=True,
                                       comment='Original text that was parsed for acreage'))


def downgrade() -> None:
    with op.batch_alter_table('properties', schema=None) as batch_op:
        batch_op.drop_column('acreage_raw_text')
        batch_op.drop_column('acreage_confidence')
        batch_op.drop_column('acreage_source')
