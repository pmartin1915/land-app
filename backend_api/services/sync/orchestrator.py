"""
Sync Orchestrator - Main coordinator for synchronization operations.
Thin layer that coordinates between differ, resolver, and logger.
"""

import logging
from typing import Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ...database.models import Property, SyncLog
from ...models.sync import (
    DeltaSyncRequest, DeltaSyncResponse, FullSyncRequest, FullSyncResponse,
    SyncStatusResponse, BatchSyncRequest, BatchSyncResponse,
    SyncMetrics, SyncLogEntry, SyncLogListResponse,
    SyncStatus, SyncOperation, PropertyChange, RejectedChange
)
from ...models.property import PropertyCreate, PropertyUpdate
from ..property_service import PropertyService
from ..scoring import validate_algorithm_compatibility
from .sync_logger import SyncLogger
from .differ import SyncDiffer
from .conflict_resolver import ConflictResolver

logger = logging.getLogger(__name__)


class SyncOrchestrator:
    """
    Orchestrates synchronization operations.
    Coordinates between differ, conflict resolver, and logger.
    """

    def __init__(self, db: Session, property_service: Optional[PropertyService] = None):
        """
        Initialize SyncOrchestrator with dependencies.

        Args:
            db: SQLAlchemy database session
            property_service: PropertyService instance (created if not provided)
        """
        self.db = db
        self.property_service = property_service or PropertyService(db)
        self.sync_logger = SyncLogger(db)
        self.differ = SyncDiffer(db)
        self.conflict_resolver = ConflictResolver(db, self.property_service)

    # =========================================================================
    # DELTA SYNC
    # =========================================================================

    def process_delta_sync(self, request: DeltaSyncRequest) -> DeltaSyncResponse:
        """
        Execute delta synchronization.

        Args:
            request: DeltaSyncRequest with client changes and sync metadata

        Returns:
            DeltaSyncResponse with server changes, conflicts, and status

        Raises:
            ValueError: If algorithm validation fails
        """
        # Validate algorithm compatibility
        algorithm_compatible, compatibility_message = validate_algorithm_compatibility(
            request.algorithm_version,
            request.app_version
        )

        # Create sync log
        sync_log = self.sync_logger.create_log(
            request.device_id,
            "delta",
            algorithm_compatible
        )

        if not algorithm_compatible:
            self.sync_logger.mark_failed(sync_log, compatibility_message)
            self.db.commit()
            raise ValueError(f"Algorithm compatibility error: {compatibility_message}")

        # Process client changes with transaction safety
        changes_applied, changes_rejected, conflicts, rejected_details = self._process_client_changes(
            request.device_id,
            request.changes
        )

        # Get server changes
        server_changes = self.differ.get_server_changes(
            request.device_id,
            request.last_sync_timestamp
        )

        # Update sync log
        self.sync_logger.mark_success(
            sync_log,
            records_processed=len(request.changes),
            conflicts_detected=len(conflicts)
        )

        new_sync_timestamp = datetime.utcnow()
        self.db.commit()

        # Determine overall status
        if conflicts:
            sync_status = SyncStatus.CONFLICT
        elif changes_rejected > 0:
            sync_status = SyncStatus.PARTIAL
        else:
            sync_status = SyncStatus.SUCCESS

        logger.info(
            f"Delta sync completed for device {request.device_id}: "
            f"{changes_applied} applied, {changes_rejected} rejected, {len(conflicts)} conflicts"
        )

        return DeltaSyncResponse(
            server_changes=server_changes,
            conflicts=conflicts,
            new_sync_timestamp=new_sync_timestamp,
            sync_status=sync_status,
            changes_applied=changes_applied,
            changes_rejected=changes_rejected,
            rejected_details=rejected_details,
            server_changes_count=len(server_changes),
            conflicts_count=len(conflicts),
            algorithm_compatibility=algorithm_compatible,
            algorithm_validation_message=compatibility_message
        )

    def _process_client_changes(self, device_id: str, changes: list):
        """
        Process incoming client changes with transaction safety.

        Uses savepoints to allow partial rollback on batch failures.
        Returns detailed rejection information for failed changes.
        """
        changes_applied = 0
        rejected_changes = []
        conflicts = []

        # First pass: detect conflicts without modifying data
        non_conflicting, detected_conflicts = self.conflict_resolver.batch_detect_conflicts(
            device_id, changes
        )
        conflicts.extend(detected_conflicts)

        # Try batch processing with savepoint for atomicity
        # Using context manager to ensure proper rollback even if begin_nested() fails
        try:
            with self.db.begin_nested():
                for change in non_conflicting:
                    self._apply_single_change(change, device_id)
                    changes_applied += 1
                # Context manager commits on successful exit

        except Exception as batch_error:
            # Batch failed - context manager already rolled back
            logger.warning(f"Batch processing failed, falling back to individual: {str(batch_error)}")

            # Reset counter and process one by one
            changes_applied = 0
            changes_applied, rejected_changes = self._process_changes_individually(
                device_id, non_conflicting
            )

        return changes_applied, len(rejected_changes), conflicts, rejected_changes

    def _apply_single_change(self, change: PropertyChange, device_id: str):
        """Apply a single change operation. Raises on failure."""
        if change.operation == SyncOperation.CREATE:
            property_create = PropertyCreate(**change.data)
            self.property_service.create_property(property_create, device_id)

        elif change.operation == SyncOperation.UPDATE:
            update_data = {k: v for k, v in change.data.items() if k != 'id'}
            property_update = PropertyUpdate(**update_data)
            self.property_service.update_property(
                change.property_id, property_update, device_id
            )

        elif change.operation == SyncOperation.DELETE:
            self.property_service.delete_property(change.property_id, device_id)

    def _process_changes_individually(self, device_id: str, changes: list):
        """
        Process changes one at a time with individual error handling.
        Used as fallback when batch processing fails.
        """
        changes_applied = 0
        rejected_changes = []

        for change in changes:
            try:
                with self.db.begin_nested():
                    self._apply_single_change(change, device_id)
                    # Context manager commits on successful exit
                changes_applied += 1

            except Exception as e:
                # Context manager already rolled back on exception
                error_msg = str(e)
                logger.error(f"Failed to process change {change.property_id}: {error_msg}")

                # Categorize error
                error_code = self._categorize_error(e)
                recoverable = error_code not in ["VALIDATION_ERROR", "CONSTRAINT_VIOLATION"]

                rejected_changes.append(RejectedChange(
                    property_id=change.property_id,
                    operation=change.operation,
                    reason=error_msg,
                    error_code=error_code,
                    recoverable=recoverable
                ))

        return changes_applied, rejected_changes

    def _categorize_error(self, error: Exception) -> str:
        """Categorize an error for client handling."""
        error_str = str(error).lower()

        if "validation" in error_str or "invalid" in error_str:
            return "VALIDATION_ERROR"
        elif "constraint" in error_str or "duplicate" in error_str:
            return "CONSTRAINT_VIOLATION"
        elif "not found" in error_str:
            return "NOT_FOUND"
        elif "permission" in error_str or "unauthorized" in error_str:
            return "PERMISSION_DENIED"
        else:
            return "INTERNAL_ERROR"

    # =========================================================================
    # FULL SYNC
    # =========================================================================

    def process_full_sync(self, request: FullSyncRequest) -> FullSyncResponse:
        """
        Execute full synchronization.

        Args:
            request: FullSyncRequest with device info and options

        Returns:
            FullSyncResponse with all properties and sync timestamp

        Raises:
            ValueError: If algorithm validation fails
        """
        # Validate algorithm compatibility
        algorithm_compatible, compatibility_message = validate_algorithm_compatibility(
            request.algorithm_version,
            request.app_version
        )

        # Create sync log
        sync_log = self.sync_logger.create_log(
            request.device_id,
            "full",
            algorithm_compatible
        )

        if not algorithm_compatible:
            self.sync_logger.mark_failed(sync_log, compatibility_message)
            self.db.commit()
            raise ValueError(f"Algorithm compatibility error: {compatibility_message}")

        # Get all properties
        all_properties, deleted_ids = self.differ.get_all_active_properties(
            include_deleted=request.include_deleted
        )

        # Update sync log
        self.sync_logger.mark_success(sync_log, records_processed=len(all_properties))

        sync_timestamp = datetime.utcnow()
        self.db.commit()

        logger.info(
            f"Full sync completed for device {request.device_id}: "
            f"{len(all_properties)} properties"
        )

        return FullSyncResponse(
            all_properties=all_properties,
            deleted_properties=deleted_ids,
            sync_timestamp=sync_timestamp,
            total_properties=len(all_properties),
            algorithm_compatibility=algorithm_compatible
        )

    # =========================================================================
    # BATCH SYNC
    # =========================================================================

    def process_batch_sync(self, request: BatchSyncRequest) -> BatchSyncResponse:
        """
        Get batch of properties for large dataset synchronization.

        Args:
            request: BatchSyncRequest with batch parameters

        Returns:
            BatchSyncResponse with paginated property data
        """
        batch_data, next_start, has_more = self.differ.get_batch(
            start_from=request.start_from,
            batch_size=request.batch_size,
            include_calculations=request.include_calculations,
            property_service=self.property_service
        )

        # Estimate remaining records
        total_remaining = None
        if has_more and next_start:
            remaining_query = self.db.query(Property).filter(
                Property.is_deleted == False,
                Property.id > next_start
            )
            total_remaining = remaining_query.count()

        return BatchSyncResponse(
            batch_data=batch_data,
            next_batch_start=next_start,
            has_more_data=has_more,
            batch_count=len(batch_data),
            total_remaining=total_remaining
        )

    # =========================================================================
    # STATUS & METRICS
    # =========================================================================

    def get_device_status(self, device_id: str) -> SyncStatusResponse:
        """
        Get synchronization status for a device.

        Args:
            device_id: Device to check status for

        Returns:
            SyncStatusResponse with pending changes, conflicts, etc.
        """
        # Get last successful sync
        last_sync = self.sync_logger.get_last_successful_sync(device_id)
        last_sync_timestamp = last_sync.completed_at if last_sync else None

        # Count pending changes
        pending_changes = self.differ.get_pending_change_count(device_id, last_sync_timestamp)

        # Check for unresolved conflicts
        sync_conflicts = self.sync_logger.count_unresolved_conflicts(device_id)

        # Check algorithm compatibility
        algorithm_compatible, _ = validate_algorithm_compatibility("1.0.0", "1.0.0")

        is_sync_required = pending_changes > 0 or sync_conflicts > 0

        return SyncStatusResponse(
            device_id=device_id,
            last_sync_timestamp=last_sync_timestamp,
            pending_changes=pending_changes,
            sync_conflicts=sync_conflicts,
            is_sync_required=is_sync_required,
            algorithm_version_compatible=algorithm_compatible
        )

    def get_device_metrics(self, device_id: str) -> Optional[SyncMetrics]:
        """
        Get synchronization metrics for a device (last 7 days).

        Args:
            device_id: Device to get metrics for

        Returns:
            SyncMetrics for the device, or None if no recent syncs
        """
        # Get recent sync operations
        recent_syncs = self.db.query(SyncLog).filter(
            SyncLog.device_id == device_id,
            SyncLog.started_at > datetime.utcnow() - timedelta(days=7)
        ).order_by(SyncLog.started_at.desc()).all()

        if not recent_syncs:
            return None

        latest_sync = recent_syncs[0]

        return SyncMetrics(
            device_id=device_id,
            operation_type=latest_sync.operation,
            started_at=latest_sync.started_at,
            completed_at=latest_sync.completed_at,
            duration_seconds=latest_sync.duration_seconds,
            records_processed=latest_sync.records_processed,
            records_successful=latest_sync.records_processed - (latest_sync.conflicts_detected or 0),
            records_failed=latest_sync.conflicts_detected or 0,
            conflicts_detected=latest_sync.conflicts_detected or 0,
            conflicts_resolved=latest_sync.conflicts_resolved or 0,
            error_message=latest_sync.error_message,
            algorithm_validation_passed=latest_sync.algorithm_validation_passed
        )

    def get_logs(
        self,
        device_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> SyncLogListResponse:
        """
        Get paginated sync logs.

        Args:
            device_id: Optional device filter
            page: Page number (1-indexed)
            page_size: Number of logs per page

        Returns:
            SyncLogListResponse with paginated log entries
        """
        query = self.db.query(SyncLog)

        if device_id:
            query = query.filter(SyncLog.device_id == device_id)

        total_count = query.count()
        offset = (page - 1) * page_size
        logs = query.order_by(SyncLog.started_at.desc()).offset(offset).limit(page_size).all()

        log_entries = [SyncLogEntry.from_orm(log) for log in logs]

        return SyncLogListResponse(
            logs=log_entries,
            total_count=total_count,
            page=page,
            page_size=page_size
        )


# Dependency injection helper
def get_sync_orchestrator(db: Session) -> SyncOrchestrator:
    """
    Dependency injection helper for FastAPI.

    Args:
        db: SQLAlchemy database session

    Returns:
        SyncOrchestrator instance
    """
    return SyncOrchestrator(db)
