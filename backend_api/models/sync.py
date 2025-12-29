"""
Pydantic models for synchronization operations between iOS and backend
Implements delta sync protocol with conflict resolution (last-write-wins)
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class SyncOperation(str, Enum):
    """Synchronization operation types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    NO_CHANGE = "no_change"


class RejectedChange(BaseModel):
    """Details about a rejected change during sync."""
    property_id: str = Field(..., description="Property that was rejected")
    operation: SyncOperation = Field(..., description="Operation that failed")
    reason: str = Field(..., description="Why the change was rejected")
    error_code: Optional[str] = Field(None, description="Error code for categorization")
    recoverable: bool = Field(True, description="Whether the error is recoverable")

class SyncStatus(str, Enum):
    """Synchronization status values."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    CONFLICT = "conflict"
    PENDING = "pending"
    QUEUED = "queued"

class ConflictResolution(str, Enum):
    """Conflict resolution strategies."""
    USE_LOCAL = "use_local"
    USE_REMOTE = "use_remote"
    MERGE = "merge"
    ASK_USER = "ask_user"

class PropertyChange(BaseModel):
    """Model for individual property changes in sync operations."""
    property_id: str = Field(..., description="Unique property identifier")
    operation: SyncOperation = Field(..., description="Type of change operation")
    data: Optional[Dict[str, Any]] = Field(None, description="Property data (for create/update)")
    timestamp: datetime = Field(..., description="When the change occurred")
    device_id: str = Field(..., description="Device that made the change")
    checksum: Optional[str] = Field(None, description="Data checksum for integrity verification")

    @model_validator(mode='after')
    def validate_data_for_operation(self):
        """Validate that data is provided for create/update operations."""
        if self.operation in [SyncOperation.CREATE, SyncOperation.UPDATE] and self.data is None:
            raise ValueError(f"Data is required for {self.operation} operations")
        return self

class SyncConflict(BaseModel):
    """Model for synchronization conflicts."""
    property_id: str = Field(..., description="Property with conflict")
    local_timestamp: datetime = Field(..., description="Local modification timestamp")
    remote_timestamp: datetime = Field(..., description="Remote modification timestamp")
    local_data: Dict[str, Any] = Field(..., description="Local property data")
    remote_data: Dict[str, Any] = Field(..., description="Remote property data")
    conflict_fields: List[str] = Field(..., description="Fields that have conflicts")
    resolution: Optional[ConflictResolution] = Field(None, description="How to resolve conflict")

class DeltaSyncRequest(BaseModel):
    """Model for delta synchronization requests from iOS."""
    device_id: str = Field(..., description="Unique iOS device identifier")
    last_sync_timestamp: datetime = Field(..., description="Last successful sync timestamp")
    changes: List[PropertyChange] = Field(default=[], description="Local changes to upload")
    algorithm_version: str = Field(..., description="iOS algorithm version for compatibility check")
    app_version: str = Field(..., description="iOS app version")

    @field_validator('device_id')
    @classmethod
    def validate_device_id(cls, v: str) -> str:
        """Validate device ID format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Device ID cannot be empty")
        return v.strip()

class DeltaSyncResponse(BaseModel):
    """Model for delta synchronization responses to iOS."""
    server_changes: List[PropertyChange] = Field(..., description="Changes from server since last sync")
    conflicts: List[SyncConflict] = Field(default=[], description="Conflicts requiring resolution")
    new_sync_timestamp: datetime = Field(..., description="New sync timestamp for client")
    sync_status: SyncStatus = Field(..., description="Overall sync operation status")

    # Statistics
    changes_applied: int = Field(..., description="Number of client changes successfully applied")
    changes_rejected: int = Field(default=0, description="Number of client changes rejected")
    rejected_details: List["RejectedChange"] = Field(default=[], description="Details of rejected changes")
    server_changes_count: int = Field(..., description="Number of server changes sent to client")
    conflicts_count: int = Field(..., description="Number of conflicts detected")

    # Algorithm validation
    algorithm_compatibility: bool = Field(..., description="Whether algorithms are compatible")
    algorithm_validation_message: Optional[str] = Field(None, description="Algorithm validation details")

class FullSyncRequest(BaseModel):
    """Model for full synchronization requests (initial sync or after conflicts)."""
    device_id: str = Field(..., description="Unique iOS device identifier")
    force_sync: bool = Field(False, description="Force full sync even if recent")
    include_deleted: bool = Field(False, description="Include soft-deleted records")
    algorithm_version: str = Field(..., description="iOS algorithm version")
    app_version: str = Field(..., description="iOS app version")

class FullSyncResponse(BaseModel):
    """Model for full synchronization responses."""
    all_properties: List[Dict[str, Any]] = Field(..., description="All active properties")
    deleted_properties: List[str] = Field(default=[], description="IDs of deleted properties")
    sync_timestamp: datetime = Field(..., description="Sync timestamp for future delta syncs")
    total_properties: int = Field(..., description="Total number of properties")
    algorithm_compatibility: bool = Field(..., description="Algorithm compatibility status")

class SyncStatusRequest(BaseModel):
    """Model for sync status requests."""
    device_id: str = Field(..., description="Device to check status for")

class SyncStatusResponse(BaseModel):
    """Model for sync status responses."""
    device_id: str = Field(..., description="Device identifier")
    last_sync_timestamp: Optional[datetime] = Field(None, description="Last successful sync")
    pending_changes: int = Field(..., description="Number of pending changes on server")
    sync_conflicts: int = Field(default=0, description="Number of unresolved conflicts")
    is_sync_required: bool = Field(..., description="Whether sync is recommended")
    algorithm_version_compatible: bool = Field(..., description="Algorithm compatibility status")

class ConflictResolutionRequest(BaseModel):
    """Model for conflict resolution requests."""
    device_id: str = Field(..., description="Device resolving conflicts")
    resolutions: List[SyncConflict] = Field(..., description="Conflicts with resolution decisions")

class ConflictResolutionResponse(BaseModel):
    """Model for conflict resolution responses."""
    resolved_conflicts: int = Field(..., description="Number of conflicts resolved")
    remaining_conflicts: int = Field(..., description="Number of conflicts still pending")
    status: SyncStatus = Field(..., description="Resolution operation status")
    errors: List[str] = Field(default=[], description="Any errors during resolution")

class SyncMetrics(BaseModel):
    """Model for sync operation metrics and monitoring."""
    device_id: str = Field(..., description="Device identifier")
    operation_type: str = Field(..., description="Type of sync operation")
    started_at: datetime = Field(..., description="Operation start time")
    completed_at: Optional[datetime] = Field(None, description="Operation completion time")
    duration_seconds: Optional[float] = Field(None, description="Operation duration")

    # Data metrics
    records_processed: int = Field(default=0, description="Records processed")
    records_successful: int = Field(default=0, description="Successful records")
    records_failed: int = Field(default=0, description="Failed records")
    conflicts_detected: int = Field(default=0, description="Conflicts detected")
    conflicts_resolved: int = Field(default=0, description="Conflicts resolved")

    # Performance metrics
    network_time_seconds: Optional[float] = Field(None, description="Network time")
    processing_time_seconds: Optional[float] = Field(None, description="Processing time")
    algorithm_time_seconds: Optional[float] = Field(None, description="Algorithm calculation time")

    # Error information
    error_message: Optional[str] = Field(None, description="Error details if operation failed")
    algorithm_validation_passed: bool = Field(default=True, description="Algorithm compatibility check")

class BatchSyncRequest(BaseModel):
    """Model for batch synchronization operations."""
    device_id: str = Field(..., description="Device performing batch sync")
    batch_size: int = Field(100, description="Number of records per batch", ge=1, le=1000)
    start_from: Optional[str] = Field(None, description="Property ID to start batch from")
    include_calculations: bool = Field(True, description="Include algorithm calculations")

class BatchSyncResponse(BaseModel):
    """Model for batch synchronization responses."""
    batch_data: List[Dict[str, Any]] = Field(..., description="Batch of property data")
    next_batch_start: Optional[str] = Field(None, description="ID for next batch (if more data available)")
    has_more_data: bool = Field(..., description="Whether more batches are available")
    batch_count: int = Field(..., description="Number of records in this batch")
    total_remaining: Optional[int] = Field(None, description="Estimated total records remaining")

class SyncLogEntry(BaseModel):
    """Model for sync operation logging."""
    id: str = Field(..., description="Unique log entry ID")
    device_id: str = Field(..., description="Device identifier")
    operation: str = Field(..., description="Sync operation type")
    status: SyncStatus = Field(..., description="Operation status")

    # Timing
    started_at: datetime = Field(..., description="Operation start time")
    completed_at: Optional[datetime] = Field(None, description="Operation completion time")
    duration_seconds: Optional[float] = Field(None, description="Operation duration")

    # Statistics
    records_processed: int = Field(default=0, description="Records processed")
    conflicts_detected: int = Field(default=0, description="Conflicts detected")
    conflicts_resolved: int = Field(default=0, description="Conflicts resolved")

    # Error information
    error_message: Optional[str] = Field(None, description="Error details if failed")
    algorithm_validation_passed: bool = Field(default=True, description="Algorithm compatibility")

    class Config:
        from_attributes = True

class SyncLogListResponse(BaseModel):
    """Model for sync log list responses."""
    logs: List[SyncLogEntry] = Field(..., description="List of sync log entries")
    total_count: int = Field(..., description="Total number of log entries")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")

# Utility functions for sync operations
def create_property_change(
    property_id: str,
    operation: SyncOperation,
    data: Optional[Dict[str, Any]],
    device_id: str
) -> PropertyChange:
    """Create a PropertyChange instance with current timestamp."""
    return PropertyChange(
        property_id=property_id,
        operation=operation,
        data=data,
        timestamp=datetime.utcnow(),
        device_id=device_id
    )

def detect_conflict(
    local_data: Dict[str, Any],
    remote_data: Dict[str, Any],
    local_timestamp: datetime,
    remote_timestamp: datetime
) -> Optional[SyncConflict]:
    """Detect conflicts between local and remote data."""
    if local_timestamp == remote_timestamp:
        return None

    # Find conflicting fields
    conflict_fields = []
    for key in set(local_data.keys()) | set(remote_data.keys()):
        if local_data.get(key) != remote_data.get(key):
            conflict_fields.append(key)

    if not conflict_fields:
        return None

    return SyncConflict(
        property_id=local_data.get('id', ''),
        local_timestamp=local_timestamp,
        remote_timestamp=remote_timestamp,
        local_data=local_data,
        remote_data=remote_data,
        conflict_fields=conflict_fields
    )

def resolve_conflict_last_write_wins(conflict: SyncConflict) -> ConflictResolution:
    """Resolve conflict using last-write-wins strategy."""
    if conflict.local_timestamp > conflict.remote_timestamp:
        return ConflictResolution.USE_LOCAL
    else:
        return ConflictResolution.USE_REMOTE