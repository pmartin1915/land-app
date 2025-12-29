"""
Conflict Resolver for synchronization conflicts.
Implements various resolution strategies.
"""

import logging
from typing import List, Optional, Tuple
from datetime import datetime

from sqlalchemy.orm import Session

from ...database.models import Property, SyncLog
from ...models.sync import (
    SyncConflict, ConflictResolution, ConflictResolutionRequest,
    ConflictResolutionResponse, SyncStatus, PropertyChange, SyncOperation,
    detect_conflict
)
from ...models.property import PropertyUpdate
from ..property_service import PropertyService

logger = logging.getLogger(__name__)


class ConflictResolver:
    """
    Handles detection and resolution of synchronization conflicts.
    Supports multiple resolution strategies.
    """

    def __init__(self, db: Session, property_service: Optional[PropertyService] = None):
        """
        Initialize ConflictResolver.

        Args:
            db: SQLAlchemy database session
            property_service: PropertyService instance for updates
        """
        self.db = db
        self.property_service = property_service or PropertyService(db)

    def detect_update_conflict(
        self,
        change: PropertyChange,
        existing_property: Property
    ) -> Optional[SyncConflict]:
        """
        Detect if an update creates a conflict.

        Args:
            change: Incoming property change
            existing_property: Current property state

        Returns:
            SyncConflict if conflict detected, None otherwise
        """
        if not existing_property:
            return None

        # Compare timestamps to detect conflicts
        if existing_property.updated_at > change.timestamp:
            # Server version is newer - conflict detected
            return detect_conflict(
                change.data,
                existing_property.to_dict(),
                change.timestamp,
                existing_property.updated_at
            )

        return None

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
                success = self._apply_resolution(conflict, request.device_id)
                if success:
                    resolved_conflicts += 1
                else:
                    remaining_conflicts += 1
            except Exception as e:
                error_msg = f"Failed to resolve conflict for property {conflict.property_id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
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

    def _apply_resolution(
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
            return self._apply_local_data(conflict, device_id)

        elif conflict.resolution == ConflictResolution.USE_REMOTE:
            # Keep remote data - no action needed
            return True

        elif conflict.resolution == ConflictResolution.MERGE:
            return self._apply_merge(conflict, device_id)

        elif conflict.resolution == ConflictResolution.ASK_USER:
            # Cannot resolve automatically - needs user decision
            logger.warning(f"Conflict {conflict.property_id} requires user decision")
            return False

        else:
            logger.error(f"Unknown resolution type: {conflict.resolution}")
            return False

    def _apply_local_data(self, conflict: SyncConflict, device_id: str) -> bool:
        """Apply local data to resolve conflict."""
        if not conflict.local_data:
            logger.error(f"No local data for conflict {conflict.property_id}")
            return False

        update_data = {k: v for k, v in conflict.local_data.items() if k != 'id'}
        property_update = PropertyUpdate(**update_data)
        self.property_service.update_property(
            conflict.property_id,
            property_update,
            device_id
        )
        return True

    def _apply_merge(self, conflict: SyncConflict, device_id: str) -> bool:
        """
        Apply merge resolution using last-write-wins strategy.

        For more sophisticated merging, this could be extended to:
        - Field-level merging
        - Three-way merge
        - Custom merge rules per field
        """
        # Default merge: last-write-wins
        if conflict.local_timestamp and conflict.remote_timestamp:
            if conflict.local_timestamp > conflict.remote_timestamp:
                return self._apply_local_data(conflict, device_id)
            else:
                # Remote is newer, keep it
                return True

        # If timestamps not available, prefer local
        if conflict.local_data:
            return self._apply_local_data(conflict, device_id)

        return True

    def batch_detect_conflicts(
        self,
        device_id: str,
        changes: List[PropertyChange]
    ) -> Tuple[List[PropertyChange], List[SyncConflict]]:
        """
        Detect conflicts for a batch of changes.

        Args:
            device_id: Device making changes
            changes: List of property changes

        Returns:
            Tuple of (non-conflicting changes, conflicts)
        """
        non_conflicting = []
        conflicts = []

        for change in changes:
            if change.operation != SyncOperation.UPDATE:
                non_conflicting.append(change)
                continue

            # Get existing property
            existing = self.property_service.get_property(change.property_id)
            if not existing:
                non_conflicting.append(change)
                continue

            # Check for conflict
            conflict = self.detect_update_conflict(change, existing)
            if conflict:
                conflicts.append(conflict)
            else:
                non_conflicting.append(change)

        return non_conflicting, conflicts
