"""Initial schema baseline

Revision ID: 001_initial
Revises:
Create Date: 2025-12-26

This migration establishes the baseline schema for Alabama Auction Watcher.
All tables already exist if created via Base.metadata.create_all().
Running this migration on an existing database will be a no-op due to
the checkfirst=True parameter.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Properties table
    op.create_table(
        'properties',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('parcel_id', sa.String(), nullable=False, index=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('acreage', sa.Float(), nullable=True),
        sa.Column('price_per_acre', sa.Float(), nullable=True),
        sa.Column('water_score', sa.Float(), default=0.0),
        sa.Column('investment_score', sa.Float(), nullable=True),
        sa.Column('estimated_all_in_cost', sa.Float(), nullable=True),
        # Enhanced Description Intelligence Fields
        sa.Column('lot_dimensions_score', sa.Float(), default=0.0),
        sa.Column('shape_efficiency_score', sa.Float(), default=0.0),
        sa.Column('corner_lot_bonus', sa.Float(), default=0.0),
        sa.Column('irregular_shape_penalty', sa.Float(), default=0.0),
        sa.Column('subdivision_quality_score', sa.Float(), default=0.0),
        sa.Column('road_access_score', sa.Float(), default=0.0),
        sa.Column('location_type_score', sa.Float(), default=0.0),
        sa.Column('title_complexity_score', sa.Float(), default=0.0),
        sa.Column('survey_requirement_score', sa.Float(), default=0.0),
        sa.Column('premium_water_access_score', sa.Float(), default=0.0),
        sa.Column('total_description_score', sa.Float(), default=0.0),
        # County Intelligence Fields
        sa.Column('county_market_score', sa.Float(), default=0.0),
        sa.Column('geographic_score', sa.Float(), default=0.0),
        sa.Column('market_timing_score', sa.Float(), default=0.0),
        # Financial and property details
        sa.Column('assessed_value', sa.Float(), nullable=True),
        sa.Column('assessed_value_ratio', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('county', sa.String(), nullable=True),
        sa.Column('owner_name', sa.String(), nullable=True),
        sa.Column('year_sold', sa.String(), nullable=True),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('device_id', sa.String(), nullable=True),
        sa.Column('sync_timestamp', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        if_not_exists=True
    )

    # Counties table
    op.create_table(
        'counties',
        sa.Column('code', sa.String(2), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        if_not_exists=True
    )

    # Sync logs table
    op.create_table(
        'sync_logs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('device_id', sa.String(), nullable=False),
        sa.Column('operation', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('records_processed', sa.Integer(), default=0),
        sa.Column('conflicts_detected', sa.Integer(), default=0),
        sa.Column('conflicts_resolved', sa.Integer(), default=0),
        sa.Column('started_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('algorithm_validation_passed', sa.Boolean(), default=True),
        if_not_exists=True
    )

    # User profiles table
    op.create_table(
        'user_profiles',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('address', sa.String(), nullable=False),
        sa.Column('city', sa.String(), nullable=False),
        sa.Column('state', sa.String(), nullable=False),
        sa.Column('zip_code', sa.String(), nullable=False),
        sa.Column('max_investment_amount', sa.Float(), nullable=True),
        sa.Column('min_acreage', sa.Float(), nullable=True),
        sa.Column('max_acreage', sa.Float(), nullable=True),
        sa.Column('preferred_counties', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('is_active', sa.Boolean(), default=True),
        if_not_exists=True
    )

    # Property applications table
    op.create_table(
        'property_applications',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_profile_id', sa.String(), nullable=False),
        sa.Column('property_id', sa.String(), nullable=False),
        sa.Column('cs_number', sa.String(), nullable=True),
        sa.Column('parcel_number', sa.String(), nullable=False),
        sa.Column('sale_year', sa.String(), nullable=False),
        sa.Column('county', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('assessed_name', sa.String(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('acreage', sa.Float(), nullable=True),
        sa.Column('investment_score', sa.Float(), nullable=True),
        sa.Column('estimated_total_cost', sa.Float(), nullable=True),
        sa.Column('roi_estimate', sa.Float(), nullable=True),
        sa.Column('status', sa.String(), default='draft'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('price_request_date', sa.DateTime(), nullable=True),
        sa.Column('price_received_date', sa.DateTime(), nullable=True),
        sa.Column('final_price', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        if_not_exists=True
    )

    # Application batches table
    op.create_table(
        'application_batches',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_profile_id', sa.String(), nullable=False),
        sa.Column('batch_name', sa.String(), nullable=True),
        sa.Column('total_estimated_investment', sa.Float(), nullable=True),
        sa.Column('forms_generated', sa.Integer(), default=0),
        sa.Column('applications_submitted', sa.Integer(), default=0),
        sa.Column('prices_received', sa.Integer(), default=0),
        sa.Column('status', sa.String(), default='draft'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        if_not_exists=True
    )

    # Application notifications table
    op.create_table(
        'application_notifications',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_profile_id', sa.String(), nullable=False),
        sa.Column('property_id', sa.String(), nullable=True),
        sa.Column('notification_type', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('state_email_expected', sa.Boolean(), default=False),
        sa.Column('state_email_received', sa.Boolean(), default=False),
        sa.Column('price_amount', sa.Float(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('action_required', sa.Boolean(), default=False),
        sa.Column('action_deadline', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True
    )


def downgrade() -> None:
    op.drop_table('application_notifications', if_exists=True)
    op.drop_table('application_batches', if_exists=True)
    op.drop_table('property_applications', if_exists=True)
    op.drop_table('user_profiles', if_exists=True)
    op.drop_table('sync_logs', if_exists=True)
    op.drop_table('counties', if_exists=True)
    op.drop_table('properties', if_exists=True)
