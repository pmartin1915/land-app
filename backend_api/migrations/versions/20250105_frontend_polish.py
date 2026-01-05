"""
Frontend polish: Add user preferences, property interactions, and scrape jobs tables

Revision ID: 006_frontend_polish
Revises: 005_filter_indexes
Create Date: 2025-01-05
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '006_frontend_polish'
down_revision = '005_filter_indexes'
branch_labels = None
depends_on = None


def upgrade():
    """Create tables for user preferences, property interactions, and scrape jobs."""

    # User Preferences table - stores investment budget and settings per device
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('device_id', sa.String(), unique=True, index=True, nullable=False,
                  comment='Links to device auth - one preference set per device'),
        sa.Column('investment_budget', sa.Float(), default=10000.0, nullable=True,
                  comment='User investment capital budget in USD'),
        sa.Column('excluded_states', sa.String(), nullable=True,
                  comment='JSON array of state codes to exclude from results'),
        sa.Column('default_filters', sa.Text(), nullable=True,
                  comment='JSON of saved filter presets'),
        sa.Column('max_property_price', sa.Float(), nullable=True,
                  comment='Maximum price per property (derived from budget)'),
        sa.Column('preferred_states', sa.String(), nullable=True,
                  comment='JSON array of preferred state codes'),
        sa.Column('notifications_enabled', sa.Boolean(), default=True,
                  comment='Whether to show notifications'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )

    # Property Interactions table - user overlay for watchlist/notes
    # IMPORTANT: Separate from Property table to survive scraper re-runs
    op.create_table(
        'property_interactions',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('device_id', sa.String(), index=True, nullable=False,
                  comment='Device that created this interaction'),
        sa.Column('property_id', sa.String(), sa.ForeignKey('properties.id', ondelete='CASCADE'),
                  index=True, nullable=False, comment='FK to properties table'),
        sa.Column('is_watched', sa.Boolean(), default=False,
                  comment='Whether property is on watchlist'),
        sa.Column('star_rating', sa.Integer(), nullable=True,
                  comment='User rating 1-5 stars'),
        sa.Column('user_notes', sa.Text(), nullable=True,
                  comment='User notes about this property'),
        sa.Column('dismissed', sa.Boolean(), default=False,
                  comment='User dismissed/hidden this property'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )

    # Unique constraint: one interaction per device per property
    op.create_index(
        'ix_property_interactions_device_property',
        'property_interactions',
        ['device_id', 'property_id'],
        unique=True
    )

    # Scrape Jobs table - track scraper runs
    op.create_table(
        'scrape_jobs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('state', sa.String(2), nullable=False, index=True,
                  comment='State code being scraped'),
        sa.Column('county', sa.String(100), nullable=True,
                  comment='County name if county-specific, NULL for all counties'),
        sa.Column('status', sa.String(20), nullable=False, default='pending',
                  comment='pending, running, completed, failed, cancelled'),
        sa.Column('items_found', sa.Integer(), default=0,
                  comment='Total properties found during scrape'),
        sa.Column('items_added', sa.Integer(), default=0,
                  comment='New properties added to database'),
        sa.Column('items_updated', sa.Integer(), default=0,
                  comment='Existing properties updated'),
        sa.Column('started_at', sa.DateTime(), nullable=True,
                  comment='When scrape job started'),
        sa.Column('completed_at', sa.DateTime(), nullable=True,
                  comment='When scrape job completed'),
        sa.Column('error_message', sa.Text(), nullable=True,
                  comment='Error details if job failed'),
        sa.Column('triggered_by', sa.String(), nullable=True,
                  comment='Device ID or system that triggered the job'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )

    # Index for querying recent jobs
    op.create_index('ix_scrape_jobs_created_at', 'scrape_jobs', ['created_at'])


def downgrade():
    """Remove frontend polish tables."""
    op.drop_index('ix_scrape_jobs_created_at', table_name='scrape_jobs')
    op.drop_table('scrape_jobs')

    op.drop_index('ix_property_interactions_device_property', table_name='property_interactions')
    op.drop_table('property_interactions')

    op.drop_table('user_preferences')
