"""
Tests for SyncDiffer - delta calculation between client and server state.

Tests cover:
- Server change retrieval with device exclusion (echo prevention)
- Batch pagination with cursor-based navigation
- Deleted record handling
- Pending change counting
"""

import pytest
from unittest.mock import MagicMock, Mock, patch
from datetime import datetime, timedelta
from uuid import uuid4

from backend_api.services.sync.differ import SyncDiffer
from backend_api.models.sync import SyncOperation


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []
    db.query.return_value.filter.return_value.count.return_value = 0
    return db


@pytest.fixture
def differ(mock_db):
    """Create a SyncDiffer with mocked database."""
    return SyncDiffer(mock_db)


class TestGetServerChanges:
    """Tests for get_server_changes method - echo prevention."""

    @pytest.mark.unit
    def test_excludes_changes_from_requesting_device(self, differ, mock_db):
        """Changes made by the requesting device should be excluded."""
        device_id = "device-123"
        since = datetime.utcnow() - timedelta(hours=1)

        differ.get_server_changes(device_id, since)

        # Verify the query filters by device_id
        filter_call = mock_db.query.return_value.filter
        assert filter_call.called
        # The filter should exclude the device's own changes

    @pytest.mark.unit
    def test_returns_changes_after_timestamp(self, differ, mock_db):
        """Only changes after the given timestamp should be returned."""
        device_id = "device-123"
        since = datetime.utcnow() - timedelta(hours=1)

        # Mock properties modified after the timestamp
        mock_prop = Mock()
        mock_prop.id = str(uuid4())
        mock_prop.is_deleted = False
        mock_prop.device_id = "other-device"
        mock_prop.to_dict.return_value = {"id": mock_prop.id, "status": "new"}

        mock_db.query.return_value.filter.return_value.all.return_value = [mock_prop]

        changes = differ.get_server_changes(device_id, since)

        assert len(changes) == 1
        assert changes[0].property_id == mock_prop.id

    @pytest.mark.unit
    def test_respects_limit_parameter(self, differ, mock_db):
        """Limit parameter should restrict the number of results."""
        device_id = "device-123"
        since = datetime.utcnow() - timedelta(hours=1)

        differ.get_server_changes(device_id, since, limit=10)

        # Verify limit was applied
        mock_db.query.return_value.filter.return_value.limit.assert_called_with(10)

    @pytest.mark.unit
    def test_no_limit_when_not_specified(self, differ, mock_db):
        """No limit should be applied when not specified."""
        device_id = "device-123"
        since = datetime.utcnow() - timedelta(hours=1)

        # Setup mock to return results from filter directly
        mock_db.query.return_value.filter.return_value.all.return_value = []

        differ.get_server_changes(device_id, since)

        # limit() should not be called
        mock_db.query.return_value.filter.return_value.limit.assert_not_called()

    @pytest.mark.unit
    def test_empty_result_when_no_changes(self, differ, mock_db):
        """Empty list returned when no changes exist."""
        device_id = "device-123"
        since = datetime.utcnow()

        mock_db.query.return_value.filter.return_value.all.return_value = []

        changes = differ.get_server_changes(device_id, since)

        assert changes == []


class TestGetBatch:
    """Tests for get_batch method - pagination."""

    @pytest.mark.unit
    def test_returns_batch_of_correct_size(self, differ, mock_db):
        """Batch should contain at most batch_size items."""
        # Create mock properties
        mock_props = [
            Mock(id=str(uuid4()), is_deleted=False, to_dict=lambda: {"id": "test"})
            for _ in range(5)
        ]

        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_props

        batch_data, next_start, has_more = differ.get_batch(batch_size=10)

        assert len(batch_data) <= 10

    @pytest.mark.unit
    def test_has_more_true_when_extra_item_exists(self, differ, mock_db):
        """has_more should be True when more data exists beyond batch_size."""
        # Return batch_size + 1 items to indicate more data
        mock_props = []
        for i in range(101):
            prop = Mock()
            prop.id = str(uuid4())
            prop.is_deleted = False
            prop.to_dict = Mock(return_value={"id": prop.id})
            mock_props.append(prop)

        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_props

        batch_data, next_start, has_more = differ.get_batch(batch_size=100)

        assert has_more is True
        assert len(batch_data) == 100  # Extra item removed

    @pytest.mark.unit
    def test_has_more_false_when_exact_batch(self, differ, mock_db):
        """has_more should be False when exactly batch_size items exist."""
        # Return exactly batch_size items
        mock_props = []
        for i in range(100):
            prop = Mock()
            prop.id = str(uuid4())
            prop.is_deleted = False
            prop.to_dict = Mock(return_value={"id": prop.id})
            mock_props.append(prop)

        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_props

        batch_data, next_start, has_more = differ.get_batch(batch_size=100)

        assert has_more is False
        assert len(batch_data) == 100

    @pytest.mark.unit
    def test_cursor_pagination_with_start_from(self, differ, mock_db):
        """Cursor pagination should filter by start_from UUID."""
        start_uuid = str(uuid4())

        differ.get_batch(start_from=start_uuid, batch_size=10)

        # Verify filter was called (cursor pagination applied)
        assert mock_db.query.return_value.filter.called

    @pytest.mark.unit
    def test_empty_batch_returns_no_next_start(self, differ, mock_db):
        """Empty result should return None for next_start."""
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        batch_data, next_start, has_more = differ.get_batch(batch_size=10)

        assert batch_data == []
        assert next_start is None
        assert has_more is False

    @pytest.mark.unit
    def test_next_start_is_last_item_id(self, differ, mock_db):
        """next_start should be the ID of the last item in the batch."""
        last_id = str(uuid4())
        mock_props = []
        for i in range(5):
            prop = Mock()
            prop.id = str(uuid4()) if i < 4 else last_id
            prop.is_deleted = False
            prop.to_dict = Mock(return_value={"id": prop.id})
            mock_props.append(prop)

        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_props

        batch_data, next_start, has_more = differ.get_batch(batch_size=10)

        assert next_start == last_id


class TestPropertyToChange:
    """Tests for _property_to_change method."""

    @pytest.mark.unit
    def test_deleted_property_returns_delete_operation(self, differ):
        """Deleted property should return DELETE operation with no data."""
        mock_prop = Mock()
        mock_prop.id = str(uuid4())
        mock_prop.is_deleted = True
        mock_prop.device_id = "device-123"
        mock_prop.to_dict = Mock(return_value={"id": mock_prop.id})

        change = differ._property_to_change(mock_prop)

        assert change.operation == SyncOperation.DELETE
        assert change.data is None

    @pytest.mark.unit
    def test_active_property_returns_update_operation(self, differ):
        """Active property should return UPDATE operation with data."""
        mock_prop = Mock()
        mock_prop.id = str(uuid4())
        mock_prop.is_deleted = False
        mock_prop.device_id = "device-123"
        mock_prop.to_dict = Mock(return_value={"id": mock_prop.id, "status": "new"})

        change = differ._property_to_change(mock_prop)

        assert change.operation == SyncOperation.UPDATE
        assert change.data is not None
        assert change.data["id"] == mock_prop.id

    @pytest.mark.unit
    def test_device_id_preserved_in_change(self, differ):
        """Device ID should be preserved in the change object."""
        mock_prop = Mock()
        mock_prop.id = str(uuid4())
        mock_prop.is_deleted = False
        mock_prop.device_id = "original-device"
        mock_prop.to_dict = Mock(return_value={"id": mock_prop.id})

        change = differ._property_to_change(mock_prop)

        assert change.device_id == "original-device"

    @pytest.mark.unit
    def test_null_device_id_becomes_server(self, differ):
        """Null device_id should default to 'server'."""
        mock_prop = Mock()
        mock_prop.id = str(uuid4())
        mock_prop.is_deleted = False
        mock_prop.device_id = None
        mock_prop.to_dict = Mock(return_value={"id": mock_prop.id})

        change = differ._property_to_change(mock_prop)

        assert change.device_id == "server"


class TestGetAllActiveProperties:
    """Tests for get_all_active_properties method."""

    @pytest.mark.unit
    def test_excludes_deleted_properties(self, differ, mock_db):
        """Deleted properties should not appear in active list."""
        active_prop = Mock()
        active_prop.is_deleted = False
        active_prop.to_dict = Mock(return_value={"id": "active-1"})

        mock_db.query.return_value.filter.return_value.all.return_value = [active_prop]

        all_props, deleted_ids = differ.get_all_active_properties()

        assert len(all_props) == 1
        assert all_props[0]["id"] == "active-1"

    @pytest.mark.unit
    def test_includes_deleted_ids_when_requested(self, differ, mock_db):
        """Deleted property IDs should be returned when include_deleted=True."""
        # Setup active properties query
        mock_db.query.return_value.filter.return_value.all.return_value = []

        # Setup deleted IDs query - need to handle chained calls
        deleted_mock = Mock()
        deleted_mock.id = "deleted-1"

        # Mock the chain for Property.id query
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            [],  # First call for active properties
            [deleted_mock]  # Second call for deleted IDs
        ]

        all_props, deleted_ids = differ.get_all_active_properties(include_deleted=True)

        assert len(deleted_ids) == 1


class TestGetPendingChangeCount:
    """Tests for get_pending_change_count method."""

    @pytest.mark.unit
    def test_counts_changes_after_timestamp(self, differ, mock_db):
        """Should count changes after the given timestamp."""
        since = datetime.utcnow() - timedelta(hours=1)
        mock_db.query.return_value.filter.return_value.count.return_value = 5

        count = differ.get_pending_change_count("device-123", since)

        assert count == 5

    @pytest.mark.unit
    def test_counts_all_active_when_no_timestamp(self, differ, mock_db):
        """Should count all active properties when no timestamp provided."""
        mock_db.query.return_value.filter.return_value.count.return_value = 100

        count = differ.get_pending_change_count("device-123", None)

        assert count == 100
