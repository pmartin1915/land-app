"""
Synchronization endpoints for iOS-backend communication
Implements delta sync protocol with conflict resolution (last-write-wins)

This router is a thin HTTP layer that delegates all business logic to SyncService.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
import logging

from ..database.connection import get_db
from ..services.sync_service import SyncService, get_sync_service
from ..models.sync import (
    DeltaSyncRequest, DeltaSyncResponse, FullSyncRequest, FullSyncResponse,
    SyncStatusResponse, ConflictResolutionRequest, ConflictResolutionResponse,
    SyncMetrics, BatchSyncRequest, BatchSyncResponse,
    SyncLogListResponse
)
from ..config import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


def get_sync_service_dep(db: Session = Depends(get_db)) -> SyncService:
    """Dependency to get SyncService instance."""
    return SyncService(db)

@router.post("/delta", response_model=DeltaSyncResponse)
@limiter.limit("20/minute")
async def delta_sync(
    request: Request,
    sync_request: DeltaSyncRequest,
    sync_service: SyncService = Depends(get_sync_service_dep)
):
    """
    Perform delta synchronization between iOS and backend.
    Returns only changes since last sync timestamp.
    """
    try:
        return sync_service.process_delta_sync(sync_request)
    except ValueError as e:
        # Algorithm compatibility errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Delta sync failed for device {sync_request.device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Delta sync failed")

@router.post("/full", response_model=FullSyncResponse)
@limiter.limit("5/minute")
async def full_sync(
    request: Request,
    sync_request: FullSyncRequest,
    sync_service: SyncService = Depends(get_sync_service_dep)
):
    """
    Perform full synchronization (initial sync or after conflicts).
    Returns all active properties.
    """
    try:
        return sync_service.process_full_sync(sync_request)
    except ValueError as e:
        # Algorithm compatibility errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Full sync failed for device {sync_request.device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Full sync failed")

@router.get("/status", response_model=SyncStatusResponse)
@limiter.limit("100/minute")
async def get_sync_status(
    request: Request,
    device_id: str,
    sync_service: SyncService = Depends(get_sync_service_dep)
):
    """Get synchronization status for a device."""
    try:
        return sync_service.get_device_status(device_id)
    except Exception as e:
        logger.error(f"Failed to get sync status for device {device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get sync status")

@router.post("/resolve-conflicts", response_model=ConflictResolutionResponse)
@limiter.limit("10/minute")
async def resolve_conflicts(
    request: Request,
    resolution_request: ConflictResolutionRequest,
    sync_service: SyncService = Depends(get_sync_service_dep)
):
    """Resolve synchronization conflicts using user decisions."""
    try:
        return sync_service.resolve_conflicts(resolution_request)
    except Exception as e:
        logger.error(f"Conflict resolution failed for device {resolution_request.device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Conflict resolution failed")

@router.post("/batch", response_model=BatchSyncResponse)
@limiter.limit("10/minute")
async def batch_sync(
    request: Request,
    batch_request: BatchSyncRequest,
    sync_service: SyncService = Depends(get_sync_service_dep)
):
    """
    Batch synchronization for large datasets.
    Returns data in manageable chunks.
    """
    try:
        return sync_service.process_batch_sync(batch_request)
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
    sync_service: SyncService = Depends(get_sync_service_dep)
):
    """Get synchronization logs for monitoring and debugging."""
    try:
        return sync_service.get_logs(device_id, page, page_size)
    except Exception as e:
        logger.error(f"Failed to get sync logs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get sync logs")

@router.get("/metrics/{device_id}", response_model=SyncMetrics)
@limiter.limit("20/minute")
async def get_sync_metrics(
    request: Request,
    device_id: str,
    sync_service: SyncService = Depends(get_sync_service_dep)
):
    """Get synchronization metrics for a specific device."""
    try:
        metrics = sync_service.get_device_metrics(device_id)
        if metrics is None:
            raise HTTPException(status_code=404, detail="No recent sync metrics found")
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sync metrics for device {device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get sync metrics")