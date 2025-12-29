"""
Integration tests for sync transaction safety.

Tests the orchestrator's ability to handle batch failures,
rollback partial changes, and provide detailed error information.
"""

import pytest
from datetime import timedelta
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from sqlalchemy.exc import IntegrityError, NoResultFound, DataError

from backend_api.services.sync.orchestrator import SyncOrchestrator
from backend_api.utils import utc_now
from backend_api.services.sync.conflict_resolver import ConflictResolver
from backend_api.services.sync.differ import SyncDiffer
from backend_api.services.sync.sync_logger import SyncLogger
from backend_api.models.sync import (
    DeltaSyncRequest, PropertyChange, SyncOperation,
    SyncStatus, RejectedChange
)


@pytest.fixture
def mock_db():
    """Create a mock database session with savepoint support."""
    db = MagicMock()

    # Mock savepoint as context manager (for 'with db.begin_nested():' pattern)
    savepoint = MagicMock()
    savepoint.__enter__ = MagicMock(return_value=savepoint)
    savepoint.__exit__ = MagicMock(return_value=False)  # Don't suppress exceptions
    db.begin_nested.return_value = savepoint

    return db


@pytest.fixture
def mock_property_service():
    """Create a mock property service."""
    service = MagicMock()
    service.create_property.return_value = Mock(id=str(uuid4()))
    service.update_property.return_value = Mock(id=str(uuid4()))
    service.delete_property.return_value = True
    service.get_property.return_value = Mock(
        id=str(uuid4()),
        updated_at=utc_now() - timedelta(hours=1),
        to_dict=lambda: {"id": str(uuid4()), "status": "new"}
    )
    return service


@pytest.fixture
def orchestrator(mock_db, mock_property_service):
    """Create an orchestrator with mocked dependencies."""
    with patch.object(SyncOrchestrator, '__init__', lambda self, db, ps=None: None):
        orch = SyncOrchestrator.__new__(SyncOrchestrator)
        orch.db = mock_db
        orch.property_service = mock_property_service
        orch.sync_logger = MagicMock()
        orch.differ = MagicMock()
        orch.conflict_resolver = MagicMock()

        # Default: no conflicts
        orch.conflict_resolver.batch_detect_conflicts.return_value = ([], [])

        return orch


class TestBatchProcessing:
    """Tests for batch processing with transaction safety."""

    @pytest.mark.integration
    def test_successful_batch_commits_savepoint(self, orchestrator, mock_db):
        """Successful batch should use savepoint context manager and apply all changes."""
        changes = [
            PropertyChange(
                property_id=str(uuid4()),
                operation=SyncOperation.CREATE,
                data={"parcel_id": "TEST-001", "amount": 1000},
                timestamp=utc_now(),
                device_id="test-device"
            ),
            PropertyChange(
                property_id=str(uuid4()),
                operation=SyncOperation.CREATE,
                data={"parcel_id": "TEST-002", "amount": 2000},
                timestamp=utc_now(),
                device_id="test-device"
            )
        ]

        orchestrator.conflict_resolver.batch_detect_conflicts.return_value = (changes, [])

        applied, rejected, conflicts, rejected_details, affected_ids = orchestrator._process_client_changes(
            "test-device", changes
        )

        assert applied == 2
        assert rejected == 0
        assert len(conflicts) == 0
        assert len(rejected_details) == 0
        assert len(affected_ids) == 2
        # Verify context manager was used (begin_nested called, __enter__ invoked)
        mock_db.begin_nested.assert_called()
        mock_db.begin_nested.return_value.__enter__.assert_called()

    @pytest.mark.integration
    def test_batch_failure_triggers_rollback(self, orchestrator, mock_db, mock_property_service):
        """Batch failure should trigger context manager exit and retry individually."""
        changes = [
            PropertyChange(
                property_id=str(uuid4()),
                operation=SyncOperation.CREATE,
                data={"parcel_id": "TEST-001", "amount": 1000},
                timestamp=utc_now(),
                device_id="test-device"
            ),
            PropertyChange(
                property_id=str(uuid4()),
                operation=SyncOperation.CREATE,
                data={"parcel_id": "TEST-002", "amount": 2000},
                timestamp=utc_now(),
                device_id="test-device"
            )
        ]

        orchestrator.conflict_resolver.batch_detect_conflicts.return_value = (changes, [])

        # First call fails (batch mode), subsequent calls succeed (individual mode)
        call_count = [0]

        def create_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # Use IntegrityError which is caught for fallback to individual processing
                raise IntegrityError("INSERT", {}, Exception("UNIQUE constraint failed"))
            return Mock(id=str(uuid4()))

        mock_property_service.create_property.side_effect = create_side_effect

        applied, rejected, conflicts, rejected_details, affected_ids = orchestrator._process_client_changes(
            "test-device", changes
        )

        # Context manager __exit__ should be called (handles rollback internally)
        mock_db.begin_nested.return_value.__exit__.assert_called()
        # Should have retried with individual processing (multiple begin_nested calls)
        assert mock_db.begin_nested.call_count >= 2

    @pytest.mark.integration
    def test_individual_failures_tracked_with_details(self, orchestrator, mock_db, mock_property_service):
        """Individual failures should include detailed error information."""
        changes = [
            PropertyChange(
                property_id="prop-1",
                operation=SyncOperation.CREATE,
                data={"parcel_id": "TEST-001", "amount": 1000},
                timestamp=utc_now(),
                device_id="test-device"
            ),
            PropertyChange(
                property_id="prop-2",
                operation=SyncOperation.CREATE,
                data={"parcel_id": "TEST-002", "amount": 2000},
                timestamp=utc_now(),
                device_id="test-device"
            )
        ]

        orchestrator.conflict_resolver.batch_detect_conflicts.return_value = (changes, [])

        # Batch always fails to trigger individual processing
        def batch_fail(*args, **kwargs):
            raise IntegrityError("INSERT", {}, Exception("Batch failed"))

        # First create succeeds, second fails with validation error
        create_results = [
            Mock(id=str(uuid4())),
            ValueError("Invalid property data: validation error")
        ]
        call_count = [0]

        def create_side_effect(*args, **kwargs):
            result = create_results[call_count[0] % len(create_results)]
            call_count[0] += 1
            if isinstance(result, Exception):
                raise result
            return result

        mock_property_service.create_property.side_effect = create_side_effect

        # Force individual processing by making batch fail
        with patch.object(orchestrator, '_apply_single_change') as mock_apply:
            mock_apply.side_effect = [None, ValueError("Invalid data validation error")]

            # _process_changes_individually returns (applied, rejected_changes, affected_ids)
            applied, rejected_changes, affected_ids = orchestrator._process_changes_individually(
                "test-device", changes
            )

        assert applied == 1
        assert len(rejected_changes) == 1
        assert len(affected_ids) == 1
        assert "prop-1" in affected_ids

        rejection = rejected_changes[0]
        assert rejection.property_id == "prop-2"
        assert rejection.operation == SyncOperation.CREATE
        assert "validation" in rejection.reason.lower()
        assert rejection.error_code == "VALIDATION_ERROR"
        assert rejection.recoverable is False


class TestErrorCategorization:
    """Tests for error categorization logic using exception types."""

    @pytest.mark.unit
    def test_categorize_validation_error(self, orchestrator):
        """ValueError should be categorized as VALIDATION_ERROR."""
        error = ValueError("Invalid property data")
        assert orchestrator._categorize_error(error) == "VALIDATION_ERROR"

    @pytest.mark.unit
    def test_categorize_type_error(self, orchestrator):
        """TypeError should be categorized as VALIDATION_ERROR."""
        error = TypeError("Expected int, got str")
        assert orchestrator._categorize_error(error) == "VALIDATION_ERROR"

    @pytest.mark.unit
    def test_categorize_constraint_violation(self, orchestrator):
        """IntegrityError should be categorized as CONSTRAINT_VIOLATION."""
        # IntegrityError requires specific constructor args
        error = IntegrityError("INSERT", {}, Exception("UNIQUE constraint failed"))
        assert orchestrator._categorize_error(error) == "CONSTRAINT_VIOLATION"

    @pytest.mark.unit
    def test_categorize_not_found_exception(self, orchestrator):
        """NoResultFound should be categorized as NOT_FOUND."""
        error = NoResultFound()
        assert orchestrator._categorize_error(error) == "NOT_FOUND"

    @pytest.mark.unit
    def test_categorize_not_found_string_fallback(self, orchestrator):
        """String containing 'not found' should fallback to NOT_FOUND."""
        error = Exception("Property not found: prop-123")
        assert orchestrator._categorize_error(error) == "NOT_FOUND"

    @pytest.mark.unit
    def test_categorize_data_error(self, orchestrator):
        """DataError should be categorized as VALIDATION_ERROR."""
        error = DataError("INSERT", {}, Exception("Invalid data type"))
        assert orchestrator._categorize_error(error) == "VALIDATION_ERROR"

    @pytest.mark.unit
    def test_categorize_permission_denied(self, orchestrator):
        """PermissionError should be categorized as PERMISSION_DENIED."""
        error = PermissionError("Access denied")
        assert orchestrator._categorize_error(error) == "PERMISSION_DENIED"

    @pytest.mark.unit
    def test_categorize_permission_string_fallback(self, orchestrator):
        """String containing 'permission' should fallback to PERMISSION_DENIED."""
        error = Exception("Permission denied for this operation")
        assert orchestrator._categorize_error(error) == "PERMISSION_DENIED"

    @pytest.mark.unit
    def test_categorize_unknown_error(self, orchestrator):
        """Unknown errors should default to INTERNAL_ERROR."""
        error = Exception("Something unexpected happened")
        assert orchestrator._categorize_error(error) == "INTERNAL_ERROR"


class TestDeltaSyncResponse:
    """Tests for delta sync response with rejection details."""

    @pytest.mark.integration
    def test_partial_status_on_rejections(self, orchestrator, mock_db):
        """Response should have PARTIAL status when some changes are rejected."""
        request = DeltaSyncRequest(
            device_id="test-device",
            last_sync_timestamp=utc_now() - timedelta(hours=1),
            changes=[],
            algorithm_version="1.0.0",
            app_version="1.0.0"
        )

        # Mock the process_client_changes to return rejections
        with patch.object(orchestrator, '_process_client_changes') as mock_process:
            mock_process.return_value = (
                1,  # applied
                1,  # rejected count
                [],  # conflicts
                [RejectedChange(
                    property_id="prop-1",
                    operation=SyncOperation.CREATE,
                    reason="Test error",
                    error_code="INTERNAL_ERROR",
                    recoverable=True
                )],
                {"prop-1"}  # affected_ids
            )

            # Mock other dependencies
            orchestrator.differ.get_server_changes.return_value = []
            orchestrator.sync_logger.create_log.return_value = Mock()

            with patch('backend_api.services.sync.orchestrator.validate_algorithm_compatibility') as mock_validate:
                mock_validate.return_value = (True, "Compatible")

                response = orchestrator.process_delta_sync(request)

        assert response.sync_status == SyncStatus.PARTIAL
        assert response.changes_applied == 1
        assert response.changes_rejected == 1
        assert len(response.rejected_details) == 1
        assert response.rejected_details[0].property_id == "prop-1"

    @pytest.mark.integration
    def test_success_status_on_no_rejections(self, orchestrator, mock_db):
        """Response should have SUCCESS status when all changes applied."""
        request = DeltaSyncRequest(
            device_id="test-device",
            last_sync_timestamp=utc_now() - timedelta(hours=1),
            changes=[],
            algorithm_version="1.0.0",
            app_version="1.0.0"
        )

        with patch.object(orchestrator, '_process_client_changes') as mock_process:
            mock_process.return_value = (2, 0, [], [], {"prop-1", "prop-2"})  # added affected_ids

            orchestrator.differ.get_server_changes.return_value = []
            orchestrator.sync_logger.create_log.return_value = Mock()

            with patch('backend_api.services.sync.orchestrator.validate_algorithm_compatibility') as mock_validate:
                mock_validate.return_value = (True, "Compatible")

                response = orchestrator.process_delta_sync(request)

        assert response.sync_status == SyncStatus.SUCCESS
        assert response.changes_rejected == 0
        assert len(response.rejected_details) == 0


class TestConflictDetection:
    """Tests for conflict detection during batch processing."""

    @pytest.mark.integration
    def test_conflicts_detected_before_applying(self, orchestrator, mock_db):
        """Conflicts should be detected before any changes are applied."""
        changes = [
            PropertyChange(
                property_id="prop-1",
                operation=SyncOperation.UPDATE,
                data={"status": "reviewing"},
                timestamp=utc_now(),
                device_id="test-device"
            )
        ]

        # Simulate conflict detection
        mock_conflict = Mock(property_id="prop-1")
        orchestrator.conflict_resolver.batch_detect_conflicts.return_value = (
            [],  # non-conflicting (empty - all have conflicts)
            [mock_conflict]  # conflicts
        )

        applied, rejected, conflicts, rejected_details, affected_ids = orchestrator._process_client_changes(
            "test-device", changes
        )

        assert applied == 0
        assert len(conflicts) == 1
        assert conflicts[0].property_id == "prop-1"
        assert len(affected_ids) == 0  # No changes applied due to conflicts
