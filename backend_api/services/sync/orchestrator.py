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
    SyncStatus, SyncOperation, PropertyChange
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

        # Process client changes
        changes_applied, changes_rejected, conflicts = self._process_client_changes(
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

        logger.info(
            f"Delta sync completed for device {request.device_id}: "
            f"{changes_applied} applied, {changes_rejected} rejected, {len(conflicts)} conflicts"
        )

        return DeltaSyncResponse(
            server_changes=server_changes,
            conflicts=conflicts,
            new_sync_timestamp=new_sync_timestamp,
            sync_status=SyncStatus.SUCCESS if not conflicts else SyncStatus.CONFLICT,
            changes_applied=changes_applied,
            changes_rejected=changes_rejected,
            server_changes_count=len(server_changes),
            conflicts_count=len(conflicts),
            algorithm_compatibility=algorithm_compatible,
            algorithm_validation_message=compatibility_message
        )

    def _process_client_changes(self, device_id: str, changes: list):
        """Process incoming client changes."""
        changes_applied = 0
        changes_rejected = 0
        conflicts = []

        for change in changes:
            try:
                if change.operation == SyncOperation.CREATE:
                    property_create = PropertyCreate(**change.data)
                    self.property_service.create_property(property_create, device_id)
                    changes_applied += 1

                elif change.operation == SyncOperation.UPDATE:
                    existing = self.property_service.get_property(change.property_id)
                    conflict = self.conflict_resolver.detect_update_conflict(change, existing)
                    if conflict:
                        conflicts.append(conflict)
                    else:
                        update_data = {k: v for k, v in change.data.items() if k != 'id'}
                        property_update = PropertyUpdate(**update_data)
                        self.property_service.update_property(
                            change.property_id, property_update, device_id
                        )
                        changes_applied += 1

                elif change.operation == SyncOperation.DELETE:
                    self.property_service.delete_property(change.property_id, device_id)
                    changes_applied += 1

            except Exception as e:
                logger.error(f"Failed to process change {change.property_id}: {str(e)}")
                changes_rejected += 1

        return changes_applied, changes_rejected, conflicts

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
