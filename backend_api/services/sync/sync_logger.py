"""
Sync Logger for tracking synchronization operations.
Provides atomic logging with proper transaction handling.
"""

import logging
from typing import Optional
from contextlib import contextmanager

from sqlalchemy.orm import Session

from ...database.models import SyncLog
from ...utils import utc_now

logger = logging.getLogger(__name__)


class SyncLogger:
    """
    Manages sync log entries with atomic operations.
    Ensures proper transaction handling to prevent zombie jobs.
    """

    def __init__(self, db: Session):
        """
        Initialize SyncLogger with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_log(
        self,
        device_id: str,
        operation: str,
        algorithm_compatible: bool
    ) -> SyncLog:
        """
        Create a new sync log entry.

        Args:
            device_id: Device identifier
            operation: Sync operation type (delta, full, resolve_conflicts, etc.)
            algorithm_compatible: Whether algorithm validation passed

        Returns:
            Created SyncLog instance (not yet committed)
        """
        sync_log = SyncLog(
            device_id=device_id,
            operation=operation,
            status="pending",
            algorithm_validation_passed=algorithm_compatible,
            started_at=utc_now()
        )
        self.db.add(sync_log)
        self.db.flush()  # Get ID without committing
        return sync_log

    def update_log(
        self,
        sync_log: SyncLog,
        status: str,
        records_processed: int = 0,
        conflicts_detected: int = 0,
        conflicts_resolved: int = 0,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update an existing sync log with results.

        Args:
            sync_log: SyncLog instance to update
            status: New status (success, failed, conflict, partial)
            records_processed: Number of records processed
            conflicts_detected: Number of conflicts detected
            conflicts_resolved: Number of conflicts resolved
            error_message: Error message if failed
        """
        sync_log.status = status
        sync_log.records_processed = records_processed
        sync_log.conflicts_detected = conflicts_detected
        sync_log.conflicts_resolved = conflicts_resolved
        sync_log.error_message = error_message
        sync_log.completed_at = utc_now()

        if sync_log.started_at:
            sync_log.duration_seconds = (
                sync_log.completed_at - sync_log.started_at
            ).total_seconds()

    def mark_failed(
        self,
        sync_log: SyncLog,
        error_message: str
    ) -> None:
        """
        Mark a sync log as failed.

        Args:
            sync_log: SyncLog instance to update
            error_message: Error description
        """
        self.update_log(sync_log, "failed", error_message=error_message)

    def mark_success(
        self,
        sync_log: SyncLog,
        records_processed: int = 0,
        conflicts_detected: int = 0,
        conflicts_resolved: int = 0
    ) -> None:
        """
        Mark a sync log as successful.

        Args:
            sync_log: SyncLog instance to update
            records_processed: Number of records processed
            conflicts_detected: Number of conflicts detected
            conflicts_resolved: Number of conflicts resolved
        """
        status = "success" if conflicts_detected == 0 else "conflict"
        self.update_log(
            sync_log,
            status,
            records_processed=records_processed,
            conflicts_detected=conflicts_detected,
            conflicts_resolved=conflicts_resolved
        )

    @contextmanager
    def sync_operation(
        self,
        device_id: str,
        operation: str,
        algorithm_compatible: bool
    ):
        """
        Context manager for sync operations with automatic logging.

        Usage:
            with sync_logger.sync_operation("device123", "delta", True) as log:
                # Do sync work
                log.records_processed = 10

        Args:
            device_id: Device identifier
            operation: Operation type
            algorithm_compatible: Algorithm validation status

        Yields:
            SyncLog instance for the operation
        """
        sync_log = self.create_log(device_id, operation, algorithm_compatible)

        try:
            yield sync_log
            # If no exception, mark as success (caller should update counts)
            if sync_log.status == "pending":
                self.mark_success(sync_log)
        except Exception as e:
            self.mark_failed(sync_log, str(e))
            raise
        finally:
            # Ensure changes are flushed
            self.db.flush()

    def get_last_successful_sync(self, device_id: str) -> Optional[SyncLog]:
        """
        Get the last successful sync for a device.

        Args:
            device_id: Device identifier

        Returns:
            Last successful SyncLog or None
        """
        return self.db.query(SyncLog).filter(
            SyncLog.device_id == device_id,
            SyncLog.status == "success"
        ).order_by(SyncLog.completed_at.desc()).first()

    def count_unresolved_conflicts(self, device_id: str) -> int:
        """
        Count unresolved conflicts for a device.

        Args:
            device_id: Device identifier

        Returns:
            Count of unresolved conflicts
        """
        return self.db.query(SyncLog).filter(
            SyncLog.device_id == device_id,
            SyncLog.status == "conflict",
            SyncLog.conflicts_resolved == 0
        ).count()
