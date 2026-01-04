"""Add multi-state scoring columns

Revision ID: 003_multistate_scores
Revises: 002_multistate
Create Date: 2025-01-03

Adds buy_hold_score and wholesale_score columns to properties table
for the new multi-state scoring engine.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_multistate_scores'
down_revision: Union[str, None] = '002_multistate'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new scoring columns to properties table
    with op.batch_alter_table('properties', schema=None) as batch_op:
        batch_op.add_column(sa.Column('buy_hold_score', sa.Float(), nullable=True,
                                       comment='Time-adjusted investment score (0-100)'))
        batch_op.add_column(sa.Column('wholesale_score', sa.Float(), nullable=True,
                                       comment='Wholesale viability score (0-100)'))
        batch_op.add_column(sa.Column('effective_cost', sa.Float(), nullable=True,
                                       comment='Total cost including quiet title'))
        batch_op.add_column(sa.Column('time_penalty_factor', sa.Float(), nullable=True,
                                       comment='Time decay multiplier (0-1)'))


def downgrade() -> None:
    with op.batch_alter_table('properties', schema=None) as batch_op:
        batch_op.drop_column('time_penalty_factor')
        batch_op.drop_column('effective_cost')
        batch_op.drop_column('wholesale_score')
        batch_op.drop_column('buy_hold_score')
