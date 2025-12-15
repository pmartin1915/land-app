"""
Tests for the AI-enhanced exception system.

These tests validate that the AI-friendly error handling, correlation tracking,
and recovery mechanisms work correctly for machine-readable error analysis.
"""

import json
import pytest
import time
from unittest.mock import Mock, patch

from scripts.ai_exceptions import (
    ErrorSeverity, ErrorCategory, RecoveryAction,
    ErrorContext, RecoveryInstruction, AIFriendlyError,
    AIDataValidationError, AICountyValidationError, AINetworkError,
    AIParseError, AIRateLimitError, AIDataProcessingError,
    AIConfigurationError, AIFileOperationError,
    ErrorCorrelationTracker, ErrorTrackingContext,
    track_error, get_error_patterns, get_improvement_suggestions,
    analyze_error_for_ai, create_error_from_dict
)


class TestErrorEnums:
    """Test error enumeration values."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_error_severity_values(self):
        """Test error severity enum values."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_error_category_values(self):
        """Test error category enum values."""
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.PARSING.value == "parsing"
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.CONFIGURATION.value == "configuration"
        assert ErrorCategory.SYSTEM.value == "system"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_recovery_action_values(self):
        """Test recovery action enum values."""
        assert RecoveryAction.RETRY.value == "retry"
        assert RecoveryAction.RETRY_WITH_BACKOFF.value == "retry_with_backoff"
        assert RecoveryAction.VALIDATE_INPUT.value == "validate_input"
        assert RecoveryAction.ESCALATE_TO_HUMAN.value == "escalate_to_human"


class TestErrorContext:
    """Test error context functionality."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_error_context_creation(self):
        """Test error context creation."""
        context = ErrorContext(
            timestamp=time.time(),
            correlation_id="test-123",
            operation="test_operation",
            component="test_component"
        )

        assert context.timestamp is not None
        assert context.correlation_id == "test-123"
        assert context.operation == "test_operation"
        assert context.component == "test_component"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_error_context_to_dict(self):
        """Test error context dictionary conversion."""
        context = ErrorContext(
            timestamp=123456789.0,
            correlation_id="test-123",
            operation="test_operation",
            additional_data={"key": "value"}
        )

        context_dict = context.to_dict()

        assert isinstance(context_dict, dict)
        assert context_dict["timestamp"] == 123456789.0
        assert context_dict["correlation_id"] == "test-123"
        assert context_dict["operation"] == "test_operation"
        assert context_dict["additional_data"]["key"] == "value"


class TestRecoveryInstruction:
    """Test recovery instruction functionality."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_recovery_instruction_creation(self):
        """Test recovery instruction creation."""
        instruction = RecoveryInstruction(
            action=RecoveryAction.RETRY,
            parameters={"delay": 5},
            max_attempts=3,
            timeout_seconds=30
        )

        assert instruction.action == RecoveryAction.RETRY
        assert instruction.parameters["delay"] == 5
        assert instruction.max_attempts == 3
        assert instruction.timeout_seconds == 30

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_recovery_instruction_to_dict(self):
        """Test recovery instruction dictionary conversion."""
        instruction = RecoveryInstruction(
            action=RecoveryAction.RETRY_WITH_BACKOFF,
            parameters={"initial_delay": 2, "max_delay": 60},
            condition="network_available"
        )

        instruction_dict = instruction.to_dict()

        assert instruction_dict["action"] == "retry_with_backoff"
        assert instruction_dict["parameters"]["initial_delay"] == 2
        assert instruction_dict["parameters"]["max_delay"] == 60
        assert instruction_dict["condition"] == "network_available"


class TestAIFriendlyError:
    """Test AI-friendly error base functionality."""

    @pytest.fixture
    def mock_error(self):
        """Create a mock AI-friendly error for testing."""
        class MockAIError(AIFriendlyError, Exception):
            pass
        return MockAIError("Test error message")

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_ai_error_initialization(self, mock_error):
        """Test AI error initialization."""
        assert mock_error.correlation_id is not None
        assert mock_error.timestamp is not None
        assert mock_error.severity == ErrorSeverity.MEDIUM
        assert mock_error.recoverable is True
        assert isinstance(mock_error.recovery_instructions, list)
        assert isinstance(mock_error.related_errors, list)
        assert isinstance(mock_error.metric_tags, dict)

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_ai_error_method_chaining(self, mock_error):
        """Test AI error method chaining."""
        result = (mock_error
                 .set_error_code("TEST_001")
                 .set_category(ErrorCategory.VALIDATION)
                 .set_severity(ErrorSeverity.HIGH)
                 .set_recoverable(False))

        assert result is mock_error  # Method chaining
        assert mock_error.error_code == "TEST_001"
        assert mock_error.category == ErrorCategory.VALIDATION
        assert mock_error.severity == ErrorSeverity.HIGH
        assert mock_error.recoverable is False

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_ai_error_recovery_instructions(self, mock_error):
        """Test adding recovery instructions."""
        instruction = RecoveryInstruction(
            action=RecoveryAction.RETRY,
            parameters={"delay": 5}
        )

        mock_error.add_recovery_instruction(instruction)

        assert len(mock_error.recovery_instructions) == 1
        assert mock_error.recovery_instructions[0] == instruction

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_ai_error_to_dict(self, mock_error):
        """Test AI error dictionary conversion."""
        mock_error.set_error_code("TEST_001").set_category(ErrorCategory.NETWORK)

        error_dict = mock_error.to_ai_dict()

        assert isinstance(error_dict, dict)
        assert error_dict["error_code"] == "TEST_001"
        assert error_dict["category"] == "network"
        assert error_dict["message"] == "Test error message"
        assert error_dict["exception_type"] == "MockAIError"
        assert "timestamp" in error_dict
        assert "error_id" in error_dict

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_ai_error_to_json(self, mock_error):
        """Test AI error JSON serialization."""
        mock_error.set_error_code("TEST_001")

        json_str = mock_error.to_json()

        assert isinstance(json_str, str)
        error_data = json.loads(json_str)
        assert error_data["error_code"] == "TEST_001"
        assert error_data["message"] == "Test error message"


class TestSpecificAIErrors:
    """Test specific AI-enhanced error types."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_ai_data_validation_error(self):
        """Test AI data validation error."""
        error = AIDataValidationError("Invalid value", field="price", value="invalid")

        assert "DATA_VALIDATION_PRICE_001" in error.error_code
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.recoverable is True
        assert len(error.recovery_instructions) >= 1
        assert error.recovery_instructions[0].action == RecoveryAction.VALIDATE_INPUT

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_ai_county_validation_error(self):
        """Test AI county validation error."""
        error = AICountyValidationError("99")

        assert error.error_code == "COUNTY_VALIDATION_001"
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.HIGH
        assert error.recoverable is False
        assert len(error.recovery_instructions) >= 2
        assert error.documentation_url is not None

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_ai_network_error_with_status_codes(self):
        """Test AI network error with different status codes."""
        # Test rate limit error (429)
        rate_limit_error = AINetworkError("Rate limited", status_code=429)
        assert "NETWORK_CLIENT_429" in rate_limit_error.error_code
        assert rate_limit_error.recoverable is True

        # Test server error (500)
        server_error = AINetworkError("Server error", status_code=500)
        assert "NETWORK_SERVER_500" in server_error.error_code
        assert server_error.recoverable is True

        # Test connection error (no status code)
        connection_error = AINetworkError("Connection failed")
        assert "NETWORK_CONNECTION_001" in connection_error.error_code

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_ai_network_error_recovery_instructions(self):
        """Test network error recovery instructions."""
        error = AINetworkError("Rate limited", status_code=429)

        # Should have retry with backoff instruction
        retry_instructions = [
            instr for instr in error.recovery_instructions
            if instr.action == RecoveryAction.RETRY_WITH_BACKOFF
        ]
        assert len(retry_instructions) >= 1

        # Should have fallback instruction
        fallback_instructions = [
            instr for instr in error.recovery_instructions
            if instr.action == RecoveryAction.FALLBACK_TO_CACHE
        ]
        assert len(fallback_instructions) >= 1

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_ai_parse_error(self):
        """Test AI parse error."""
        error = AIParseError("Invalid HTML", page_content_length=1024)

        assert error.error_code == "PARSE_HTML_001"
        assert error.category == ErrorCategory.PARSING
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.recoverable is True

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_ai_rate_limit_error(self):
        """Test AI rate limit error."""
        error = AIRateLimitError(retry_after=60)

        assert error.error_code == "RATE_LIMIT_001"
        assert error.category == ErrorCategory.EXTERNAL_SERVICE
        assert error.recoverable is True
        assert len(error.recovery_instructions) >= 1

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_ai_configuration_error(self):
        """Test AI configuration error."""
        error = AIConfigurationError("Missing config", config_key="database_url", default_value="sqlite://")

        assert "CONFIG_DATABASE_URL_001" in error.error_code
        assert error.category == ErrorCategory.CONFIGURATION
        assert error.severity == ErrorSeverity.HIGH

        # Should have recovery instruction for default value
        use_default_instructions = [
            instr for instr in error.recovery_instructions
            if instr.action == RecoveryAction.USE_DEFAULT_VALUE
        ]
        assert len(use_default_instructions) >= 1


class TestErrorCorrelationTracker:
    """Test error correlation and tracking functionality."""

    @pytest.fixture
    def tracker(self):
        """Create error tracker for testing."""
        return ErrorCorrelationTracker()

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_error_tracking(self, tracker):
        """Test error tracking functionality."""
        error = AIDataValidationError("Test error")
        error.set_error_code("TEST_001").set_category(ErrorCategory.VALIDATION)

        tracker.track_error(error)

        assert len(tracker.error_history) == 1
        assert tracker.error_history[0]["error_code"] == "TEST_001"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_error_correlation(self, tracker):
        """Test error correlation functionality."""
        # Create multiple similar errors
        for i in range(3):
            error = AIDataValidationError(f"Test error {i}")
            error.set_error_code("TEST_001").set_category(ErrorCategory.VALIDATION)
            tracker.track_error(error)

        # Check correlation groups
        correlation_key = "validation_TEST_001"
        assert correlation_key in tracker.correlation_groups
        assert len(tracker.correlation_groups[correlation_key]) == 3

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_error_patterns(self, tracker):
        """Test error pattern detection."""
        # Create multiple similar errors
        for i in range(6):  # Above threshold for pattern detection
            error = AIDataValidationError(f"Test error {i}")
            error.set_error_code("TEST_001").set_category(ErrorCategory.VALIDATION)
            tracker.track_error(error)

        patterns = tracker.get_error_patterns()

        assert len(patterns) >= 1
        pattern_key = "validation_TEST_001"
        assert pattern_key in patterns
        assert patterns[pattern_key]["frequency"] == 6

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_improvement_suggestions(self, tracker):
        """Test improvement suggestions."""
        # Create many similar errors to trigger suggestions
        for i in range(12):  # Above threshold for suggestions
            error = AIDataValidationError(f"Test error {i}")
            error.set_error_code("FREQUENT_ERROR_001").set_category(ErrorCategory.VALIDATION)
            tracker.track_error(error)

        suggestions = tracker.suggest_improvements()

        assert len(suggestions) >= 1
        assert suggestions[0]["type"] == "frequent_error"
        assert suggestions[0]["priority"] == "high"


class TestErrorTrackingContext:
    """Test error tracking context manager."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_context_manager_normal_operation(self):
        """Test context manager with normal operation."""
        with ErrorTrackingContext("test_operation", component="test_component") as ctx:
            assert ctx.context is not None
            assert ctx.context.operation == "test_operation"
            assert ctx.context.component == "test_component"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_context_manager_with_ai_error(self):
        """Test context manager with AI error."""
        with pytest.raises(AIDataValidationError) as exc_info:
            with ErrorTrackingContext("test_operation") as ctx:
                error = AIDataValidationError("Test error")
                raise error

        # Error should have context set
        error = exc_info.value
        assert error.context is not None
        assert error.context.operation == "test_operation"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_context_manager_with_regular_error(self):
        """Test context manager with regular Python error."""
        with pytest.raises(ValueError):
            with ErrorTrackingContext("test_operation"):
                raise ValueError("Regular error")

        # The error should be tracked internally


class TestUtilityFunctions:
    """Test utility functions for AI error analysis."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_analyze_error_for_ai_with_ai_error(self):
        """Test analyzing AI-friendly error."""
        error = AIDataValidationError("Test error")
        error.set_error_code("TEST_001")

        analysis = analyze_error_for_ai(error)

        assert isinstance(analysis, dict)
        assert analysis["error_code"] == "TEST_001"
        assert analysis["exception_type"] == "AIDataValidationError"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_analyze_error_for_ai_with_regular_error(self):
        """Test analyzing regular Python error."""
        error = ValueError("Regular error")

        analysis = analyze_error_for_ai(error)

        assert isinstance(analysis, dict)
        assert analysis["exception_type"] == "ValueError"
        assert analysis["message"] == "Regular error"
        assert analysis["recoverable"] is False

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_create_error_from_dict(self):
        """Test creating error from dictionary data."""
        error_data = {
            "message": "Test error",
            "error_code": "TEST_001",
            "category": "validation",
            "severity": "high",
            "recoverable": False
        }

        error = create_error_from_dict(error_data)

        assert isinstance(error, AIDataValidationError)
        assert error.error_code == "TEST_001"
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.HIGH
        assert error.recoverable is False

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_global_error_tracking(self):
        """Test global error tracking functions."""
        # Clear any existing patterns
        global _error_tracker
        _error_tracker = ErrorCorrelationTracker()

        error = AIDataValidationError("Global tracking test")
        error.set_error_code("GLOBAL_001")

        track_error(error)

        patterns = get_error_patterns()
        suggestions = get_improvement_suggestions()

        assert isinstance(patterns, dict)
        assert isinstance(suggestions, list)


@pytest.mark.parametrize("error_type,expected_category", [
    (AIDataValidationError, ErrorCategory.VALIDATION),
    (AINetworkError, ErrorCategory.NETWORK),
    (AIParseError, ErrorCategory.PARSING),
    (AIConfigurationError, ErrorCategory.CONFIGURATION),
])
@pytest.mark.unit
@pytest.mark.ai_test
def test_error_category_assignment(error_type, expected_category):
    """Parametrized test for error category assignment."""
    if error_type == AINetworkError:
        error = error_type("Test error", url="http://test.com")
    elif error_type == AIConfigurationError:
        error = error_type("Test error", config_key="test_key")
    else:
        error = error_type("Test error")

    assert error.category == expected_category


@pytest.mark.parametrize("status_code,expected_recoverable", [
    (429, True),   # Rate limit - recoverable
    (500, True),   # Server error - recoverable
    (404, False),  # Not found - not recoverable
    (401, False),  # Unauthorized - not recoverable
])
@pytest.mark.unit
@pytest.mark.ai_test
def test_network_error_recoverability(status_code, expected_recoverable):
    """Parametrized test for network error recoverability."""
    error = AINetworkError("Test error", status_code=status_code)

    assert error.recoverable == expected_recoverable


class TestAIErrorJSONSerialization:
    """Test JSON serialization for AI consumption."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_complete_error_json_serialization(self):
        """Test complete error serialization to JSON."""
        context = ErrorContext(
            timestamp=time.time(),
            correlation_id="test-123",
            operation="test_op"
        )

        recovery_instruction = RecoveryInstruction(
            action=RecoveryAction.RETRY,
            parameters={"delay": 5}
        )

        error = (AIDataValidationError("Test error")
                .set_error_code("TEST_001")
                .set_category(ErrorCategory.VALIDATION)
                .set_severity(ErrorSeverity.HIGH)
                .set_context(context)
                .add_recovery_instruction(recovery_instruction)
                .add_related_error("related-error-123")
                .set_documentation_url("https://docs.example.com/errors/TEST_001")
                .add_metric_tag("module", "validation"))

        json_str = error.to_json()
        error_data = json.loads(json_str)

        # Validate all fields are present and correct
        assert error_data["error_code"] == "TEST_001"
        assert error_data["category"] == "validation"
        assert error_data["severity"] == "high"
        assert error_data["context"]["operation"] == "test_op"
        assert len(error_data["recovery_instructions"]) == 1
        assert error_data["recovery_instructions"][0]["action"] == "retry"
        assert "related-error-123" in error_data["related_errors"]
        assert error_data["documentation_url"] == "https://docs.example.com/errors/TEST_001"
        assert error_data["metric_tags"]["module"] == "validation"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_error_json_round_trip(self):
        """Test error JSON serialization round trip."""
        original_error = (AIDataValidationError("Test error")
                         .set_error_code("TEST_001")
                         .set_category(ErrorCategory.VALIDATION))

        # Serialize to JSON
        json_str = original_error.to_json()
        error_data = json.loads(json_str)

        # Create new error from data
        recreated_error = create_error_from_dict(error_data)

        # Validate key properties match
        assert recreated_error.error_code == original_error.error_code
        assert recreated_error.category == original_error.category
        assert str(recreated_error) == str(original_error)