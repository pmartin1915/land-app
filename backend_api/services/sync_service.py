"""
Synchronization service layer.
Implements delta sync protocol with conflict resolution (last-write-wins).

NOTE: This module now delegates to the decomposed sync package internally.
Maintained for backwards compatibility with existing router imports.
"""

import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from .sync import SyncOrchestrator
from .scoring import validate_algorithm_compatibility
from .property_service import PropertyService

from ..models.sync import (
    DeltaSyncRequest, DeltaSyncResponse, FullSyncRequest, FullSyncResponse,
    SyncStatusResponse, ConflictResolutionRequest, ConflictResolutionResponse,
    SyncMetrics, BatchSyncRequest, BatchSyncResponse,
    SyncLogListResponse
)

logger = logging.getLogger(__name__)


class SyncService:
    """
    Synchronization service handling all sync operations.

    This class now delegates to the decomposed sync package:
    - SyncOrchestrator: Main coordinator
    - SyncDiffer: Delta calculation
    - ConflictResolver: Conflict handling
    - SyncLogger: Operation logging

    Maintains backwards compatibility with existing code.
    """

    def __init__(self, db: Session, property_service: Optional[PropertyService] = None):
        """
        Initialize SyncService with database session.

        Args:
            db: SQLAlchemy database session
            property_service: Optional PropertyService instance
        """
        self.db = db
        self.property_service = property_service or PropertyService(db)
        self._orchestrator = SyncOrchestrator(db, self.property_service)

    def validate_algorithm_compatibility(
        self,
        algorithm_version: str,
        app_version: str
    ) -> Tuple[bool, str]:
        """
        Validate algorithm compatibility.

        Args:
            algorithm_version: Algorithm version string
            app_version: Client app version string

        Returns:
            Tuple of (is_compatible, message)
        """
        return validate_algorithm_compatibility(algorithm_version, app_version)

    def process_delta_sync(self, request: DeltaSyncRequest) -> DeltaSyncResponse:
        """
        Execute delta synchronization.

        Args:
            request: DeltaSyncRequest with client changes

        Returns:
            DeltaSyncResponse with server changes and conflicts
        """
        return self._orchestrator.process_delta_sync(request)

    def process_full_sync(self, request: FullSyncRequest) -> FullSyncResponse:
        """
        Execute full synchronization.

        Args:
            request: FullSyncRequest with device info

        Returns:
            FullSyncResponse with all properties
        """
        return self._orchestrator.process_full_sync(request)

    def process_batch_sync(self, request: BatchSyncRequest) -> BatchSyncResponse:
        """
        Get batch of properties for large dataset sync.

        Args:
            request: BatchSyncRequest with batch parameters

        Returns:
            BatchSyncResponse with paginated data
        """
        return self._orchestrator.process_batch_sync(request)

    def get_device_status(self, device_id: str) -> SyncStatusResponse:
        """
        Get synchronization status for a device.

        Args:
            device_id: Device to check

        Returns:
            SyncStatusResponse with status info
        """
        return self._orchestrator.get_device_status(device_id)

    def resolve_conflicts(
        self,
        request: ConflictResolutionRequest
    ) -> ConflictResolutionResponse:
        """
        Resolve synchronization conflicts.

        Args:
            request: ConflictResolutionRequest with resolutions

        Returns:
            ConflictResolutionResponse with results
        """
        return self._orchestrator.conflict_resolver.resolve_conflicts(request)

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
            page: Page number
            page_size: Items per page

        Returns:
            SyncLogListResponse with log entries
        """
        return self._orchestrator.get_logs(device_id, page, page_size)

    def get_device_metrics(self, device_id: str) -> Optional[SyncMetrics]:
        """
        Get synchronization metrics for a device.

        Args:
            device_id: Device to get metrics for

        Returns:
            SyncMetrics or None
        """
        return self._orchestrator.get_device_metrics(device_id)


# Dependency injection helper
def get_sync_service(db: Session) -> SyncService:
    """
    Dependency injection helper for FastAPI.

    Args:
        db: SQLAlchemy database session

    Returns:
        SyncService instance
    """
    return SyncService(db)
