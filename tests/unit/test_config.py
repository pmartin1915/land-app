"""
Comprehensive unit tests for config modules in Alabama Auction Watcher.

Tests all configuration modules including settings, logging_config, ai_logging, and ai_diagnostics.
Provides AI-testable infrastructure with performance benchmarks and integration scenarios.

Coverage targets:
- config/settings.py (176 lines)
- config/logging_config.py (186 lines)
- config/ai_logging.py (625 lines)
- config/ai_diagnostics.py (1566 lines)
Total: 2553 lines across 4 modules
"""

import pytest
import json
import time
import logging
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from dataclasses import asdict
from typing import Dict, Any

import config.settings as settings
import config.logging_config as logging_config
from config.ai_logging import (
    LogLevel, LogCategory, LogContext, PerformanceMetrics, ErrorMetrics,
    AIJSONFormatter, AILoggerAdapter, AILogAnalyzer, AILoggingManager,
    get_ai_logger, setup_ai_logging, ai_operation_context
)
from config.ai_diagnostics import (
    SystemComponent, HealthStatus, DiagnosticSeverity, HealthMetrics,
    DiagnosticAlert, AIHealthChecker
)


class TestConfigSettings:
    """Test config/settings.py constants and configurations."""

    def test_filtering_defaults_exist(self):
        """Test filtering default constants are properly defined."""
        assert hasattr(settings, 'MIN_ACRES')
        assert hasattr(settings, 'MAX_ACRES')
        assert hasattr(settings, 'MAX_PRICE')
        assert settings.MIN_ACRES == 1.0
        assert settings.MAX_ACRES == 5.0
        assert settings.MAX_PRICE == 20000.0

    def test_fee_calculation_settings(self):
        """Test fee calculation settings are properly configured."""
        assert settings.RECORDING_FEE == 35.0
        assert settings.COUNTY_FEE_PERCENT == 0.05
        assert settings.MISC_FEES == 100.0

    def test_water_feature_keywords_structure(self):
        """Test water feature keywords are properly structured."""
        assert isinstance(settings.PRIMARY_WATER_KEYWORDS, list)
        assert isinstance(settings.SECONDARY_WATER_KEYWORDS, list)
        assert isinstance(settings.TERTIARY_WATER_KEYWORDS, list)

        assert 'creek' in settings.PRIMARY_WATER_KEYWORDS
        assert 'stream' in settings.PRIMARY_WATER_KEYWORDS
        assert 'branch' in settings.SECONDARY_WATER_KEYWORDS
        assert 'water' in settings.TERTIARY_WATER_KEYWORDS

    def test_water_score_weights(self):
        """Test water score weights are properly configured."""
        assert settings.WATER_SCORE_WEIGHTS['primary'] == 3.0
        assert settings.WATER_SCORE_WEIGHTS['secondary'] == 2.0
        assert settings.WATER_SCORE_WEIGHTS['tertiary'] == 1.0

    def test_column_mappings_structure(self):
        """Test column mappings are properly structured."""
        required_fields = ['parcel_id', 'amount', 'assessed_value', 'description',
                          'acreage', 'year_sold', 'owner_name', 'county']

        for field in required_fields:
            assert field in settings.COLUMN_MAPPINGS
            assert isinstance(settings.COLUMN_MAPPINGS[field], list)
            assert len(settings.COLUMN_MAPPINGS[field]) > 0

    def test_investment_score_weights_sum(self):
        """Test investment score weights sum appropriately."""
        total_weight = sum(settings.INVESTMENT_SCORE_WEIGHTS.values())
        assert abs(total_weight - 1.0) < 0.001

    def test_acreage_patterns_structure(self):
        """Test acreage parsing patterns are properly defined."""
        pattern_types = ['direct_acres', 'square_feet', 'rectangular', 'fractional']

        for pattern_type in pattern_types:
            assert pattern_type in settings.ACREAGE_PATTERNS
            assert isinstance(settings.ACREAGE_PATTERNS[pattern_type], str)

    def test_output_columns_order(self):
        """Test output columns are in expected order."""
        expected_first_columns = ['parcel_id', 'county', 'amount', 'acreage']

        for i, column in enumerate(expected_first_columns):
            assert settings.OUTPUT_COLUMNS[i] == column

    def test_validation_rules_sanity(self):
        """Test validation rules have sensible values."""
        assert settings.MIN_REASONABLE_PRICE < settings.MAX_REASONABLE_PRICE
        assert settings.MIN_REASONABLE_ACRES < settings.MAX_REASONABLE_ACRES
        assert settings.MIN_REASONABLE_PRICE > 0
        assert settings.MIN_REASONABLE_ACRES > 0

    def test_chart_colors_format(self):
        """Test chart colors are properly formatted hex values."""
        for color_name, color_value in settings.CHART_COLORS.items():
            assert color_value.startswith('#')
            assert len(color_value) == 7


class TestLoggingConfig:
    """Test config/logging_config.py logging functionality."""

    def test_log_levels_mapping(self):
        """Test log levels are properly mapped."""
        assert logging_config.LOG_LEVELS['DEBUG'] == logging.DEBUG
        assert logging_config.LOG_LEVELS['INFO'] == logging.INFO
        assert logging_config.LOG_LEVELS['WARNING'] == logging.WARNING
        assert logging_config.LOG_LEVELS['ERROR'] == logging.ERROR
        assert logging_config.LOG_LEVELS['CRITICAL'] == logging.CRITICAL

    def test_setup_logging_console_only(self):
        """Test logging setup with console output only."""
        logger = logging_config.setup_logging(
            log_level='INFO',
            console_output=True,
            log_file=None
        )

        assert isinstance(logger, logging.Logger)
        assert logger.level == logging.INFO
        assert len(logger.handlers) >= 1

    def test_setup_logging_with_file(self):
        """Test logging setup with file output."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            logger = logging_config.setup_logging(
                log_level='DEBUG',
                log_file=tmp_file.name,
                console_output=False
            )

            assert isinstance(logger, logging.Logger)
            assert logger.level == logging.DEBUG

        os.unlink(tmp_file.name)

    def test_get_logger_returns_logger(self):
        """Test get_logger returns proper logger instance."""
        logger = logging_config.get_logger('test_module')
        assert isinstance(logger, logging.Logger)
        assert logger.name == 'test_module'

    def test_log_performance_formatting(self):
        """Test performance logging formats correctly."""
        logger = MagicMock()

        logging_config.log_performance(logger, "test_operation", 1.5, 100)

        logger.info.assert_called_once()
        call_args = logger.info.call_args[0][0]
        assert "PERFORMANCE" in call_args
        assert "test_operation" in call_args
        assert "1.50s" in call_args
        assert "100" in call_args

    def test_log_scraping_metrics_formatting(self):
        """Test scraping metrics logging formats correctly."""
        logger = MagicMock()

        logging_config.log_scraping_metrics(logger, "Baldwin", 10, 250, 30.5, 2)

        logger.info.assert_called_once()
        call_args = logger.info.call_args[0][0]
        assert "SCRAPING_METRICS" in call_args
        assert "Baldwin" in call_args
        assert "Pages=10" in call_args
        assert "Records=250" in call_args

    def test_log_processing_metrics_formatting(self):
        """Test processing metrics logging formats correctly."""
        logger = MagicMock()

        logging_config.log_processing_metrics(logger, "filter_properties", 1000, 850, 5.2)

        logger.info.assert_called_once()
        call_args = logger.info.call_args[0][0]
        assert "PROCESSING_METRICS" in call_args
        assert "filter_properties" in call_args
        assert "Input=1000" in call_args
        assert "Output=850" in call_args
        assert "85.0%" in call_args

    def test_log_error_with_context_formatting(self):
        """Test error logging with context formats correctly."""
        logger = MagicMock()

        error = ValueError("Test error")
        logging_config.log_error_with_context(
            logger, error, "processing data",
            county="Baldwin", records=100
        )

        logger.error.assert_called_once()
        call_args = logger.error.call_args[0][0]
        assert "ERROR" in call_args
        assert "processing data" in call_args
        assert "ValueError" in call_args
        assert "county=Baldwin" in call_args

    @patch.dict(os.environ, {
        'LOG_LEVEL': 'DEBUG',
        'LOG_FILE': '/tmp/test.log',
        'LOG_DETAILED': 'true'
    })
    def test_setup_environment_logging(self):
        """Test environment-based logging setup."""
        with patch('config.logging_config.setup_logging') as mock_setup:
            logging_config.setup_environment_logging()

            mock_setup.assert_called_once_with(
                log_level='DEBUG',
                log_file='/tmp/test.log',
                detailed_format=True
            )


class TestAILogging:
    """Test config/ai_logging.py AI-friendly logging functionality."""

    def test_log_level_enum_values(self):
        """Test LogLevel enum has correct values."""
        assert LogLevel.DEBUG.value == "debug"
        assert LogLevel.INFO.value == "info"
        assert LogLevel.WARNING.value == "warning"
        assert LogLevel.ERROR.value == "error"
        assert LogLevel.CRITICAL.value == "critical"

    def test_log_category_enum_values(self):
        """Test LogCategory enum has expected categories."""
        expected_categories = [
            "performance", "error", "business", "security",
            "system", "user_action", "external_service", "data_flow"
        ]

        for category in expected_categories:
            assert any(cat.value == category for cat in LogCategory)

    def test_log_context_creation(self):
        """Test LogContext creation and serialization."""
        context = LogContext(
            timestamp=time.time(),
            correlation_id="test-123",
            operation="test_operation",
            component="test_component"
        )

        assert context.correlation_id == "test-123"
        assert context.operation == "test_operation"
        assert context.component == "test_component"

        context_dict = context.to_dict()
        assert isinstance(context_dict, dict)
        assert context_dict['correlation_id'] == "test-123"

    def test_performance_metrics_creation(self):
        """Test PerformanceMetrics creation and serialization."""
        metrics = PerformanceMetrics(
            operation="parse_csv",
            duration_ms=150.5,
            records_processed=1000,
            records_per_second=6.6
        )

        assert metrics.operation == "parse_csv"
        assert metrics.duration_ms == 150.5
        assert metrics.records_processed == 1000

        metrics_dict = metrics.to_dict()
        assert isinstance(metrics_dict, dict)
        assert metrics_dict['operation'] == "parse_csv"

    def test_error_metrics_creation(self):
        """Test ErrorMetrics creation and defaults."""
        metrics = ErrorMetrics(
            error_type="ValueError",
            error_category="data_validation",
            severity="high"
        )

        assert metrics.error_type == "ValueError"
        assert metrics.error_category == "data_validation"
        assert metrics.severity == "high"
        assert metrics.related_errors == []

    def test_ai_json_formatter_basic_formatting(self):
        """Test AIJSONFormatter basic log formatting."""
        formatter = AIJSONFormatter()

        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=100,
            msg="Test message",
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data['level'] == 'info'
        assert log_data['message'] == 'Test message'
        assert log_data['logger'] == 'test_logger'
        assert 'correlation_id' in log_data
        assert 'ai_analysis' in log_data

    def test_ai_json_formatter_auto_category_detection(self):
        """Test AIJSONFormatter auto-detects categories correctly."""
        formatter = AIJSONFormatter()

        test_cases = [
            ("Performance metrics: duration 150ms", "performance"),
            ("User clicked submit button", "user_action"),
            ("HTTP request to external API", "external_service"),
            ("Processing CSV data", "data_flow"),
            ("System startup complete", "system")
        ]

        for message, expected_category in test_cases:
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="test.py",
                lineno=1, msg=message, args=(), exc_info=None
            )

            formatted = formatter.format(record)
            log_data = json.loads(formatted)
            assert log_data['category'] == expected_category

    def test_ai_logger_adapter_correlation_id(self):
        """Test AILoggerAdapter adds correlation ID."""
        base_logger = logging.getLogger('test')
        adapter = AILoggerAdapter(base_logger)

        assert hasattr(adapter, 'correlation_id')
        assert len(adapter.correlation_id) > 0

    def test_ai_logger_adapter_log_performance(self):
        """Test AILoggerAdapter performance logging."""
        base_logger = MagicMock()
        adapter = AILoggerAdapter(base_logger)

        adapter.log_performance("test_op", 100.5, records_processed=50)

        base_logger.info.assert_called_once()
        call_args = base_logger.info.call_args
        assert "Performance: test_op completed" in call_args[0][0]
        assert 'extra' in call_args[1]

    def test_ai_log_analyzer_error_pattern_detection(self):
        """Test AILogAnalyzer detects error patterns."""
        analyzer = AILogAnalyzer()

        log_entry = {
            "level": "error",
            "exception": {"type": "ValueError"},
            "message": "Test error message"
        }

        analysis = analyzer.analyze_log_entry(log_entry)

        assert 'alerts' in analysis
        assert 'insights' in analysis
        assert 'recommendations' in analysis

    def test_ai_log_analyzer_performance_anomaly_detection(self):
        """Test AILogAnalyzer detects performance anomalies."""
        analyzer = AILogAnalyzer()

        # Establish baseline
        normal_entry = {
            "category": "performance",
            "performance_metrics": {
                "operation": "test_op",
                "duration_ms": 100
            }
        }
        analyzer.analyze_log_entry(normal_entry)

        # Test anomaly detection
        slow_entry = {
            "category": "performance",
            "performance_metrics": {
                "operation": "test_op",
                "duration_ms": 500
            }
        }
        analysis = analyzer.analyze_log_entry(slow_entry)

        assert any(alert['type'] == 'performance_degradation' for alert in analysis.get('alerts', []))

    def test_ai_logging_manager_initialization(self):
        """Test AILoggingManager initialization."""
        config = {'console_output': True, 'json_log_file': 'test.jsonl'}
        manager = AILoggingManager(config)

        assert manager.config == config
        assert isinstance(manager.analyzer, AILogAnalyzer)
        assert isinstance(manager.loggers, dict)

    def test_ai_logging_manager_get_logger(self):
        """Test AILoggingManager logger creation."""
        manager = AILoggingManager()
        logger = manager.get_logger('test_component', operation='test')

        assert isinstance(logger, AILoggerAdapter)
        assert 'test_component' in manager.loggers

    def test_ai_operation_context_manager(self):
        """Test AI operation context manager functionality."""
        with patch('config.ai_logging._ai_logging_manager') as mock_manager:
            mock_logger = MagicMock()
            mock_manager.operation_context.return_value.__enter__.return_value = mock_logger

            with ai_operation_context("test_operation") as logger:
                assert logger == mock_logger

    def test_get_ai_logger_global_instance(self):
        """Test get_ai_logger creates global manager instance."""
        logger = get_ai_logger('test_module')
        assert isinstance(logger, AILoggerAdapter)

    def test_setup_ai_logging_configuration(self):
        """Test setup_ai_logging with custom configuration."""
        config = {'console_output': False, 'json_log_file': 'custom.jsonl'}
        manager = setup_ai_logging(config)

        assert isinstance(manager, AILoggingManager)
        assert manager.config == config


class TestAIDiagnostics:
    """Test config/ai_diagnostics.py diagnostic framework functionality."""

    def test_system_component_enum_values(self):
        """Test SystemComponent enum has expected components."""
        expected_components = [
            "web_scraper", "csv_parser", "data_processor", "file_system",
            "network", "memory", "cpu", "storage", "external_services", "logging_system"
        ]

        for component in expected_components:
            assert any(comp.value == component for comp in SystemComponent)

    def test_health_status_enum_values(self):
        """Test HealthStatus enum has expected statuses."""
        expected_statuses = ["healthy", "warning", "critical", "down", "unknown", "recovering"]

        for status in expected_statuses:
            assert any(stat.value == status for stat in HealthStatus)

    def test_diagnostic_severity_enum_values(self):
        """Test DiagnosticSeverity enum has expected levels."""
        expected_levels = ["info", "low", "medium", "high", "critical"]

        for level in expected_levels:
            assert any(sev.value == level for sev in DiagnosticSeverity)

    def test_health_metrics_creation(self):
        """Test HealthMetrics creation and serialization."""
        metrics = HealthMetrics(
            component="web_scraper",
            status=HealthStatus.HEALTHY,
            score=0.95,
            response_time_ms=150.5,
            success_rate=0.98
        )

        assert metrics.component == "web_scraper"
        assert metrics.status == HealthStatus.HEALTHY
        assert metrics.score == 0.95
        assert metrics.additional_metrics == {}

        metrics_dict = metrics.to_dict()
        assert metrics_dict['status'] == 'healthy'
        assert 'timestamp' in metrics_dict

    def test_diagnostic_alert_creation(self):
        """Test DiagnosticAlert creation and defaults."""
        alert = DiagnosticAlert(
            id="alert-123",
            component="cpu",
            severity=DiagnosticSeverity.HIGH,
            title="High CPU Usage",
            description="CPU usage exceeded threshold"
        )

        assert alert.id == "alert-123"
        assert alert.component == "cpu"
        assert alert.severity == DiagnosticSeverity.HIGH
        assert alert.recovery_instructions == []
        assert not alert.resolved

    def test_ai_health_checker_initialization(self):
        """Test AIHealthChecker initialization."""
        checker = AIHealthChecker()

        assert hasattr(checker, 'health_history')
        assert hasattr(checker, 'baseline_metrics')
        assert hasattr(checker, 'thresholds')
        assert hasattr(checker, 'recovery_strategies')

    def test_ai_health_checker_default_thresholds(self):
        """Test AIHealthChecker loads default thresholds correctly."""
        checker = AIHealthChecker()

        # Check web scraper thresholds
        web_scraper_thresholds = checker.thresholds[SystemComponent.WEB_SCRAPER.value]
        assert 'max_response_time_ms' in web_scraper_thresholds
        assert 'min_success_rate' in web_scraper_thresholds
        assert web_scraper_thresholds['max_response_time_ms'] == 30000
        assert web_scraper_thresholds['min_success_rate'] == 0.95

    def test_ai_health_checker_recovery_strategies(self):
        """Test AIHealthChecker initializes recovery strategies."""
        checker = AIHealthChecker()

        assert 'high_memory_usage' in checker.recovery_strategies
        assert 'network_failure' in checker.recovery_strategies

        memory_strategies = checker.recovery_strategies['high_memory_usage']
        assert len(memory_strategies) > 0
        assert all(hasattr(strategy, 'action') for strategy in memory_strategies)


class TestConfigIntegration:
    """Integration tests across config modules."""

    def test_logging_integration_with_ai_system(self):
        """Test logging config integrates with AI logging system."""
        # Setup traditional logging
        logger = logging_config.setup_logging('INFO', console_output=False)

        # Setup AI logging
        ai_logger = get_ai_logger('integration_test')

        # Verify both systems can coexist
        assert isinstance(logger, logging.Logger)
        assert isinstance(ai_logger, AILoggerAdapter)

    def test_settings_used_in_diagnostic_thresholds(self):
        """Test settings constants are compatible with diagnostic thresholds."""
        checker = AIHealthChecker()

        # Verify settings values are reasonable for diagnostic thresholds
        assert settings.MAX_REASONABLE_PRICE < 1000000  # Within diagnostic range
        assert settings.MIN_REASONABLE_ACRES > 0  # Positive values

        # Check that diagnostic thresholds exist for relevant components
        assert SystemComponent.WEB_SCRAPER.value in checker.thresholds
        assert SystemComponent.CSV_PARSER.value in checker.thresholds

    def test_ai_logging_with_diagnostic_framework(self):
        """Test AI logging integrates with diagnostic framework."""
        # Create AI logger
        logger = get_ai_logger('diagnostic_test')

        # Create health checker with logger
        checker = AIHealthChecker(logger=logger)

        # Verify integration
        assert checker.logger == logger
        assert hasattr(checker.logger, 'log_performance')
        assert hasattr(checker.logger, 'log_error_with_ai_context')

    @patch('time.time', return_value=1234567890.0)
    def test_cross_module_timestamp_consistency(self, mock_time):
        """Test timestamp consistency across modules."""
        # Create log context
        context = LogContext(
            timestamp=time.time(),
            correlation_id="test-123"
        )

        # Create health metrics
        metrics = HealthMetrics(
            component="test",
            status=HealthStatus.HEALTHY,
            score=1.0
        )

        # Verify timestamps are consistent
        context_dict = context.to_dict()
        metrics_dict = metrics.to_dict()

        assert context_dict['timestamp'] == metrics_dict['timestamp']


class TestConfigPerformance:
    """Performance benchmarks for config modules."""

    def test_settings_import_performance(self):
        """Test settings module import performance."""
        import importlib

        start_time = time.time()
        importlib.reload(settings)
        import_time = time.time() - start_time

        assert import_time < 0.1  # Should import quickly

    def test_ai_json_formatter_performance(self):
        """Test AIJSONFormatter performance with large log records."""
        formatter = AIJSONFormatter()

        # Create a log record with substantial data
        record = logging.LogRecord(
            name="performance_test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Performance test message with substantial content",
            args=(),
            exc_info=None
        )

        # Add extra data to test serialization performance
        record.large_data = list(range(1000))
        record.nested_dict = {f"key_{i}": f"value_{i}" for i in range(100)}

        start_time = time.time()
        formatted = formatter.format(record)
        format_time = time.time() - start_time

        assert format_time < 0.01  # Should format quickly
        assert len(formatted) > 0

        # Verify it's valid JSON
        parsed = json.loads(formatted)
        assert isinstance(parsed, dict)

    def test_health_checker_initialization_performance(self):
        """Test AIHealthChecker initialization performance."""
        start_time = time.time()
        checker = AIHealthChecker()
        init_time = time.time() - start_time

        assert init_time < 0.1  # Should initialize quickly
        assert len(checker.thresholds) > 0
        assert len(checker.recovery_strategies) > 0

    def test_ai_logging_manager_performance(self):
        """Test AILoggingManager performance with multiple loggers."""
        manager = AILoggingManager({'console_output': False})

        start_time = time.time()

        # Create multiple loggers
        loggers = []
        for i in range(100):
            logger = manager.get_logger(f'test_logger_{i}')
            loggers.append(logger)

        creation_time = time.time() - start_time

        assert creation_time < 0.5  # Should create loggers efficiently
        assert len(loggers) == 100
        assert len(manager.loggers) == 100


if __name__ == "__main__":
    # AI-testable performance benchmarks
    print("=== CONFIG MODULE TEST SPECIFICATIONS ===")
    print("Coverage targets:")
    print("- config/settings.py: 176 lines")
    print("- config/logging_config.py: 186 lines")
    print("- config/ai_logging.py: 625 lines")
    print("- config/ai_diagnostics.py: 1566 lines")
    print("Total: 2553 lines across 4 modules")
    print("\nPerformance requirements:")
    print("- Settings import: < 100ms")
    print("- AI JSON formatting: < 10ms per record")
    print("- Health checker init: < 100ms")
    print("- Logger creation: < 5ms per logger")
    print("\nIntegration requirements:")
    print("- Cross-module timestamp consistency")
    print("- Logging system interoperability")
    print("- Diagnostic framework integration")
    print("- Configuration value compatibility")