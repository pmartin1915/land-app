"""
Synchronization endpoints for iOS-backend communication
Implements delta sync protocol with conflict resolution (last-write-wins)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
import logging
from datetime import datetime, timedelta
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..database.connection import get_db
from ..database.models import Property, SyncLog
from ..services.property_service import PropertyService
from ..models.sync import (
    DeltaSyncRequest, DeltaSyncResponse, FullSyncRequest, FullSyncResponse,
    SyncStatusResponse, ConflictResolutionRequest, ConflictResolutionResponse,
    SyncMetrics, BatchSyncRequest, BatchSyncResponse, SyncLogEntry,
    SyncLogListResponse, SyncOperation, SyncStatus, ConflictResolution,
    create_property_change, detect_conflict
)

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()

def get_property_service(db: Session = Depends(get_db)) -> PropertyService:
    """Dependency to get PropertyService instance."""
    return PropertyService(db)

def validate_algorithm_compatibility(algorithm_version: str, app_version: str) -> tuple[bool, str]:
    """
    Validate algorithm compatibility between iOS and backend.
    CRITICAL: Ensures mathematical consistency across platforms.
    """
    try:
        # Import and test algorithms
        from scripts.utils import calculate_investment_score, calculate_water_score
        from config.settings import INVESTMENT_SCORE_WEIGHTS

        # Quick validation test with known values
        test_investment_score = calculate_investment_score(5000.0, 3.0, 6.0, 0.8, INVESTMENT_SCORE_WEIGHTS)
        test_water_score = calculate_water_score('Beautiful creek frontage')

        # Expected values from algorithm validation
        if abs(test_investment_score - 52.8) > 0.1:
            return False, f"Investment score algorithm mismatch: expected 52.8, got {test_investment_score}"

        if abs(test_water_score - 3.0) > 0.1:
            return False, f"Water score algorithm mismatch: expected 3.0, got {test_water_score}"

        # Version compatibility check
        compatible_versions = ["1.0.0", "1.0.1", "1.1.0"]  # Add iOS app versions as they're released
        if algorithm_version not in compatible_versions:
            return False, f"Algorithm version {algorithm_version} not supported"

        return True, "Algorithms compatible"

    except Exception as e:
        return False, f"Algorithm validation failed: {str(e)}"

@router.post("/delta", response_model=DeltaSyncResponse)
@limiter.limit("20/minute")
async def delta_sync(
    request: Request,
    sync_request: DeltaSyncRequest,
    db: Session = Depends(get_db),
    property_service: PropertyService = Depends(get_property_service)
):
    """
    Perform delta synchronization between iOS and backend.
    Returns only changes since last sync timestamp.
    """
    sync_log = None
    try:
        # Validate algorithm compatibility
        algorithm_compatible, compatibility_message = validate_algorithm_compatibility(
            sync_request.algorithm_version,
            sync_request.app_version
        )

        # Create sync log entry
        sync_log = SyncLog(
            device_id=sync_request.device_id,
            operation="delta",
            status="pending",
            algorithm_validation_passed=algorithm_compatible
        )
        db.add(sync_log)
        db.flush()  # Get ID without committing

        if not algorithm_compatible:
            sync_log.status = "failed"
            sync_log.error_message = compatibility_message
            sync_log.completed_at = datetime.utcnow()
            db.commit()

            raise HTTPException(
                status_code=400,
                detail=f"Algorithm compatibility error: {compatibility_message}"
            )

        # Process client changes
        changes_applied = 0
        changes_rejected = 0
        conflicts = []

        for change in sync_request.changes:
            try:
                if change.operation == SyncOperation.CREATE:
                    # Create new property
                    from ..models.property import PropertyCreate
                    property_create = PropertyCreate(**change.data)
                    property_service.create_property(property_create, sync_request.device_id)
                    changes_applied += 1

                elif change.operation == SyncOperation.UPDATE:
                    # Check for conflicts
                    existing_property = property_service.get_property(change.property_id)
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
                                conflicts.append(conflict)
                                continue

                    # Update property
                    from ..models.property import PropertyUpdate
                    update_data = {k: v for k, v in change.data.items() if k != 'id'}
                    property_update = PropertyUpdate(**update_data)
                    property_service.update_property(change.property_id, property_update, sync_request.device_id)
                    changes_applied += 1

                elif change.operation == SyncOperation.DELETE:
                    # Soft delete property
                    property_service.delete_property(change.property_id, sync_request.device_id)
                    changes_applied += 1

            except Exception as e:
                logger.error(f"Failed to process change {change.property_id}: {str(e)}")
                changes_rejected += 1

        # Get server changes since last sync
        server_changes = []
        server_properties = db.query(Property).filter(
            Property.updated_at > sync_request.last_sync_timestamp,
            Property.device_id != sync_request.device_id  # Exclude changes from this device
        ).all()

        for prop in server_properties:
            operation = SyncOperation.DELETE if prop.is_deleted else SyncOperation.UPDATE
            server_changes.append(create_property_change(
                prop.id,
                operation,
                prop.to_dict() if not prop.is_deleted else None,
                prop.device_id or "server"
            ))

        # Update sync log
        sync_log.status = "success" if not conflicts else "conflict"
        sync_log.records_processed = len(sync_request.changes)
        sync_log.conflicts_detected = len(conflicts)
        sync_log.completed_at = datetime.utcnow()
        sync_log.duration_seconds = (sync_log.completed_at - sync_log.started_at).total_seconds()

        new_sync_timestamp = datetime.utcnow()

        db.commit()

        logger.info(f"Delta sync completed for device {sync_request.device_id}: "
                   f"{changes_applied} applied, {changes_rejected} rejected, {len(conflicts)} conflicts")

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

    except HTTPException:
        if sync_log:
            sync_log.status = "failed"
            sync_log.completed_at = datetime.utcnow()
            db.commit()
        raise
    except Exception as e:
        if sync_log:
            sync_log.status = "failed"
            sync_log.error_message = str(e)
            sync_log.completed_at = datetime.utcnow()
            db.commit()

        logger.error(f"Delta sync failed for device {sync_request.device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Delta sync failed")

@router.post("/full", response_model=FullSyncResponse)
@limiter.limit("5/minute")
async def full_sync(
    request: Request,
    sync_request: FullSyncRequest,
    db: Session = Depends(get_db)
):
    """
    Perform full synchronization (initial sync or after conflicts).
    Returns all active properties.
    """
    sync_log = None
    try:
        # Validate algorithm compatibility
        algorithm_compatible, compatibility_message = validate_algorithm_compatibility(
            sync_request.algorithm_version,
            sync_request.app_version
        )

        # Create sync log entry
        sync_log = SyncLog(
            device_id=sync_request.device_id,
            operation="full",
            status="pending",
            algorithm_validation_passed=algorithm_compatible
        )
        db.add(sync_log)
        db.flush()

        if not algorithm_compatible:
            sync_log.status = "failed"
            sync_log.error_message = compatibility_message
            sync_log.completed_at = datetime.utcnow()
            db.commit()

            raise HTTPException(
                status_code=400,
                detail=f"Algorithm compatibility error: {compatibility_message}"
            )

        # Get all active properties
        active_properties = db.query(Property).filter(Property.is_deleted == False).all()
        all_properties = [prop.to_dict() for prop in active_properties]

        # Get deleted property IDs if requested
        deleted_properties = []
        if sync_request.include_deleted:
            deleted_props = db.query(Property.id).filter(Property.is_deleted == True).all()
            deleted_properties = [prop.id for prop in deleted_props]

        # Update sync log
        sync_log.status = "success"
        sync_log.records_processed = len(all_properties)
        sync_log.completed_at = datetime.utcnow()
        sync_log.duration_seconds = (sync_log.completed_at - sync_log.started_at).total_seconds()

        sync_timestamp = datetime.utcnow()

        db.commit()

        logger.info(f"Full sync completed for device {sync_request.device_id}: {len(all_properties)} properties")

        return FullSyncResponse(
            all_properties=all_properties,
            deleted_properties=deleted_properties,
            sync_timestamp=sync_timestamp,
            total_properties=len(all_properties),
            algorithm_compatibility=algorithm_compatible
        )

    except HTTPException:
        if sync_log:
            sync_log.status = "failed"
            sync_log.completed_at = datetime.utcnow()
            db.commit()
        raise
    except Exception as e:
        if sync_log:
            sync_log.status = "failed"
            sync_log.error_message = str(e)
            sync_log.completed_at = datetime.utcnow()
            db.commit()

        logger.error(f"Full sync failed for device {sync_request.device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Full sync failed")

@router.get("/status", response_model=SyncStatusResponse)
@limiter.limit("100/minute")
async def get_sync_status(
    request: Request,
    device_id: str,
    db: Session = Depends(get_db)
):
    """Get synchronization status for a device."""
    try:
        # Get last successful sync
        last_sync = db.query(SyncLog).filter(
            SyncLog.device_id == device_id,
            SyncLog.status == "success"
        ).order_by(SyncLog.completed_at.desc()).first()

        last_sync_timestamp = last_sync.completed_at if last_sync else None

        # Count pending changes on server (changes from other devices)
        if last_sync_timestamp:
            pending_changes = db.query(Property).filter(
                Property.updated_at > last_sync_timestamp,
                Property.device_id != device_id
            ).count()
        else:
            pending_changes = db.query(Property).filter(Property.is_deleted == False).count()

        # Check for unresolved conflicts
        sync_conflicts = db.query(SyncLog).filter(
            SyncLog.device_id == device_id,
            SyncLog.status == "conflict",
            SyncLog.conflicts_resolved == 0
        ).count()

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

    except Exception as e:
        logger.error(f"Failed to get sync status for device {device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get sync status")

@router.post("/resolve-conflicts", response_model=ConflictResolutionResponse)
@limiter.limit("10/minute")
async def resolve_conflicts(
    request: Request,
    resolution_request: ConflictResolutionRequest,
    db: Session = Depends(get_db),
    property_service: PropertyService = Depends(get_property_service)
):
    """Resolve synchronization conflicts using user decisions."""
    try:
        resolved_conflicts = 0
        remaining_conflicts = 0
        errors = []

        for conflict in resolution_request.resolutions:
            try:
                if conflict.resolution == ConflictResolution.USE_LOCAL:
                    # Apply local data
                    from ..models.property import PropertyUpdate
                    update_data = {k: v for k, v in conflict.local_data.items() if k != 'id'}
                    property_update = PropertyUpdate(**update_data)
                    property_service.update_property(conflict.property_id, property_update, resolution_request.device_id)
                    resolved_conflicts += 1

                elif conflict.resolution == ConflictResolution.USE_REMOTE:
                    # Keep remote data (no action needed)
                    resolved_conflicts += 1

                elif conflict.resolution == ConflictResolution.MERGE:
                    # Implement merge logic (custom implementation needed)
                    # For now, default to last-write-wins
                    if conflict.local_timestamp > conflict.remote_timestamp:
                        from ..models.property import PropertyUpdate
                        update_data = {k: v for k, v in conflict.local_data.items() if k != 'id'}
                        property_update = PropertyUpdate(**update_data)
                        property_service.update_property(conflict.property_id, property_update, resolution_request.device_id)
                    resolved_conflicts += 1

                else:
                    # ASK_USER - should not reach here in automated resolution
                    remaining_conflicts += 1

            except Exception as e:
                errors.append(f"Failed to resolve conflict for property {conflict.property_id}: {str(e)}")
                remaining_conflicts += 1

        # Update sync log for conflict resolution
        sync_log = SyncLog(
            device_id=resolution_request.device_id,
            operation="resolve_conflicts",
            status="success" if not errors else "partial",
            records_processed=len(resolution_request.resolutions),
            conflicts_resolved=resolved_conflicts,
            completed_at=datetime.utcnow()
        )
        db.add(sync_log)
        db.commit()

        return ConflictResolutionResponse(
            resolved_conflicts=resolved_conflicts,
            remaining_conflicts=remaining_conflicts,
            status=SyncStatus.SUCCESS if not errors else SyncStatus.PARTIAL,
            errors=errors
        )

    except Exception as e:
        logger.error(f"Conflict resolution failed for device {resolution_request.device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Conflict resolution failed")

@router.post("/batch", response_model=BatchSyncResponse)
@limiter.limit("10/minute")
async def batch_sync(
    request: Request,
    batch_request: BatchSyncRequest,
    db: Session = Depends(get_db)
):
    """
    Batch synchronization for large datasets.
    Returns data in manageable chunks.
    """
    try:
        # Build query for active properties
        query = db.query(Property).filter(Property.is_deleted == False)

        # Apply starting point if provided
        if batch_request.start_from:
            query = query.filter(Property.id > batch_request.start_from)

        # Order by ID for consistent pagination
        query = query.order_by(Property.id)

        # Get batch + 1 to check if more data exists
        properties = query.limit(batch_request.batch_size + 1).all()

        # Determine if more data is available
        has_more_data = len(properties) > batch_request.batch_size
        if has_more_data:
            properties = properties[:-1]  # Remove the extra item

        # Convert to dictionaries
        batch_data = []
        for prop in properties:
            prop_dict = prop.to_dict()

            # Include algorithm calculations if requested
            if batch_request.include_calculations and not prop_dict.get('investment_score'):
                # Recalculate if missing
                from ..services.property_service import PropertyService
                service = PropertyService(db)
                calculated = service.calculate_property_metrics(prop_dict)
                prop_dict.update(calculated)

            batch_data.append(prop_dict)

        # Determine next batch start
        next_batch_start = properties[-1].id if properties else None

        # Estimate remaining records (rough approximation)
        total_remaining = None
        if has_more_data:
            remaining_query = db.query(Property).filter(
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

    except Exception as e:
        logger.error(f"Batch sync failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Batch sync failed")

@router.get("/logs", response_model=SyncLogListResponse)
@limiter.limit("20/minute")
async def get_sync_logs(
    request: Request,
    device_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db)
):
    """Get synchronization logs for monitoring and debugging."""
    try:
        # Build query
        query = db.query(SyncLog)

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

    except Exception as e:
        logger.error(f"Failed to get sync logs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get sync logs")

@router.get("/metrics/{device_id}", response_model=SyncMetrics)
@limiter.limit("20/minute")
async def get_sync_metrics(
    request: Request,
    device_id: str,
    db: Session = Depends(get_db)
):
    """Get synchronization metrics for a specific device."""
    try:
        # Get recent sync operations for this device
        recent_syncs = db.query(SyncLog).filter(
            SyncLog.device_id == device_id,
            SyncLog.started_at > datetime.utcnow() - timedelta(days=7)  # Last 7 days
        ).order_by(SyncLog.started_at.desc()).all()

        if not recent_syncs:
            raise HTTPException(status_code=404, detail="No recent sync metrics found")

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sync metrics for device {device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get sync metrics")