"""
Synchronization service layer for iOS-backend communication.
Implements delta sync protocol with conflict resolution (last-write-wins).
Extracts business logic from routers for testability and UI/Core separation.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from ..database.models import Property, SyncLog
from ..models.sync import (
    DeltaSyncRequest, DeltaSyncResponse, FullSyncRequest, FullSyncResponse,
    SyncStatusResponse, ConflictResolutionRequest, ConflictResolutionResponse,
    SyncMetrics, BatchSyncRequest, BatchSyncResponse, SyncLogEntry,
    SyncLogListResponse, SyncOperation, SyncStatus, ConflictResolution,
    PropertyChange, SyncConflict, create_property_change, detect_conflict
)
from ..models.property import PropertyCreate, PropertyUpdate
from .property_service import PropertyService

logger = logging.getLogger(__name__)


class SyncService:
    """
    Synchronization service handling all sync operations.
    Ensures separation of concerns: router handles HTTP, service handles logic.
    """

    # Algorithm compatibility constants
    COMPATIBLE_ALGORITHM_VERSIONS = ["1.0.0", "1.0.1", "1.1.0"]
    EXPECTED_INVESTMENT_SCORE = 52.8
    EXPECTED_WATER_SCORE = 3.0
    SCORE_TOLERANCE = 0.1

    def __init__(self, db: Session, property_service: Optional[PropertyService] = None):
        """
        Initialize SyncService with database session and optional PropertyService.

        Args:
            db: SQLAlchemy database session
            property_service: Optional PropertyService instance (created if not provided)
        """
        self.db = db
        self.property_service = property_service or PropertyService(db)

    # =========================================================================
    # ALGORITHM VALIDATION
    # =========================================================================

    def validate_algorithm_compatibility(
        self,
        algorithm_version: str,
        app_version: str
    ) -> Tuple[bool, str]:
        """
        Validate algorithm compatibility between iOS and backend.
        CRITICAL: Ensures mathematical consistency across platforms.

        Args:
            algorithm_version: iOS algorithm version string
            app_version: iOS app version string

        Returns:
            Tuple of (is_compatible, message)
        """
        try:
            # Import and test algorithms
            from scripts.utils import calculate_investment_score, calculate_water_score
            from config.settings import INVESTMENT_SCORE_WEIGHTS

            # Quick validation test with known values
            test_investment_score = calculate_investment_score(
                5000.0, 3.0, 6.0, 0.8, INVESTMENT_SCORE_WEIGHTS
            )
            test_water_score = calculate_water_score('Beautiful creek frontage')

            # Validate investment score
            if abs(test_investment_score - self.EXPECTED_INVESTMENT_SCORE) > self.SCORE_TOLERANCE:
                return False, (
                    f"Investment score algorithm mismatch: "
                    f"expected {self.EXPECTED_INVESTMENT_SCORE}, got {test_investment_score}"
                )

            # Validate water score
            if abs(test_water_score - self.EXPECTED_WATER_SCORE) > self.SCORE_TOLERANCE:
                return False, (
                    f"Water score algorithm mismatch: "
                    f"expected {self.EXPECTED_WATER_SCORE}, got {test_water_score}"
                )

            # Version compatibility check
            if algorithm_version not in self.COMPATIBLE_ALGORITHM_VERSIONS:
                return False, f"Algorithm version {algorithm_version} not supported"

            return True, "Algorithms compatible"

        except Exception as e:
            return False, f"Algorithm validation failed: {str(e)}"

    # =========================================================================
    # SYNC LOG MANAGEMENT
    # =========================================================================

    def create_sync_log(
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
            Created SyncLog instance
        """
        sync_log = SyncLog(
            device_id=device_id,
            operation=operation,
            status="pending",
            algorithm_validation_passed=algorithm_compatible
        )
        self.db.add(sync_log)
        self.db.flush()  # Get ID without committing
        return sync_log

    def update_sync_log(
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
        sync_log.completed_at = datetime.utcnow()
        if sync_log.started_at:
            sync_log.duration_seconds = (
                sync_log.completed_at - sync_log.started_at
            ).total_seconds()

    # =========================================================================
    # DELTA SYNC
    # =========================================================================

    def process_client_changes(
        self,
        device_id: str,
        changes: List[PropertyChange]
    ) -> Tuple[int, int, List[SyncConflict]]:
        """
        Process incoming client changes from iOS.

        Args:
            device_id: Device that made the changes
            changes: List of property changes to process

        Returns:
            Tuple of (changes_applied, changes_rejected, conflicts)
        """
        changes_applied = 0
        changes_rejected = 0
        conflicts = []

        for change in changes:
            try:
                if change.operation == SyncOperation.CREATE:
                    self._process_create(change, device_id)
                    changes_applied += 1

                elif change.operation == SyncOperation.UPDATE:
                    conflict = self._process_update(change, device_id)
                    if conflict:
                        conflicts.append(conflict)
                    else:
                        changes_applied += 1

                elif change.operation == SyncOperation.DELETE:
                    self._process_delete(change, device_id)
                    changes_applied += 1

            except Exception as e:
                logger.error(f"Failed to process change {change.property_id}: {str(e)}")
                changes_rejected += 1

        return changes_applied, changes_rejected, conflicts

    def _process_create(self, change: PropertyChange, device_id: str) -> None:
        """Process a CREATE operation."""
        property_create = PropertyCreate(**change.data)
        self.property_service.create_property(property_create, device_id)

    def _process_update(
        self,
        change: PropertyChange,
        device_id: str
    ) -> Optional[SyncConflict]:
        """
        Process an UPDATE operation with conflict detection.

        Returns:
            SyncConflict if conflict detected, None otherwise
        """
        existing_property = self.property_service.get_property(change.property_id)

        if existing_property:
            # Compare timestamps to detect conflicts
            if existing_property.updated_at > change.timestamp:
                # Conflict detected - server is newer
                conflict = detect_conflict(
                    change.data,
                    existing_property.to_dict(),
                    change.timestamp,
                    existing_property.updated_at
                )
                if conflict:
                    return conflict

        # No conflict - apply update
        update_data = {k: v for k, v in change.data.items() if k != 'id'}
        property_update = PropertyUpdate(**update_data)
        self.property_service.update_property(change.property_id, property_update, device_id)
        return None

    def _process_delete(self, change: PropertyChange, device_id: str) -> None:
        """Process a DELETE operation (soft delete)."""
        self.property_service.delete_property(change.property_id, device_id)

    def get_server_changes(
        self,
        device_id: str,
        since_timestamp: datetime
    ) -> List[PropertyChange]:
        """
        Get server changes since last sync, excluding device's own changes.

        Args:
            device_id: Device requesting changes (excluded from results)
            since_timestamp: Timestamp to get changes after

        Returns:
            List of PropertyChange objects representing server changes
        """
        server_properties = self.db.query(Property).filter(
            Property.updated_at > since_timestamp,
            Property.device_id != device_id  # Exclude changes from this device
        ).all()

        server_changes = []
        for prop in server_properties:
            operation = SyncOperation.DELETE if prop.is_deleted else SyncOperation.UPDATE
            server_changes.append(create_property_change(
                prop.id,
                operation,
                prop.to_dict() if not prop.is_deleted else None,
                prop.device_id or "server"
            ))

        return server_changes

    def process_delta_sync(self, request: DeltaSyncRequest) -> DeltaSyncResponse:
        """
        Execute delta synchronization: process client changes, return server changes.

        Args:
            request: DeltaSyncRequest with client changes and sync metadata

        Returns:
            DeltaSyncResponse with server changes, conflicts, and status

        Raises:
            ValueError: If algorithm validation fails
        """
        # Validate algorithm compatibility
        algorithm_compatible, compatibility_message = self.validate_algorithm_compatibility(
            request.algorithm_version,
            request.app_version
        )

        # Create sync log
        sync_log = self.create_sync_log(
            request.device_id,
            "delta",
            algorithm_compatible
        )

        if not algorithm_compatible:
            self.update_sync_log(sync_log, "failed", error_message=compatibility_message)
            self.db.commit()
            raise ValueError(f"Algorithm compatibility error: {compatibility_message}")

        # Process client changes
        changes_applied, changes_rejected, conflicts = self.process_client_changes(
            request.device_id,
            request.changes
        )

        # Get server changes
        server_changes = self.get_server_changes(
            request.device_id,
            request.last_sync_timestamp
        )

        # Update sync log
        status = "success" if not conflicts else "conflict"
        self.update_sync_log(
            sync_log,
            status,
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

    # =========================================================================
    # FULL SYNC
    # =========================================================================

    def process_full_sync(self, request: FullSyncRequest) -> FullSyncResponse:
        """
        Execute full synchronization: return all properties.

        Args:
            request: FullSyncRequest with device info and options

        Returns:
            FullSyncResponse with all properties and sync timestamp

        Raises:
            ValueError: If algorithm validation fails
        """
        # Validate algorithm compatibility
        algorithm_compatible, compatibility_message = self.validate_algorithm_compatibility(
            request.algorithm_version,
            request.app_version
        )

        # Create sync log
        sync_log = self.create_sync_log(
            request.device_id,
            "full",
            algorithm_compatible
        )

        if not algorithm_compatible:
            self.update_sync_log(sync_log, "failed", error_message=compatibility_message)
            self.db.commit()
            raise ValueError(f"Algorithm compatibility error: {compatibility_message}")

        # Get all active properties
        active_properties = self.db.query(Property).filter(
            Property.is_deleted == False
        ).all()
        all_properties = [prop.to_dict() for prop in active_properties]

        # Get deleted property IDs if requested
        deleted_properties = []
        if request.include_deleted:
            deleted_props = self.db.query(Property.id).filter(
                Property.is_deleted == True
            ).all()
            deleted_properties = [prop.id for prop in deleted_props]

        # Update sync log
        self.update_sync_log(
            sync_log,
            "success",
            records_processed=len(all_properties)
        )

        sync_timestamp = datetime.utcnow()
        self.db.commit()

        logger.info(
            f"Full sync completed for device {request.device_id}: "
            f"{len(all_properties)} properties"
        )

        return FullSyncResponse(
            all_properties=all_properties,
            deleted_properties=deleted_properties,
            sync_timestamp=sync_timestamp,
            total_properties=len(all_properties),
            algorithm_compatibility=algorithm_compatible
        )

    # =========================================================================
    # SYNC STATUS
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
        last_sync = self.db.query(SyncLog).filter(
            SyncLog.device_id == device_id,
            SyncLog.status == "success"
        ).order_by(SyncLog.completed_at.desc()).first()

        last_sync_timestamp = last_sync.completed_at if last_sync else None

        # Count pending changes on server
        if last_sync_timestamp:
            pending_changes = self.db.query(Property).filter(
                Property.updated_at > last_sync_timestamp,
                Property.device_id != device_id
            ).count()
        else:
            pending_changes = self.db.query(Property).filter(
                Property.is_deleted == False
            ).count()

        # Check for unresolved conflicts
        sync_conflicts = self.db.query(SyncLog).filter(
            SyncLog.device_id == device_id,
            SyncLog.status == "conflict",
            SyncLog.conflicts_resolved == 0
        ).count()

        # Check algorithm compatibility
        algorithm_compatible, _ = self.validate_algorithm_compatibility("1.0.0", "1.0.0")

        is_sync_required = pending_changes > 0 or sync_conflicts > 0

        return SyncStatusResponse(
            device_id=device_id,
            last_sync_timestamp=last_sync_timestamp,
            pending_changes=pending_changes,
            sync_conflicts=sync_conflicts,
            is_sync_required=is_sync_required,
            algorithm_version_compatible=algorithm_compatible
        )

    # =========================================================================
    # CONFLICT RESOLUTION
    # =========================================================================

    def resolve_conflicts(
        self,
        request: ConflictResolutionRequest
    ) -> ConflictResolutionResponse:
        """
        Resolve synchronization conflicts using user decisions.

        Args:
            request: ConflictResolutionRequest with resolution decisions

        Returns:
            ConflictResolutionResponse with resolution results
        """
        resolved_conflicts = 0
        remaining_conflicts = 0
        errors = []

        for conflict in request.resolutions:
            try:
                success = self._apply_conflict_resolution(
                    conflict,
                    request.device_id
                )
                if success:
                    resolved_conflicts += 1
                else:
                    remaining_conflicts += 1
            except Exception as e:
                errors.append(
                    f"Failed to resolve conflict for property {conflict.property_id}: {str(e)}"
                )
                remaining_conflicts += 1

        # Create sync log for conflict resolution
        sync_log = SyncLog(
            device_id=request.device_id,
            operation="resolve_conflicts",
            status="success" if not errors else "partial",
            records_processed=len(request.resolutions),
            conflicts_resolved=resolved_conflicts,
            completed_at=datetime.utcnow()
        )
        self.db.add(sync_log)
        self.db.commit()

        return ConflictResolutionResponse(
            resolved_conflicts=resolved_conflicts,
            remaining_conflicts=remaining_conflicts,
            status=SyncStatus.SUCCESS if not errors else SyncStatus.PARTIAL,
            errors=errors
        )

    def _apply_conflict_resolution(
        self,
        conflict: SyncConflict,
        device_id: str
    ) -> bool:
        """
        Apply a single conflict resolution decision.

        Args:
            conflict: SyncConflict with resolution decision
            device_id: Device making the resolution

        Returns:
            True if resolution applied successfully
        """
        if conflict.resolution == ConflictResolution.USE_LOCAL:
            # Apply local data
            update_data = {k: v for k, v in conflict.local_data.items() if k != 'id'}
            property_update = PropertyUpdate(**update_data)
            self.property_service.update_property(
                conflict.property_id,
                property_update,
                device_id
            )
            return True

        elif conflict.resolution == ConflictResolution.USE_REMOTE:
            # Keep remote data (no action needed)
            return True

        elif conflict.resolution == ConflictResolution.MERGE:
            # Merge logic: default to last-write-wins
            if conflict.local_timestamp > conflict.remote_timestamp:
                update_data = {k: v for k, v in conflict.local_data.items() if k != 'id'}
                property_update = PropertyUpdate(**update_data)
                self.property_service.update_property(
                    conflict.property_id,
                    property_update,
                    device_id
                )
            return True

        else:
            # ASK_USER - should not reach here in automated resolution
            return False

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
        # Build query for active properties
        query = self.db.query(Property).filter(Property.is_deleted == False)

        # Apply starting point if provided
        if request.start_from:
            query = query.filter(Property.id > request.start_from)

        # Order by ID for consistent pagination
        query = query.order_by(Property.id)

        # Get batch + 1 to check if more data exists
        properties = query.limit(request.batch_size + 1).all()

        # Determine if more data is available
        has_more_data = len(properties) > request.batch_size
        if has_more_data:
            properties = properties[:-1]  # Remove the extra item

        # Convert to dictionaries
        batch_data = []
        for prop in properties:
            prop_dict = prop.to_dict()

            # Include algorithm calculations if requested
            if request.include_calculations and not prop_dict.get('investment_score'):
                calculated = self.property_service.calculate_property_metrics(prop_dict)
                prop_dict.update(calculated)

            batch_data.append(prop_dict)

        # Determine next batch start
        next_batch_start = properties[-1].id if properties else None

        # Estimate remaining records
        total_remaining = None
        if has_more_data and next_batch_start:
            remaining_query = self.db.query(Property).filter(
                Property.is_deleted == False,
                Property.id > next_batch_start
            )
            total_remaining = remaining_query.count()

        return BatchSyncResponse(
            batch_data=batch_data,
            next_batch_start=next_batch_start,
            has_more_data=has_more_data,
            batch_count=len(batch_data),
            total_remaining=total_remaining
        )

    # =========================================================================
    # SYNC LOGS
    # =========================================================================

    def get_logs(
        self,
        device_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> SyncLogListResponse:
        """
        Get paginated sync logs for monitoring and debugging.

        Args:
            device_id: Optional device filter
            page: Page number (1-indexed)
            page_size: Number of logs per page

        Returns:
            SyncLogListResponse with paginated log entries
        """
        # Build query
        query = self.db.query(SyncLog)

        if device_id:
            query = query.filter(SyncLog.device_id == device_id)

        # Get total count
        total_count = query.count()

        # Apply pagination and ordering
        offset = (page - 1) * page_size
        logs = query.order_by(SyncLog.started_at.desc()).offset(offset).limit(page_size).all()

        # Convert to response models
        log_entries = [SyncLogEntry.from_orm(log) for log in logs]

        return SyncLogListResponse(
            logs=log_entries,
            total_count=total_count,
            page=page,
            page_size=page_size
        )

    # =========================================================================
    # SYNC METRICS
    # =========================================================================

    def get_device_metrics(self, device_id: str) -> Optional[SyncMetrics]:
        """
        Get synchronization metrics for a specific device (last 7 days).

        Args:
            device_id: Device to get metrics for

        Returns:
            SyncMetrics for the device, or None if no recent syncs
        """
        # Get recent sync operations for this device
        recent_syncs = self.db.query(SyncLog).filter(
            SyncLog.device_id == device_id,
            SyncLog.started_at > datetime.utcnow() - timedelta(days=7)
        ).order_by(SyncLog.started_at.desc()).all()

        if not recent_syncs:
            return None

        # Use the most recent sync for metrics
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


# Dependency injection helper (mirrors property_service pattern)
def get_sync_service(db: Session) -> SyncService:
    """
    Dependency injection helper for FastAPI.
    Creates SyncService with database session.
    """
    return SyncService(db)
