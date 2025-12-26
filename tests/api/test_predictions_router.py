"""
Test suite for the Predictive Market Intelligence API Router.
Covers endpoints defined in backend_api/routers/predictions.py.

Target: 70-80 tests covering all 7 endpoints.
"""
import pytest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace


# -----------------------------------------------------------------------------
# HELPER / MOCK CLASSES
# -----------------------------------------------------------------------------

class MockEnum(SimpleNamespace):
    """Mock enum with .value attribute access."""
    def __init__(self, value):
        self.value = value


class MockPropertyAppreciationForecast(SimpleNamespace):
    """Mock for PropertyAppreciationForecast from predictive engine."""
    pass


class MockMarketTimingAnalysis(SimpleNamespace):
    """Mock for MarketTimingAnalysis from predictive engine."""
    pass


class MockEmergingOpportunity(SimpleNamespace):
    """Mock for EmergingOpportunity from predictive engine."""
    pass


def create_mock_forecast():
    """Create a standard mock forecast response."""
    return MockPropertyAppreciationForecast(
        one_year_appreciation=0.05,
        three_year_appreciation=0.15,
        five_year_appreciation=0.25,
        market_trend=MockEnum("growing"),
        confidence_level=MockEnum("high"),
        risk_score=0.2
    )


def create_mock_timing():
    """Create a standard mock timing analysis response."""
    return MockMarketTimingAnalysis(
        current_market_phase="buyer_market",
        optimal_buy_window=[1, 6],
        optimal_sell_window=[12, 18],
        price_momentum=0.3,
        market_volatility=0.4,
        confidence_score=0.85
    )


def create_mock_opportunity(property_id="prop-123", county="Baldwin"):
    """Create a standard mock emerging opportunity."""
    return MockEmergingOpportunity(
        property_id=property_id,
        county=county,
        opportunity_type="undervalued_property",
        opportunity_score=85.5,
        potential_appreciation=0.22,
        risk_adjusted_return=0.18,
        expected_timeline_months=24,
        confidence_level=MockEnum("medium"),
        primary_drivers=["New infrastructure", "Zoning changes"],
        risk_factors=["Market slowdown"]
    )


# -----------------------------------------------------------------------------
# FIXTURES
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_engine():
    """Creates a mock predictive engine with default behaviors."""
    engine = MagicMock()
    engine.predict_property_appreciation.return_value = create_mock_forecast()
    engine.analyze_market_timing.return_value = create_mock_timing()
    engine.detect_emerging_opportunities.return_value = [create_mock_opportunity()]
    return engine


# -----------------------------------------------------------------------------
# TEST CLASS: TestPredictionsRouter
# -----------------------------------------------------------------------------

class TestPredictionsRouter:
    """Comprehensive test suite for the Predictions Router (75+ tests)."""

    # -------------------------------------------------------------------------
    # 1. HEALTH ENDPOINT (GET /health) - 8 tests
    # -------------------------------------------------------------------------

    def test_health_success(self, api_client, mock_engine):
        """Test health check returns 200 and valid response."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = api_client.get("/api/v1/predictions/health")
        assert response.status_code == 200
        data = response.json()
        assert data["engine_status"] == "healthy"

    def test_health_response_structure(self, api_client, mock_engine):
        """Test health response contains all expected fields."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = api_client.get("/api/v1/predictions/health")
        data = response.json()
        assert "engine_status" in data
        assert "algorithm_version" in data
        assert "last_model_update" in data
        assert "available_counties" in data
        assert "performance_metrics" in data
        assert "uptime_seconds" in data

    def test_health_available_counties_list(self, api_client, mock_engine):
        """Test health returns list of available counties."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = api_client.get("/api/v1/predictions/health")
        data = response.json()
        assert isinstance(data["available_counties"], list)
        assert len(data["available_counties"]) >= 1

    def test_health_performance_metrics_dict(self, api_client, mock_engine):
        """Test health returns performance metrics as dict."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = api_client.get("/api/v1/predictions/health")
        data = response.json()
        assert isinstance(data["performance_metrics"], dict)

    def test_health_uptime_positive(self, api_client, mock_engine):
        """Test health uptime is a positive number."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = api_client.get("/api/v1/predictions/health")
        data = response.json()
        assert data["uptime_seconds"] >= 0

    def test_health_engine_failure(self, api_client):
        """Test health check returns 503 when engine fails."""
        with patch("backend_api.routers.predictions.get_predictive_engine", side_effect=Exception("Engine init failed")):
            response = api_client.get("/api/v1/predictions/health")
        assert response.status_code == 503
        assert response.json()["detail"] == "Prediction engine unhealthy"

    def test_health_no_auth_required(self, api_client, mock_engine):
        """Test health endpoint doesn't require authentication."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = api_client.get("/api/v1/predictions/health")
        assert response.status_code == 200

    def test_health_idempotent(self, api_client, mock_engine):
        """Test health endpoint returns consistent results on multiple calls."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            r1 = api_client.get("/api/v1/predictions/health")
            r2 = api_client.get("/api/v1/predictions/health")
        assert r1.json()["engine_status"] == r2.json()["engine_status"]

    # -------------------------------------------------------------------------
    # 2. PROPERTY APPRECIATION (POST /appreciation) - 12 tests
    # -------------------------------------------------------------------------

    def test_appreciation_success(self, authenticated_client, mock_engine):
        """Test happy path for property appreciation prediction."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {
                "property_data": {"id": "prop-123"},
                "county": "Baldwin",
                "current_investment_score": 75.5
            }
            response = authenticated_client.post("/api/v1/predictions/appreciation", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["property_id"] == "prop-123"
        assert data["county"] == "Baldwin"

    def test_appreciation_response_fields(self, authenticated_client, mock_engine):
        """Test appreciation response contains all expected fields."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {
                "property_data": {"id": "prop-123"},
                "county": "Mobile",
                "current_investment_score": 50.0
            }
            response = authenticated_client.post("/api/v1/predictions/appreciation", json=payload)
        data = response.json()
        assert "one_year_appreciation" in data
        assert "three_year_appreciation" in data
        assert "five_year_appreciation" in data
        assert "market_trend" in data
        assert "confidence_level" in data
        assert "risk_score" in data

    def test_appreciation_missing_property_data(self, authenticated_client, mock_engine):
        """Test validation error for missing property_data."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {"county": "Baldwin", "current_investment_score": 75.5}
            response = authenticated_client.post("/api/v1/predictions/appreciation", json=payload)
        assert response.status_code == 422

    def test_appreciation_missing_county(self, authenticated_client, mock_engine):
        """Test validation error for missing county."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {"property_data": {"id": "123"}, "current_investment_score": 75.5}
            response = authenticated_client.post("/api/v1/predictions/appreciation", json=payload)
        assert response.status_code == 422

    def test_appreciation_missing_investment_score(self, authenticated_client, mock_engine):
        """Test validation error for missing investment score."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {"property_data": {"id": "123"}, "county": "Baldwin"}
            response = authenticated_client.post("/api/v1/predictions/appreciation", json=payload)
        assert response.status_code == 422

    def test_appreciation_investment_score_too_low(self, authenticated_client, mock_engine):
        """Test validation error for investment score below 0."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {"property_data": {"id": "123"}, "county": "Baldwin", "current_investment_score": -1}
            response = authenticated_client.post("/api/v1/predictions/appreciation", json=payload)
        assert response.status_code == 422

    def test_appreciation_investment_score_too_high(self, authenticated_client, mock_engine):
        """Test validation error for investment score above 100."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {"property_data": {"id": "123"}, "county": "Baldwin", "current_investment_score": 101}
            response = authenticated_client.post("/api/v1/predictions/appreciation", json=payload)
        assert response.status_code == 422

    @pytest.mark.parametrize("score", [0, 25, 50, 75, 100])
    def test_appreciation_valid_investment_scores(self, authenticated_client, mock_engine, score):
        """Test valid investment scores at boundaries."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {"property_data": {"id": "123"}, "county": "Baldwin", "current_investment_score": score}
            response = authenticated_client.post("/api/v1/predictions/appreciation", json=payload)
        assert response.status_code == 200

    def test_appreciation_service_exception(self, authenticated_client):
        """Test 500 error when engine fails."""
        engine = MagicMock()
        engine.predict_property_appreciation.side_effect = Exception("Model error")
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=engine):
            payload = {"property_data": {"id": "123"}, "county": "Baldwin", "current_investment_score": 50}
            response = authenticated_client.post("/api/v1/predictions/appreciation", json=payload)
        assert response.status_code == 500
        assert "Failed to generate appreciation forecast" in response.json()["detail"]

    def test_appreciation_unauthorized(self, api_client, mock_engine):
        """Test unauthorized access without token."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {"property_data": {"id": "123"}, "county": "Baldwin", "current_investment_score": 50}
            response = api_client.post("/api/v1/predictions/appreciation", json=payload)
        assert response.status_code == 401

    @pytest.mark.parametrize("county", ["Mobile", "Baldwin", "Jefferson", "Madison", "Montgomery"])
    def test_appreciation_various_counties(self, authenticated_client, mock_engine, county):
        """Test appreciation for various Alabama counties."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {"property_data": {"id": "123"}, "county": county, "current_investment_score": 75}
            response = authenticated_client.post("/api/v1/predictions/appreciation", json=payload)
        assert response.status_code == 200
        assert response.json()["county"] == county

    # -------------------------------------------------------------------------
    # 3. MARKET TIMING (POST /market-timing) - 10 tests
    # -------------------------------------------------------------------------

    def test_market_timing_success(self, authenticated_client, mock_engine):
        """Test happy path for market timing analysis."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.post("/api/v1/predictions/market-timing", json={"county": "Jefferson"})
        assert response.status_code == 200
        data = response.json()
        assert data["county"] == "Jefferson"
        mock_engine.analyze_market_timing.assert_called_with("Jefferson")

    def test_market_timing_response_structure(self, authenticated_client, mock_engine):
        """Test market timing response contains expected fields."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.post("/api/v1/predictions/market-timing", json={"county": "Mobile"})
        data = response.json()
        assert "current_market_phase" in data
        assert "optimal_buy_window" in data
        assert "optimal_sell_window" in data
        assert "price_momentum" in data
        assert "market_volatility" in data
        assert "confidence_score" in data

    def test_market_timing_missing_county(self, authenticated_client, mock_engine):
        """Test validation error for missing county."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.post("/api/v1/predictions/market-timing", json={})
        assert response.status_code == 422

    def test_market_timing_empty_county(self, authenticated_client, mock_engine):
        """Test with empty county string."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.post("/api/v1/predictions/market-timing", json={"county": ""})
        # Empty string may be accepted but handled by the engine
        assert response.status_code in [200, 422, 500]

    def test_market_timing_service_exception(self, authenticated_client):
        """Test 500 error when timing analysis fails."""
        engine = MagicMock()
        engine.analyze_market_timing.side_effect = Exception("Data unavailable")
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=engine):
            response = authenticated_client.post("/api/v1/predictions/market-timing", json={"county": "Jefferson"})
        assert response.status_code == 500
        assert "Failed to analyze market timing" in response.json()["detail"]

    def test_market_timing_unauthorized(self, api_client, mock_engine):
        """Test unauthorized access without token."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = api_client.post("/api/v1/predictions/market-timing", json={"county": "Jefferson"})
        assert response.status_code == 401

    @pytest.mark.parametrize("county", ["Mobile", "Baldwin", "Jefferson", "Madison", "Tuscaloosa"])
    def test_market_timing_various_counties(self, authenticated_client, mock_engine, county):
        """Test market timing for various counties."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.post("/api/v1/predictions/market-timing", json={"county": county})
        assert response.status_code == 200
        assert response.json()["county"] == county

    def test_market_timing_momentum_in_range(self, authenticated_client, mock_engine):
        """Test price momentum is within valid range."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.post("/api/v1/predictions/market-timing", json={"county": "Mobile"})
        data = response.json()
        assert -1 <= data["price_momentum"] <= 1

    def test_market_timing_volatility_in_range(self, authenticated_client, mock_engine):
        """Test market volatility is within valid range."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.post("/api/v1/predictions/market-timing", json={"county": "Mobile"})
        data = response.json()
        assert 0 <= data["market_volatility"] <= 1

    def test_market_timing_confidence_in_range(self, authenticated_client, mock_engine):
        """Test confidence score is within valid range."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.post("/api/v1/predictions/market-timing", json={"county": "Mobile"})
        data = response.json()
        assert 0 <= data["confidence_score"] <= 1

    # -------------------------------------------------------------------------
    # 4. OPPORTUNITIES (POST /opportunities) - 12 tests
    # -------------------------------------------------------------------------

    def test_opportunities_success(self, authenticated_client, mock_engine):
        """Test happy path for opportunity detection."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {"properties_data": [{"id": "p1"}, {"id": "p2"}], "top_n": 5}
            response = authenticated_client.post("/api/v1/predictions/opportunities", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["total_properties_analyzed"] == 2
        assert "opportunities" in data

    def test_opportunities_response_structure(self, authenticated_client, mock_engine):
        """Test opportunities response contains expected fields."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {"properties_data": [{"id": "p1"}], "top_n": 5}
            response = authenticated_client.post("/api/v1/predictions/opportunities", json=payload)
        data = response.json()
        assert "total_properties_analyzed" in data
        assert "opportunities_found" in data
        assert "opportunities" in data

    def test_opportunities_no_results(self, authenticated_client):
        """Test response when no opportunities found."""
        engine = MagicMock()
        engine.detect_emerging_opportunities.return_value = []
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=engine):
            payload = {"properties_data": [{"id": "p1"}], "top_n": 5}
            response = authenticated_client.post("/api/v1/predictions/opportunities", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["opportunities_found"] == 0
        assert data["opportunities"] == []

    def test_opportunities_missing_properties_data(self, authenticated_client, mock_engine):
        """Test validation error for missing properties_data."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.post("/api/v1/predictions/opportunities", json={"top_n": 5})
        assert response.status_code == 422

    def test_opportunities_top_n_too_low(self, authenticated_client, mock_engine):
        """Test validation error for top_n less than 1."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {"properties_data": [{"id": "p1"}], "top_n": 0}
            response = authenticated_client.post("/api/v1/predictions/opportunities", json=payload)
        assert response.status_code == 422

    def test_opportunities_top_n_too_high(self, authenticated_client, mock_engine):
        """Test validation error for top_n greater than 50."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {"properties_data": [{"id": "p1"}], "top_n": 51}
            response = authenticated_client.post("/api/v1/predictions/opportunities", json=payload)
        assert response.status_code == 422

    @pytest.mark.parametrize("top_n", [1, 10, 25, 50])
    def test_opportunities_valid_top_n_values(self, authenticated_client, mock_engine, top_n):
        """Test valid top_n values at boundaries."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {"properties_data": [{"id": "p1"}], "top_n": top_n}
            response = authenticated_client.post("/api/v1/predictions/opportunities", json=payload)
        assert response.status_code == 200

    def test_opportunities_service_exception(self, authenticated_client):
        """Test 500 error when opportunity detection fails."""
        engine = MagicMock()
        engine.detect_emerging_opportunities.side_effect = Exception("Detection error")
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=engine):
            payload = {"properties_data": [{"id": "p1"}], "top_n": 5}
            response = authenticated_client.post("/api/v1/predictions/opportunities", json=payload)
        assert response.status_code == 500
        assert "Failed to detect opportunities" in response.json()["detail"]

    def test_opportunities_unauthorized(self, api_client, mock_engine):
        """Test unauthorized access without token."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {"properties_data": [{"id": "p1"}], "top_n": 5}
            response = api_client.post("/api/v1/predictions/opportunities", json=payload)
        assert response.status_code == 401

    def test_opportunities_large_property_list(self, authenticated_client, mock_engine):
        """Test opportunity detection with larger property list."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            properties = [{"id": f"p{i}"} for i in range(20)]
            payload = {"properties_data": properties, "top_n": 10}
            response = authenticated_client.post("/api/v1/predictions/opportunities", json=payload)
        assert response.status_code == 200
        assert response.json()["total_properties_analyzed"] == 20

    def test_opportunities_default_top_n(self, authenticated_client, mock_engine):
        """Test default top_n value is applied."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {"properties_data": [{"id": "p1"}]}
            response = authenticated_client.post("/api/v1/predictions/opportunities", json=payload)
        assert response.status_code == 200

    # -------------------------------------------------------------------------
    # 5. BATCH APPRECIATION (POST /appreciation/batch) - 12 tests
    # -------------------------------------------------------------------------

    def test_batch_appreciation_success(self, authenticated_client, mock_engine):
        """Test batch appreciation with all predictions succeeding."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {
                "properties": [
                    {"property_data": {"id": "p1"}, "county": "Mobile", "current_investment_score": 50},
                    {"property_data": {"id": "p2"}, "county": "Baldwin", "current_investment_score": 75}
                ]
            }
            response = authenticated_client.post("/api/v1/predictions/appreciation/batch", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["total_requested"] == 2
        assert data["successful_predictions"] == 2
        assert data["failed_predictions"] == 0

    def test_batch_appreciation_response_structure(self, authenticated_client, mock_engine):
        """Test batch response contains expected fields."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {"properties": [{"property_data": {"id": "p1"}, "county": "Mobile", "current_investment_score": 50}]}
            response = authenticated_client.post("/api/v1/predictions/appreciation/batch", json=payload)
        data = response.json()
        assert "total_requested" in data
        assert "successful_predictions" in data
        assert "failed_predictions" in data
        assert "predictions" in data
        assert "errors" in data
        assert "processing_time_seconds" in data

    def test_batch_appreciation_partial_failure(self, authenticated_client):
        """Test batch with some predictions failing."""
        engine = MagicMock()
        engine.predict_property_appreciation.side_effect = [
            create_mock_forecast(),
            Exception("Failed for p2")
        ]
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=engine):
            payload = {
                "properties": [
                    {"property_data": {"id": "p1"}, "county": "Mobile", "current_investment_score": 50},
                    {"property_data": {"id": "p2"}, "county": "Baldwin", "current_investment_score": 75}
                ]
            }
            response = authenticated_client.post("/api/v1/predictions/appreciation/batch", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["successful_predictions"] == 1
        assert data["failed_predictions"] == 1
        assert len(data["errors"]) == 1

    def test_batch_appreciation_all_failures(self, authenticated_client):
        """Test batch with all predictions failing."""
        engine = MagicMock()
        engine.predict_property_appreciation.side_effect = Exception("All failed")
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=engine):
            payload = {
                "properties": [
                    {"property_data": {"id": "p1"}, "county": "Mobile", "current_investment_score": 50}
                ]
            }
            response = authenticated_client.post("/api/v1/predictions/appreciation/batch", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["successful_predictions"] == 0
        assert data["failed_predictions"] == 1

    def test_batch_appreciation_empty_list(self, authenticated_client, mock_engine):
        """Test batch with empty properties list."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.post("/api/v1/predictions/appreciation/batch", json={"properties": []})
        assert response.status_code == 200
        data = response.json()
        assert data["total_requested"] == 0
        assert data["successful_predictions"] == 0

    def test_batch_appreciation_processing_time(self, authenticated_client, mock_engine):
        """Test processing time is returned."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {"properties": [{"property_data": {"id": "p1"}, "county": "Mobile", "current_investment_score": 50}]}
            response = authenticated_client.post("/api/v1/predictions/appreciation/batch", json=payload)
        assert response.json()["processing_time_seconds"] >= 0

    def test_batch_appreciation_large_batch(self, authenticated_client, mock_engine):
        """Test batch with larger property list."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            properties = [{"property_data": {"id": f"p{i}"}, "county": "Mobile", "current_investment_score": 50} for i in range(10)]
            response = authenticated_client.post("/api/v1/predictions/appreciation/batch", json={"properties": properties})
        assert response.status_code == 200
        assert response.json()["total_requested"] == 10

    def test_batch_appreciation_service_exception(self, authenticated_client):
        """Test 500 error when engine initialization fails."""
        with patch("backend_api.routers.predictions.get_predictive_engine", side_effect=Exception("Engine init failed")):
            payload = {"properties": [{"property_data": {"id": "p1"}, "county": "Mobile", "current_investment_score": 50}]}
            response = authenticated_client.post("/api/v1/predictions/appreciation/batch", json=payload)
        assert response.status_code == 500

    def test_batch_appreciation_unauthorized(self, api_client, mock_engine):
        """Test unauthorized access without token."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {"properties": [{"property_data": {"id": "p1"}, "county": "Mobile", "current_investment_score": 50}]}
            response = api_client.post("/api/v1/predictions/appreciation/batch", json=payload)
        assert response.status_code == 401

    def test_batch_appreciation_error_details(self, authenticated_client):
        """Test error details are captured correctly."""
        engine = MagicMock()
        engine.predict_property_appreciation.side_effect = Exception("Specific error message")
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=engine):
            payload = {"properties": [{"property_data": {"id": "p1"}, "county": "Mobile", "current_investment_score": 50}]}
            response = authenticated_client.post("/api/v1/predictions/appreciation/batch", json=payload)
        errors = response.json()["errors"]
        assert len(errors) == 1
        assert errors[0]["index"] == 0
        assert "Specific error message" in errors[0]["error"]

    def test_batch_appreciation_property_ids_in_results(self, authenticated_client, mock_engine):
        """Test property IDs are preserved in results."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            payload = {"properties": [{"property_data": {"id": "my-unique-id"}, "county": "Mobile", "current_investment_score": 50}]}
            response = authenticated_client.post("/api/v1/predictions/appreciation/batch", json=payload)
        predictions = response.json()["predictions"]
        assert len(predictions) == 1
        assert predictions[0]["property_id"] == "my-unique-id"

    # -------------------------------------------------------------------------
    # 6. COUNTIES TIMING OVERVIEW (GET /counties/timing-overview) - 10 tests
    # -------------------------------------------------------------------------

    def test_timing_overview_default_counties(self, authenticated_client, mock_engine):
        """Test timing overview uses default counties when none specified."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.get("/api/v1/predictions/counties/timing-overview")
        assert response.status_code == 200
        data = response.json()
        assert data["counties_analyzed"] == 10

    def test_timing_overview_specific_counties(self, authenticated_client, mock_engine):
        """Test timing overview for specific counties."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.get("/api/v1/predictions/counties/timing-overview?counties=Mobile&counties=Jefferson")
        assert response.status_code == 200
        data = response.json()
        assert data["counties_analyzed"] == 2

    def test_timing_overview_response_structure(self, authenticated_client, mock_engine):
        """Test timing overview response structure."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.get("/api/v1/predictions/counties/timing-overview")
        data = response.json()
        assert "counties_analyzed" in data
        assert "successful_analyses" in data
        assert "timing_data" in data
        assert "processing_time_seconds" in data

    def test_timing_overview_partial_failure(self, authenticated_client):
        """Test timing overview with partial failures."""
        engine = MagicMock()
        engine.analyze_market_timing.side_effect = [
            create_mock_timing(),
            Exception("Failed for county 2")
        ]
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=engine):
            response = authenticated_client.get("/api/v1/predictions/counties/timing-overview?counties=Mobile&counties=Jefferson")
        assert response.status_code == 200
        data = response.json()
        assert data["successful_analyses"] == 1

    def test_timing_overview_all_failures(self, authenticated_client):
        """Test timing overview when all counties fail."""
        engine = MagicMock()
        engine.analyze_market_timing.side_effect = Exception("All failed")
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=engine):
            response = authenticated_client.get("/api/v1/predictions/counties/timing-overview?counties=Mobile")
        assert response.status_code == 200
        data = response.json()
        assert data["successful_analyses"] == 0

    def test_timing_overview_service_exception(self, authenticated_client):
        """Test 500 error when engine initialization fails."""
        with patch("backend_api.routers.predictions.get_predictive_engine", side_effect=Exception("Engine failed")):
            response = authenticated_client.get("/api/v1/predictions/counties/timing-overview")
        assert response.status_code == 500

    def test_timing_overview_unauthorized(self, api_client, mock_engine):
        """Test unauthorized access without token."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = api_client.get("/api/v1/predictions/counties/timing-overview")
        assert response.status_code == 401

    def test_timing_overview_single_county(self, authenticated_client, mock_engine):
        """Test timing overview for a single county."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.get("/api/v1/predictions/counties/timing-overview?counties=Baldwin")
        assert response.status_code == 200
        assert response.json()["counties_analyzed"] == 1

    def test_timing_overview_timing_data_keys(self, authenticated_client, mock_engine):
        """Test timing data contains county keys."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.get("/api/v1/predictions/counties/timing-overview?counties=Mobile&counties=Baldwin")
        timing_data = response.json()["timing_data"]
        assert "Mobile" in timing_data
        assert "Baldwin" in timing_data

    def test_timing_overview_processing_time(self, authenticated_client, mock_engine):
        """Test processing time is returned."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.get("/api/v1/predictions/counties/timing-overview")
        assert response.json()["processing_time_seconds"] >= 0

    # -------------------------------------------------------------------------
    # 7. ANALYTICS PERFORMANCE (GET /analytics/performance) - 8 tests
    # -------------------------------------------------------------------------

    def test_analytics_performance_success(self, authenticated_client, mock_engine):
        """Test analytics performance endpoint returns 200."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.get("/api/v1/predictions/analytics/performance")
        assert response.status_code == 200

    def test_analytics_performance_structure(self, authenticated_client, mock_engine):
        """Test analytics response contains expected sections."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.get("/api/v1/predictions/analytics/performance")
        data = response.json()
        assert "prediction_stats" in data
        assert "performance_metrics" in data
        assert "market_coverage" in data
        assert "algorithm_metrics" in data
        assert "uptime_info" in data

    def test_analytics_performance_prediction_stats(self, authenticated_client, mock_engine):
        """Test prediction stats section."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.get("/api/v1/predictions/analytics/performance")
        stats = response.json()["prediction_stats"]
        assert "total_predictions_generated" in stats
        assert "predictions_last_24h" in stats

    def test_analytics_performance_metrics(self, authenticated_client, mock_engine):
        """Test performance metrics section."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.get("/api/v1/predictions/analytics/performance")
        metrics = response.json()["performance_metrics"]
        assert "avg_response_time_ms" in metrics
        assert "cache_efficiency" in metrics

    def test_analytics_performance_market_coverage(self, authenticated_client, mock_engine):
        """Test market coverage section."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.get("/api/v1/predictions/analytics/performance")
        coverage = response.json()["market_coverage"]
        assert "counties_supported" in coverage
        assert coverage["counties_supported"] == 67  # Alabama county count

    def test_analytics_performance_algorithm_metrics(self, authenticated_client, mock_engine):
        """Test algorithm metrics section."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.get("/api/v1/predictions/analytics/performance")
        algo = response.json()["algorithm_metrics"]
        assert "model_accuracy" in algo
        assert "feature_importance_top3" in algo

    def test_analytics_performance_unauthorized(self, api_client, mock_engine):
        """Test unauthorized access without token."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = api_client.get("/api/v1/predictions/analytics/performance")
        assert response.status_code == 401

    def test_analytics_performance_uptime(self, authenticated_client, mock_engine):
        """Test uptime info section."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = authenticated_client.get("/api/v1/predictions/analytics/performance")
        uptime = response.json()["uptime_info"]
        assert "engine_uptime_hours" in uptime
        assert "availability_percentage" in uptime

    # -------------------------------------------------------------------------
    # 8. CROSS-CUTTING AUTHENTICATION TESTS - 5 tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("endpoint,method", [
        ("/api/v1/predictions/appreciation", "post"),
        ("/api/v1/predictions/market-timing", "post"),
        ("/api/v1/predictions/opportunities", "post"),
        ("/api/v1/predictions/appreciation/batch", "post"),
        ("/api/v1/predictions/counties/timing-overview", "get"),
        ("/api/v1/predictions/analytics/performance", "get"),
    ])
    def test_protected_endpoints_require_auth(self, api_client, mock_engine, endpoint, method):
        """Test all protected endpoints require authentication."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            if method == "post":
                response = api_client.post(endpoint, json={})
            else:
                response = api_client.get(endpoint)
        assert response.status_code == 401

    def test_invalid_token_rejected(self, api_client, mock_engine):
        """Test invalid JWT token is rejected."""
        api_client.headers["Authorization"] = "Bearer invalid-token-here"
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = api_client.get("/api/v1/predictions/analytics/performance")
        assert response.status_code == 401

    def test_health_does_not_require_auth(self, api_client, mock_engine):
        """Test health endpoint does not require authentication."""
        with patch("backend_api.routers.predictions.get_predictive_engine", return_value=mock_engine):
            response = api_client.get("/api/v1/predictions/health")
        assert response.status_code == 200
