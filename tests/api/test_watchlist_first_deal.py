"""
Test suite for Watchlist First Deal endpoints.
Covers the My First Deal feature endpoints in backend_api/routers/watchlist.py (lines 430-674).

Endpoints tested:
- GET /watchlist/first-deal - Get current first deal
- POST /watchlist/property/{property_id}/set-first-deal - Set property as first deal
- PUT /watchlist/first-deal/stage - Update pipeline stage
- DELETE /watchlist/first-deal - Remove first deal assignment
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import FastAPI

from backend_api.routers.watchlist import router
from backend_api.database.connection import get_db
from backend_api.auth import get_current_user_auth
from tests.api.auth_helpers import generate_test_api_key


# -----------------------------------------------------------------------------
# MOCK CLASSES
# -----------------------------------------------------------------------------

class MockProperty:
    """Mock Property ORM object."""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 'test-property-id')
        self.parcel_id = kwargs.get('parcel_id', '123-456-789')
        self.amount = kwargs.get('amount', 5000.0)
        self.acreage = kwargs.get('acreage', 2.5)
        self.county = kwargs.get('county', 'CARROLL')
        self.state = kwargs.get('state', 'AR')
        self.is_deleted = kwargs.get('is_deleted', False)
        self.description = kwargs.get('description', 'Test property')
        self.investment_score = kwargs.get('investment_score', 45.0)
        self.water_score = kwargs.get('water_score', 2.0)
        # Add all other required fields
        for key, value in kwargs.items():
            if not hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self):
        return {
            'id': self.id,
            'parcel_id': self.parcel_id,
            'amount': self.amount,
            'acreage': self.acreage,
            'county': self.county,
            'state': self.state,
            'description': self.description,
        }


class MockPropertyInteraction:
    """Mock PropertyInteraction ORM object."""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 'test-interaction-id')
        self.device_id = kwargs.get('device_id', 'test-device-123')
        self.property_id = kwargs.get('property_id', 'test-property-id')
        self.is_watched = kwargs.get('is_watched', True)
        self.star_rating = kwargs.get('star_rating', None)
        self.user_notes = kwargs.get('user_notes', None)
        self.dismissed = kwargs.get('dismissed', False)
        self.is_first_deal = kwargs.get('is_first_deal', False)
        self.first_deal_stage = kwargs.get('first_deal_stage', None)
        self.first_deal_assigned_at = kwargs.get('first_deal_assigned_at', None)
        self.first_deal_updated_at = kwargs.get('first_deal_updated_at', None)
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())

    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'property_id': self.property_id,
            'is_watched': self.is_watched,
            'star_rating': self.star_rating,
            'user_notes': self.user_notes,
            'dismissed': self.dismissed,
            'is_first_deal': self.is_first_deal,
            'first_deal_stage': self.first_deal_stage,
            'first_deal_assigned_at': self.first_deal_assigned_at.isoformat() if self.first_deal_assigned_at else None,
            'first_deal_updated_at': self.first_deal_updated_at.isoformat() if self.first_deal_updated_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class MockQuery:
    """Mock SQLAlchemy query object."""
    def __init__(self, result=None):
        self._result = result
        self._filters = []

    def filter(self, *args):
        self._filters.extend(args)
        return self

    def join(self, *args, **kwargs):
        return self

    def first(self):
        return self._result

    def update(self, values):
        return 1  # Number of rows updated

    def all(self):
        return [self._result] if self._result else []


class MockSession:
    """Mock SQLAlchemy session."""
    def __init__(self):
        self._queries = {}
        self._added = []
        self._committed = False

    def set_query_result(self, model, result):
        """Set the result for queries on a specific model."""
        self._queries[model] = result

    def query(self, *models):
        # Return first model's result if set
        for model in models:
            if model in self._queries:
                return MockQuery(self._queries[model])
        return MockQuery(None)

    def add(self, obj):
        self._added.append(obj)

    def commit(self):
        self._committed = True

    def rollback(self):
        pass

    def refresh(self, obj):
        pass


# -----------------------------------------------------------------------------
# FIXTURES
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MockSession()


@pytest.fixture
def mock_auth():
    """Create mock auth data."""
    return {
        "type": "api_key",
        "device_id": "test-device-123",
        "app_version": "1.0.0-test",
        "scopes": ["property:read", "property:write"]
    }


@pytest.fixture
def client(mock_db, mock_auth):
    """TestClient with dependency overrides."""
    app = FastAPI()
    app.include_router(router, prefix="/watchlist")

    # Override dependencies
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user_auth] = lambda: mock_auth

    return TestClient(app)


@pytest.fixture
def api_key():
    """Generate a valid API key for testing."""
    return generate_test_api_key("test-device-123")


@pytest.fixture
def sample_property():
    """Create a sample property for testing."""
    return MockProperty(
        id="test-property-id",
        parcel_id="320-00416-000",
        amount=538.61,
        acreage=1.25,
        county="CARROLL",
        state="AR"
    )


@pytest.fixture
def sample_interaction(sample_property):
    """Create a sample interaction marked as first deal."""
    now = datetime.utcnow()
    return MockPropertyInteraction(
        id="test-interaction-id",
        device_id="test-device-123",
        property_id=sample_property.id,
        is_watched=True,
        is_first_deal=True,
        first_deal_stage="research",
        first_deal_assigned_at=now,
        first_deal_updated_at=now
    )


# -----------------------------------------------------------------------------
# TEST: GET /watchlist/first-deal
# -----------------------------------------------------------------------------

class TestGetFirstDeal:
    """Tests for GET /watchlist/first-deal endpoint."""

    def test_get_first_deal_none_set(self, client, mock_db):
        """Test getting first deal when none is set."""
        # No first deal set (default mock returns None)
        response = client.get("/watchlist/first-deal")

        assert response.status_code == 200
        data = response.json()
        assert data["has_first_deal"] is False
        assert data["property"] is None
        assert data["interaction"] is None
        assert data["stage"] is None

    def test_get_first_deal_exists(self, client, mock_db, sample_property, sample_interaction):
        """Test getting first deal when one exists."""
        # Set up mock to return the interaction and property
        from backend_api.database.models import PropertyInteraction, Property
        mock_db.set_query_result(PropertyInteraction, (sample_interaction, sample_property))

        response = client.get("/watchlist/first-deal")

        assert response.status_code == 200
        data = response.json()
        assert data["has_first_deal"] is True
        assert data["property"] is not None
        assert data["stage"] == "research"


# -----------------------------------------------------------------------------
# TEST: POST /watchlist/property/{property_id}/set-first-deal
# -----------------------------------------------------------------------------

class TestSetFirstDeal:
    """Tests for POST /watchlist/property/{property_id}/set-first-deal endpoint."""

    def test_set_first_deal_success(self, client, mock_db, sample_property):
        """Test successfully setting a property as first deal."""
        from backend_api.database.models import Property, PropertyInteraction
        mock_db.set_query_result(Property, sample_property)
        mock_db.set_query_result(PropertyInteraction, None)  # No existing interaction

        response = client.post(f"/watchlist/property/{sample_property.id}/set-first-deal")

        assert response.status_code == 200
        data = response.json()
        assert data["property_id"] == sample_property.id
        assert data["is_first_deal"] is True
        assert data["stage"] == "research"
        assert "message" in data

    def test_set_first_deal_property_not_found(self, client, mock_db):
        """Test setting first deal with invalid property ID."""
        from backend_api.database.models import Property
        mock_db.set_query_result(Property, None)  # Property not found

        response = client.post("/watchlist/property/invalid-id/set-first-deal")

        assert response.status_code == 404
        assert "Property not found" in response.json()["detail"]

    def test_set_first_deal_replaces_existing(self, client, mock_db, sample_property, sample_interaction):
        """Test that setting a new first deal replaces the existing one."""
        from backend_api.database.models import Property, PropertyInteraction

        # Create a second property
        new_property = MockProperty(
            id="new-property-id",
            parcel_id="999-888-777",
            amount=1000.0,
            acreage=5.0,
            county="BENTON",
            state="AR"
        )

        mock_db.set_query_result(Property, new_property)
        mock_db.set_query_result(PropertyInteraction, None)

        response = client.post(f"/watchlist/property/{new_property.id}/set-first-deal")

        assert response.status_code == 200
        data = response.json()
        assert data["property_id"] == new_property.id
        assert data["stage"] == "research"


# -----------------------------------------------------------------------------
# TEST: PUT /watchlist/first-deal/stage
# -----------------------------------------------------------------------------

class TestUpdateFirstDealStage:
    """Tests for PUT /watchlist/first-deal/stage endpoint."""

    @pytest.mark.parametrize("stage", [
        "research", "bid", "won", "quiet_title", "sold", "holding"
    ])
    def test_update_stage_valid(self, client, mock_db, sample_interaction, stage):
        """Test updating to each valid stage."""
        from backend_api.database.models import PropertyInteraction
        mock_db.set_query_result(PropertyInteraction, sample_interaction)

        response = client.put(
            "/watchlist/first-deal/stage",
            json={"stage": stage}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == stage
        assert "updated_at" in data

    def test_update_stage_invalid(self, client, mock_db, sample_interaction):
        """Test updating to an invalid stage."""
        from backend_api.database.models import PropertyInteraction
        mock_db.set_query_result(PropertyInteraction, sample_interaction)

        response = client.put(
            "/watchlist/first-deal/stage",
            json={"stage": "invalid_stage"}
        )

        assert response.status_code == 422  # Validation error

    def test_update_stage_no_first_deal(self, client, mock_db):
        """Test updating stage when no first deal is set."""
        from backend_api.database.models import PropertyInteraction
        mock_db.set_query_result(PropertyInteraction, None)  # No first deal

        response = client.put(
            "/watchlist/first-deal/stage",
            json={"stage": "bid"}
        )

        assert response.status_code == 404
        assert "No first deal assigned" in response.json()["detail"]


# -----------------------------------------------------------------------------
# TEST: DELETE /watchlist/first-deal
# -----------------------------------------------------------------------------

class TestRemoveFirstDeal:
    """Tests for DELETE /watchlist/first-deal endpoint."""

    def test_remove_first_deal_success(self, client, mock_db, sample_interaction):
        """Test successfully removing first deal."""
        from backend_api.database.models import PropertyInteraction
        mock_db.set_query_result(PropertyInteraction, sample_interaction)

        response = client.delete("/watchlist/first-deal")

        assert response.status_code == 200
        data = response.json()
        assert data["property_id"] == sample_interaction.property_id
        assert "message" in data

    def test_remove_first_deal_not_found(self, client, mock_db):
        """Test removing first deal when none is set."""
        from backend_api.database.models import PropertyInteraction
        mock_db.set_query_result(PropertyInteraction, None)  # No first deal

        response = client.delete("/watchlist/first-deal")

        assert response.status_code == 404
        assert "No first deal assigned" in response.json()["detail"]


# -----------------------------------------------------------------------------
# INTEGRATION TESTS
# -----------------------------------------------------------------------------

class TestFirstDealWorkflow:
    """Integration tests for the complete first deal workflow."""

    def test_full_workflow(self, client, mock_db, sample_property):
        """Test the complete workflow: set -> update stage -> remove."""
        from backend_api.database.models import Property, PropertyInteraction

        # Step 1: Set first deal
        mock_db.set_query_result(Property, sample_property)
        mock_db.set_query_result(PropertyInteraction, None)

        response = client.post(f"/watchlist/property/{sample_property.id}/set-first-deal")
        assert response.status_code == 200
        assert response.json()["stage"] == "research"

        # Step 2: Update stage to "bid"
        interaction = MockPropertyInteraction(
            property_id=sample_property.id,
            is_first_deal=True,
            first_deal_stage="research",
            first_deal_assigned_at=datetime.utcnow(),
            first_deal_updated_at=datetime.utcnow()
        )
        mock_db.set_query_result(PropertyInteraction, interaction)

        response = client.put(
            "/watchlist/first-deal/stage",
            json={"stage": "bid"}
        )
        assert response.status_code == 200
        assert response.json()["stage"] == "bid"

        # Step 3: Update stage to "won"
        response = client.put(
            "/watchlist/first-deal/stage",
            json={"stage": "won"}
        )
        assert response.status_code == 200
        assert response.json()["stage"] == "won"

        # Step 4: Remove first deal
        response = client.delete("/watchlist/first-deal")
        assert response.status_code == 200
