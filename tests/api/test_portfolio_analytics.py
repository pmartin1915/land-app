"""
Test suite for Portfolio Analytics endpoints.
Covers the Portfolio Analytics feature in backend_api/routers/portfolio.py.

Endpoints tested:
- GET /portfolio/summary - Get portfolio summary
- GET /portfolio/geographic - Get geographic breakdown
- GET /portfolio/scores - Get score distribution
- GET /portfolio/risk - Get risk analysis
- GET /portfolio/performance - Get performance tracking
- GET /portfolio/export - Export complete analytics
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from fastapi import FastAPI

from backend_api.routers.portfolio import router
from backend_api.database.connection import get_db
from backend_api.auth import get_current_user_or_api_key


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
        self.buy_hold_score = kwargs.get('buy_hold_score', 50.0)
        self.wholesale_score = kwargs.get('wholesale_score', 30.0)
        self.water_score = kwargs.get('water_score', 2.0)
        self.price_per_acre = kwargs.get('price_per_acre', 2000.0)
        self.effective_cost = kwargs.get('effective_cost', 5500.0)
        self.time_to_ownership_days = kwargs.get('time_to_ownership_days', 180)
        self.is_market_reject = kwargs.get('is_market_reject', False)
        self.is_delta_region = kwargs.get('is_delta_region', False)
        self.year_sold = kwargs.get('year_sold', '2020')
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
            'investment_score': self.investment_score,
            'buy_hold_score': self.buy_hold_score,
            'wholesale_score': self.wholesale_score,
            'water_score': self.water_score,
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


class MockAggregateResult:
    """Mock for SQLAlchemy aggregate query result."""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockQuery:
    """Mock SQLAlchemy query object."""
    def __init__(self, result=None):
        self._result = result
        self._filters = []
        self._count = 0

    def filter(self, *args):
        self._filters.extend(args)
        return self

    def join(self, *args, **kwargs):
        return self

    def select_from(self, *args, **kwargs):
        return self

    def group_by(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._result

    def all(self):
        if isinstance(self._result, list):
            return self._result
        return [self._result] if self._result else []

    def count(self):
        if isinstance(self._result, list):
            return len(self._result)
        return self._count


class MockSession:
    """Mock SQLAlchemy session."""
    def __init__(self):
        self._queries = {}
        self._added = []
        self._committed = False
        self._aggregate_result = None

    def set_query_result(self, model, result):
        """Set the result for queries on a specific model."""
        self._queries[model] = result

    def set_aggregate_result(self, result):
        """Set the result for aggregate queries."""
        self._aggregate_result = result

    def query(self, *args, **kwargs):
        # If first arg is a func (aggregation), return aggregate result
        if self._aggregate_result is not None:
            query = MockQuery(self._aggregate_result)
            return query

        # Return first model's result if set
        for model in args:
            if model in self._queries:
                result = self._queries[model]
                query = MockQuery(result)
                if isinstance(result, list):
                    query._count = len(result)
                return query
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
    app.include_router(router, prefix="/portfolio")

    # Override dependencies
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user_or_api_key] = lambda: mock_auth

    return TestClient(app)


@pytest.fixture
def sample_properties():
    """Create sample properties for testing."""
    return [
        MockProperty(
            id="prop-1",
            parcel_id="320-00416-000",
            amount=5000.0,
            acreage=2.5,
            county="CARROLL",
            state="AR",
            investment_score=75.0,
            buy_hold_score=70.0,
            water_score=3.0,
        ),
        MockProperty(
            id="prop-2",
            parcel_id="123-456-789",
            amount=3000.0,
            acreage=1.5,
            county="JEFFERSON",
            state="AL",
            investment_score=45.0,
            buy_hold_score=40.0,
            water_score=0.0,
        ),
        MockProperty(
            id="prop-3",
            parcel_id="987-654-321",
            amount=8000.0,
            acreage=5.0,
            county="HARRIS",
            state="TX",
            investment_score=85.0,
            buy_hold_score=80.0,
            water_score=5.0,
        ),
    ]


@pytest.fixture
def sample_interactions(sample_properties):
    """Create sample interactions for testing."""
    now = datetime.utcnow()
    return [
        MockPropertyInteraction(
            id="int-1",
            device_id="test-device-123",
            property_id=sample_properties[0].id,
            is_watched=True,
            star_rating=4,
            created_at=now - timedelta(days=3),
        ),
        MockPropertyInteraction(
            id="int-2",
            device_id="test-device-123",
            property_id=sample_properties[1].id,
            is_watched=True,
            star_rating=3,
            created_at=now - timedelta(days=10),
        ),
        MockPropertyInteraction(
            id="int-3",
            device_id="test-device-123",
            property_id=sample_properties[2].id,
            is_watched=True,
            star_rating=5,
            is_first_deal=True,
            first_deal_stage="bid",
            created_at=now - timedelta(days=1),
        ),
    ]


# -----------------------------------------------------------------------------
# TEST: GET /portfolio/summary
# -----------------------------------------------------------------------------

class TestPortfolioSummary:
    """Tests for GET /portfolio/summary endpoint."""

    def test_summary_empty_portfolio(self, client, mock_db):
        """Test summary when portfolio is empty."""
        # Set up empty aggregate result
        mock_db.set_aggregate_result(MockAggregateResult(
            total_count=0,
            total_value=0,
            total_acreage=0,
            total_effective_cost=0,
            avg_investment_score=None,
            avg_buy_hold_score=None,
            avg_wholesale_score=None,
            avg_price_per_acre=None,
            water_count=0,
        ))

        response = client.get("/portfolio/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert data["total_value"] == 0
        assert data["water_access_percentage"] == 0

    def test_summary_with_properties(self, client, mock_db):
        """Test summary with watched properties."""
        mock_db.set_aggregate_result(MockAggregateResult(
            total_count=3,
            total_value=16000.0,
            total_acreage=9.0,
            total_effective_cost=17600.0,
            avg_investment_score=68.3,
            avg_buy_hold_score=63.3,
            avg_wholesale_score=30.0,
            avg_price_per_acre=1777.78,
            water_count=2,
        ))

        response = client.get("/portfolio/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 3
        assert data["total_value"] == 16000.0
        assert data["total_acreage"] == 9.0
        assert data["properties_with_water"] == 2
        assert data["timestamp"] is not None


# -----------------------------------------------------------------------------
# TEST: GET /portfolio/geographic
# -----------------------------------------------------------------------------

class TestGeographicBreakdown:
    """Tests for GET /portfolio/geographic endpoint."""

    def test_geographic_empty_portfolio(self, client, mock_db):
        """Test geographic breakdown with empty portfolio."""
        from backend_api.database.models import Property
        mock_db.set_query_result(Property, [])

        response = client.get("/portfolio/geographic")

        assert response.status_code == 200
        data = response.json()
        assert data["total_states"] == 0
        assert data["total_counties"] == 0
        assert data["states"] == []


# -----------------------------------------------------------------------------
# TEST: GET /portfolio/scores
# -----------------------------------------------------------------------------

class TestScoreDistribution:
    """Tests for GET /portfolio/scores endpoint."""

    def test_scores_empty_portfolio(self, client, mock_db):
        """Test score distribution with empty portfolio."""
        from backend_api.database.models import Property
        mock_db.set_query_result(Property, [])

        response = client.get("/portfolio/scores")

        assert response.status_code == 200
        data = response.json()
        assert data["top_performers_count"] == 0
        assert data["underperformers_count"] == 0
        assert len(data["investment_score_buckets"]) == 5


# -----------------------------------------------------------------------------
# TEST: GET /portfolio/risk
# -----------------------------------------------------------------------------

class TestRiskAnalysis:
    """Tests for GET /portfolio/risk endpoint."""

    def test_risk_empty_portfolio(self, client, mock_db):
        """Test risk analysis with empty portfolio."""
        from backend_api.database.models import Property
        mock_db.set_query_result(Property, [])

        response = client.get("/portfolio/risk")

        assert response.status_code == 200
        data = response.json()
        assert data["overall_risk_level"] == "low"
        assert data["risk_flags"] == []
        assert data["concentration"]["diversification_score"] == 100


# -----------------------------------------------------------------------------
# TEST: GET /portfolio/performance
# -----------------------------------------------------------------------------

class TestPerformanceTracking:
    """Tests for GET /portfolio/performance endpoint."""

    def test_performance_empty_portfolio(self, client, mock_db):
        """Test performance tracking with empty portfolio."""
        from backend_api.database.models import Property
        mock_db.set_query_result(Property, [])

        response = client.get("/portfolio/performance")

        assert response.status_code == 200
        data = response.json()
        assert data["additions_last_7_days"] == 0
        assert data["additions_last_30_days"] == 0
        assert data["has_first_deal"] is False


# -----------------------------------------------------------------------------
# TEST: GET /portfolio/export
# -----------------------------------------------------------------------------

class TestPortfolioExport:
    """Tests for GET /portfolio/export endpoint."""

    def test_export_empty_portfolio(self, client, mock_db):
        """Test export with empty portfolio - uses patched service."""
        from unittest.mock import patch, MagicMock
        from datetime import datetime
        from backend_api.models.portfolio import (
            PortfolioSummaryResponse, GeographicBreakdownResponse,
            ScoreDistributionResponse, RiskAnalysisResponse,
            PerformanceTrackingResponse, PortfolioAnalyticsExport,
            ConcentrationRisk, ScoreBucket
        )

        # Create mock responses
        now = datetime.utcnow()
        mock_summary = PortfolioSummaryResponse(
            total_count=0, total_value=0, total_acreage=0, total_effective_cost=0,
            avg_investment_score=0, avg_price_per_acre=0, capital_utilized=0,
            properties_with_water=0, water_access_percentage=0, timestamp=now
        )
        mock_geographic = GeographicBreakdownResponse(
            total_states=0, total_counties=0, states=[], timestamp=now
        )
        empty_buckets = [
            ScoreBucket(range_label=f"{i}-{i+19}", min_score=i, max_score=i+19, count=0, percentage=0, property_ids=[])
            for i in range(0, 100, 20)
        ]
        mock_scores = ScoreDistributionResponse(
            investment_score_buckets=empty_buckets, buy_hold_score_buckets=empty_buckets,
            top_performers_count=0, top_performers=[], underperformers_count=0,
            underperformers=[], timestamp=now
        )
        mock_risk = RiskAnalysisResponse(
            concentration=ConcentrationRisk(
                highest_state_concentration=0, highest_county_concentration=0, diversification_score=100
            ),
            properties_over_1_year=0, properties_over_3_years=0,
            delta_region_count=0, delta_region_percentage=0, delta_region_counties=[],
            market_reject_count=0, market_reject_percentage=0,
            largest_single_property_pct=0, top_3_properties_pct=0,
            overall_risk_level="low", risk_flags=[], timestamp=now
        )
        mock_performance = PerformanceTrackingResponse(
            additions_last_7_days=0, additions_last_30_days=0, recent_additions=[],
            star_rating_breakdown=[], rated_count=0, unrated_count=0,
            has_first_deal=False, activity_by_week={}, timestamp=now
        )

        mock_export = PortfolioAnalyticsExport(
            summary=mock_summary, geographic=mock_geographic, scores=mock_scores,
            risk=mock_risk, performance=mock_performance, exported_at=now
        )

        with patch('backend_api.routers.portfolio.PortfolioService') as MockService:
            mock_service_instance = MagicMock()
            mock_service_instance.get_full_export.return_value = mock_export
            MockService.return_value = mock_service_instance

            response = client.get("/portfolio/export")

        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "geographic" in data
        assert "scores" in data
        assert "risk" in data
        assert "performance" in data
        assert "exported_at" in data


# -----------------------------------------------------------------------------
# TEST: Authentication/Device Isolation
# -----------------------------------------------------------------------------

class TestDeviceIsolation:
    """Tests for device-based data isolation."""

    def test_different_device_gets_empty_portfolio(self, mock_db):
        """Test that different device IDs see different data."""
        app = FastAPI()
        app.include_router(router, prefix="/portfolio")

        # First device has data
        device1_auth = {
            "type": "api_key",
            "device_id": "device-1",
            "scopes": ["property:read"]
        }

        # Second device should see empty
        device2_auth = {
            "type": "api_key",
            "device_id": "device-2",
            "scopes": ["property:read"]
        }

        # Set up mock with no data (simulating different device)
        mock_db.set_aggregate_result(MockAggregateResult(
            total_count=0,
            total_value=0,
            total_acreage=0,
            total_effective_cost=0,
            avg_investment_score=None,
            avg_buy_hold_score=None,
            avg_wholesale_score=None,
            avg_price_per_acre=None,
            water_count=0,
        ))

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user_or_api_key] = lambda: device2_auth

        client = TestClient(app)
        response = client.get("/portfolio/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0


# -----------------------------------------------------------------------------
# TEST: Response Model Validation
# -----------------------------------------------------------------------------

class TestResponseValidation:
    """Tests for response model validation."""

    def test_summary_response_has_all_required_fields(self, client, mock_db):
        """Test that summary response contains all required fields."""
        mock_db.set_aggregate_result(MockAggregateResult(
            total_count=1,
            total_value=5000.0,
            total_acreage=2.5,
            total_effective_cost=5500.0,
            avg_investment_score=75.0,
            avg_buy_hold_score=70.0,
            avg_wholesale_score=30.0,
            avg_price_per_acre=2000.0,
            water_count=1,
        ))

        response = client.get("/portfolio/summary")

        assert response.status_code == 200
        data = response.json()

        # Check all required fields exist
        required_fields = [
            "total_count", "total_value", "total_acreage", "total_effective_cost",
            "avg_investment_score", "avg_price_per_acre",
            "capital_budget", "capital_utilized",
            "properties_with_water", "water_access_percentage",
            "timestamp"
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_risk_response_has_concentration_object(self, client, mock_db):
        """Test that risk response has concentration object."""
        from backend_api.database.models import Property
        mock_db.set_query_result(Property, [])

        response = client.get("/portfolio/risk")

        assert response.status_code == 200
        data = response.json()

        assert "concentration" in data
        concentration = data["concentration"]
        assert "highest_state_concentration" in concentration
        assert "highest_county_concentration" in concentration
        assert "diversification_score" in concentration
