"""
Test suite for the AI Testing & Validation API Router.
Covers endpoints defined in backend_api/routers/testing.py.

Target: 60-70 tests covering all 8 endpoints.
"""
import pytest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
from datetime import datetime


# -----------------------------------------------------------------------------
# HELPER / MOCK CLASSES
# -----------------------------------------------------------------------------

class MockValidationStatus:
    """Mock enum for validation status."""
    def __init__(self, value):
        self.value = value


def create_mock_validation_result():
    """Create a mock ValidationResult."""
    return SimpleNamespace(
        accuracy_score=0.85,
        precision_score=0.82,
        recall_score=0.88,
        mean_absolute_error=0.05,
        confidence_calibration=0.90,
        validation_status=MockValidationStatus("passed"),
        total_predictions=100,
        successful_predictions=85,
        failed_predictions=15,
        validation_duration=2.5,
        model_version="1.0.0",
        validation_timestamp=datetime.now(),
        county_performance={"Mobile": 0.88, "Baldwin": 0.82}
    )


def create_mock_backtest_result():
    """Create a mock BacktestResult."""
    return SimpleNamespace(
        overall_accuracy=0.82,
        market_trend_accuracy=0.78,
        appreciation_mae=0.03,
        appreciation_rmse=0.05,
        high_confidence_accuracy=0.90,
        medium_confidence_accuracy=0.80,
        low_confidence_accuracy=0.70,
        test_properties_count=500,
        execution_time_seconds=15.5,
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31),
        prediction_horizon_months=12,
        backtest_timestamp=datetime.now()
    )


# -----------------------------------------------------------------------------
# FIXTURES
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_validator():
    """Creates a mock prediction validator."""
    validator = MagicMock()
    validator.validate_current_predictions.return_value = create_mock_validation_result()
    validator.run_backtest.return_value = create_mock_backtest_result()
    validator.get_validation_history.return_value = [create_mock_validation_result() for _ in range(5)]
    validator.backtest_results = [create_mock_backtest_result() for _ in range(3)]
    return validator


# -----------------------------------------------------------------------------
# TEST CLASS: TestTestingRouter
# -----------------------------------------------------------------------------

class TestTestingRouter:
    """Comprehensive test suite for the Testing Router (65 tests)."""

    # -------------------------------------------------------------------------
    # 1. HEALTH ENDPOINT (GET /health) - 6 tests
    # -------------------------------------------------------------------------

    def test_health_success(self, api_client, mock_validator):
        """Test health check returns 200 and valid response."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = api_client.get("/api/v1/testing/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_response_structure(self, api_client, mock_validator):
        """Test health response contains expected fields."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = api_client.get("/api/v1/testing/health")
        data = response.json()
        assert "status" in data
        assert "system" in data
        assert "version" in data
        assert "timestamp" in data
        assert "database_connected" in data
        assert "validator_initialized" in data

    def test_health_system_name(self, api_client, mock_validator):
        """Test health returns correct system name."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = api_client.get("/api/v1/testing/health")
        assert response.json()["system"] == "AI Testing & Validation"

    def test_health_engine_failure(self, api_client):
        """Test health check returns 503 when validator fails."""
        with patch("backend_api.routers.testing.get_prediction_validator", side_effect=Exception("Validator init failed")):
            response = api_client.get("/api/v1/testing/health")
        assert response.status_code == 503
        assert response.json()["detail"] == "Testing system unhealthy"

    def test_health_no_auth_required(self, api_client, mock_validator):
        """Test health endpoint doesn't require authentication."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = api_client.get("/api/v1/testing/health")
        assert response.status_code == 200

    def test_health_version(self, api_client, mock_validator):
        """Test health returns version."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = api_client.get("/api/v1/testing/health")
        assert response.json()["version"] == "1.0.0"

    # -------------------------------------------------------------------------
    # 2. VALIDATE ENDPOINT (POST /validate) - 10 tests
    # -------------------------------------------------------------------------

    def test_validate_success(self, authenticated_client, mock_validator):
        """Test successful prediction validation."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            payload = {
                "properties_sample": [{"id": "p1", "county": "Mobile"}],
                "validation_period": "2024-Q1",
                "prediction_horizon": "3_year"
            }
            response = authenticated_client.post("/api/v1/testing/validate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["accuracy_score"] == 0.85

    def test_validate_response_structure(self, authenticated_client, mock_validator):
        """Test validation response contains expected fields."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            payload = {"properties_sample": [{"id": "p1"}]}
            response = authenticated_client.post("/api/v1/testing/validate", json=payload)
        data = response.json()
        assert "accuracy_score" in data
        assert "precision_score" in data
        assert "recall_score" in data
        assert "mean_absolute_error" in data
        assert "validation_status" in data
        assert "total_predictions" in data

    def test_validate_missing_properties(self, authenticated_client, mock_validator):
        """Test validation error for missing properties_sample."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = authenticated_client.post("/api/v1/testing/validate", json={})
        assert response.status_code == 422

    def test_validate_empty_properties(self, authenticated_client, mock_validator):
        """Test validation with empty properties list."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            payload = {"properties_sample": []}
            response = authenticated_client.post("/api/v1/testing/validate", json=payload)
        # Empty list may be valid but produce minimal results
        assert response.status_code in [200, 422]

    def test_validate_service_exception(self, authenticated_client):
        """Test 500 error when validation fails."""
        validator = MagicMock()
        validator.validate_current_predictions.side_effect = Exception("Validation error")
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=validator):
            payload = {"properties_sample": [{"id": "p1"}]}
            response = authenticated_client.post("/api/v1/testing/validate", json=payload)
        assert response.status_code == 500
        assert "Failed to validate predictions" in response.json()["detail"]

    def test_validate_unauthorized(self, api_client, mock_validator):
        """Test unauthorized access without token."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            payload = {"properties_sample": [{"id": "p1"}]}
            response = api_client.post("/api/v1/testing/validate", json=payload)
        assert response.status_code == 401

    def test_validate_default_period(self, authenticated_client, mock_validator):
        """Test validation uses default period when not specified."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            payload = {"properties_sample": [{"id": "p1"}]}
            response = authenticated_client.post("/api/v1/testing/validate", json=payload)
        assert response.status_code == 200

    def test_validate_default_horizon(self, authenticated_client, mock_validator):
        """Test validation uses default horizon when not specified."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            payload = {"properties_sample": [{"id": "p1"}]}
            response = authenticated_client.post("/api/v1/testing/validate", json=payload)
        assert response.status_code == 200

    def test_validate_model_version_returned(self, authenticated_client, mock_validator):
        """Test validation returns model version."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            payload = {"properties_sample": [{"id": "p1"}]}
            response = authenticated_client.post("/api/v1/testing/validate", json=payload)
        assert response.json()["model_version"] == "1.0.0"

    def test_validate_duration_returned(self, authenticated_client, mock_validator):
        """Test validation returns duration."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            payload = {"properties_sample": [{"id": "p1"}]}
            response = authenticated_client.post("/api/v1/testing/validate", json=payload)
        assert response.json()["validation_duration"] >= 0

    # -------------------------------------------------------------------------
    # 3. BACKTEST ENDPOINT (POST /backtest) - Tests (Admin only)
    # Note: Endpoint has 3/hour rate limit, so tests are consolidated
    # -------------------------------------------------------------------------

    def test_backtest_success_and_response_structure(self, admin_client, mock_validator):
        """Test successful backtest with full response structure validation.
        Consolidated test to stay within 3/hour rate limit.
        """
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            payload = {"days_back": 365, "horizon_months": 12, "property_limit": 100}
            response = admin_client.post("/api/v1/testing/backtest", json=payload)
        assert response.status_code == 200
        data = response.json()
        # Test response accuracy value
        assert data["overall_accuracy"] == 0.82
        # Test response structure
        assert "overall_accuracy" in data
        assert "market_trend_accuracy" in data
        assert "appreciation_mae" in data
        assert "test_properties_count" in data
        assert "execution_time_seconds" in data
        # Test dates returned
        assert "start_date" in data
        assert "end_date" in data

    def test_backtest_boundary_values_and_exception(self, admin_client, mock_validator):
        """Test backtest with boundary values.
        Note: Rate limit is 3/hour, so we only make 2 calls here (1 already used by success test).
        """
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            # Test minimum and maximum boundary in same call context
            response_min = admin_client.post("/api/v1/testing/backtest", json={"days_back": 30})
            assert response_min.status_code == 200
            assert "overall_accuracy" in response_min.json()

        # Test service exception (uses rate limit slot 3)
        validator_with_error = MagicMock()
        validator_with_error.run_backtest.side_effect = Exception("Backtest error")
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=validator_with_error):
            response_error = admin_client.post("/api/v1/testing/backtest", json={"days_back": 1095})
        assert response_error.status_code == 500
        assert "Failed to run backtest" in response_error.json()["detail"]

    def test_backtest_days_too_low(self, admin_client, mock_validator):
        """Test validation error for days_back below 30."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            payload = {"days_back": 20}
            response = admin_client.post("/api/v1/testing/backtest", json=payload)
        assert response.status_code == 422

    def test_backtest_days_too_high(self, admin_client, mock_validator):
        """Test validation error for days_back above 1095."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            payload = {"days_back": 1100}
            response = admin_client.post("/api/v1/testing/backtest", json=payload)
        assert response.status_code == 422

    def test_backtest_unauthorized(self, api_client, mock_validator):
        """Test unauthorized access without token."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            payload = {"days_back": 365}
            response = api_client.post("/api/v1/testing/backtest", json=payload)
        assert response.status_code == 401

    def test_backtest_requires_admin(self, authenticated_client, mock_validator):
        """Test backtest requires admin scope, not just property:read."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            payload = {"days_back": 365}
            response = authenticated_client.post("/api/v1/testing/backtest", json=payload)
        assert response.status_code == 403  # Forbidden - not admin

    # -------------------------------------------------------------------------
    # 4. PERFORMANCE STATUS (GET /performance/status) - 8 tests
    # -------------------------------------------------------------------------

    def test_performance_status_success(self, authenticated_client):
        """Test performance status endpoint returns 200."""
        mock_status = {
            "status": "healthy",
            "metrics": {
                "current_accuracy": 0.85,
                "accuracy_trend": "stable",
                "predictions_validated": 1000,
                "average_confidence": 0.80,
                "last_validation": "2024-12-25T10:00:00",
                "uptime_hours": 720
            },
            "alerts": []
        }
        with patch("backend_api.routers.testing.get_prediction_performance_status", return_value=mock_status):
            response = authenticated_client.get("/api/v1/testing/performance/status")
        assert response.status_code == 200

    def test_performance_status_response_structure(self, authenticated_client):
        """Test performance status response structure."""
        mock_status = {"status": "healthy", "metrics": {}, "alerts": []}
        with patch("backend_api.routers.testing.get_prediction_performance_status", return_value=mock_status):
            response = authenticated_client.get("/api/v1/testing/performance/status")
        data = response.json()
        assert "status" in data
        assert "alerts" in data

    def test_performance_status_with_alerts(self, authenticated_client):
        """Test performance status with alerts."""
        mock_status = {
            "status": "warning",
            "metrics": {"current_accuracy": 0.65},
            "alerts": ["Low accuracy detected", "Declining trend"]
        }
        with patch("backend_api.routers.testing.get_prediction_performance_status", return_value=mock_status):
            response = authenticated_client.get("/api/v1/testing/performance/status")
        data = response.json()
        assert len(data["alerts"]) == 2

    def test_performance_status_service_exception(self, authenticated_client):
        """Test 500 error when status retrieval fails."""
        with patch("backend_api.routers.testing.get_prediction_performance_status", side_effect=Exception("Status error")):
            response = authenticated_client.get("/api/v1/testing/performance/status")
        assert response.status_code == 500
        assert "Failed to retrieve performance status" in response.json()["detail"]

    def test_performance_status_unauthorized(self, api_client):
        """Test unauthorized access without token."""
        mock_status = {"status": "healthy", "metrics": {}, "alerts": []}
        with patch("backend_api.routers.testing.get_prediction_performance_status", return_value=mock_status):
            response = api_client.get("/api/v1/testing/performance/status")
        assert response.status_code == 401

    def test_performance_status_healthy(self, authenticated_client):
        """Test healthy status."""
        mock_status = {"status": "healthy", "metrics": {"current_accuracy": 0.90}, "alerts": []}
        with patch("backend_api.routers.testing.get_prediction_performance_status", return_value=mock_status):
            response = authenticated_client.get("/api/v1/testing/performance/status")
        assert response.json()["status"] == "healthy"

    def test_performance_status_warning(self, authenticated_client):
        """Test warning status."""
        mock_status = {"status": "warning", "metrics": {"current_accuracy": 0.65}, "alerts": ["Low accuracy"]}
        with patch("backend_api.routers.testing.get_prediction_performance_status", return_value=mock_status):
            response = authenticated_client.get("/api/v1/testing/performance/status")
        assert response.json()["status"] == "warning"

    def test_performance_status_uptime(self, authenticated_client):
        """Test uptime is returned."""
        mock_status = {"status": "healthy", "metrics": {"uptime_hours": 100}, "alerts": []}
        with patch("backend_api.routers.testing.get_prediction_performance_status", return_value=mock_status):
            response = authenticated_client.get("/api/v1/testing/performance/status")
        assert response.json()["uptime_hours"] == 100

    # -------------------------------------------------------------------------
    # 5. VALIDATION HISTORY (GET /validation/history) - 10 tests
    # -------------------------------------------------------------------------

    def test_validation_history_success(self, authenticated_client, mock_validator):
        """Test validation history retrieval."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = authenticated_client.get("/api/v1/testing/validation/history")
        assert response.status_code == 200

    def test_validation_history_response_structure(self, authenticated_client, mock_validator):
        """Test validation history response structure."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = authenticated_client.get("/api/v1/testing/validation/history")
        data = response.json()
        assert "validations" in data
        assert "total_count" in data
        assert "date_range" in data
        assert "performance_summary" in data

    def test_validation_history_with_days_param(self, authenticated_client, mock_validator):
        """Test validation history with days parameter."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = authenticated_client.get("/api/v1/testing/validation/history?days=7")
        assert response.status_code == 200

    def test_validation_history_days_too_low(self, authenticated_client, mock_validator):
        """Test validation error for days less than 1."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = authenticated_client.get("/api/v1/testing/validation/history?days=0")
        assert response.status_code == 422

    def test_validation_history_days_too_high(self, authenticated_client, mock_validator):
        """Test validation error for days greater than 365."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = authenticated_client.get("/api/v1/testing/validation/history?days=400")
        assert response.status_code == 422

    @pytest.mark.parametrize("days", [1, 30, 90, 180, 365])
    def test_validation_history_valid_days(self, authenticated_client, mock_validator, days):
        """Test valid days parameter values."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = authenticated_client.get(f"/api/v1/testing/validation/history?days={days}")
        assert response.status_code == 200

    def test_validation_history_empty(self, authenticated_client):
        """Test validation history when no data exists."""
        validator = MagicMock()
        validator.get_validation_history.return_value = []
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=validator):
            response = authenticated_client.get("/api/v1/testing/validation/history")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert data["validations"] == []

    def test_validation_history_service_exception(self, authenticated_client):
        """Test 500 error when history retrieval fails."""
        with patch("backend_api.routers.testing.get_prediction_validator", side_effect=Exception("History error")):
            response = authenticated_client.get("/api/v1/testing/validation/history")
        assert response.status_code == 500
        assert "Failed to retrieve validation history" in response.json()["detail"]

    def test_validation_history_unauthorized(self, api_client, mock_validator):
        """Test unauthorized access without token."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = api_client.get("/api/v1/testing/validation/history")
        assert response.status_code == 401

    # -------------------------------------------------------------------------
    # 6. PERFORMANCE METRICS (GET /performance/metrics) - 8 tests
    # -------------------------------------------------------------------------

    def test_performance_metrics_success(self, authenticated_client, mock_validator):
        """Test performance metrics retrieval."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = authenticated_client.get("/api/v1/testing/performance/metrics")
        assert response.status_code == 200

    def test_performance_metrics_response_structure(self, authenticated_client, mock_validator):
        """Test performance metrics response structure."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = authenticated_client.get("/api/v1/testing/performance/metrics")
        data = response.json()
        assert "status" in data
        assert "metrics" in data

    def test_performance_metrics_with_days_param(self, authenticated_client, mock_validator):
        """Test performance metrics with days parameter."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = authenticated_client.get("/api/v1/testing/performance/metrics?days=14")
        assert response.status_code == 200

    def test_performance_metrics_no_data(self, authenticated_client):
        """Test performance metrics when no data exists."""
        validator = MagicMock()
        validator.get_validation_history.return_value = []
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=validator):
            response = authenticated_client.get("/api/v1/testing/performance/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "no_data"

    def test_performance_metrics_service_exception(self, authenticated_client):
        """Test 500 error when metrics retrieval fails."""
        with patch("backend_api.routers.testing.get_prediction_validator", side_effect=Exception("Metrics error")):
            response = authenticated_client.get("/api/v1/testing/performance/metrics")
        assert response.status_code == 500
        assert "Failed to retrieve performance metrics" in response.json()["detail"]

    def test_performance_metrics_unauthorized(self, api_client, mock_validator):
        """Test unauthorized access without token."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = api_client.get("/api/v1/testing/performance/metrics")
        assert response.status_code == 401

    def test_performance_metrics_days_boundary_low(self, authenticated_client, mock_validator):
        """Test days parameter at minimum boundary."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = authenticated_client.get("/api/v1/testing/performance/metrics?days=1")
        assert response.status_code == 200

    def test_performance_metrics_days_boundary_high(self, authenticated_client, mock_validator):
        """Test days parameter at maximum boundary."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = authenticated_client.get("/api/v1/testing/performance/metrics?days=90")
        assert response.status_code == 200

    # -------------------------------------------------------------------------
    # 7. QUICK VALIDATION (POST /validate/quick) - 8 tests
    # -------------------------------------------------------------------------

    def test_quick_validation_success(self, authenticated_client):
        """Test quick validation endpoint."""
        mock_result = create_mock_validation_result()
        with patch("backend_api.routers.testing.validate_predictions_sample", return_value=mock_result):
            response = authenticated_client.post("/api/v1/testing/validate/quick")
        assert response.status_code == 200

    def test_quick_validation_response_structure(self, authenticated_client):
        """Test quick validation response structure."""
        mock_result = create_mock_validation_result()
        with patch("backend_api.routers.testing.validate_predictions_sample", return_value=mock_result):
            response = authenticated_client.post("/api/v1/testing/validate/quick")
        data = response.json()
        assert "status" in data
        assert "validation_type" in data
        assert "sample_size" in data
        assert "accuracy" in data

    def test_quick_validation_with_count(self, authenticated_client):
        """Test quick validation with property_count parameter."""
        mock_result = create_mock_validation_result()
        with patch("backend_api.routers.testing.validate_predictions_sample", return_value=mock_result):
            response = authenticated_client.post("/api/v1/testing/validate/quick?property_count=50")
        assert response.status_code == 200

    def test_quick_validation_count_too_low(self, authenticated_client):
        """Test validation error for property_count below 5."""
        mock_result = create_mock_validation_result()
        with patch("backend_api.routers.testing.validate_predictions_sample", return_value=mock_result):
            response = authenticated_client.post("/api/v1/testing/validate/quick?property_count=3")
        assert response.status_code == 422

    def test_quick_validation_count_too_high(self, authenticated_client):
        """Test validation error for property_count above 100."""
        mock_result = create_mock_validation_result()
        with patch("backend_api.routers.testing.validate_predictions_sample", return_value=mock_result):
            response = authenticated_client.post("/api/v1/testing/validate/quick?property_count=150")
        assert response.status_code == 422

    def test_quick_validation_service_exception(self, authenticated_client):
        """Test 500 error when quick validation fails."""
        with patch("backend_api.routers.testing.validate_predictions_sample", side_effect=Exception("Quick validation error")):
            response = authenticated_client.post("/api/v1/testing/validate/quick")
        assert response.status_code == 500
        assert "Failed to run quick validation" in response.json()["detail"]

    def test_quick_validation_unauthorized(self, api_client):
        """Test unauthorized access without token."""
        mock_result = create_mock_validation_result()
        with patch("backend_api.routers.testing.validate_predictions_sample", return_value=mock_result):
            response = api_client.post("/api/v1/testing/validate/quick")
        assert response.status_code == 401

    def test_quick_validation_completed_status(self, authenticated_client):
        """Test quick validation returns completed status."""
        mock_result = create_mock_validation_result()
        with patch("backend_api.routers.testing.validate_predictions_sample", return_value=mock_result):
            response = authenticated_client.post("/api/v1/testing/validate/quick")
        assert response.json()["status"] == "completed"

    # -------------------------------------------------------------------------
    # 8. ANALYTICS SUMMARY (GET /analytics/summary) - 8 tests (Admin only)
    # -------------------------------------------------------------------------

    def test_analytics_summary_success(self, admin_client, mock_validator):
        """Test analytics summary endpoint."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = admin_client.get("/api/v1/testing/analytics/summary")
        assert response.status_code == 200

    def test_analytics_summary_response_structure(self, admin_client, mock_validator):
        """Test analytics summary response structure."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = admin_client.get("/api/v1/testing/analytics/summary")
        data = response.json()
        assert "summary_generated" in data
        assert "system_statistics" in data
        assert "performance_trends" in data
        assert "operational_health" in data

    def test_analytics_summary_system_stats(self, admin_client, mock_validator):
        """Test analytics summary contains system statistics."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = admin_client.get("/api/v1/testing/analytics/summary")
        stats = response.json()["system_statistics"]
        assert "total_validations_30d" in stats
        assert "total_backtests" in stats

    def test_analytics_summary_service_exception(self, admin_client):
        """Test 500 error when analytics retrieval fails."""
        with patch("backend_api.routers.testing.get_prediction_validator", side_effect=Exception("Analytics error")):
            response = admin_client.get("/api/v1/testing/analytics/summary")
        assert response.status_code == 500
        assert "Failed to retrieve analytics summary" in response.json()["detail"]

    def test_analytics_summary_unauthorized(self, api_client, mock_validator):
        """Test unauthorized access without token."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = api_client.get("/api/v1/testing/analytics/summary")
        assert response.status_code == 401

    def test_analytics_summary_requires_admin(self, authenticated_client, mock_validator):
        """Test analytics summary requires admin scope."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = authenticated_client.get("/api/v1/testing/analytics/summary")
        assert response.status_code == 403  # Forbidden - not admin

    def test_analytics_summary_performance_trends(self, admin_client, mock_validator):
        """Test analytics summary contains performance trends."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = admin_client.get("/api/v1/testing/analytics/summary")
        trends = response.json()["performance_trends"]
        assert "accuracy_trend" in trends

    def test_analytics_summary_operational_health(self, admin_client, mock_validator):
        """Test analytics summary contains operational health."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = admin_client.get("/api/v1/testing/analytics/summary")
        health = response.json()["operational_health"]
        assert "status" in health

    # -------------------------------------------------------------------------
    # 9. CROSS-CUTTING AUTHENTICATION TESTS
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("endpoint,method", [
        ("/api/v1/testing/validate", "post"),
        ("/api/v1/testing/backtest", "post"),
        ("/api/v1/testing/performance/status", "get"),
        ("/api/v1/testing/validation/history", "get"),
        ("/api/v1/testing/performance/metrics", "get"),
        ("/api/v1/testing/validate/quick", "post"),
        ("/api/v1/testing/analytics/summary", "get"),
    ])
    def test_protected_endpoints_require_auth(self, api_client, mock_validator, endpoint, method):
        """Test all protected endpoints require authentication."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            with patch("backend_api.routers.testing.get_prediction_performance_status", return_value={"status": "ok", "metrics": {}, "alerts": []}):
                with patch("backend_api.routers.testing.validate_predictions_sample", return_value=create_mock_validation_result()):
                    if method == "post":
                        response = api_client.post(endpoint, json={})
                    else:
                        response = api_client.get(endpoint)
        assert response.status_code == 401

    def test_health_does_not_require_auth(self, api_client, mock_validator):
        """Test health endpoint does not require authentication."""
        with patch("backend_api.routers.testing.get_prediction_validator", return_value=mock_validator):
            response = api_client.get("/api/v1/testing/health")
        assert response.status_code == 200
