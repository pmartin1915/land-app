"""
Unit Tests for Prediction Accuracy Validation System
Alabama Auction Watcher - AI Testing Framework

Tests for the prediction accuracy validator, backtesting functionality,
and performance monitoring systems.

Author: Claude Code AI Assistant
Date: 2025-09-20
Version: 1.0.0
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, patch, MagicMock
import tempfile
import sqlite3

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.prediction_accuracy_validator import (
    PredictionAccuracyValidator,
    ValidationResult,
    BacktestResult,
    ValidationStatus,
    ValidationMetricType,
    get_prediction_validator,
    validate_predictions_sample,
    run_prediction_backtest,
    get_prediction_performance_status
)

from scripts.predictive_market_engine import (
    PropertyAppreciationForecast,
    MarketTimingAnalysis,
    PredictionConfidence,
    MarketTrend
)


class TestPredictionAccuracyValidator:
    """Test class for PredictionAccuracyValidator functionality."""

    @pytest.fixture
    def temp_database(self):
        """Create a temporary database for testing."""
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        yield temp_db.name
        Path(temp_db.name).unlink(missing_ok=True)

    @pytest.fixture
    def validator(self, temp_database):
        """Create a validator instance with temporary database."""
        return PredictionAccuracyValidator(database_path=temp_database)

    @pytest.fixture
    def sample_properties(self):
        """Create sample property data for testing."""
        return [
            {
                "id": "test_1",
                "county": "Mobile",
                "amount": 100.0,
                "acreage": 2.0,
                "price_per_acre": 50.0,
                "investment_score": 75.0,
                "water_score": 0.0,
                "description": "Test property 1"
            },
            {
                "id": "test_2",
                "county": "Baldwin",
                "amount": 500.0,
                "acreage": 5.0,
                "price_per_acre": 100.0,
                "investment_score": 85.0,
                "water_score": 3.0,
                "description": "Test property 2 with water access"
            },
            {
                "id": "test_3",
                "county": "Jefferson",
                "amount": 200.0,
                "acreage": 1.5,
                "price_per_acre": 133.33,
                "investment_score": 60.0,
                "water_score": 0.0,
                "description": "Test property 3"
            }
        ]

    @pytest.fixture
    def mock_forecast(self):
        """Create a mock prediction forecast."""
        return PropertyAppreciationForecast(
            one_year_appreciation=0.04,
            three_year_appreciation=0.12,
            five_year_appreciation=0.20,
            confidence_level=PredictionConfidence.HIGH,
            market_trend=MarketTrend.GROWTH,
            risk_score=0.3,
            county_growth_factor=0.02,
            economic_factor=0.015,
            geographic_factor=0.01,
            market_timing_factor=0.005,
            property_specific_factor=0.01
        )

    def test_validator_initialization(self, validator):
        """Test validator initialization and database setup."""
        assert validator is not None
        assert validator.predictive_engine is not None
        assert validator.validation_results == []
        assert validator.backtest_results == []

        # Test database tables are created
        with sqlite3.connect(validator.database_path) as conn:
            cursor = conn.cursor()

            # Check validation results table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prediction_validation_results'")
            assert cursor.fetchone() is not None

            # Check backtest results table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prediction_backtest_results'")
            assert cursor.fetchone() is not None

            # Check prediction tracking table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prediction_tracking'")
            assert cursor.fetchone() is not None

    def test_validation_status_determination(self, validator):
        """Test validation status determination logic."""
        assert validator._determine_validation_status(0.95) == ValidationStatus.EXCELLENT
        assert validator._determine_validation_status(0.85) == ValidationStatus.GOOD
        assert validator._determine_validation_status(0.75) == ValidationStatus.ACCEPTABLE
        assert validator._determine_validation_status(0.65) == ValidationStatus.POOR
        assert validator._determine_validation_status(0.45) == ValidationStatus.CRITICAL

    @patch('scripts.prediction_accuracy_validator.get_predictive_engine')
    def test_validate_current_predictions_success(self, mock_engine, validator, sample_properties, mock_forecast):
        """Test successful validation of current predictions."""
        # Mock the predictive engine
        mock_engine_instance = Mock()
        mock_engine_instance.predict_property_appreciation.return_value = mock_forecast
        mock_engine.return_value = mock_engine_instance
        validator.predictive_engine = mock_engine_instance

        # Run validation
        result = validator.validate_current_predictions(sample_properties, "test_period")

        # Verify results
        assert isinstance(result, ValidationResult)
        assert result.total_predictions == len(sample_properties)
        assert result.successful_predictions > 0
        assert result.validation_period == "test_period"
        assert result.prediction_horizon == "3_year"
        assert 0.0 <= result.accuracy_score <= 1.0
        assert 0.0 <= result.precision_score <= 1.0
        assert 0.0 <= result.recall_score <= 1.0
        assert result.validation_status in ValidationStatus

        # Verify predictive engine was called correctly
        assert mock_engine_instance.predict_property_appreciation.call_count == len(sample_properties)

    def test_validate_current_predictions_empty_input(self, validator):
        """Test validation with empty property list."""
        result = validator.validate_current_predictions([], "empty_test")

        assert isinstance(result, ValidationResult)
        assert result.total_predictions == 0
        assert result.successful_predictions == 0
        assert result.failed_predictions == 0
        assert result.accuracy_score == 0.0

    @patch('scripts.prediction_accuracy_validator.get_predictive_engine')
    def test_validate_current_predictions_with_failures(self, mock_engine, validator, sample_properties):
        """Test validation with some prediction failures."""
        # Mock the predictive engine to fail on some properties
        mock_engine_instance = Mock()

        def side_effect(prop, county, score):
            if prop["id"] == "test_2":
                raise Exception("Prediction failed")
            return PropertyAppreciationForecast()

        mock_engine_instance.predict_property_appreciation.side_effect = side_effect
        mock_engine.return_value = mock_engine_instance
        validator.predictive_engine = mock_engine_instance

        result = validator.validate_current_predictions(sample_properties, "failure_test")

        assert result.total_predictions == len(sample_properties)
        assert result.successful_predictions == 2  # Only 2 should succeed
        assert result.failed_predictions == 1

    def test_single_prediction_validation(self, validator, mock_forecast):
        """Test validation of a single prediction."""
        pred_data = {
            "forecast": mock_forecast,
            "property": {
                "investment_score": 80,
                "price_per_acre": 100
            },
            "county": "Mobile"
        }

        result = validator._validate_single_prediction(pred_data)

        assert isinstance(result, dict)
        assert "accuracy" in result
        assert "confidence" in result
        assert "error" in result
        assert 0.0 <= result["accuracy"] <= 1.0
        # Confidence should be numeric conversion of the enum
        expected_confidence = {
            "very_high": 0.95,
            "high": 0.85,
            "medium": 0.70,
            "low": 0.55
        }.get(mock_forecast.confidence_level.value, 0.70)
        assert result["confidence"] == expected_confidence

    def test_confidence_calibration_calculation(self, validator, sample_properties, mock_forecast):
        """Test confidence calibration calculation."""
        # Create predictions with known confidence levels
        predictions = []
        for prop in sample_properties:
            predictions.append({
                "forecast": mock_forecast,
                "property": prop
            })

        calibration = validator._calculate_confidence_calibration(predictions)

        assert isinstance(calibration, float)
        assert 0.0 <= calibration <= 1.0

    def test_accuracy_trend_calculation(self, validator):
        """Test accuracy trend calculation."""
        # Create validation results with different accuracies
        results = [
            ValidationResult(accuracy_score=0.85),  # Most recent
            ValidationResult(accuracy_score=0.80),
            ValidationResult(accuracy_score=0.75),
            ValidationResult(accuracy_score=0.70)   # Oldest
        ]

        # Test improving trend
        trend = validator._calculate_accuracy_trend(results)
        assert trend in ["improving", "declining", "stable"]

        # Test single result
        single_result_trend = validator._calculate_accuracy_trend([results[0]])
        assert single_result_trend == "stable"

    def test_performance_alerts_check(self, validator):
        """Test performance alerts generation."""
        # Test with good metrics
        good_metrics = {
            "current_accuracy": 0.85,
            "accuracy_trend": "stable",
            "confidence_performance": {"high": 0.9, "medium": 0.8, "low": 0.7}
        }
        alerts = validator._check_performance_alerts(good_metrics)
        assert len(alerts) == 0

        # Test with poor metrics
        poor_metrics = {
            "current_accuracy": 0.65,  # Below threshold
            "accuracy_trend": "declining",
            "confidence_performance": {"high": 0.7, "medium": 0.6, "low": 0.5}
        }
        alerts = validator._check_performance_alerts(poor_metrics)
        assert len(alerts) > 0
        assert any("below threshold" in alert for alert in alerts)
        assert any("declining" in alert for alert in alerts)

    @patch('scripts.prediction_accuracy_validator.get_predictive_engine')
    def test_run_backtest(self, mock_engine, validator, mock_forecast):
        """Test backtesting functionality."""
        # Mock the predictive engine
        mock_engine_instance = Mock()
        mock_engine_instance.predict_property_appreciation.return_value = mock_forecast
        mock_engine.return_value = mock_engine_instance
        validator.predictive_engine = mock_engine_instance

        # Mock historical data loading
        with patch.object(validator, '_load_historical_data') as mock_load:
            mock_load.return_value = [
                {"id": "hist_1", "county": "Mobile", "investment_score": 75},
                {"id": "hist_2", "county": "Baldwin", "investment_score": 80},
            ]

            # Run backtest
            start_date = datetime.now() - timedelta(days=365)
            end_date = datetime.now()
            result = validator.run_backtest(start_date, end_date, 12)

            # Verify results
            assert isinstance(result, BacktestResult)
            assert result.start_date == start_date
            assert result.end_date == end_date
            assert result.prediction_horizon_months == 12
            assert 0.0 <= result.overall_accuracy <= 1.0
            assert 0.0 <= result.market_trend_accuracy <= 1.0
            assert result.execution_time_seconds >= 0

    def test_run_backtest_no_data(self, validator):
        """Test backtest with no historical data."""
        with patch.object(validator, '_load_historical_data') as mock_load:
            mock_load.return_value = []

            start_date = datetime.now() - timedelta(days=365)
            end_date = datetime.now()
            result = validator.run_backtest(start_date, end_date, 12)

            assert result.test_properties_count == 0
            assert result.overall_accuracy == 0.0

    def test_monitor_prediction_performance(self, validator):
        """Test performance monitoring."""
        # Add some validation results
        validator.validation_results = [
            ValidationResult(
                accuracy_score=0.85,
                validation_status=ValidationStatus.GOOD,
                total_predictions=50,
                successful_predictions=45,
                average_confidence=0.8
            ),
            ValidationResult(
                accuracy_score=0.82,
                validation_status=ValidationStatus.GOOD,
                total_predictions=40,
                successful_predictions=38,
                average_confidence=0.75
            )
        ]

        performance = validator.monitor_prediction_performance()

        assert isinstance(performance, dict)
        assert "status" in performance
        assert "metrics" in performance or "message" in performance

        if "metrics" in performance:
            metrics = performance["metrics"]
            assert "current_accuracy" in metrics
            assert "accuracy_trend" in metrics

    def test_validation_result_storage(self, validator):
        """Test storing validation results in database."""
        result = ValidationResult(
            accuracy_score=0.85,
            precision_score=0.80,
            recall_score=0.75,
            mean_absolute_error=0.05,
            confidence_calibration=0.82,
            validation_status=ValidationStatus.GOOD,
            total_predictions=100,
            successful_predictions=95,
            failed_predictions=5,
            validation_period="test_storage",
            prediction_horizon="3_year",
            model_version="1.0.0"
        )

        # Store result
        validator._store_validation_result(result)

        # Verify storage
        with sqlite3.connect(validator.database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM prediction_validation_results")
            count = cursor.fetchone()[0]
            assert count == 1

            cursor.execute("SELECT * FROM prediction_validation_results ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            assert row is not None
            assert row[2] == 0.85  # accuracy_score

    def test_backtest_result_storage(self, validator):
        """Test storing backtest results in database."""
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now()

        result = BacktestResult(
            start_date=start_date,
            end_date=end_date,
            prediction_horizon_months=12,
            test_properties_count=50,
            overall_accuracy=0.78,
            market_trend_accuracy=0.82,
            appreciation_mae=0.03,
            appreciation_rmse=0.05,
            high_confidence_accuracy=0.85,
            medium_confidence_accuracy=0.75,
            low_confidence_accuracy=0.65,
            execution_time_seconds=45.2
        )

        # Store result
        validator._store_backtest_result(result)

        # Verify storage
        with sqlite3.connect(validator.database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM prediction_backtest_results")
            count = cursor.fetchone()[0]
            assert count == 1

            cursor.execute("SELECT * FROM prediction_backtest_results ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            assert row is not None
            assert row[5] == 0.78  # overall_accuracy

    def test_get_validation_history(self, validator):
        """Test retrieving validation history."""
        # Store some validation results first
        for i in range(5):
            result = ValidationResult(
                accuracy_score=0.8 + (i * 0.02),
                validation_status=ValidationStatus.GOOD,
                total_predictions=50,
                successful_predictions=45,
                validation_timestamp=datetime.now() - timedelta(days=i)
            )
            validator._store_validation_result(result)

        # Retrieve history
        history = validator.get_validation_history(days=7)

        assert isinstance(history, list)
        assert len(history) == 5
        assert all(isinstance(result, ValidationResult) for result in history)

        # Check ordering (most recent first)
        timestamps = [result.validation_timestamp for result in history]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_historical_data_loading(self, validator):
        """Test historical data loading functionality."""
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now()

        # Test with empty database
        historical_data = validator._load_historical_data(start_date, end_date)
        assert isinstance(historical_data, list)

    def test_historical_prediction_validation(self, validator):
        """Test historical prediction validation."""
        pred_data = {
            "forecast": PropertyAppreciationForecast(three_year_appreciation=0.12),
            "property": {"investment_score": 75},
            "prediction_date": datetime.now() - timedelta(days=365),
            "validation_date": datetime.now()
        }

        validation_data = [{"id": "val_1", "county": "Mobile"}]

        result = validator._validate_historical_prediction(pred_data, validation_data)

        assert isinstance(result, dict)
        assert "accuracy" in result
        assert "trend_accuracy" in result
        assert "appreciation_error" in result


class TestConvenienceFunctions:
    """Test convenience functions for validation system."""

    @patch('scripts.prediction_accuracy_validator.get_prediction_validator')
    def test_validate_predictions_sample(self, mock_get_validator):
        """Test the convenience function for validating predictions."""
        mock_validator = Mock()
        mock_result = ValidationResult(accuracy_score=0.85)
        mock_validator.validate_current_predictions.return_value = mock_result
        mock_get_validator.return_value = mock_validator

        sample_properties = [{"id": "test_1", "county": "Mobile"}]
        result = validate_predictions_sample(sample_properties)

        assert result == mock_result
        mock_validator.validate_current_predictions.assert_called_once_with(sample_properties)

    @patch('scripts.prediction_accuracy_validator.get_prediction_validator')
    def test_run_prediction_backtest(self, mock_get_validator):
        """Test the convenience function for running backtests."""
        mock_validator = Mock()
        mock_result = BacktestResult(
            start_date=datetime.now() - timedelta(days=365),
            end_date=datetime.now(),
            prediction_horizon_months=12,
            test_properties_count=50
        )
        mock_validator.run_backtest.return_value = mock_result
        mock_get_validator.return_value = mock_validator

        result = run_prediction_backtest(days_back=365, horizon_months=12)

        assert result == mock_result
        mock_validator.run_backtest.assert_called_once()

    @patch('scripts.prediction_accuracy_validator.get_prediction_validator')
    def test_get_prediction_performance_status(self, mock_get_validator):
        """Test the convenience function for getting performance status."""
        mock_validator = Mock()
        mock_status = {"status": "healthy", "metrics": {}}
        mock_validator.monitor_prediction_performance.return_value = mock_status
        mock_get_validator.return_value = mock_validator

        result = get_prediction_performance_status()

        assert result == mock_status
        mock_validator.monitor_prediction_performance.assert_called_once()

    def test_get_prediction_validator_singleton(self):
        """Test that get_prediction_validator returns consistent instance."""
        validator1 = get_prediction_validator()
        validator2 = get_prediction_validator()

        assert validator1 is validator2  # Should be the same instance


class TestValidationResultDataClass:
    """Test ValidationResult data class functionality."""

    def test_validation_result_creation(self):
        """Test creating ValidationResult instances."""
        result = ValidationResult(
            accuracy_score=0.85,
            precision_score=0.80,
            total_predictions=100
        )

        assert result.accuracy_score == 0.85
        assert result.precision_score == 0.80
        assert result.total_predictions == 100
        assert result.validation_status == ValidationStatus.ACCEPTABLE  # Default
        assert isinstance(result.validation_timestamp, datetime)

    def test_validation_result_defaults(self):
        """Test default values in ValidationResult."""
        result = ValidationResult()

        assert result.accuracy_score == 0.0
        assert result.validation_status == ValidationStatus.ACCEPTABLE
        assert result.error_patterns == {}
        assert result.county_performance == {}
        assert isinstance(result.validation_timestamp, datetime)


class TestBacktestResultDataClass:
    """Test BacktestResult data class functionality."""

    def test_backtest_result_creation(self):
        """Test creating BacktestResult instances."""
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now()

        result = BacktestResult(
            start_date=start_date,
            end_date=end_date,
            prediction_horizon_months=12,
            test_properties_count=50,
            overall_accuracy=0.85
        )

        assert result.start_date == start_date
        assert result.end_date == end_date
        assert result.prediction_horizon_months == 12
        assert result.test_properties_count == 50
        assert result.overall_accuracy == 0.85
        assert isinstance(result.backtest_timestamp, datetime)

    def test_backtest_result_defaults(self):
        """Test default values in BacktestResult."""
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now()

        result = BacktestResult(
            start_date=start_date,
            end_date=end_date,
            prediction_horizon_months=12,
            test_properties_count=0
        )

        assert result.overall_accuracy == 0.0
        assert result.county_results == {}
        assert result.price_tier_results == {}
        assert isinstance(result.backtest_timestamp, datetime)


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"])