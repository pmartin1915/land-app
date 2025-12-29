"""
Tests for SyncLogger - atomic logging for synchronization operations.

Tests cover:
- Log creation and updates
- Context manager exception handling
- Duration calculation
- Query methods for last sync and conflict counts
"""

import pytest
from unittest.mock import MagicMock, Mock, patch
from datetime import datetime, timedelta

from backend_api.services.sync.sync_logger import SyncLogger


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    return db


@pytest.fixture
def sync_logger(mock_db):
    """Create a SyncLogger with mocked database."""
    return SyncLogger(mock_db)


class TestCreateLog:
    """Tests for create_log method."""

    @pytest.mark.unit
    def test_creates_log_with_pending_status(self, sync_logger, mock_db):
        """New log should have 'pending' status."""
        log = sync_logger.create_log("device-123", "delta", True)

        assert log.status == "pending"
        assert log.device_id == "device-123"
        assert log.operation == "delta"

    @pytest.mark.unit
    def test_sets_algorithm_validation_flag(self, sync_logger, mock_db):
        """Algorithm validation flag should be set."""
        log_compatible = sync_logger.create_log("device-123", "delta", True)
        assert log_compatible.algorithm_validation_passed is True

        log_incompatible = sync_logger.create_log("device-123", "delta", False)
        assert log_incompatible.algorithm_validation_passed is False

    @pytest.mark.unit
    def test_sets_started_at_timestamp(self, sync_logger, mock_db):
        """started_at should be set to current time."""
        before = datetime.utcnow()
        log = sync_logger.create_log("device-123", "delta", True)
        after = datetime.utcnow()

        assert log.started_at >= before
        assert log.started_at <= after

    @pytest.mark.unit
    def test_adds_log_to_session(self, sync_logger, mock_db):
        """Log should be added to database session."""
        sync_logger.create_log("device-123", "delta", True)

        mock_db.add.assert_called_once()

    @pytest.mark.unit
    def test_flushes_to_get_id(self, sync_logger, mock_db):
        """Session should be flushed to get the log ID."""
        sync_logger.create_log("device-123", "delta", True)

        mock_db.flush.assert_called_once()


class TestUpdateLog:
    """Tests for update_log method."""

    @pytest.mark.unit
    def test_updates_status(self, sync_logger):
        """Status should be updated."""
        log = Mock()
        log.started_at = datetime.utcnow() - timedelta(seconds=5)

        sync_logger.update_log(log, "success", records_processed=10)

        assert log.status == "success"

    @pytest.mark.unit
    def test_updates_record_counts(self, sync_logger):
        """Record counts should be updated."""
        log = Mock()
        log.started_at = datetime.utcnow()

        sync_logger.update_log(
            log,
            "conflict",
            records_processed=100,
            conflicts_detected=5,
            conflicts_resolved=3
        )

        assert log.records_processed == 100
        assert log.conflicts_detected == 5
        assert log.conflicts_resolved == 3

    @pytest.mark.unit
    def test_sets_completed_at(self, sync_logger):
        """completed_at should be set."""
        log = Mock()
        log.started_at = datetime.utcnow() - timedelta(seconds=5)

        before = datetime.utcnow()
        sync_logger.update_log(log, "success")
        after = datetime.utcnow()

        assert log.completed_at >= before
        assert log.completed_at <= after

    @pytest.mark.unit
    def test_calculates_duration(self, sync_logger):
        """duration_seconds should be calculated from timestamps."""
        log = Mock()
        log.started_at = datetime.utcnow() - timedelta(seconds=10)

        sync_logger.update_log(log, "success")

        # Duration should be approximately 10 seconds
        assert log.duration_seconds >= 9.9
        assert log.duration_seconds <= 11.0

    @pytest.mark.unit
    def test_sets_error_message_on_failure(self, sync_logger):
        """Error message should be set on failure."""
        log = Mock()
        log.started_at = datetime.utcnow()

        sync_logger.update_log(log, "failed", error_message="Connection timeout")

        assert log.error_message == "Connection timeout"


class TestMarkFailed:
    """Tests for mark_failed method."""

    @pytest.mark.unit
    def test_sets_failed_status(self, sync_logger):
        """Status should be set to 'failed'."""
        log = Mock()
        log.started_at = datetime.utcnow()

        sync_logger.mark_failed(log, "Database error")

        assert log.status == "failed"
        assert log.error_message == "Database error"


class TestMarkSuccess:
    """Tests for mark_success method."""

    @pytest.mark.unit
    def test_sets_success_status_without_conflicts(self, sync_logger):
        """Status should be 'success' when no conflicts."""
        log = Mock()
        log.started_at = datetime.utcnow()

        sync_logger.mark_success(log, records_processed=50)

        assert log.status == "success"

    @pytest.mark.unit
    def test_sets_conflict_status_with_conflicts(self, sync_logger):
        """Status should be 'conflict' when conflicts detected."""
        log = Mock()
        log.started_at = datetime.utcnow()

        sync_logger.mark_success(log, records_processed=50, conflicts_detected=3)

        assert log.status == "conflict"


class TestSyncOperationContextManager:
    """Tests for sync_operation context manager."""

    @pytest.mark.unit
    def test_creates_and_yields_log(self, sync_logger, mock_db):
        """Should create log and yield it for use."""
        with sync_logger.sync_operation("device-123", "delta", True) as log:
            assert log is not None
            assert log.device_id == "device-123"

    @pytest.mark.unit
    def test_marks_success_on_normal_exit(self, sync_logger, mock_db):
        """Log should be marked success when context exits normally."""
        with sync_logger.sync_operation("device-123", "delta", True) as log:
            pass  # Normal exit

        # Should have called flush at the end
        assert mock_db.flush.called

    @pytest.mark.unit
    def test_marks_failed_on_exception(self, sync_logger, mock_db):
        """Log should be marked failed when exception is raised."""
        log_ref = None

        with pytest.raises(ValueError):
            with sync_logger.sync_operation("device-123", "delta", True) as log:
                log_ref = log
                raise ValueError("Test error")

        # The log status should be 'failed'
        assert log_ref.status == "failed"
        assert "Test error" in log_ref.error_message

    @pytest.mark.unit
    def test_reraises_exception(self, sync_logger, mock_db):
        """Exception should be re-raised after logging."""
        with pytest.raises(RuntimeError, match="Custom error"):
            with sync_logger.sync_operation("device-123", "delta", True):
                raise RuntimeError("Custom error")

    @pytest.mark.unit
    def test_flushes_on_exception(self, sync_logger, mock_db):
        """Session should be flushed even on exception."""
        try:
            with sync_logger.sync_operation("device-123", "delta", True):
                raise Exception("Test")
        except Exception:
            pass

        # flush called at least twice: once in create_log, once in finally
        assert mock_db.flush.call_count >= 2


class TestGetLastSuccessfulSync:
    """Tests for get_last_successful_sync method."""

    @pytest.mark.unit
    def test_returns_last_successful_sync(self, sync_logger, mock_db):
        """Should return the most recent successful sync log."""
        mock_log = Mock()
        mock_log.completed_at = datetime.utcnow()
        mock_log.status = "success"

        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_log

        result = sync_logger.get_last_successful_sync("device-123")

        assert result == mock_log

    @pytest.mark.unit
    def test_returns_none_when_no_syncs(self, sync_logger, mock_db):
        """Should return None when device has no successful syncs."""
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        result = sync_logger.get_last_successful_sync("new-device")

        assert result is None


class TestCountUnresolvedConflicts:
    """Tests for count_unresolved_conflicts method."""

    @pytest.mark.unit
    def test_counts_conflict_status_with_zero_resolved(self, sync_logger, mock_db):
        """Should count logs with 'conflict' status and zero resolved."""
        mock_db.query.return_value.filter.return_value.count.return_value = 3

        count = sync_logger.count_unresolved_conflicts("device-123")

        assert count == 3

    @pytest.mark.unit
    def test_returns_zero_when_no_conflicts(self, sync_logger, mock_db):
        """Should return zero when no unresolved conflicts."""
        mock_db.query.return_value.filter.return_value.count.return_value = 0

        count = sync_logger.count_unresolved_conflicts("device-123")

        assert count == 0
