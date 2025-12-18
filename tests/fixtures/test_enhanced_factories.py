"""
Tests for enhanced data factories related to application management and sync logs.

Validates the structure, data types, and builder methods of the new factories.
"""
import pytest
import uuid
import json
from datetime import datetime, timedelta
from typing import Any, Dict

from tests.fixtures.data_factories import (
    SyncLogFactory,
    UserProfileFactory,
    PropertyApplicationFactory,
    ApplicationBatchFactory,
    ApplicationNotificationFactory
)

# --- Helper Functions ---

def assert_is_uuid_string(value: Any):
    """Assert that a value is a valid UUID string."""
    assert isinstance(value, str)
    try:
        uuid.UUID(value)
    except (ValueError, TypeError):
        pytest.fail(f"'{value}' is not a valid UUID string.")

def assert_is_datetime_or_none(value: Any):
    """Assert that a value is a datetime object or None."""
    if value is not None:
        assert isinstance(value, datetime)

def assert_is_json_string_or_none(value: Any):
    """Assert that a value is a valid JSON string or None."""
    if value is not None:
        assert isinstance(value, str)
        try:
            json.loads(value)
        except json.JSONDecodeError:
            pytest.fail(f"'{value}' is not a valid JSON string.")


# --- Test Suites ---

@pytest.mark.unit
class TestSyncLogFactory:
    """Tests for the SyncLogFactory."""

    def test_create_valid_sync_log(self):
        """Test basic creation of a valid SyncLog dictionary."""
        log = SyncLogFactory()
        assert_is_uuid_string(log['id'])
        assert isinstance(log['device_id'], str)
        assert log['operation'] in ['delta', 'full', 'upload', 'download']
        assert log['status'] in ['success', 'failed', 'partial']
        assert isinstance(log['records_processed'], int)
        assert isinstance(log['conflicts_detected'], int)
        assert isinstance(log['conflicts_resolved'], int)
        assert isinstance(log['started_at'], datetime)
        assert_is_datetime_or_none(log['completed_at'])
        assert isinstance(log['duration_seconds'], (float, int))
        assert log['error_message'] is None
        assert isinstance(log['algorithm_validation_passed'], bool)

    def test_successful_sync_builder(self):
        """Test the successful_sync builder method."""
        log = SyncLogFactory.successful_sync(operation='full')
        assert log['status'] == 'success'
        assert log['operation'] == 'full'
        assert log['error_message'] is None
        assert log['conflicts_detected'] == 0

    def test_failed_sync_builder(self):
        """Test the failed_sync builder method."""
        log = SyncLogFactory.failed_sync(error_type='server')
        assert log['status'] == 'failed'
        assert 'Internal Server Error' in log['error_message']
        assert log['completed_at'] is None
        assert log['duration_seconds'] is None

    def test_with_conflicts_builder(self):
        """Test the with_conflicts builder method."""
        log = SyncLogFactory.with_conflicts()
        assert log['status'] == 'partial'
        assert log['conflicts_detected'] > 0
        assert log['conflicts_resolved'] <= log['conflicts_detected']

    def test_data_consistency(self):
        """Test logical consistency of generated data."""
        log = SyncLogFactory()
        assert log['completed_at'] > log['started_at']
        duration = (log['completed_at'] - log['started_at']).total_seconds()
        assert log['duration_seconds'] == pytest.approx(duration)
        assert log['conflicts_resolved'] <= log['conflicts_detected']

@pytest.mark.unit
class TestUserProfileFactory:
    """Tests for the UserProfileFactory."""

    def test_create_valid_user_profile(self):
        """Test basic creation of a valid UserProfile dictionary."""
        profile = UserProfileFactory()
        assert_is_uuid_string(profile['id'])
        assert isinstance(profile['full_name'], str)
        assert '@' in profile['email']
        assert isinstance(profile['phone'], str)
        assert isinstance(profile['address'], str)
        assert isinstance(profile['city'], str)
        assert isinstance(profile['state'], str)
        assert isinstance(profile['zip_code'], str)
        assert isinstance(profile['max_investment_amount'], float)
        assert isinstance(profile['min_acreage'], float)
        assert isinstance(profile['max_acreage'], float)
        assert_is_json_string_or_none(profile['preferred_counties'])
        assert isinstance(profile['created_at'], datetime)
        assert isinstance(profile['updated_at'], datetime)
        assert profile['is_active'] is True

    def test_aggressive_investor_builder(self):
        """Test the aggressive_investor builder method."""
        profile = UserProfileFactory.aggressive_investor()
        assert profile['max_investment_amount'] >= 500000
        assert profile['min_acreage'] >= 10
        assert profile['max_acreage'] >= 200

    def test_conservative_investor_builder(self):
        """Test the conservative_investor builder method."""
        profile = UserProfileFactory.conservative_investor()
        assert profile['max_investment_amount'] <= 50000
        assert profile['max_acreage'] <= 5.0

    def test_minimal_profile_builder(self):
        """Test the minimal_profile builder for nullable fields."""
        profile = UserProfileFactory.minimal_profile()
        assert profile['max_investment_amount'] is None
        assert profile['min_acreage'] is None
        assert profile['max_acreage'] is None
        assert profile['preferred_counties'] is None

    def test_data_consistency(self):
        """Test logical consistency of user profile data."""
        profile = UserProfileFactory()
        assert profile['min_acreage'] < profile['max_acreage']
        counties = json.loads(profile['preferred_counties'])
        assert isinstance(counties, list)
        assert len(counties) > 0


@pytest.mark.unit
class TestPropertyApplicationFactory:
    """Tests for the PropertyApplicationFactory."""

    def test_create_valid_property_application(self):
        """Test basic creation of a valid PropertyApplication dictionary."""
        app = PropertyApplicationFactory()
        assert_is_uuid_string(app['id'])
        assert_is_uuid_string(app['user_profile_id'])
        assert_is_uuid_string(app['property_id'])
        assert isinstance(app['parcel_number'], str)
        assert isinstance(app['sale_year'], str)
        assert isinstance(app['county'], str)
        assert isinstance(app['description'], str)
        assert isinstance(app['amount'], float)
        assert app['status'] in ['draft', 'submitted', 'price_requested', 'price_received', 'completed', 'cancelled']
        assert isinstance(app['created_at'], datetime)

    def test_draft_application_builder(self):
        """Test the draft_application builder method."""
        app = PropertyApplicationFactory.draft_application()
        assert app['status'] == 'draft'
        assert app['price_request_date'] is None
        assert app['price_received_date'] is None
        assert app['final_price'] is None

    def test_submitted_application_builder(self):
        """Test the submitted_application builder method."""
        app = PropertyApplicationFactory.submitted_application()
        assert app['status'] == 'submitted'
        assert isinstance(app['price_request_date'], datetime)
        assert app['price_received_date'] is None
        assert app['final_price'] is None

    def test_with_price_received_builder(self):
        """Test the with_price_received builder method."""
        app = PropertyApplicationFactory.with_price_received()
        assert app['status'] == 'price_received'
        assert isinstance(app['price_request_date'], datetime)
        assert isinstance(app['price_received_date'], datetime)
        assert isinstance(app['final_price'], float)
        assert app['final_price'] > app['amount']

    def test_data_consistency(self):
        """Test logical consistency of application data."""
        app = PropertyApplicationFactory.with_price_received()
        assert app['price_received_date'] > app['price_request_date']
        assert app['estimated_total_cost'] > app['amount']


@pytest.mark.unit
class TestApplicationBatchFactory:
    """Tests for the ApplicationBatchFactory."""

    def test_create_valid_application_batch(self):
        """Test basic creation of a valid ApplicationBatch dictionary."""
        batch = ApplicationBatchFactory()
        assert_is_uuid_string(batch['id'])
        assert_is_uuid_string(batch['user_profile_id'])
        assert isinstance(batch['batch_name'], str)
        assert isinstance(batch['total_estimated_investment'], float)
        assert isinstance(batch['forms_generated'], int)
        assert isinstance(batch['applications_submitted'], int)
        assert isinstance(batch['prices_received'], int)
        assert batch['status'] in ['draft', 'in_progress', 'completed', 'cancelled']
        assert isinstance(batch['created_at'], datetime)

    def test_small_batch_builder(self):
        """Test the small_batch builder method."""
        batch = ApplicationBatchFactory.small_batch()
        assert 1 <= batch['forms_generated'] <= 5
        assert batch['status'] == 'in_progress'

    def test_large_batch_builder(self):
        """Test the large_batch builder method."""
        batch = ApplicationBatchFactory.large_batch()
        assert batch['forms_generated'] >= 50

    def test_completed_batch_builder(self):
        """Test the completed_batch builder method."""
        batch = ApplicationBatchFactory.completed_batch()
        assert batch['status'] == 'completed'
        assert batch['forms_generated'] == batch['applications_submitted']
        assert batch['forms_generated'] == batch['prices_received']

    def test_data_consistency(self):
        """Test logical consistency of batch data."""
        batch = ApplicationBatchFactory()
        assert batch['applications_submitted'] <= batch['forms_generated']
        assert batch['prices_received'] <= batch['applications_submitted']


@pytest.mark.unit
class TestApplicationNotificationFactory:
    """Tests for the ApplicationNotificationFactory."""

    def test_create_valid_notification(self):
        """Test basic creation of a valid ApplicationNotification dictionary."""
        notification = ApplicationNotificationFactory()
        assert_is_uuid_string(notification['id'])
        assert_is_uuid_string(notification['user_profile_id'])
        assert_is_uuid_string(notification['property_id'])
        assert notification['notification_type'] in ['price_update', 'status_change', 'deadline_reminder', 'error_alert']
        assert isinstance(notification['title'], str)
        assert isinstance(notification['message'], str)
        assert isinstance(notification['state_email_expected'], bool)
        assert isinstance(notification['state_email_received'], bool)
        assert notification['price_amount'] is None
        assert notification['read_at'] is None
        assert isinstance(notification['action_required'], bool)
        assert notification['action_deadline'] is None
        assert isinstance(notification['created_at'], datetime)

    def test_price_notification_builder(self):
        """Test the price_notification builder method."""
        notification = ApplicationNotificationFactory.price_notification()
        assert notification['notification_type'] == 'price_update'
        assert notification['state_email_received'] is True
        assert isinstance(notification['price_amount'], float)
        assert notification['action_required'] is True

    def test_deadline_reminder_builder(self):
        """Test the deadline_reminder builder method."""
        notification = ApplicationNotificationFactory.deadline_reminder()
        assert notification['notification_type'] == 'deadline_reminder'
        assert notification['action_required'] is True
        assert isinstance(notification['action_deadline'], datetime)
        assert notification['action_deadline'] > datetime.now()

    def test_error_alert_builder(self):
        """Test the error_alert builder method."""
        notification = ApplicationNotificationFactory.error_alert()
        assert notification['notification_type'] == 'error_alert'
        assert 'error' in notification['title'].lower()
        assert notification['action_required'] is True
        assert notification['read_at'] is None

    def test_data_consistency(self):
        """Test logical consistency of notification data."""
        notification = ApplicationNotificationFactory()
        if not notification['state_email_expected']:
            assert not notification['state_email_received']
