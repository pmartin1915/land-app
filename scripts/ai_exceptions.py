"""
Enhanced AI-friendly exception system for Alabama Auction Watcher.

This module extends the base exception system with AI-friendly features including
structured error codes, recovery suggestions, error correlation, and JSON serialization
for machine-readable error analysis.
"""

import json
import time
import traceback
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict

# Import base exceptions
from scripts.exceptions import (
    DataValidationError, CountyValidationError, NetworkError,
    ParseError, RateLimitError, DataProcessingError, ConfigurationError,
    FileOperationError
)


class ErrorSeverity(Enum):
    """Error severity levels for AI prioritization."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for AI classification."""
    NETWORK = "network"
    PARSING = "parsing"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    USER_INPUT = "user_input"


class RecoveryAction(Enum):
    """Suggested recovery actions for AI systems."""
    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    VALIDATE_INPUT = "validate_input"
    CHECK_CONFIGURATION = "check_configuration"
    CHECK_NETWORK = "check_network"
    CHECK_EXTERNAL_SERVICE = "check_external_service"
    FALLBACK_TO_CACHE = "fallback_to_cache"
    USE_DEFAULT_VALUE = "use_default_value"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    LOG_AND_CONTINUE = "log_and_continue"
    ABORT_OPERATION = "abort_operation"
    RESET_STATE = "reset_state"


@dataclass
class ErrorContext:
    """Structured error context for AI analysis."""
    timestamp: float
    correlation_id: str
    operation: Optional[str] = None
    component: Optional[str] = None
    user_action: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    environment: Optional[str] = None
    version: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class RecoveryInstruction:
    """AI recovery instruction with parameters."""
    action: RecoveryAction
    parameters: Dict[str, Any]
    max_attempts: int = 3
    timeout_seconds: int = 30
    condition: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "action": self.action.value,
            "parameters": self.parameters,
            "max_attempts": self.max_attempts,
            "timeout_seconds": self.timeout_seconds,
            "condition": self.condition
        }


class AIFriendlyError:
    """Mixin class to add AI-friendly features to exceptions."""

    def __init__(self, *args, **kwargs):
        """Initialize AI-friendly error features."""
        super().__init__(*args, **kwargs)

        # AI-friendly error properties
        self.error_code: Optional[str] = None
        self.category: Optional[ErrorCategory] = None
        self.severity: ErrorSeverity = ErrorSeverity.MEDIUM
        self.recoverable: bool = True
        self.context: Optional[ErrorContext] = None
        self.recovery_instructions: List[RecoveryInstruction] = []
        self.related_errors: List[str] = []
        self.documentation_url: Optional[str] = None
        self.metric_tags: Dict[str, str] = {}

        # Auto-generate correlation ID
        self.correlation_id = str(uuid.uuid4())
        self.timestamp = time.time()

    def set_error_code(self, code: str) -> 'AIFriendlyError':
        """Set the error code for AI classification."""
        self.error_code = code
        return self

    def set_category(self, category: ErrorCategory) -> 'AIFriendlyError':
        """Set the error category for AI classification."""
        self.category = category
        return self

    def set_severity(self, severity: ErrorSeverity) -> 'AIFriendlyError':
        """Set the error severity for AI prioritization."""
        self.severity = severity
        return self

    def set_recoverable(self, recoverable: bool) -> 'AIFriendlyError':
        """Set whether the error is recoverable by AI."""
        self.recoverable = recoverable
        return self

    def set_context(self, context: ErrorContext) -> 'AIFriendlyError':
        """Set structured error context."""
        self.context = context
        return self

    def add_recovery_instruction(self, instruction: RecoveryInstruction) -> 'AIFriendlyError':
        """Add a recovery instruction for AI systems."""
        self.recovery_instructions.append(instruction)
        return self

    def add_related_error(self, error_id: str) -> 'AIFriendlyError':
        """Add a related error for correlation analysis."""
        self.related_errors.append(error_id)
        return self

    def set_documentation_url(self, url: str) -> 'AIFriendlyError':
        """Set documentation URL for AI reference."""
        self.documentation_url = url
        return self

    def add_metric_tag(self, key: str, value: str) -> 'AIFriendlyError':
        """Add metric tag for AI monitoring."""
        self.metric_tags[key] = value
        return self

    def to_ai_dict(self) -> Dict[str, Any]:
        """Convert error to AI-readable dictionary format."""
        return {
            "error_id": self.correlation_id,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
            "error_code": self.error_code,
            "category": self.category.value if self.category else None,
            "severity": self.severity.value,
            "message": str(self),
            "exception_type": type(self).__name__,
            "recoverable": self.recoverable,
            "context": self.context.to_dict() if self.context else None,
            "recovery_instructions": [instr.to_dict() for instr in self.recovery_instructions],
            "related_errors": self.related_errors,
            "documentation_url": self.documentation_url,
            "metric_tags": self.metric_tags,
            "stack_trace": traceback.format_exc() if hasattr(self, '__traceback__') else None
        }

    def to_json(self) -> str:
        """Convert error to JSON for AI consumption."""
        return json.dumps(self.to_ai_dict(), indent=2)


# Enhanced exception classes with AI-friendly features
class AIDataValidationError(AIFriendlyError, DataValidationError):
    """AI-enhanced data validation error."""

    def __init__(self, message: str, field: str = None, value: str = None, **kwargs):
        super().__init__(message, field, value)

        # Set default AI properties
        self.set_error_code(f"DATA_VALIDATION_{field.upper() if field else 'GENERAL'}_001")
        self.set_category(ErrorCategory.VALIDATION)
        self.set_severity(ErrorSeverity.MEDIUM)
        self.set_recoverable(True)

        # Add default recovery instructions
        self.add_recovery_instruction(RecoveryInstruction(
            action=RecoveryAction.VALIDATE_INPUT,
            parameters={"field": field, "value": value, "expected_format": kwargs.get("expected_format")}
        ))

        if kwargs.get("can_use_default"):
            self.add_recovery_instruction(RecoveryInstruction(
                action=RecoveryAction.USE_DEFAULT_VALUE,
                parameters={"default_value": kwargs.get("default_value")}
            ))


class AICountyValidationError(AIFriendlyError, CountyValidationError):
    """AI-enhanced county validation error."""

    def __init__(self, county_input: str, **kwargs):
        super().__init__(county_input)

        self.set_error_code("COUNTY_VALIDATION_001")
        self.set_category(ErrorCategory.VALIDATION)
        self.set_severity(ErrorSeverity.HIGH)
        self.set_recoverable(False)  # Invalid county codes can't be auto-recovered

        # Add recovery instructions
        self.add_recovery_instruction(RecoveryInstruction(
            action=RecoveryAction.VALIDATE_INPUT,
            parameters={"county_input": county_input, "valid_range": "01-67", "expected_format": "2-digit code or Alabama county name"}
        ))

        self.add_recovery_instruction(RecoveryInstruction(
            action=RecoveryAction.ESCALATE_TO_HUMAN,
            parameters={"reason": "Invalid county code requires human verification"}
        ))

        self.set_documentation_url("https://docs.alabama-auction-watcher.com/errors/county-validation")


class AINetworkError(AIFriendlyError, NetworkError):
    """AI-enhanced network error."""

    def __init__(self, message: str, url: str = None, status_code: int = None, **kwargs):
        super().__init__(message, url, status_code)

        # Determine error code based on status code
        if status_code:
            if 400 <= status_code < 500:
                self.set_error_code(f"NETWORK_CLIENT_{status_code}")
                self.set_severity(ErrorSeverity.HIGH)
                self.set_recoverable(status_code in [408, 429])  # Timeout and rate limit are recoverable
            elif 500 <= status_code < 600:
                self.set_error_code(f"NETWORK_SERVER_{status_code}")
                self.set_severity(ErrorSeverity.MEDIUM)
                self.set_recoverable(True)
            else:
                self.set_error_code(f"NETWORK_HTTP_{status_code}")
        else:
            self.set_error_code("NETWORK_CONNECTION_001")

        self.set_category(ErrorCategory.NETWORK)

        # Add context-specific recovery instructions
        if status_code == 429 or "rate limit" in message.lower():
            self.add_recovery_instruction(RecoveryInstruction(
                action=RecoveryAction.RETRY_WITH_BACKOFF,
                parameters={"initial_delay": 60, "max_delay": 300, "backoff_factor": 2.0}
            ))
        elif status_code in [500, 502, 503, 504] or "timeout" in message.lower():
            self.add_recovery_instruction(RecoveryInstruction(
                action=RecoveryAction.RETRY_WITH_BACKOFF,
                parameters={"initial_delay": 5, "max_delay": 60, "backoff_factor": 1.5}
            ))
        elif "connection" in message.lower():
            self.add_recovery_instruction(RecoveryInstruction(
                action=RecoveryAction.CHECK_NETWORK,
                parameters={"target_url": url}
            ))

        # Always add fallback option
        self.add_recovery_instruction(RecoveryInstruction(
            action=RecoveryAction.FALLBACK_TO_CACHE,
            parameters={"cache_ttl_hours": 24}
        ))


class AIParseError(AIFriendlyError, ParseError):
    """AI-enhanced parse error."""

    def __init__(self, message: str, page_content_length: int = None, **kwargs):
        super().__init__(message, page_content_length)

        self.set_error_code("PARSE_HTML_001")
        self.set_category(ErrorCategory.PARSING)
        self.set_severity(ErrorSeverity.MEDIUM)
        self.set_recoverable(True)

        # Add recovery instructions
        self.add_recovery_instruction(RecoveryInstruction(
            action=RecoveryAction.RETRY,
            parameters={"retry_reason": "HTML structure may have changed temporarily"}
        ))

        self.add_recovery_instruction(RecoveryInstruction(
            action=RecoveryAction.CHECK_EXTERNAL_SERVICE,
            parameters={"service_name": "ADOR_website", "expected_structure": kwargs.get("expected_structure")}
        ))

        if kwargs.get("fallback_parser"):
            self.add_recovery_instruction(RecoveryInstruction(
                action=RecoveryAction.USE_DEFAULT_VALUE,
                parameters={"fallback_parser": kwargs.get("fallback_parser")}
            ))


class AIRateLimitError(AIFriendlyError, RateLimitError):
    """AI-enhanced rate limit error."""

    def __init__(self, retry_after: int = None, **kwargs):
        super().__init__(retry_after)

        self.set_error_code("RATE_LIMIT_001")
        self.set_category(ErrorCategory.EXTERNAL_SERVICE)
        self.set_severity(ErrorSeverity.MEDIUM)
        self.set_recoverable(True)

        # Add specific retry instruction with rate limit handling
        retry_delay = retry_after or kwargs.get("default_retry_delay", 60)
        self.add_recovery_instruction(RecoveryInstruction(
            action=RecoveryAction.RETRY_WITH_BACKOFF,
            parameters={
                "initial_delay": retry_delay,
                "respect_retry_after": True,
                "add_jitter": True,
                "jitter_max": 10
            }
        ))


class AIDataProcessingError(AIFriendlyError, DataProcessingError):
    """AI-enhanced data processing error."""

    def __init__(self, message: str, operation: str = None, records_affected: int = None, **kwargs):
        super().__init__(message, operation, records_affected)

        self.set_error_code(f"DATA_PROCESSING_{operation.upper() if operation else 'GENERAL'}_001")
        self.set_category(ErrorCategory.BUSINESS_LOGIC)
        self.set_severity(ErrorSeverity.MEDIUM)
        self.set_recoverable(True)

        # Add recovery instructions based on operation type
        if operation and "calculation" in operation.lower():
            self.add_recovery_instruction(RecoveryInstruction(
                action=RecoveryAction.USE_DEFAULT_VALUE,
                parameters={"calculation_method": "fallback", "affected_records": records_affected}
            ))

        self.add_recovery_instruction(RecoveryInstruction(
            action=RecoveryAction.LOG_AND_CONTINUE,
            parameters={"operation": operation, "records_affected": records_affected}
        ))


class AIConfigurationError(AIFriendlyError, ConfigurationError):
    """AI-enhanced configuration error."""

    def __init__(self, message: str, config_key: str = None, **kwargs):
        super().__init__(message, config_key)

        self.set_error_code(f"CONFIG_{config_key.upper() if config_key else 'GENERAL'}_001")
        self.set_category(ErrorCategory.CONFIGURATION)
        self.set_severity(ErrorSeverity.HIGH)
        self.set_recoverable(kwargs.get("has_default", False))

        # Add recovery instructions
        self.add_recovery_instruction(RecoveryInstruction(
            action=RecoveryAction.CHECK_CONFIGURATION,
            parameters={"config_key": config_key, "expected_type": kwargs.get("expected_type")}
        ))

        if kwargs.get("default_value") is not None:
            self.add_recovery_instruction(RecoveryInstruction(
                action=RecoveryAction.USE_DEFAULT_VALUE,
                parameters={"default_value": kwargs.get("default_value")}
            ))
        else:
            self.add_recovery_instruction(RecoveryInstruction(
                action=RecoveryAction.ESCALATE_TO_HUMAN,
                parameters={"reason": "Configuration value required for operation"}
            ))


class AIFileOperationError(AIFriendlyError, FileOperationError):
    """AI-enhanced file operation error."""

    def __init__(self, message: str, file_path: str = None, operation: str = None, **kwargs):
        super().__init__(message, file_path, operation)

        self.set_error_code(f"FILE_{operation.upper() if operation else 'OPERATION'}_001")
        self.set_category(ErrorCategory.SYSTEM)
        self.set_severity(ErrorSeverity.MEDIUM)
        self.set_recoverable(True)

        # Add recovery instructions based on operation
        if operation == "read":
            self.add_recovery_instruction(RecoveryInstruction(
                action=RecoveryAction.RETRY,
                parameters={"file_path": file_path, "retry_reason": "File may be temporarily locked"}
            ))
            if kwargs.get("fallback_path"):
                self.add_recovery_instruction(RecoveryInstruction(
                    action=RecoveryAction.USE_DEFAULT_VALUE,
                    parameters={"fallback_path": kwargs.get("fallback_path")}
                ))
        elif operation == "write":
            self.add_recovery_instruction(RecoveryInstruction(
                action=RecoveryAction.RETRY,
                parameters={"file_path": file_path, "ensure_directory": True}
            ))


# Error correlation and tracking utilities
class ErrorCorrelationTracker:
    """Track and correlate errors for AI analysis."""

    def __init__(self):
        self.error_history: List[Dict[str, Any]] = []
        self.correlation_groups: Dict[str, List[str]] = {}

    def track_error(self, error: AIFriendlyError, context: Optional[Dict[str, Any]] = None):
        """Track an error occurrence."""
        error_data = error.to_ai_dict()
        if context:
            error_data["additional_context"] = context

        self.error_history.append(error_data)

        # Correlate with similar errors
        self._correlate_error(error)

    def _correlate_error(self, error: AIFriendlyError):
        """Correlate error with similar errors."""
        correlation_key = f"{error.category.value if error.category else 'unknown'}_{error.error_code}"

        if correlation_key not in self.correlation_groups:
            self.correlation_groups[correlation_key] = []

        self.correlation_groups[correlation_key].append(error.correlation_id)

    def get_error_patterns(self) -> Dict[str, Any]:
        """Get error patterns for AI analysis."""
        patterns = {}

        for correlation_key, error_ids in self.correlation_groups.items():
            if len(error_ids) > 1:  # Only patterns with multiple occurrences
                patterns[correlation_key] = {
                    "frequency": len(error_ids),
                    "error_ids": error_ids,
                    "latest_occurrence": max(
                        (e["timestamp"] for e in self.error_history if e["error_id"] in error_ids),
                        default=0
                    )
                }

        return patterns

    def suggest_improvements(self) -> List[Dict[str, Any]]:
        """Suggest improvements based on error patterns."""
        suggestions = []
        patterns = self.get_error_patterns()

        for pattern_key, pattern_data in patterns.items():
            if pattern_data["frequency"] > 5:  # Frequent error
                suggestions.append({
                    "type": "frequent_error",
                    "pattern": pattern_key,
                    "frequency": pattern_data["frequency"],
                    "suggestion": "Consider adding preventive measures or improving error handling",
                    "priority": "high" if pattern_data["frequency"] > 10 else "medium"
                })

        return suggestions


# Global error tracker instance
_error_tracker = ErrorCorrelationTracker()


def track_error(error: Union[AIFriendlyError, Exception], context: Optional[Dict[str, Any]] = None):
    """Global function to track errors."""
    if isinstance(error, AIFriendlyError):
        _error_tracker.track_error(error, context)
    else:
        # Convert regular exception to AI-friendly format
        ai_error = AIDataValidationError(str(error))
        ai_error.set_error_code("UNKNOWN_001")
        ai_error.set_category(ErrorCategory.SYSTEM)
        _error_tracker.track_error(ai_error, context)


def get_error_patterns() -> Dict[str, Any]:
    """Get current error patterns."""
    return _error_tracker.get_error_patterns()


def get_improvement_suggestions() -> List[Dict[str, Any]]:
    """Get suggestions for improving error handling."""
    return _error_tracker.suggest_improvements()


# Context manager for error tracking
class ErrorTrackingContext:
    """Context manager for tracking errors in specific operations."""

    def __init__(self, operation: str, component: str = None, **context_data):
        self.operation = operation
        self.component = component
        self.context_data = context_data
        self.context = None

    def __enter__(self):
        self.context = ErrorContext(
            timestamp=time.time(),
            correlation_id=str(uuid.uuid4()),
            operation=self.operation,
            component=self.component,
            **self.context_data
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val and isinstance(exc_val, AIFriendlyError):
            exc_val.set_context(self.context)
            track_error(exc_val)
        elif exc_val:
            # Convert regular exception
            ai_error = AIDataValidationError(str(exc_val))
            ai_error.set_context(self.context)
            track_error(ai_error)

        return False  # Don't suppress exceptions


# Utility functions for AI error analysis
def analyze_error_for_ai(error: Exception) -> Dict[str, Any]:
    """Analyze any error for AI consumption."""
    if isinstance(error, AIFriendlyError):
        return error.to_ai_dict()
    else:
        # Convert to AI-friendly format
        return {
            "error_id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "exception_type": type(error).__name__,
            "message": str(error),
            "recoverable": False,  # Unknown errors are not recoverable by default
            "severity": "medium",
            "category": "system",
            "stack_trace": traceback.format_exc()
        }


def create_error_from_dict(error_data: Dict[str, Any]) -> AIFriendlyError:
    """Create an AI-friendly error from dictionary data."""
    error = AIDataValidationError(error_data.get("message", "Unknown error"))

    if "error_code" in error_data:
        error.set_error_code(error_data["error_code"])
    if "category" in error_data:
        error.set_category(ErrorCategory(error_data["category"]))
    if "severity" in error_data:
        error.set_severity(ErrorSeverity(error_data["severity"]))
    if "recoverable" in error_data:
        error.set_recoverable(error_data["recoverable"])

    return error