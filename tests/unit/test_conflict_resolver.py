"""
Tests for ConflictResolver - synchronization conflict detection and resolution.

Tests cover:
- Conflict detection based on timestamps
- Resolution strategies (USE_LOCAL, USE_REMOTE, MERGE, ASK_USER)
- Batch conflict detection with bulk fetch optimization
- Error handling during resolution
"""

import pytest
from unittest.mock import MagicMock, Mock, patch
from datetime import datetime, timedelta
from uuid import uuid4

from backend_api.services.sync.conflict_resolver import ConflictResolver
from backend_api.models.sync import (
    PropertyChange, SyncOperation, SyncConflict, ConflictResolution,
    ConflictResolutionRequest, SyncStatus
)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []
    return db


@pytest.fixture
def mock_property_service():
    """Create a mock property service."""
    service = MagicMock()
    service.update_property.return_value = Mock(id=str(uuid4()))
    service.get_property.return_value = None
    return service


@pytest.fixture
def resolver(mock_db, mock_property_service):
    """Create a ConflictResolver with mocked dependencies."""
    return ConflictResolver(mock_db, mock_property_service)


class TestDetectUpdateConflict:
    """Tests for detect_update_conflict method."""

    def test_no_conflict_when_no_existing_property(self, resolver):
        """No conflict if property doesn't exist."""
        change = PropertyChange(
            property_id=str(uuid4()),
            operation=SyncOperation.UPDATE,
            data={"status": "new"},
            timestamp=datetime.utcnow(),
            device_id="test-device"
        )

        result = resolver.detect_update_conflict(change, None)

        assert result is None

    def test_no_conflict_when_local_is_newer(self, resolver):
        """No conflict if local change is newer than server."""
        now = datetime.utcnow()
        change = PropertyChange(
            property_id="prop-1",
            operation=SyncOperation.UPDATE,
            data={"id": "prop-1", "status": "updated"},
            timestamp=now,
            device_id="test-device"
        )

        existing = Mock()
        existing.updated_at = now - timedelta(hours=1)
        existing.to_dict.return_value = {"id": "prop-1", "status": "old"}

        result = resolver.detect_update_conflict(change, existing)

        assert result is None

    def test_conflict_when_server_is_newer(self, resolver):
        """Conflict detected if server version is newer than local change."""
        now = datetime.utcnow()
        change = PropertyChange(
            property_id="prop-1",
            operation=SyncOperation.UPDATE,
            data={"id": "prop-1", "status": "local_update"},
            timestamp=now - timedelta(hours=1),
            device_id="test-device"
        )

        existing = Mock()
        existing.updated_at = now
        existing.to_dict.return_value = {"id": "prop-1", "status": "server_update"}

        result = resolver.detect_update_conflict(change, existing)

        assert result is not None
        assert result.property_id == "prop-1"
        assert "status" in result.conflict_fields


class TestApplyResolution:
    """Tests for _apply_resolution method."""

    def test_use_remote_returns_true_without_action(self, resolver):
        """USE_REMOTE resolution keeps server data (no action needed)."""
        conflict = SyncConflict(
            property_id="prop-1",
            local_timestamp=datetime.utcnow(),
            remote_timestamp=datetime.utcnow(),
            local_data={"status": "local"},
            remote_data={"status": "remote"},
            conflict_fields=["status"],
            resolution=ConflictResolution.USE_REMOTE
        )

        result = resolver._apply_resolution(conflict, "test-device")

        assert result is True
        resolver.property_service.update_property.assert_not_called()

    def test_use_local_applies_local_data(self, resolver):
        """USE_LOCAL resolution applies local data to server."""
        conflict = SyncConflict(
            property_id="prop-1",
            local_timestamp=datetime.utcnow(),
            remote_timestamp=datetime.utcnow(),
            local_data={"id": "prop-1", "status": "local", "amount": 1000},
            remote_data={"id": "prop-1", "status": "remote"},
            conflict_fields=["status"],
            resolution=ConflictResolution.USE_LOCAL
        )

        result = resolver._apply_resolution(conflict, "test-device")

        assert result is True
        resolver.property_service.update_property.assert_called_once()

    def test_use_local_fails_without_local_data(self, resolver):
        """USE_LOCAL resolution fails if no local data available."""
        conflict = SyncConflict(
            property_id="prop-1",
            local_timestamp=datetime.utcnow(),
            remote_timestamp=datetime.utcnow(),
            local_data={},
            remote_data={"status": "remote"},
            conflict_fields=["status"],
            resolution=ConflictResolution.USE_LOCAL
        )

        result = resolver._apply_resolution(conflict, "test-device")

        assert result is False

    def test_ask_user_returns_false(self, resolver):
        """ASK_USER resolution cannot be auto-resolved."""
        conflict = SyncConflict(
            property_id="prop-1",
            local_timestamp=datetime.utcnow(),
            remote_timestamp=datetime.utcnow(),
            local_data={"status": "local"},
            remote_data={"status": "remote"},
            conflict_fields=["status"],
            resolution=ConflictResolution.ASK_USER
        )

        result = resolver._apply_resolution(conflict, "test-device")

        assert result is False

    def test_unknown_resolution_returns_false(self, resolver):
        """Unknown resolution type returns False."""
        conflict = SyncConflict(
            property_id="prop-1",
            local_timestamp=datetime.utcnow(),
            remote_timestamp=datetime.utcnow(),
            local_data={"status": "local"},
            remote_data={"status": "remote"},
            conflict_fields=["status"],
            resolution=None
        )

        result = resolver._apply_resolution(conflict, "test-device")

        assert result is False


class TestApplyMerge:
    """Tests for _apply_merge method (last-write-wins strategy)."""

    def test_merge_uses_local_when_local_is_newer(self, resolver):
        """MERGE applies local data when local timestamp is newer."""
        now = datetime.utcnow()
        conflict = SyncConflict(
            property_id="prop-1",
            local_timestamp=now,
            remote_timestamp=now - timedelta(hours=1),
            local_data={"id": "prop-1", "status": "local"},
            remote_data={"status": "remote"},
            conflict_fields=["status"],
            resolution=ConflictResolution.MERGE
        )

        result = resolver._apply_merge(conflict, "test-device")

        assert result is True
        resolver.property_service.update_property.assert_called_once()

    def test_merge_keeps_remote_when_remote_is_newer(self, resolver):
        """MERGE keeps remote data when remote timestamp is newer."""
        now = datetime.utcnow()
        conflict = SyncConflict(
            property_id="prop-1",
            local_timestamp=now - timedelta(hours=1),
            remote_timestamp=now,
            local_data={"status": "local"},
            remote_data={"status": "remote"},
            conflict_fields=["status"],
            resolution=ConflictResolution.MERGE
        )

        result = resolver._apply_merge(conflict, "test-device")

        assert result is True
        resolver.property_service.update_property.assert_not_called()

    def test_merge_with_equal_timestamps_prefers_local(self, resolver):
        """MERGE prefers local data when timestamps are equal."""
        now = datetime.utcnow()
        conflict = SyncConflict(
            property_id="prop-1",
            local_timestamp=now,
            remote_timestamp=now,
            local_data={"id": "prop-1", "status": "local"},
            remote_data={"status": "remote"},
            conflict_fields=["status"],
            resolution=ConflictResolution.MERGE
        )

        result = resolver._apply_merge(conflict, "test-device")

        # When timestamps are equal, neither branch triggers, falls through to local preference
        assert result is True


class TestResolveConflicts:
    """Tests for resolve_conflicts method."""

    def test_successful_resolution_returns_success_status(self, resolver, mock_db):
        """Successful resolution of all conflicts returns SUCCESS status."""
        now = datetime.utcnow()
        request = ConflictResolutionRequest(
            device_id="test-device",
            resolutions=[
                SyncConflict(
                    property_id="prop-1",
                    local_timestamp=now,
                    remote_timestamp=now,
                    local_data={"status": "local"},
                    remote_data={"status": "remote"},
                    conflict_fields=["status"],
                    resolution=ConflictResolution.USE_REMOTE
                )
            ]
        )

        response = resolver.resolve_conflicts(request)

        assert response.status == SyncStatus.SUCCESS
        assert response.resolved_conflicts == 1
        assert response.remaining_conflicts == 0
        assert len(response.errors) == 0

    def test_partial_resolution_returns_partial_status(self, resolver, mock_db):
        """Partial resolution (some failures) returns PARTIAL status."""
        now = datetime.utcnow()
        request = ConflictResolutionRequest(
            device_id="test-device",
            resolutions=[
                SyncConflict(
                    property_id="prop-1",
                    local_timestamp=now,
                    remote_timestamp=now,
                    local_data={"status": "local"},
                    remote_data={"status": "remote"},
                    conflict_fields=["status"],
                    resolution=ConflictResolution.USE_REMOTE
                ),
                SyncConflict(
                    property_id="prop-2",
                    local_timestamp=now,
                    remote_timestamp=now,
                    local_data={},
                    remote_data={"status": "remote"},
                    conflict_fields=["status"],
                    resolution=ConflictResolution.USE_LOCAL  # Will fail - no local data
                )
            ]
        )

        response = resolver.resolve_conflicts(request)

        assert response.resolved_conflicts == 1
        assert response.remaining_conflicts == 1

    def test_resolution_creates_sync_log(self, resolver, mock_db):
        """Resolution creates a sync log entry."""
        now = datetime.utcnow()
        request = ConflictResolutionRequest(
            device_id="test-device",
            resolutions=[
                SyncConflict(
                    property_id="prop-1",
                    local_timestamp=now,
                    remote_timestamp=now,
                    local_data={"status": "local"},
                    remote_data={"status": "remote"},
                    conflict_fields=["status"],
                    resolution=ConflictResolution.USE_REMOTE
                )
            ]
        )

        resolver.resolve_conflicts(request)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_exception_during_resolution_is_captured(self, resolver, mock_db):
        """Exceptions during resolution are captured in errors."""
        now = datetime.utcnow()
        resolver.property_service.update_property.side_effect = Exception("DB error")

        request = ConflictResolutionRequest(
            device_id="test-device",
            resolutions=[
                SyncConflict(
                    property_id="prop-1",
                    local_timestamp=now,
                    remote_timestamp=now,
                    local_data={"id": "prop-1", "status": "local"},
                    remote_data={"status": "remote"},
                    conflict_fields=["status"],
                    resolution=ConflictResolution.USE_LOCAL
                )
            ]
        )

        response = resolver.resolve_conflicts(request)

        assert response.remaining_conflicts == 1
        assert len(response.errors) == 1
        assert "DB error" in response.errors[0]


class TestBatchDetectConflicts:
    """Tests for batch_detect_conflicts method."""

    def test_non_update_operations_pass_through(self, resolver, mock_db):
        """CREATE and DELETE operations are not checked for conflicts."""
        changes = [
            PropertyChange(
                property_id=str(uuid4()),
                operation=SyncOperation.CREATE,
                data={"parcel_id": "TEST-001"},
                timestamp=datetime.utcnow(),
                device_id="test-device"
            ),
            PropertyChange(
                property_id=str(uuid4()),
                operation=SyncOperation.DELETE,
                data={},
                timestamp=datetime.utcnow(),
                device_id="test-device"
            )
        ]

        non_conflicting, conflicts = resolver.batch_detect_conflicts("test-device", changes)

        assert len(non_conflicting) == 2
        assert len(conflicts) == 0

    def test_update_without_existing_property_passes_through(self, resolver, mock_db):
        """UPDATE for non-existing property passes through (new property)."""
        mock_db.query.return_value.filter.return_value.all.return_value = []

        changes = [
            PropertyChange(
                property_id="prop-1",
                operation=SyncOperation.UPDATE,
                data={"status": "new"},
                timestamp=datetime.utcnow(),
                device_id="test-device"
            )
        ]

        non_conflicting, conflicts = resolver.batch_detect_conflicts("test-device", changes)

        assert len(non_conflicting) == 1
        assert len(conflicts) == 0

    def test_update_with_older_server_passes_through(self, resolver, mock_db):
        """UPDATE passes through when local is newer than server."""
        now = datetime.utcnow()
        existing = Mock()
        existing.id = "prop-1"
        existing.updated_at = now - timedelta(hours=1)
        existing.to_dict.return_value = {"id": "prop-1", "status": "old"}

        mock_db.query.return_value.filter.return_value.all.return_value = [existing]

        changes = [
            PropertyChange(
                property_id="prop-1",
                operation=SyncOperation.UPDATE,
                data={"id": "prop-1", "status": "new"},
                timestamp=now,
                device_id="test-device"
            )
        ]

        non_conflicting, conflicts = resolver.batch_detect_conflicts("test-device", changes)

        assert len(non_conflicting) == 1
        assert len(conflicts) == 0

    def test_update_with_newer_server_creates_conflict(self, resolver, mock_db):
        """UPDATE creates conflict when server is newer than local."""
        now = datetime.utcnow()
        existing = Mock()
        existing.id = "prop-1"
        existing.updated_at = now
        existing.to_dict.return_value = {"id": "prop-1", "status": "server_update"}

        mock_db.query.return_value.filter.return_value.all.return_value = [existing]

        changes = [
            PropertyChange(
                property_id="prop-1",
                operation=SyncOperation.UPDATE,
                data={"id": "prop-1", "status": "local_update"},
                timestamp=now - timedelta(hours=1),
                device_id="test-device"
            )
        ]

        non_conflicting, conflicts = resolver.batch_detect_conflicts("test-device", changes)

        assert len(non_conflicting) == 0
        assert len(conflicts) == 1
        assert conflicts[0].property_id == "prop-1"

    def test_bulk_fetch_optimization(self, resolver, mock_db):
        """Batch detection uses bulk fetch instead of N+1 queries."""
        now = datetime.utcnow()

        changes = [
            PropertyChange(
                property_id=f"prop-{i}",
                operation=SyncOperation.UPDATE,
                data={"id": f"prop-{i}", "status": "updated"},
                timestamp=now,
                device_id="test-device"
            )
            for i in range(10)
        ]

        resolver.batch_detect_conflicts("test-device", changes)

        # Should only call query once for bulk fetch, not 10 times
        assert mock_db.query.call_count == 1

    def test_mixed_operations_handled_correctly(self, resolver, mock_db):
        """Mixed CREATE/UPDATE/DELETE operations are handled correctly."""
        now = datetime.utcnow()

        existing = Mock()
        existing.id = "prop-update"
        existing.updated_at = now
        existing.to_dict.return_value = {"id": "prop-update", "status": "server"}

        mock_db.query.return_value.filter.return_value.all.return_value = [existing]

        changes = [
            PropertyChange(
                property_id="prop-create",
                operation=SyncOperation.CREATE,
                data={"parcel_id": "NEW"},
                timestamp=now,
                device_id="test-device"
            ),
            PropertyChange(
                property_id="prop-update",
                operation=SyncOperation.UPDATE,
                data={"id": "prop-update", "status": "local"},
                timestamp=now - timedelta(hours=1),  # Older than server
                device_id="test-device"
            ),
            PropertyChange(
                property_id="prop-delete",
                operation=SyncOperation.DELETE,
                data={},
                timestamp=now,
                device_id="test-device"
            )
        ]

        non_conflicting, conflicts = resolver.batch_detect_conflicts("test-device", changes)

        # CREATE and DELETE pass through, UPDATE conflicts
        assert len(non_conflicting) == 2
        assert len(conflicts) == 1
        assert conflicts[0].property_id == "prop-update"
