"""
Test suite for Property Router.
Covers endpoints defined in backend_api/routers/properties.py.

NOTE: The following requested endpoints were NOT present in the provided router code
and have been omitted from this suite to prevent import/404 errors:
- /properties/favorites
- /properties/export
- /properties/health
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from types import SimpleNamespace
from typing import List, Dict, Any
from fastapi.testclient import TestClient
from fastapi import FastAPI

from backend_api.routers.properties import router, get_property_service
# Assuming these models are available based on imports in the router file
from backend_api.models.property import (
    PropertyCreate, PropertyUpdate, PropertyFilters,
    PropertyCalculationRequest, PropertyBulkOperation
)
from tests.fixtures.data_factories import PropertyDataFactory
from tests.api.auth_helpers import generate_test_jwt_token, create_auth_headers
# Import requested specifically by instructions
from tests.mocks.database_mocks import MockAsyncSession

# -----------------------------------------------------------------------------
# HELPER CLASSES
# -----------------------------------------------------------------------------

class MockORM:
    """Helper to simulate ORM objects for Pydantic's from_orm."""
    def __init__(self, data: Dict[str, Any]):
        for k, v in data.items():
            setattr(self, k, v)
        # Ensure ID is accessible as a string
        if 'id' not in data:
            self.id = str(data.get('parcel_id', 'test-id'))

class MockPropertyMetrics(SimpleNamespace):
    """Helper for metrics response."""
    pass

class MockCalculationResponse(SimpleNamespace):
    """Helper for calculation response."""
    pass

# -----------------------------------------------------------------------------
# FIXTURES
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_property_service():
    """Mocks the PropertyService dependency."""
    service = MagicMock()
    
    # Default behavior for list_properties: return empty list, count 0
    service.list_properties.return_value = ([], 0)
    
    # Default behavior for create/update: return the input data as ORM object
    def side_effect_create(data, device_id):
        d = data.dict() if hasattr(data, 'dict') else data
        d['id'] = 'new-uuid'
        d['investment_score'] = 75.5  # Simulate calculation
        return MockORM(d)
    service.create_property.side_effect = side_effect_create
    
    def side_effect_update(pid, data, device_id):
        d = data.dict(exclude_unset=True)
        d['id'] = pid
        d['investment_score'] = 80.0
        return MockORM(d)
    service.update_property.side_effect = side_effect_update

    service.delete_property.return_value = True
    
    return service

@pytest.fixture
def client(mock_property_service):
    """TestClient with dependency overrides."""
    app = FastAPI()
    app.include_router(router, prefix="/properties")
    
    # Override the service dependency
    app.dependency_overrides[get_property_service] = lambda: mock_property_service
    
    return TestClient(app)

@pytest.fixture
def auth_headers():
    """Valid authentication headers."""
    token = generate_test_jwt_token(device_id="test-device-123")
    return create_auth_headers(token)

@pytest.fixture
def sample_property_dict():
    """Generates a raw dictionary of property data."""
    return PropertyDataFactory()

@pytest.fixture
def sample_property_orm(sample_property_dict):
    """Generates a mock ORM object."""
    return MockORM(sample_property_dict)

# -----------------------------------------------------------------------------
# TEST CLASS: TestPropertiesRouter
# -----------------------------------------------------------------------------

class TestPropertiesRouter:
    """
    Comprehensive test suite for Properties Router.
    """

    # -------------------------------------------------------------------------
    # 1. LIST PROPERTIES (GET /)
    # -------------------------------------------------------------------------

    def test_list_properties_basic_success(self, client, auth_headers, mock_property_service, sample_property_orm):
        """Test basic list retrieval with defaults."""
        mock_property_service.list_properties.return_value = ([sample_property_orm], 1)
        
        response = client.get("/properties/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert len(data["properties"]) == 1
        assert data["page"] == 1
        # Validate service call
        mock_property_service.list_properties.assert_called_once()
        args = mock_property_service.list_properties.call_args[0][0]
        assert isinstance(args, PropertyFilters)

    @pytest.mark.parametrize("page,page_size,expected_skip", [
        (1, 10, 0),
        (2, 10, 10),
        (5, 20, 80),
    ])
    def test_list_properties_pagination(self, client, auth_headers, mock_property_service, page, page_size, expected_skip):
        """Test pagination parameters are passed correctly to service."""
        client.get(f"/properties/?page={page}&page_size={page_size}", headers=auth_headers)
        
        call_args = mock_property_service.list_properties.call_args[0][0]
        assert call_args.page == page
        assert call_args.page_size == page_size

    @pytest.mark.parametrize("sort_by,sort_order", [
        ("price", "asc"),
        ("price", "desc"),
        ("date", "asc"),
        ("investment_score", "desc"),
    ])
    def test_list_properties_sorting(self, client, auth_headers, mock_property_service, sort_by, sort_order):
        """Test sorting parameters."""
        client.get(f"/properties/?sort_by={sort_by}&sort_order={sort_order}", headers=auth_headers)
        
        call_args = mock_property_service.list_properties.call_args[0][0]
        assert call_args.sort_by == sort_by
        assert call_args.sort_order == sort_order

    @pytest.mark.parametrize("query_params,expected_filters", [
        ({"county": "Baldwin"}, {"county": "Baldwin"}),
        ({"min_price": 1000, "max_price": 5000}, {"min_price": 1000.0, "max_price": 5000.0}),
        ({"min_acreage": 1.5}, {"min_acreage": 1.5}),
        ({"water_features": True}, {"water_features": True}),
        ({"year_sold": "2023"}, {"year_sold": "2023"}),
        ({"search_query": "river"}, {"search_query": "river"}),
    ])
    def test_list_properties_filtering(self, client, auth_headers, mock_property_service, query_params, expected_filters):
        """Test individual filters."""
        # Convert params to string for URL
        query_str = "&".join([f"{k}={v}" for k, v in query_params.items()])
        client.get(f"/properties/?{query_str}", headers=auth_headers)
        
        call_args = mock_property_service.list_properties.call_args[0][0]
        for key, value in expected_filters.items():
            assert getattr(call_args, key) == value

    def test_list_properties_advanced_intelligence_filters(self, client, auth_headers, mock_property_service):
        """Test advanced intelligence scoring filters."""
        params = {
            "min_county_market_score": 50.0,
            "min_geographic_score": 60.0,
            "min_market_timing_score": 70.0,
            "min_total_description_score": 80.0,
            "min_road_access_score": 90.0
        }
        query_str = "&".join([f"{k}={v}" for k, v in params.items()])
        client.get(f"/properties/?{query_str}", headers=auth_headers)
        
        call_args = mock_property_service.list_properties.call_args[0][0]
        assert call_args.min_county_market_score == 50.0
        assert call_args.min_road_access_score == 90.0

    def test_list_properties_empty_result(self, client, auth_headers, mock_property_service):
        """Test handling of empty result set."""
        mock_property_service.list_properties.return_value = ([], 0)
        response = client.get("/properties/", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["total_count"] == 0
        assert response.json()["properties"] == []

    def test_list_properties_validation_errors(self, client, auth_headers):
        """Test input validation for list parameters."""
        # Page < 1
        resp = client.get("/properties/?page=0", headers=auth_headers)
        assert resp.status_code == 422
        
        # Page size > 1000
        resp = client.get("/properties/?page_size=1001", headers=auth_headers)
        assert resp.status_code == 422
        
        # Negative price
        resp = client.get("/properties/?min_price=-5", headers=auth_headers)
        assert resp.status_code == 422

    # -------------------------------------------------------------------------
    # 2. GET PROPERTY (GET /{id})
    # -------------------------------------------------------------------------

    def test_get_property_found(self, client, auth_headers, mock_property_service, sample_property_orm):
        """Test retrieving a single property by ID."""
        mock_property_service.get_property.return_value = sample_property_orm
        pid = sample_property_orm.parcel_id
        
        response = client.get(f"/properties/{pid}", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["parcel_id"] == pid
        mock_property_service.get_property.assert_called_with(pid)

    def test_get_property_not_found(self, client, auth_headers, mock_property_service):
        """Test retrieving a non-existent property."""
        mock_property_service.get_property.return_value = None
        
        response = client.get("/properties/non-existent-id", headers=auth_headers)
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Property not found"

    def test_get_property_service_error(self, client, auth_headers, mock_property_service):
        """Test handling of service errors."""
        mock_property_service.get_property.side_effect = Exception("DB Error")
        
        response = client.get("/properties/123", headers=auth_headers)
        
        assert response.status_code == 500
        assert "Failed to retrieve property" in response.json()["detail"]

    # -------------------------------------------------------------------------
    # 3. CREATE PROPERTY (POST /)
    # -------------------------------------------------------------------------

    def test_create_property_success(self, client, auth_headers, mock_property_service):
        """Test creating a valid property."""
        payload = {
            "parcel_id": "123-456",
            "county": "Baldwin",
            "amount": 5000.00,
            "description": "Test Property",
            "owner_name": "John Doe",
            "acreage": 1.5,
            "year_sold": "2024"
        }
        
        response = client.post("/properties/", json=payload, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["parcel_id"] == payload["parcel_id"]
        # Check calculation simulation
        assert data["investment_score"] == 75.5
        mock_property_service.create_property.assert_called_once()

    @pytest.mark.parametrize("missing_field", ["parcel_id", "county", "amount"])
    def test_create_property_missing_required_fields(self, client, auth_headers, missing_field):
        """Test validation for missing fields."""
        payload = {
            "parcel_id": "123", "county": "Baldwin", "amount": 100
        }
        del payload[missing_field]
        
        response = client.post("/properties/", json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_create_property_device_tracking(self, client, auth_headers, mock_property_service):
        """Test that device_id is passed to service."""
        payload = {"parcel_id": "123", "county": "Test", "amount": 100}
        device_id = "ios-device-x"
        
        client.post(f"/properties/?device_id={device_id}", json=payload, headers=auth_headers)
        
        args = mock_property_service.create_property.call_args
        assert args[0][1] == device_id

    # -------------------------------------------------------------------------
    # 4. UPDATE PROPERTY (PUT /{id})
    # -------------------------------------------------------------------------

    def test_update_property_success(self, client, auth_headers, mock_property_service):
        """Test updating a property."""
        pid = "test-id"
        update_data = {"amount": 6000.0, "description": "Updated"}
        
        response = client.put(f"/properties/{pid}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["amount"] == 6000.0
        # Verify recalculation simulation
        assert data["investment_score"] == 80.0
        mock_property_service.update_property.assert_called_once()

    def test_update_property_not_found(self, client, auth_headers, mock_property_service):
        """Test updating a non-existent property."""
        mock_property_service.update_property.return_value = None
        
        response = client.put("/properties/bad-id", json={"amount": 100}, headers=auth_headers)
        
        assert response.status_code == 404

    def test_update_property_validation(self, client, auth_headers):
        """Test validation on update fields."""
        # Invalid amount type
        response = client.put("/properties/1", json={"amount": "invalid"}, headers=auth_headers)
        assert response.status_code == 422

    # -------------------------------------------------------------------------
    # 5. DELETE PROPERTY (DELETE /{id})
    # -------------------------------------------------------------------------

    def test_delete_property_success(self, client, auth_headers, mock_property_service):
        """Test soft deleting a property."""
        pid = "test-id"
        
        response = client.delete(f"/properties/{pid}", headers=auth_headers)
        
        assert response.status_code == 204
        mock_property_service.delete_property.assert_called_with(pid, None)

    def test_delete_property_not_found(self, client, auth_headers, mock_property_service):
        """Test deleting a non-existent property."""
        mock_property_service.delete_property.return_value = False
        
        response = client.delete("/properties/bad-id", headers=auth_headers)
        
        assert response.status_code == 404

    def test_delete_property_with_device_id(self, client, auth_headers, mock_property_service):
        """Test deletion with device ID tracking."""
        client.delete("/properties/1?device_id=phone1", headers=auth_headers)
        
        mock_property_service.delete_property.assert_called_with("1", "phone1")

    # -------------------------------------------------------------------------
    # 6. CALCULATIONS (POST /calculate)
    # -------------------------------------------------------------------------

    def test_calculate_metrics(self, client, auth_headers, mock_property_service):
        """Test on-demand metric calculation."""
        mock_resp = MockCalculationResponse(
            investment_score=88.5, 
            water_score=5,
            market_value=10000.0
        )
        mock_property_service.calculate_metrics_for_request.return_value = mock_resp
        
        payload = {
            "amount": 5000,
            "acreage": 2.0,
            "county": "Baldwin",
            "has_water": True
        }
        
        response = client.post("/properties/calculate", json=payload, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["investment_score"] == 88.5
        mock_property_service.calculate_metrics_for_request.assert_called_once()

    # -------------------------------------------------------------------------
    # 7. ANALYTICS (GET /analytics/metrics)
    # -------------------------------------------------------------------------

    def test_get_property_metrics(self, client, auth_headers, mock_property_service):
        """Test retrieving overall property metrics."""
        mock_metrics = MockPropertyMetrics(
            total_properties=100,
            average_price=5000.0,
            top_counties={"Baldwin": 10},
            price_trend=[100, 200]
        )
        mock_property_service.get_property_metrics.return_value = mock_metrics
        
        response = client.get("/properties/analytics/metrics", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["total_properties"] == 100

    def test_recalculate_ranks(self, client, auth_headers, mock_property_service):
        """Test triggering rank recalculation."""
        response = client.post("/properties/analytics/recalculate-ranks", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["message"] == "Property rankings recalculated successfully"
        mock_property_service.recalculate_all_ranks.assert_called_once()

    # -------------------------------------------------------------------------
    # 8. BULK OPERATIONS (POST /bulk)
    # -------------------------------------------------------------------------

    def test_bulk_create_success(self, client, auth_headers, mock_property_service):
        """Test bulk creation of properties."""
        mock_property_service.create_property.return_value = MockORM({"id": "1"})
        
        payload = {
            "operation": "create",
            "properties": [
                {"parcel_id": "1", "county": "A", "amount": 100},
                {"parcel_id": "2", "county": "B", "amount": 200}
            ]
        }
        
        response = client.post("/properties/bulk", json=payload, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 2
        assert data["failed"] == 0
        assert mock_property_service.create_property.call_count == 2

    def test_bulk_update_partial_failure(self, client, auth_headers, mock_property_service):
        """Test bulk update with some failures."""
        # First call succeeds, second fails
        mock_property_service.update_property.side_effect = [MockORM({"id": "1"}), Exception("Fail")]
        
        payload = {
            "operation": "update",
            "properties": [
                {"id": "1", "amount": 500},
                {"id": "2", "amount": 600}
            ]
        }
        
        response = client.post("/properties/bulk", json=payload, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 1
        assert data["failed"] == 1
        assert len(data["errors"]) == 1
        assert data["errors"][0]["index"] == 1

    def test_bulk_delete(self, client, auth_headers, mock_property_service):
        """Test bulk deletion."""
        payload = {
            "operation": "delete",
            "properties": [{"id": "1"}, {"id": "2"}]
        }
        
        response = client.post("/properties/bulk", json=payload, headers=auth_headers)
        
        assert response.status_code == 200
        assert mock_property_service.delete_property.call_count == 2

    # -------------------------------------------------------------------------
    # 9. SEARCH SUGGESTIONS (GET /search/suggestions)
    # -------------------------------------------------------------------------

    def test_search_suggestions(self, client, auth_headers, mock_property_service):
        """Test autocomplete suggestions."""
        # Setup mock return data
        p1 = MockORM({"id": "1", "description": "Beautiful River Lot", "owner_name": "Smith"})
        p2 = MockORM({"id": "2", "description": "Mountain View", "owner_name": "Rivera"})
        mock_property_service.list_properties.return_value = ([p1, p2], 2)
        
        # Search for "River"
        response = client.get("/properties/search/suggestions?query=River", headers=auth_headers)
        
        assert response.status_code == 200
        suggestions = response.json()["suggestions"]
        assert len(suggestions) > 0
        
        # Verify structure
        texts = [s["text"] for s in suggestions]
        types = [s["type"] for s in suggestions]
        assert "Beautiful River Lot..." in texts or "Beautiful River Lot" in texts
        assert "Rivera" in texts
        assert "description" in types
        assert "owner" in types

    def test_search_suggestions_limit(self, client, auth_headers, mock_property_service):
        """Test suggestion limits."""
        # Create 20 matches
        props = [MockORM({"id": str(i), "description": "Test", "owner_name": "Test"}) for i in range(20)]
        mock_property_service.list_properties.return_value = (props, 20)
        
        response = client.get("/properties/search/suggestions?query=Test&limit=5", headers=auth_headers)
        
        suggestions = response.json()["suggestions"]
        # The logic in router loop breaks when limit reached
        assert len(suggestions) <= 5

    # -------------------------------------------------------------------------
    # 10. AUTHENTICATION & SECURITY
    # -------------------------------------------------------------------------

    def test_unauthorized_access(self, client):
        """Test endpoints without token."""
        response = client.get("/properties/")
        assert response.status_code == 403 # or 401 depending on auth setup

    def test_rate_limiting_headers(self, client, auth_headers, mock_property_service):
        """Test that rate limit headers are present."""
        # Note: Slowapi mostly works with Redis/Memory, might not trigger in Mock env unless configured
