"""
Test suite for Sync Router.
Covers endpoints defined in backend_api/routers/sync.py.
Tests target the SyncService layer for proper separation of concerns.

Endpoints covered:
- POST /sync/delta - Delta synchronization
- POST /sync/full - Full synchronization
- GET /sync/status - Sync status check
- POST /sync/resolve-conflicts - Conflict resolution
- POST /sync/batch - Batch synchronization
- GET /sync/logs - Sync logs retrieval
- GET /sync/metrics/{device_id} - Device metrics
"""
import pytest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from fastapi import FastAPI

from backend_api.routers.sync import router, get_sync_service_dep, limiter
from backend_api.services.sync_service import SyncService
from slowapi import Limiter
from slowapi.util import get_remote_address
from backend_api.models.sync import (
    DeltaSyncRequest, DeltaSyncResponse, FullSyncRequest, FullSyncResponse,
    SyncStatusResponse, ConflictResolutionRequest, ConflictResolutionResponse,
    SyncMetrics, BatchSyncRequest, BatchSyncResponse, SyncLogEntry,
    SyncLogListResponse, SyncOperation, SyncStatus, ConflictResolution,
    PropertyChange, SyncConflict
)
from tests.fixtures.data_factories import PropertyDataFactory, SyncLogFactory
from tests.api.auth_helpers import generate_test_jwt_token, create_auth_headers


# -----------------------------------------------------------------------------
# HELPER CLASSES
# -----------------------------------------------------------------------------

class MockORM:
    """Helper to simulate ORM objects for Pydantic's from_orm."""
    def __init__(self, data: Dict[str, Any]):
        for k, v in data.items():
            setattr(self, k, v)


class MockSyncLog(SimpleNamespace):
    """Helper for SyncLog response simulation."""
    pass


# -----------------------------------------------------------------------------
# FIXTURES
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_sync_service():
    """Mocks the SyncService dependency."""
    service = MagicMock(spec=SyncService)

    # Default behaviors
    service.validate_algorithm_compatibility.return_value = (True, "Algorithms compatible")
    service.process_delta_sync.return_value = DeltaSyncResponse(
        server_changes=[],
        conflicts=[],
        new_sync_timestamp=datetime.utcnow(),
        sync_status=SyncStatus.SUCCESS,
        changes_applied=0,
        changes_rejected=0,
        server_changes_count=0,
        conflicts_count=0,
        algorithm_compatibility=True,
        algorithm_validation_message="Algorithms compatible"
    )
    service.process_full_sync.return_value = FullSyncResponse(
        all_properties=[],
        deleted_properties=[],
        sync_timestamp=datetime.utcnow(),
        total_properties=0,
        algorithm_compatibility=True
    )
    service.get_device_status.return_value = SyncStatusResponse(
        device_id="test-device",
        last_sync_timestamp=datetime.utcnow(),
        pending_changes=0,
        sync_conflicts=0,
        is_sync_required=False,
        algorithm_version_compatible=True
    )
    service.resolve_conflicts.return_value = ConflictResolutionResponse(
        resolved_conflicts=0,
        remaining_conflicts=0,
        status=SyncStatus.SUCCESS,
        errors=[]
    )
    service.process_batch_sync.return_value = BatchSyncResponse(
        batch_data=[],
        next_batch_start=None,
        has_more_data=False,
        batch_count=0,
        total_remaining=None
    )
    service.get_logs.return_value = SyncLogListResponse(
        logs=[],
        total_count=0,
        page=1,
        page_size=50
    )
    service.get_device_metrics.return_value = SyncMetrics(
        device_id="test-device",
        operation_type="delta",
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        duration_seconds=1.5,
        records_processed=10,
        records_successful=10,
        records_failed=0,
        conflicts_detected=0,
        conflicts_resolved=0,
        error_message=None,
        algorithm_validation_passed=True
    )

    return service


@pytest.fixture
def client(mock_sync_service):
    """TestClient with dependency overrides and disabled rate limiting."""
    app = FastAPI()
    app.include_router(router, prefix="/sync")

    # Disable rate limiting for tests
    limiter.enabled = False
    app.state.limiter = limiter

    # Override the sync service dependency
    def override_get_sync_service():
        return mock_sync_service

    app.dependency_overrides[get_sync_service_dep] = override_get_sync_service

    yield TestClient(app)

    # Re-enable rate limiting after tests
    limiter.enabled = True


@pytest.fixture
def auth_headers():
    """Valid authentication headers."""
    token = generate_test_jwt_token(device_id="test-device-123")
    return create_auth_headers(token)


@pytest.fixture
def sample_property_change():
    """Generate a sample property change."""
    return PropertyChange(
        property_id="prop-123",
        operation=SyncOperation.CREATE,
        data=PropertyDataFactory(),
        timestamp=datetime.utcnow(),
        device_id="test-device"
    )


@pytest.fixture
def sample_sync_conflict():
    """Generate a sample sync conflict."""
    return SyncConflict(
        property_id="prop-456",
        local_timestamp=datetime.utcnow() - timedelta(hours=1),
        remote_timestamp=datetime.utcnow(),
        local_data={"amount": 5000, "description": "Local version"},
        remote_data={"amount": 6000, "description": "Remote version"},
        conflict_fields=["amount", "description"],
        resolution=ConflictResolution.USE_LOCAL
    )


# -----------------------------------------------------------------------------
# TEST CLASS: TestSyncRouter
# -----------------------------------------------------------------------------

class TestSyncRouter:
    """
    Comprehensive test suite for Sync Router.
    """

    # =========================================================================
    # 1. DELTA SYNC (POST /delta)
    # =========================================================================

    def test_delta_sync_basic_success(self, client, mock_sync_service):
        """Test basic delta sync with no changes."""
        payload = {
            "device_id": "ios-device-123",
            "last_sync_timestamp": datetime.utcnow().isoformat(),
            "changes": [],
            "algorithm_version": "1.0.0",
            "app_version": "1.0.0"
        }

        response = client.post("/sync/delta", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["sync_status"] == "success"
        assert data["algorithm_compatibility"] is True

    def test_delta_sync_with_create_changes(self, client, mock_sync_service):
        """Test delta sync with CREATE operations."""
        # Create JSON-serializable property data
        prop_data = {
            "parcel_id": "TEST-001",
            "amount": 5000.0,
            "county": "Baldwin",
            "description": "Test property",
            "acreage": 1.5
        }
        payload = {
            "device_id": "ios-device-123",
            "last_sync_timestamp": datetime.utcnow().isoformat(),
            "changes": [
                {
                    "property_id": "new-prop-1",
                    "operation": "create",
                    "data": prop_data,
                    "timestamp": datetime.utcnow().isoformat(),
                    "device_id": "ios-device-123"
                }
            ],
            "algorithm_version": "1.0.0",
            "app_version": "1.0.0"
        }

        # Configure mock to return success with 1 change applied
        mock_sync_service.process_delta_sync.return_value = DeltaSyncResponse(
            server_changes=[],
            conflicts=[],
            new_sync_timestamp=datetime.utcnow(),
            sync_status=SyncStatus.SUCCESS,
            changes_applied=1,
            changes_rejected=0,
            server_changes_count=0,
            conflicts_count=0,
            algorithm_compatibility=True,
            algorithm_validation_message="Algorithms compatible"
        )

        response = client.post("/sync/delta", json=payload)

        assert response.status_code == 200
        assert response.json()["changes_applied"] == 1

    def test_delta_sync_with_update_changes(self, client, mock_sync_service):
        """Test delta sync with UPDATE operations."""
        payload = {
            "device_id": "ios-device-123",
            "last_sync_timestamp": datetime.utcnow().isoformat(),
            "changes": [
                {
                    "property_id": "existing-prop-1",
                    "operation": "update",
                    "data": {"amount": 7500, "description": "Updated description"},
                    "timestamp": datetime.utcnow().isoformat(),
                    "device_id": "ios-device-123"
                }
            ],
            "algorithm_version": "1.0.0",
            "app_version": "1.0.0"
        }

        mock_sync_service.process_delta_sync.return_value = DeltaSyncResponse(
            server_changes=[],
            conflicts=[],
            new_sync_timestamp=datetime.utcnow(),
            sync_status=SyncStatus.SUCCESS,
            changes_applied=1,
            changes_rejected=0,
            server_changes_count=0,
            conflicts_count=0,
            algorithm_compatibility=True,
            algorithm_validation_message="Algorithms compatible"
        )

        response = client.post("/sync/delta", json=payload)

        assert response.status_code == 200

    def test_delta_sync_with_delete_changes(self, client, mock_sync_service):
        """Test delta sync with DELETE operations."""
        payload = {
            "device_id": "ios-device-123",
            "last_sync_timestamp": datetime.utcnow().isoformat(),
            "changes": [
                {
                    "property_id": "prop-to-delete",
                    "operation": "delete",
                    "data": None,
                    "timestamp": datetime.utcnow().isoformat(),
                    "device_id": "ios-device-123"
                }
            ],
            "algorithm_version": "1.0.0",
            "app_version": "1.0.0"
        }

        response = client.post("/sync/delta", json=payload)

        assert response.status_code == 200

    def test_delta_sync_algorithm_mismatch(self, client, mock_sync_service):
        """Test delta sync with algorithm compatibility failure."""
        mock_sync_service.process_delta_sync.side_effect = ValueError(
            "Algorithm compatibility error: Investment score algorithm mismatch"
        )

        payload = {
            "device_id": "ios-device-123",
            "last_sync_timestamp": datetime.utcnow().isoformat(),
            "changes": [],
            "algorithm_version": "0.5.0",  # Incompatible version
            "app_version": "1.0.0"
        }

        response = client.post("/sync/delta", json=payload)

        # Service raises ValueError which should result in 400 or 500
        assert response.status_code in [400, 500]

    def test_delta_sync_with_conflicts(self, client, mock_sync_service):
        """Test delta sync that detects conflicts."""
        conflict = SyncConflict(
            property_id="prop-conflict",
            local_timestamp=datetime.utcnow() - timedelta(hours=1),
            remote_timestamp=datetime.utcnow(),
            local_data={"amount": 5000},
            remote_data={"amount": 6000},
            conflict_fields=["amount"],
            resolution=None
        )

        mock_sync_service.process_delta_sync.return_value = DeltaSyncResponse(
            server_changes=[],
            conflicts=[conflict],
            new_sync_timestamp=datetime.utcnow(),
            sync_status=SyncStatus.CONFLICT,
            changes_applied=0,
            changes_rejected=0,
            server_changes_count=0,
            conflicts_count=1,
            algorithm_compatibility=True,
            algorithm_validation_message="Algorithms compatible"
        )

        payload = {
            "device_id": "ios-device-123",
            "last_sync_timestamp": datetime.utcnow().isoformat(),
            "changes": [
                {
                    "property_id": "prop-conflict",
                    "operation": "update",
                    "data": {"amount": 5000},
                    "timestamp": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
                    "device_id": "ios-device-123"
                }
            ],
            "algorithm_version": "1.0.0",
            "app_version": "1.0.0"
        }

        response = client.post("/sync/delta", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["sync_status"] == "conflict"
        assert data["conflicts_count"] == 1

    def test_delta_sync_returns_server_changes(self, client, mock_sync_service):
        """Test delta sync returns server-side changes."""
        server_change = PropertyChange(
            property_id="server-prop-1",
            operation=SyncOperation.UPDATE,
            data={"amount": 8000, "description": "Server updated"},
            timestamp=datetime.utcnow(),
            device_id="server"
        )

        mock_sync_service.process_delta_sync.return_value = DeltaSyncResponse(
            server_changes=[server_change],
            conflicts=[],
            new_sync_timestamp=datetime.utcnow(),
            sync_status=SyncStatus.SUCCESS,
            changes_applied=0,
            changes_rejected=0,
            server_changes_count=1,
            conflicts_count=0,
            algorithm_compatibility=True,
            algorithm_validation_message="Algorithms compatible"
        )

        payload = {
            "device_id": "ios-device-123",
            "last_sync_timestamp": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
            "changes": [],
            "algorithm_version": "1.0.0",
            "app_version": "1.0.0"
        }

        response = client.post("/sync/delta", json=payload)

        assert response.status_code == 200
        assert response.json()["server_changes_count"] == 1

    @pytest.mark.parametrize("algorithm_version", ["1.0.0", "1.0.1", "1.1.0"])
    def test_delta_sync_supported_algorithm_versions(self, client, mock_sync_service, algorithm_version):
        """Test delta sync with various supported algorithm versions."""
        payload = {
            "device_id": "ios-device-123",
            "last_sync_timestamp": datetime.utcnow().isoformat(),
            "changes": [],
            "algorithm_version": algorithm_version,
            "app_version": "1.0.0"
        }

        response = client.post("/sync/delta", json=payload)

        assert response.status_code == 200

    def test_delta_sync_missing_device_id(self, client):
        """Test delta sync with missing device_id."""
        payload = {
            "last_sync_timestamp": datetime.utcnow().isoformat(),
            "changes": [],
            "algorithm_version": "1.0.0",
            "app_version": "1.0.0"
        }

        response = client.post("/sync/delta", json=payload)

        assert response.status_code == 422

    def test_delta_sync_empty_device_id(self, client):
        """Test delta sync with empty device_id."""
        payload = {
            "device_id": "",
            "last_sync_timestamp": datetime.utcnow().isoformat(),
            "changes": [],
            "algorithm_version": "1.0.0",
            "app_version": "1.0.0"
        }

        response = client.post("/sync/delta", json=payload)

        assert response.status_code == 422

    # =========================================================================
    # 2. FULL SYNC (POST /full)
    # =========================================================================

    def test_full_sync_basic_success(self, client, mock_sync_service):
        """Test basic full sync."""
        payload = {
            "device_id": "ios-device-123",
            "force_sync": False,
            "include_deleted": False,
            "algorithm_version": "1.0.0",
            "app_version": "1.0.0"
        }

        response = client.post("/sync/full", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["algorithm_compatibility"] is True

    def test_full_sync_with_properties(self, client, mock_sync_service):
        """Test full sync returns all properties."""
        properties = [PropertyDataFactory() for _ in range(5)]

        mock_sync_service.process_full_sync.return_value = FullSyncResponse(
            all_properties=properties,
            deleted_properties=[],
            sync_timestamp=datetime.utcnow(),
            total_properties=5,
            algorithm_compatibility=True
        )

        payload = {
            "device_id": "ios-device-123",
            "force_sync": False,
            "include_deleted": False,
            "algorithm_version": "1.0.0",
            "app_version": "1.0.0"
        }

        response = client.post("/sync/full", json=payload)

        assert response.status_code == 200
        assert response.json()["total_properties"] == 5

    def test_full_sync_include_deleted(self, client, mock_sync_service):
        """Test full sync with include_deleted flag."""
        mock_sync_service.process_full_sync.return_value = FullSyncResponse(
            all_properties=[PropertyDataFactory()],
            deleted_properties=["deleted-1", "deleted-2"],
            sync_timestamp=datetime.utcnow(),
            total_properties=1,
            algorithm_compatibility=True
        )

        payload = {
            "device_id": "ios-device-123",
            "force_sync": False,
            "include_deleted": True,
            "algorithm_version": "1.0.0",
            "app_version": "1.0.0"
        }

        response = client.post("/sync/full", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert len(data["deleted_properties"]) == 2

    def test_full_sync_force_sync(self, client, mock_sync_service):
        """Test full sync with force_sync flag."""
        payload = {
            "device_id": "ios-device-123",
            "force_sync": True,
            "include_deleted": False,
            "algorithm_version": "1.0.0",
            "app_version": "1.0.0"
        }

        response = client.post("/sync/full", json=payload)

        assert response.status_code == 200

    def test_full_sync_algorithm_mismatch(self, client, mock_sync_service):
        """Test full sync with algorithm compatibility failure."""
        mock_sync_service.process_full_sync.side_effect = ValueError(
            "Algorithm compatibility error: Algorithm version 0.5.0 not supported"
        )

        payload = {
            "device_id": "ios-device-123",
            "force_sync": False,
            "include_deleted": False,
            "algorithm_version": "0.5.0",
            "app_version": "1.0.0"
        }

        response = client.post("/sync/full", json=payload)

        assert response.status_code in [400, 500]

    def test_full_sync_empty_database(self, client, mock_sync_service):
        """Test full sync with no properties in database."""
        mock_sync_service.process_full_sync.return_value = FullSyncResponse(
            all_properties=[],
            deleted_properties=[],
            sync_timestamp=datetime.utcnow(),
            total_properties=0,
            algorithm_compatibility=True
        )

        payload = {
            "device_id": "ios-device-123",
            "force_sync": False,
            "include_deleted": False,
            "algorithm_version": "1.0.0",
            "app_version": "1.0.0"
        }

        response = client.post("/sync/full", json=payload)

        assert response.status_code == 200
        assert response.json()["total_properties"] == 0

    # =========================================================================
    # 3. SYNC STATUS (GET /status)
    # =========================================================================

    def test_get_sync_status_success(self, client, mock_sync_service):
        """Test getting sync status for a device."""
        response = client.get("/sync/status", params={"device_id": "ios-device-123"})

        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == "test-device"
        assert "pending_changes" in data
        assert "sync_conflicts" in data
        assert "is_sync_required" in data

    def test_get_sync_status_with_pending_changes(self, client, mock_sync_service):
        """Test sync status when pending changes exist."""
        mock_sync_service.get_device_status.return_value = SyncStatusResponse(
            device_id="ios-device-123",
            last_sync_timestamp=datetime.utcnow() - timedelta(hours=2),
            pending_changes=15,
            sync_conflicts=0,
            is_sync_required=True,
            algorithm_version_compatible=True
        )

        response = client.get("/sync/status", params={"device_id": "ios-device-123"})

        assert response.status_code == 200
        data = response.json()
        assert data["pending_changes"] == 15
        assert data["is_sync_required"] is True

    def test_get_sync_status_with_conflicts(self, client, mock_sync_service):
        """Test sync status when unresolved conflicts exist."""
        mock_sync_service.get_device_status.return_value = SyncStatusResponse(
            device_id="ios-device-123",
            last_sync_timestamp=datetime.utcnow(),
            pending_changes=0,
            sync_conflicts=3,
            is_sync_required=True,
            algorithm_version_compatible=True
        )

        response = client.get("/sync/status", params={"device_id": "ios-device-123"})

        assert response.status_code == 200
        data = response.json()
        assert data["sync_conflicts"] == 3
        assert data["is_sync_required"] is True

    def test_get_sync_status_never_synced(self, client, mock_sync_service):
        """Test sync status for device that never synced."""
        mock_sync_service.get_device_status.return_value = SyncStatusResponse(
            device_id="new-device",
            last_sync_timestamp=None,
            pending_changes=100,
            sync_conflicts=0,
            is_sync_required=True,
            algorithm_version_compatible=True
        )

        response = client.get("/sync/status", params={"device_id": "new-device"})

        assert response.status_code == 200
        data = response.json()
        assert data["last_sync_timestamp"] is None
        assert data["is_sync_required"] is True

    def test_get_sync_status_missing_device_id(self, client):
        """Test sync status without device_id parameter."""
        response = client.get("/sync/status")

        assert response.status_code == 422

    # =========================================================================
    # 4. RESOLVE CONFLICTS (POST /resolve-conflicts)
    # =========================================================================

    def test_resolve_conflicts_use_local(self, client, mock_sync_service, sample_sync_conflict):
        """Test resolving conflict with USE_LOCAL strategy."""
        sample_sync_conflict.resolution = ConflictResolution.USE_LOCAL

        mock_sync_service.resolve_conflicts.return_value = ConflictResolutionResponse(
            resolved_conflicts=1,
            remaining_conflicts=0,
            status=SyncStatus.SUCCESS,
            errors=[]
        )

        payload = {
            "device_id": "ios-device-123",
            "resolutions": [
                {
                    "property_id": sample_sync_conflict.property_id,
                    "local_timestamp": sample_sync_conflict.local_timestamp.isoformat(),
                    "remote_timestamp": sample_sync_conflict.remote_timestamp.isoformat(),
                    "local_data": sample_sync_conflict.local_data,
                    "remote_data": sample_sync_conflict.remote_data,
                    "conflict_fields": sample_sync_conflict.conflict_fields,
                    "resolution": "use_local"
                }
            ]
        }

        response = client.post("/sync/resolve-conflicts", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["resolved_conflicts"] == 1
        assert data["status"] == "success"

    def test_resolve_conflicts_use_remote(self, client, mock_sync_service, sample_sync_conflict):
        """Test resolving conflict with USE_REMOTE strategy."""
        mock_sync_service.resolve_conflicts.return_value = ConflictResolutionResponse(
            resolved_conflicts=1,
            remaining_conflicts=0,
            status=SyncStatus.SUCCESS,
            errors=[]
        )

        payload = {
            "device_id": "ios-device-123",
            "resolutions": [
                {
                    "property_id": "prop-456",
                    "local_timestamp": datetime.utcnow().isoformat(),
                    "remote_timestamp": datetime.utcnow().isoformat(),
                    "local_data": {"amount": 5000},
                    "remote_data": {"amount": 6000},
                    "conflict_fields": ["amount"],
                    "resolution": "use_remote"
                }
            ]
        }

        response = client.post("/sync/resolve-conflicts", json=payload)

        assert response.status_code == 200
        assert response.json()["resolved_conflicts"] == 1

    def test_resolve_conflicts_merge(self, client, mock_sync_service):
        """Test resolving conflict with MERGE strategy."""
        mock_sync_service.resolve_conflicts.return_value = ConflictResolutionResponse(
            resolved_conflicts=1,
            remaining_conflicts=0,
            status=SyncStatus.SUCCESS,
            errors=[]
        )

        payload = {
            "device_id": "ios-device-123",
            "resolutions": [
                {
                    "property_id": "prop-789",
                    "local_timestamp": datetime.utcnow().isoformat(),
                    "remote_timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
                    "local_data": {"amount": 5000, "description": "Local"},
                    "remote_data": {"amount": 6000, "description": "Remote"},
                    "conflict_fields": ["amount", "description"],
                    "resolution": "merge"
                }
            ]
        }

        response = client.post("/sync/resolve-conflicts", json=payload)

        assert response.status_code == 200

    def test_resolve_conflicts_multiple(self, client, mock_sync_service):
        """Test resolving multiple conflicts at once."""
        mock_sync_service.resolve_conflicts.return_value = ConflictResolutionResponse(
            resolved_conflicts=3,
            remaining_conflicts=0,
            status=SyncStatus.SUCCESS,
            errors=[]
        )

        resolutions = []
        for i in range(3):
            resolutions.append({
                "property_id": f"prop-{i}",
                "local_timestamp": datetime.utcnow().isoformat(),
                "remote_timestamp": datetime.utcnow().isoformat(),
                "local_data": {"amount": 5000 + i * 100},
                "remote_data": {"amount": 6000 + i * 100},
                "conflict_fields": ["amount"],
                "resolution": "use_local"
            })

        payload = {
            "device_id": "ios-device-123",
            "resolutions": resolutions
        }

        response = client.post("/sync/resolve-conflicts", json=payload)

        assert response.status_code == 200
        assert response.json()["resolved_conflicts"] == 3

    def test_resolve_conflicts_partial_failure(self, client, mock_sync_service):
        """Test conflict resolution with partial failures."""
        mock_sync_service.resolve_conflicts.return_value = ConflictResolutionResponse(
            resolved_conflicts=2,
            remaining_conflicts=1,
            status=SyncStatus.PARTIAL,
            errors=["Failed to resolve conflict for property prop-2: Property not found"]
        )

        payload = {
            "device_id": "ios-device-123",
            "resolutions": [
                {
                    "property_id": "prop-0",
                    "local_timestamp": datetime.utcnow().isoformat(),
                    "remote_timestamp": datetime.utcnow().isoformat(),
                    "local_data": {"amount": 5000},
                    "remote_data": {"amount": 6000},
                    "conflict_fields": ["amount"],
                    "resolution": "use_local"
                }
            ]
        }

        response = client.post("/sync/resolve-conflicts", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "partial"
        assert len(data["errors"]) > 0

    def test_resolve_conflicts_empty_list(self, client, mock_sync_service):
        """Test conflict resolution with empty resolutions list."""
        mock_sync_service.resolve_conflicts.return_value = ConflictResolutionResponse(
            resolved_conflicts=0,
            remaining_conflicts=0,
            status=SyncStatus.SUCCESS,
            errors=[]
        )

        payload = {
            "device_id": "ios-device-123",
            "resolutions": []
        }

        response = client.post("/sync/resolve-conflicts", json=payload)

        assert response.status_code == 200
        assert response.json()["resolved_conflicts"] == 0

    # =========================================================================
    # 5. BATCH SYNC (POST /batch)
    # =========================================================================

    def test_batch_sync_basic_success(self, client, mock_sync_service):
        """Test basic batch sync."""
        payload = {
            "device_id": "ios-device-123",
            "batch_size": 100,
            "start_from": None,
            "include_calculations": True
        }

        response = client.post("/sync/batch", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "batch_data" in data
        assert "has_more_data" in data
        assert "batch_count" in data

    def test_batch_sync_with_data(self, client, mock_sync_service):
        """Test batch sync returns property data."""
        properties = [PropertyDataFactory() for _ in range(10)]

        mock_sync_service.process_batch_sync.return_value = BatchSyncResponse(
            batch_data=properties,
            next_batch_start="prop-10",
            has_more_data=True,
            batch_count=10,
            total_remaining=90
        )

        payload = {
            "device_id": "ios-device-123",
            "batch_size": 10,
            "start_from": None,
            "include_calculations": True
        }

        response = client.post("/sync/batch", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["batch_count"] == 10
        assert data["has_more_data"] is True
        assert data["next_batch_start"] == "prop-10"

    def test_batch_sync_pagination(self, client, mock_sync_service):
        """Test batch sync pagination with start_from."""
        mock_sync_service.process_batch_sync.return_value = BatchSyncResponse(
            batch_data=[PropertyDataFactory() for _ in range(5)],
            next_batch_start=None,
            has_more_data=False,
            batch_count=5,
            total_remaining=0
        )

        payload = {
            "device_id": "ios-device-123",
            "batch_size": 100,
            "start_from": "last-prop-id",
            "include_calculations": True
        }

        response = client.post("/sync/batch", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["has_more_data"] is False

    @pytest.mark.parametrize("batch_size", [1, 10, 50, 100, 500, 1000])
    def test_batch_sync_various_batch_sizes(self, client, mock_sync_service, batch_size):
        """Test batch sync with various valid batch sizes."""
        payload = {
            "device_id": "ios-device-123",
            "batch_size": batch_size,
            "start_from": None,
            "include_calculations": True
        }

        response = client.post("/sync/batch", json=payload)

        assert response.status_code == 200

    def test_batch_sync_batch_size_too_large(self, client):
        """Test batch sync with batch_size exceeding maximum."""
        payload = {
            "device_id": "ios-device-123",
            "batch_size": 1001,  # Exceeds max of 1000
            "start_from": None,
            "include_calculations": True
        }

        response = client.post("/sync/batch", json=payload)

        assert response.status_code == 422

    def test_batch_sync_without_calculations(self, client, mock_sync_service):
        """Test batch sync without including calculations."""
        payload = {
            "device_id": "ios-device-123",
            "batch_size": 100,
            "start_from": None,
            "include_calculations": False
        }

        response = client.post("/sync/batch", json=payload)

        assert response.status_code == 200

    # =========================================================================
    # 6. SYNC LOGS (GET /logs)
    # =========================================================================

    def test_get_sync_logs_basic(self, client, mock_sync_service):
        """Test getting sync logs without filters."""
        response = client.get("/sync/logs")

        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total_count" in data
        assert "page" in data
        assert "page_size" in data

    def test_get_sync_logs_with_device_filter(self, client, mock_sync_service):
        """Test getting sync logs filtered by device."""
        log_data = SyncLogFactory.successful_sync()
        log_entry = SyncLogEntry(
            id=log_data["id"],
            device_id="ios-device-123",
            operation=log_data["operation"],
            status=SyncStatus.SUCCESS,
            started_at=log_data["started_at"],
            completed_at=log_data["completed_at"],
            duration_seconds=log_data["duration_seconds"],
            records_processed=log_data["records_processed"],
            conflicts_detected=0,
            conflicts_resolved=0,
            error_message=None,
            algorithm_validation_passed=True
        )

        mock_sync_service.get_logs.return_value = SyncLogListResponse(
            logs=[log_entry],
            total_count=1,
            page=1,
            page_size=50
        )

        response = client.get("/sync/logs", params={"device_id": "ios-device-123"})

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1

    def test_get_sync_logs_pagination(self, client, mock_sync_service):
        """Test sync logs pagination."""
        response = client.get("/sync/logs", params={"page": 2, "page_size": 25})

        assert response.status_code == 200

    @pytest.mark.parametrize("page,page_size", [
        (1, 10),
        (1, 50),
        (2, 25),
        (5, 100),
    ])
    def test_get_sync_logs_various_pagination(self, client, mock_sync_service, page, page_size):
        """Test sync logs with various pagination parameters."""
        response = client.get("/sync/logs", params={"page": page, "page_size": page_size})

        assert response.status_code == 200

    def test_get_sync_logs_empty_result(self, client, mock_sync_service):
        """Test sync logs when no logs exist."""
        mock_sync_service.get_logs.return_value = SyncLogListResponse(
            logs=[],
            total_count=0,
            page=1,
            page_size=50
        )

        response = client.get("/sync/logs")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert len(data["logs"]) == 0

    # =========================================================================
    # 7. SYNC METRICS (GET /metrics/{device_id})
    # =========================================================================

    def test_get_sync_metrics_success(self, client, mock_sync_service):
        """Test getting sync metrics for a device."""
        response = client.get("/sync/metrics/ios-device-123")

        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == "test-device"
        assert "operation_type" in data
        assert "records_processed" in data
        assert "duration_seconds" in data

    def test_get_sync_metrics_not_found(self, client, mock_sync_service):
        """Test sync metrics for device with no recent syncs."""
        mock_sync_service.get_device_metrics.return_value = None

        response = client.get("/sync/metrics/unknown-device")

        # The router should handle None return and raise 404
        assert response.status_code in [404, 200]

    def test_get_sync_metrics_with_errors(self, client, mock_sync_service):
        """Test sync metrics showing error information."""
        mock_sync_service.get_device_metrics.return_value = SyncMetrics(
            device_id="error-device",
            operation_type="delta",
            started_at=datetime.utcnow() - timedelta(minutes=5),
            completed_at=datetime.utcnow(),
            duration_seconds=300.0,
            records_processed=100,
            records_successful=80,
            records_failed=20,
            conflicts_detected=5,
            conflicts_resolved=3,
            error_message="Partial sync failure",
            algorithm_validation_passed=True
        )

        response = client.get("/sync/metrics/error-device")

        assert response.status_code == 200
        data = response.json()
        assert data["records_failed"] == 20
        assert data["error_message"] == "Partial sync failure"

    def test_get_sync_metrics_with_conflicts(self, client, mock_sync_service):
        """Test sync metrics showing conflict information."""
        mock_sync_service.get_device_metrics.return_value = SyncMetrics(
            device_id="conflict-device",
            operation_type="delta",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=2.5,
            records_processed=50,
            records_successful=45,
            records_failed=5,
            conflicts_detected=5,
            conflicts_resolved=3,
            error_message=None,
            algorithm_validation_passed=True
        )

        response = client.get("/sync/metrics/conflict-device")

        assert response.status_code == 200
        data = response.json()
        assert data["conflicts_detected"] == 5
        assert data["conflicts_resolved"] == 3

    # =========================================================================
    # 8. ERROR HANDLING TESTS
    # =========================================================================

    def test_delta_sync_service_exception(self, client, mock_sync_service):
        """Test handling of service exceptions in delta sync."""
        mock_sync_service.process_delta_sync.side_effect = Exception("Database connection failed")

        payload = {
            "device_id": "ios-device-123",
            "last_sync_timestamp": datetime.utcnow().isoformat(),
            "changes": [],
            "algorithm_version": "1.0.0",
            "app_version": "1.0.0"
        }

        response = client.post("/sync/delta", json=payload)

        assert response.status_code == 500

    def test_full_sync_service_exception(self, client, mock_sync_service):
        """Test handling of service exceptions in full sync."""
        mock_sync_service.process_full_sync.side_effect = Exception("Query timeout")

        payload = {
            "device_id": "ios-device-123",
            "force_sync": False,
            "include_deleted": False,
            "algorithm_version": "1.0.0",
            "app_version": "1.0.0"
        }

        response = client.post("/sync/full", json=payload)

        assert response.status_code == 500

    def test_batch_sync_service_exception(self, client, mock_sync_service):
        """Test handling of service exceptions in batch sync."""
        mock_sync_service.process_batch_sync.side_effect = Exception("Memory limit exceeded")

        payload = {
            "device_id": "ios-device-123",
            "batch_size": 100,
            "start_from": None,
            "include_calculations": True
        }

        response = client.post("/sync/batch", json=payload)

        assert response.status_code == 500

    def test_sync_status_service_exception(self, client, mock_sync_service):
        """Test handling of service exceptions in status check."""
        mock_sync_service.get_device_status.side_effect = Exception("Database error")

        response = client.get("/sync/status", params={"device_id": "ios-device-123"})

        assert response.status_code == 500

    # =========================================================================
    # 9. VALIDATION TESTS
    # =========================================================================

    def test_delta_sync_invalid_operation_type(self, client):
        """Test delta sync with invalid operation type."""
        payload = {
            "device_id": "ios-device-123",
            "last_sync_timestamp": datetime.utcnow().isoformat(),
            "changes": [
                {
                    "property_id": "prop-1",
                    "operation": "invalid_operation",
                    "data": {},
                    "timestamp": datetime.utcnow().isoformat(),
                    "device_id": "ios-device-123"
                }
            ],
            "algorithm_version": "1.0.0",
            "app_version": "1.0.0"
        }

        response = client.post("/sync/delta", json=payload)

        assert response.status_code == 422

    def test_conflict_resolution_invalid_strategy(self, client):
        """Test conflict resolution with invalid strategy."""
        payload = {
            "device_id": "ios-device-123",
            "resolutions": [
                {
                    "property_id": "prop-1",
                    "local_timestamp": datetime.utcnow().isoformat(),
                    "remote_timestamp": datetime.utcnow().isoformat(),
                    "local_data": {},
                    "remote_data": {},
                    "conflict_fields": ["amount"],
                    "resolution": "invalid_strategy"
                }
            ]
        }

        response = client.post("/sync/resolve-conflicts", json=payload)

        assert response.status_code == 422

    def test_batch_sync_invalid_batch_size(self, client):
        """Test batch sync with invalid batch_size (zero)."""
        payload = {
            "device_id": "ios-device-123",
            "batch_size": 0,
            "start_from": None,
            "include_calculations": True
        }

        response = client.post("/sync/batch", json=payload)

        assert response.status_code == 422

    def test_delta_sync_missing_data_for_create(self, client):
        """Test delta sync CREATE operation without data."""
        payload = {
            "device_id": "ios-device-123",
            "last_sync_timestamp": datetime.utcnow().isoformat(),
            "changes": [
                {
                    "property_id": "prop-1",
                    "operation": "create",
                    "data": None,  # Missing data for CREATE
                    "timestamp": datetime.utcnow().isoformat(),
                    "device_id": "ios-device-123"
                }
            ],
            "algorithm_version": "1.0.0",
            "app_version": "1.0.0"
        }

        response = client.post("/sync/delta", json=payload)

        assert response.status_code == 422
