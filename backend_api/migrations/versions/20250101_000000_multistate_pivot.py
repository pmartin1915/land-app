"""Add multi-state and wholesaling support

Revision ID: 002_multistate
Revises: 001_initial
Create Date: 2025-01-01

Adds fields to properties table for multi-state tax deed tracking
and wholesaling pipeline. Preserves all existing Alabama data.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_multistate'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add new columns to properties table using batch mode for SQLite
    with op.batch_alter_table('properties', schema=None) as batch_op:
        batch_op.add_column(sa.Column('state', sa.String(2), nullable=True))
        batch_op.add_column(sa.Column('sale_type', sa.String(20), nullable=True))
        batch_op.add_column(sa.Column('redemption_period_days', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('time_to_ownership_days', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('estimated_market_value', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('wholesale_spread', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('owner_type', sa.String(20), nullable=True))
        batch_op.add_column(sa.Column('data_source', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('auction_date', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('auction_platform', sa.String(100), nullable=True))
        batch_op.create_index('ix_properties_state', ['state'])

    # Step 2: Set defaults for existing Alabama records
    op.execute("""
        UPDATE properties
        SET state = 'AL',
            sale_type = 'tax_lien',
            redemption_period_days = 1460,
            time_to_ownership_days = 2000,
            data_source = 'alabama_dor',
            auction_platform = 'GovEase'
        WHERE state IS NULL
    """)

    # Step 3: Create state_configs table
    op.create_table(
        'state_configs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('state_code', sa.String(2), nullable=False, unique=True),
        sa.Column('state_name', sa.String(50), nullable=False),
        sa.Column('sale_type', sa.String(20), nullable=False),
        sa.Column('redemption_period_days', sa.Integer(), nullable=True),
        sa.Column('interest_rate', sa.Float(), nullable=True),
        sa.Column('quiet_title_cost_estimate', sa.Float(), nullable=True),
        sa.Column('time_to_ownership_days', sa.Integer(), nullable=False),
        sa.Column('auction_platform', sa.String(100), nullable=True),
        sa.Column('scraper_module', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('recommended_for_beginners', sa.Boolean(), default=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        if_not_exists=True
    )

    # Step 4: Create wholesale_pipeline table
    op.create_table(
        'wholesale_pipeline',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('property_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='identified'),
        sa.Column('contract_price', sa.Float(), nullable=True),
        sa.Column('assignment_fee', sa.Float(), nullable=True),
        sa.Column('earnest_money', sa.Float(), nullable=True),
        sa.Column('buyer_id', sa.String(), nullable=True),
        sa.Column('buyer_name', sa.String(200), nullable=True),
        sa.Column('buyer_email', sa.String(200), nullable=True),
        sa.Column('contract_date', sa.Date(), nullable=True),
        sa.Column('closing_date', sa.Date(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('marketing_notes', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        if_not_exists=True
    )
    op.create_index('ix_wholesale_pipeline_property_id', 'wholesale_pipeline', ['property_id'])
    op.create_index('ix_wholesale_pipeline_status', 'wholesale_pipeline', ['status'])

    # Step 5: Seed state_configs with initial data
    op.execute("""
        INSERT INTO state_configs (state_code, state_name, sale_type, redemption_period_days,
                                   interest_rate, quiet_title_cost_estimate, time_to_ownership_days,
                                   auction_platform, scraper_module, is_active,
                                   recommended_for_beginners, notes)
        VALUES
        ('AL', 'Alabama', 'tax_lien', 1460, 0.12, 4000.0, 2000, 'GovEase',
         'core.scrapers.alabama_dor', 1, 0,
         'Long hold period (4 years), expensive quiet title. Not recommended for <$25k investors.'),

        ('AR', 'Arkansas', 'tax_deed', 0, NULL, 0.0, 1, 'COSL Website',
         'core.scrapers.arkansas_cosl', 1, 1,
         'Immediate ownership. State-level centralized system. Great for beginners.'),

        ('TX', 'Texas', 'redeemable_deed', 180, 0.25, 2000.0, 180, 'County-specific',
         'core.scrapers.texas_counties', 0, 1,
         'Can take possession during 6-month redemption. 25% penalty if owner redeems.'),

        ('FL', 'Florida', 'hybrid', 0, 0.18, 1500.0, 730, 'County + tax-sale.info',
         'core.scrapers.florida_counties', 0, 0,
         'Complex hybrid system (lien then deed). Requires understanding both phases.')
    """)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_wholesale_pipeline_status', table_name='wholesale_pipeline')
    op.drop_index('ix_wholesale_pipeline_property_id', table_name='wholesale_pipeline')

    # Drop new tables
    op.drop_table('wholesale_pipeline')
    op.drop_table('state_configs')

    # Remove columns from properties table
    with op.batch_alter_table('properties', schema=None) as batch_op:
        batch_op.drop_index('ix_properties_state')
        batch_op.drop_column('auction_platform')
        batch_op.drop_column('auction_date')
        batch_op.drop_column('data_source')
        batch_op.drop_column('owner_type')
        batch_op.drop_column('wholesale_spread')
        batch_op.drop_column('estimated_market_value')
        batch_op.drop_column('time_to_ownership_days')
        batch_op.drop_column('redemption_period_days')
        batch_op.drop_column('sale_type')
        batch_op.drop_column('state')
