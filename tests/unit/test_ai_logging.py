"""
Tests for the AI-enhanced structured logging system.

These tests validate that the AI-friendly logging system produces properly
structured logs, performs accurate analysis, and provides actionable insights
for machine-readable error analysis.
"""

import json
import logging
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch
from io import StringIO

from config.ai_logging import (
    LogLevel, LogCategory, LogContext, PerformanceMetrics, ErrorMetrics,
    AIJSONFormatter, AILoggerAdapter, AILogAnalyzer, AILoggingManager,
    get_ai_logger, setup_ai_logging, ai_operation_context
)
from scripts.ai_exceptions import AIDataValidationError, ErrorCategory, ErrorSeverity


class TestLogDataStructures:
    """Test log data structure functionality."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_log_context_creation(self):
        """Test log context creation and serialization."""
        context = LogContext(
            timestamp=time.time(),
            correlation_id="test-123",
            operation="test_operation",
            component="test_component",
            user_id="user-456"
        )

        assert context.correlation_id == "test-123"
        assert context.operation == "test_operation"
        assert context.component == "test_component"
        assert context.user_id == "user-456"

        # Test serialization
        context_dict = context.to_dict()
        assert isinstance(context_dict, dict)
        assert context_dict["correlation_id"] == "test-123"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_performance_metrics_creation(self):
        """Test performance metrics creation and serialization."""
        metrics = PerformanceMetrics(
            operation="test_operation",
            duration_ms=123.45,
            memory_usage_mb=64.2,
            records_processed=100,
            records_per_second=45.6
        )

        assert metrics.operation == "test_operation"
        assert metrics.duration_ms == 123.45
        assert metrics.memory_usage_mb == 64.2
        assert metrics.records_processed == 100

        # Test serialization
        metrics_dict = metrics.to_dict()
        assert isinstance(metrics_dict, dict)
        assert metrics_dict["duration_ms"] == 123.45

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_error_metrics_creation(self):
        """Test error metrics creation and serialization."""
        metrics = ErrorMetrics(
            error_type="ValidationError",
            error_code="VAL_001",
            error_category="validation",
            severity="high",
            recoverable=True
        )

        assert metrics.error_type == "ValidationError"
        assert metrics.error_code == "VAL_001"
        assert metrics.severity == "high"
        assert metrics.recoverable is True

        # Test default initialization
        assert isinstance(metrics.related_errors, list)

        # Test serialization
        metrics_dict = metrics.to_dict()
        assert isinstance(metrics_dict, dict)
        assert metrics_dict["error_type"] == "ValidationError"


class TestAIJSONFormatter:
    """Test AI JSON formatter functionality."""

    @pytest.fixture
    def formatter(self):
        """Create AI JSON formatter for testing."""
        return AIJSONFormatter(include_extra_fields=True)

    @pytest.fixture
    def log_record(self):
        """Create a sample log record for testing."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.created = 1234567890.123
        record.module = "test_module"
        record.funcName = "test_function"
        record.thread = 123456
        record.threadName = "MainThread"
        record.process = 789
        return record

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_basic_json_formatting(self, formatter, log_record):
        """Test basic JSON log formatting."""
        formatted = formatter.format(log_record)
        log_data = json.loads(formatted)

        # Validate required fields
        assert log_data["timestamp"] == 1234567890.123
        assert log_data["level"] == "info"
        assert log_data["logger"] == "test.logger"
        assert log_data["message"] == "Test message"
        assert log_data["module"] == "test_module"
        assert log_data["function"] == "test_function"
        assert log_data["line"] == 123

        # Validate AI analysis fields
        assert "ai_analysis" in log_data
        assert "importance" in log_data["ai_analysis"]
        assert "actionable" in log_data["ai_analysis"]
        assert "anomaly_score" in log_data["ai_analysis"]

        # Validate correlation ID is generated
        assert "correlation_id" in log_data

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_json_formatting_with_context(self, formatter, log_record):
        """Test JSON formatting with log context."""
        context = LogContext(
            timestamp=time.time(),
            correlation_id="test-456",
            operation="test_op"
        )
        log_record.context = context

        formatted = formatter.format(log_record)
        log_data = json.loads(formatted)

        assert "context" in log_data
        assert log_data["context"]["correlation_id"] == "test-456"
        assert log_data["context"]["operation"] == "test_op"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_json_formatting_with_performance_metrics(self, formatter, log_record):
        """Test JSON formatting with performance metrics."""
        metrics = PerformanceMetrics(
            operation="test_operation",
            duration_ms=100.5,
            records_processed=50
        )
        log_record.performance_metrics = metrics

        formatted = formatter.format(log_record)
        log_data = json.loads(formatted)

        assert "performance_metrics" in log_data
        assert log_data["performance_metrics"]["operation"] == "test_operation"
        assert log_data["performance_metrics"]["duration_ms"] == 100.5

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_json_formatting_with_exception(self, formatter, log_record):
        """Test JSON formatting with exception information."""
        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys
            log_record.exc_info = sys.exc_info()

        formatted = formatter.format(log_record)
        log_data = json.loads(formatted)

        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert log_data["exception"]["message"] == "Test exception"
        assert "traceback" in log_data["exception"]

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_category_auto_detection(self, formatter, log_record):
        """Test automatic category detection."""
        test_cases = [
            ("Error occurred", "error", logging.ERROR),
            ("Performance metrics: duration 100ms", "performance", logging.INFO),
            ("User action: login", "user_action", logging.INFO),
            ("Network request failed", "external_service", logging.WARNING),
            ("Processing data", "data_flow", logging.INFO),
            ("System startup", "system", logging.INFO)
        ]

        for message, expected_category, level in test_cases:
            log_record.msg = message
            log_record.levelno = level
            log_record.levelname = logging.getLevelName(level)

            formatted = formatter.format(log_record)
            log_data = json.loads(formatted)

            assert log_data["category"] == expected_category

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_importance_calculation(self, formatter, log_record):
        """Test importance score calculation."""
        # Test critical level
        log_record.levelno = logging.CRITICAL
        log_record.levelname = "CRITICAL"
        formatted = formatter.format(log_record)
        log_data = json.loads(formatted)
        assert log_data["ai_analysis"]["importance"] >= 0.8

        # Test info level
        log_record.levelno = logging.INFO
        log_record.levelname = "INFO"
        formatted = formatter.format(log_record)
        log_data = json.loads(formatted)
        assert log_data["ai_analysis"]["importance"] <= 0.5

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_actionable_detection(self, formatter, log_record):
        """Test actionable log detection."""
        # Test actionable message
        log_record.msg = "Operation failed with timeout"
        formatted = formatter.format(log_record)
        log_data = json.loads(formatted)
        assert log_data["ai_analysis"]["actionable"] is True

        # Test non-actionable message
        log_record.msg = "System information logged"
        formatted = formatter.format(log_record)
        log_data = json.loads(formatted)
        assert log_data["ai_analysis"]["actionable"] is False


class TestAILoggerAdapter:
    """Test AI logger adapter functionality."""

    @pytest.fixture
    def base_logger(self):
        """Create base logger for testing."""
        logger = logging.getLogger("test.ai.logger")
        logger.handlers.clear()  # Clear any existing handlers
        return logger

    @pytest.fixture
    def ai_logger(self, base_logger):
        """Create AI logger adapter for testing."""
        return AILoggerAdapter(base_logger, {"component": "test_component"})

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_ai_logger_initialization(self, ai_logger):
        """Test AI logger adapter initialization."""
        assert ai_logger.correlation_id is not None
        assert ai_logger.extra["component"] == "test_component"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_performance_logging(self, ai_logger):
        """Test performance logging functionality."""
        # Capture log output
        handler = logging.StreamHandler(StringIO())
        handler.setFormatter(AIJSONFormatter())
        ai_logger.logger.addHandler(handler)
        ai_logger.logger.setLevel(logging.INFO)

        # Log performance metrics
        ai_logger.log_performance(
            operation="test_operation",
            duration_ms=150.5,
            records_processed=100,
            memory_usage_mb=64.2
        )

        # Verify log was created
        handler.stream.seek(0)
        log_output = handler.stream.read()
        assert "Performance: test_operation" in log_output

        # Parse JSON and validate
        log_data = json.loads(log_output.strip())
        assert log_data["category"] == "performance"
        assert "performance_metrics" in log_data
        assert log_data["performance_metrics"]["operation"] == "test_operation"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_error_logging_with_ai_context(self, ai_logger):
        """Test error logging with AI context."""
        # Create AI-friendly error
        error = AIDataValidationError("Test validation error")
        error.set_error_code("TEST_001").set_category(ErrorCategory.VALIDATION)

        # Capture log output
        handler = logging.StreamHandler(StringIO())
        handler.setFormatter(AIJSONFormatter())
        ai_logger.logger.addHandler(handler)
        ai_logger.logger.setLevel(logging.ERROR)

        # Log error
        ai_logger.log_error_with_ai_context(error, operation="test_validation")

        # Verify log was created
        handler.stream.seek(0)
        log_output = handler.stream.read()
        assert "AI Error: test_validation failed" in log_output

        # Parse JSON and validate
        log_data = json.loads(log_output.strip())
        assert log_data["category"] == "error"
        assert "error_metrics" in log_data
        assert "ai_error_data" in log_data
        assert log_data["ai_error_data"]["error_code"] == "TEST_001"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_user_action_logging(self, ai_logger):
        """Test user action logging."""
        # Capture log output
        handler = logging.StreamHandler(StringIO())
        handler.setFormatter(AIJSONFormatter())
        ai_logger.logger.addHandler(handler)
        ai_logger.logger.setLevel(logging.INFO)

        # Log user action
        ai_logger.log_user_action(
            action="search_properties",
            user_id="user-123",
            county="Baldwin",
            filters={"min_acres": 1, "max_price": 20000}
        )

        # Verify log was created
        handler.stream.seek(0)
        log_output = handler.stream.read()
        log_data = json.loads(log_output.strip())

        assert log_data["category"] == "user_action"
        assert log_data["extra"]["action"] == "search_properties"
        assert log_data["extra"]["user_id"] == "user-123"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_business_event_logging(self, ai_logger):
        """Test business event logging."""
        # Capture log output
        handler = logging.StreamHandler(StringIO())
        handler.setFormatter(AIJSONFormatter())
        ai_logger.logger.addHandler(handler)
        ai_logger.logger.setLevel(logging.INFO)

        # Log business event
        ai_logger.log_business_event(
            event="property_watchlist_generated",
            county="Baldwin",
            properties_count=29,
            water_features_count=13
        )

        # Verify log was created
        handler.stream.seek(0)
        log_output = handler.stream.read()
        log_data = json.loads(log_output.strip())

        assert log_data["category"] == "business"
        assert log_data["extra"]["event"] == "property_watchlist_generated"
        assert log_data["extra"]["event_data"]["county"] == "Baldwin"


class TestAILogAnalyzer:
    """Test AI log analyzer functionality."""

    @pytest.fixture
    def analyzer(self):
        """Create AI log analyzer for testing."""
        return AILogAnalyzer()

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_error_pattern_analysis(self, analyzer):
        """Test error pattern detection."""
        # Simulate multiple similar errors
        for i in range(6):  # Above threshold
            log_entry = {
                "level": "error",
                "exception": {"type": "ValidationError"},
                "timestamp": time.time(),
                "correlation_id": f"test-{i}"
            }
            analysis = analyzer.analyze_log_entry(log_entry)

        # Check that pattern was detected
        assert len(analysis["alerts"]) > 0
        alert = analysis["alerts"][0]
        assert alert["type"] == "error_pattern"
        assert "ValidationError" in alert["message"]

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_performance_anomaly_analysis(self, analyzer):
        """Test performance anomaly detection."""
        # Establish baseline
        for i in range(3):
            log_entry = {
                "category": "performance",
                "performance_metrics": {
                    "operation": "test_operation",
                    "duration_ms": 100.0  # Normal duration
                },
                "timestamp": time.time(),
                "correlation_id": f"baseline-{i}"
            }
            analyzer.analyze_log_entry(log_entry)

        # Simulate performance degradation
        log_entry = {
            "category": "performance",
            "performance_metrics": {
                "operation": "test_operation",
                "duration_ms": 300.0  # 3x slower
            },
            "timestamp": time.time(),
            "correlation_id": "slow-operation"
        }
        analysis = analyzer.analyze_log_entry(log_entry)

        # Check that anomaly was detected
        assert len(analysis["alerts"]) > 0
        alert = analysis["alerts"][0]
        assert alert["type"] == "performance_degradation"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_security_indicator_analysis(self, analyzer):
        """Test security indicator detection."""
        log_entry = {
            "level": "warning",
            "message": "Unauthorized access attempt detected",
            "timestamp": time.time(),
            "correlation_id": "security-test"
        }
        analysis = analyzer.analyze_log_entry(log_entry)

        # Check that security indicator was detected
        assert len(analysis["alerts"]) > 0
        alert = analysis["alerts"][0]
        assert alert["type"] == "security_indicator"
        assert alert["severity"] == "high"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_anomaly_detection(self, analyzer):
        """Test general anomaly detection."""
        log_entry = {
            "level": "error",
            "ai_analysis": {"anomaly_score": 0.8},  # High anomaly score
            "timestamp": time.time(),
            "correlation_id": "anomaly-test"
        }
        analysis = analyzer.analyze_log_entry(log_entry)

        # Check that anomaly was detected
        assert len(analysis["insights"]) > 0
        insight = analysis["insights"][0]
        assert insight["type"] == "anomaly_detected"
        assert insight["score"] == 0.8

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_system_health_summary(self, analyzer):
        """Test system health summary generation."""
        # Add some errors to the analyzer
        analyzer.error_patterns = {
            "ValidationError": 3,
            "NetworkError": 2
        }
        analyzer.performance_baseline = {
            "operation1": 100.0,
            "operation2": 200.0
        }

        summary = analyzer.get_system_health_summary()

        assert "timestamp" in summary
        assert summary["error_patterns"]["ValidationError"] == 3
        assert summary["total_errors"] == 5
        assert 0.0 <= summary["health_score"] <= 1.0
        assert isinstance(summary["recommendations"], list)


class TestAILoggingManager:
    """Test AI logging manager functionality."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary directory for log files."""
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_logging_manager_initialization(self, temp_log_dir):
        """Test logging manager initialization."""
        config = {
            'json_log_file': str(temp_log_dir / 'test.jsonl'),
            'error_log_file': str(temp_log_dir / 'errors.jsonl'),
            'console_output': False
        }

        manager = AILoggingManager(config)
        assert manager.config == config
        assert isinstance(manager.analyzer, AILogAnalyzer)

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_get_logger(self, temp_log_dir):
        """Test logger creation and caching."""
        config = {
            'json_log_file': str(temp_log_dir / 'test.jsonl'),
            'console_output': False
        }

        manager = AILoggingManager(config)

        # Get logger for the first time
        logger1 = manager.get_logger("test.logger", component="test")
        assert isinstance(logger1, AILoggerAdapter)
        assert logger1.extra["component"] == "test"

        # Get same logger again (should be cached)
        logger2 = manager.get_logger("test.logger")
        assert logger1 is logger2

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_operation_context_creation(self, temp_log_dir):
        """Test operation context creation."""
        config = {'console_output': False}
        manager = AILoggingManager(config)

        context = manager.create_operation_context(
            "test_operation",
            component="test_component",
            user_id="user-123"
        )

        assert isinstance(context, LogContext)
        assert context.operation == "test_operation"
        assert context.component == "test_component"
        assert context.user_id == "user-123"
        assert context.correlation_id is not None

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_operation_context_manager(self, temp_log_dir):
        """Test operation context manager."""
        config = {
            'json_log_file': str(temp_log_dir / 'test.jsonl'),
            'console_output': False
        }
        manager = AILoggingManager(config)

        # Test successful operation
        with manager.operation_context("test_operation") as logger:
            assert isinstance(logger, AILoggerAdapter)
            logger.info("Operation in progress")

        # Test operation with exception
        with pytest.raises(ValueError):
            with manager.operation_context("failing_operation") as logger:
                raise ValueError("Test error")


class TestGlobalAILoggingFunctions:
    """Test global AI logging functions."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_get_ai_logger(self):
        """Test global get_ai_logger function."""
        logger = get_ai_logger("test.global.logger", component="global_test")

        assert isinstance(logger, AILoggerAdapter)
        assert logger.extra["component"] == "global_test"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_setup_ai_logging(self):
        """Test global setup_ai_logging function."""
        config = {'console_output': False}
        manager = setup_ai_logging(config)

        assert isinstance(manager, AILoggingManager)
        assert manager.config == config

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_ai_operation_context(self):
        """Test global ai_operation_context function."""
        with ai_operation_context("global_test_operation") as logger:
            assert isinstance(logger, AILoggerAdapter)
            logger.info("Global context test")


class TestIntegrationWithAIExceptions:
    """Test integration between AI logging and AI exceptions."""

    @pytest.mark.integration
    @pytest.mark.ai_test
    def test_ai_error_logging_integration(self):
        """Test integration between AI errors and AI logging."""
        logger = get_ai_logger("integration.test")

        # Create AI-friendly error
        error = (AIDataValidationError("Integration test error")
                .set_error_code("INTEGRATION_001")
                .set_category(ErrorCategory.VALIDATION)
                .set_severity(ErrorSeverity.HIGH))

        # Capture log output
        handler = logging.StreamHandler(StringIO())
        handler.setFormatter(AIJSONFormatter())
        logger.logger.addHandler(handler)
        logger.logger.setLevel(logging.ERROR)

        # Log the error
        logger.log_error_with_ai_context(error, operation="integration_test")

        # Verify integration
        handler.stream.seek(0)
        log_output = handler.stream.read()
        log_data = json.loads(log_output.strip())

        assert log_data["category"] == "error"
        assert "ai_error_data" in log_data
        assert log_data["ai_error_data"]["error_code"] == "INTEGRATION_001"
        assert log_data["ai_error_data"]["category"] == "validation"
        assert log_data["ai_error_data"]["severity"] == "high"


@pytest.mark.parametrize("log_level,expected_importance", [
    ("DEBUG", 0.1),
    ("INFO", 0.3),
    ("WARNING", 0.6),
    ("ERROR", 0.8),
    ("CRITICAL", 1.0)
])
@pytest.mark.unit
@pytest.mark.ai_test
def test_importance_calculation_by_level(log_level, expected_importance):
    """Parametrized test for importance calculation by log level."""
    formatter = AIJSONFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=getattr(logging, log_level),
        pathname="/test/path.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    record.levelname = log_level

    formatted = formatter.format(record)
    log_data = json.loads(formatted)

    assert log_data["ai_analysis"]["importance"] >= expected_importance - 0.1
    assert log_data["ai_analysis"]["importance"] <= expected_importance + 0.1


@pytest.mark.parametrize("message,expected_category", [
    ("Performance test completed", "performance"),
    ("User login successful", "user_action"),
    ("Network timeout occurred", "external_service"),
    ("Data processing started", "data_flow"),
    ("System configuration loaded", "system"),
    ("Critical error occurred", "error")
])
@pytest.mark.unit
@pytest.mark.ai_test
def test_category_detection_parametrized(message, expected_category):
    """Parametrized test for category detection."""
    formatter = AIJSONFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.ERROR if "error" in message.lower() else logging.INFO,
        pathname="/test/path.py",
        lineno=1,
        msg=message,
        args=(),
        exc_info=None
    )
    record.levelname = "ERROR" if "error" in message.lower() else "INFO"

    formatted = formatter.format(record)
    log_data = json.loads(formatted)

    assert log_data["category"] == expected_category