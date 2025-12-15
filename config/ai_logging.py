"""
AI-friendly structured JSON logging system for Alabama Auction Watcher.

This module provides comprehensive logging capabilities specifically designed for
AI consumption, including structured JSON output, error correlation, performance
tracking, and automated log analysis.
"""

import json
import logging
import logging.handlers
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import contextmanager

# Import AI exceptions for integration
from scripts.ai_exceptions import AIFriendlyError


class LogLevel(Enum):
    """Log levels for AI categorization."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogCategory(Enum):
    """Log categories for AI classification."""
    PERFORMANCE = "performance"
    ERROR = "error"
    BUSINESS = "business"
    SECURITY = "security"
    SYSTEM = "system"
    USER_ACTION = "user_action"
    EXTERNAL_SERVICE = "external_service"
    DATA_FLOW = "data_flow"


@dataclass
class LogContext:
    """Structured log context for AI analysis."""
    timestamp: float
    correlation_id: str
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    operation: Optional[str] = None
    component: Optional[str] = None
    version: Optional[str] = None
    environment: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class PerformanceMetrics:
    """Performance metrics for AI analysis."""
    operation: str
    duration_ms: float
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    records_processed: Optional[int] = None
    records_per_second: Optional[float] = None
    error_count: int = 0
    success_rate: Optional[float] = None
    throughput_mbps: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class ErrorMetrics:
    """Error metrics for AI analysis."""
    error_type: str
    error_code: Optional[str] = None
    error_category: Optional[str] = None
    severity: str = "medium"
    recoverable: bool = False
    recovery_time_ms: Optional[float] = None
    impact_score: Optional[float] = None
    related_errors: List[str] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.related_errors is None:
            self.related_errors = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class AIJSONFormatter(logging.Formatter):
    """JSON formatter for AI-consumable logs."""

    def __init__(self, include_extra_fields: bool = True):
        """Initialize the JSON formatter."""
        super().__init__()
        self.include_extra_fields = include_extra_fields

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Build base log entry
        log_entry = {
            "timestamp": record.created,
            "timestamp_iso": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
            "process": record.process
        }

        # Add correlation tracking
        if hasattr(record, 'correlation_id'):
            log_entry["correlation_id"] = record.correlation_id
        else:
            log_entry["correlation_id"] = str(uuid.uuid4())

        # Add context if available
        if hasattr(record, 'context'):
            log_entry["context"] = record.context.to_dict() if hasattr(record.context, 'to_dict') else record.context

        # Add performance metrics if available
        if hasattr(record, 'performance_metrics'):
            log_entry["performance_metrics"] = record.performance_metrics.to_dict() if hasattr(record.performance_metrics, 'to_dict') else record.performance_metrics

        # Add error metrics if available
        if hasattr(record, 'error_metrics'):
            log_entry["error_metrics"] = record.error_metrics.to_dict() if hasattr(record.error_metrics, 'to_dict') else record.error_metrics

        # Add category for AI classification
        if hasattr(record, 'category'):
            log_entry["category"] = record.category.value if isinstance(record.category, LogCategory) else record.category
        else:
            # Auto-detect category based on level and content
            log_entry["category"] = self._auto_detect_category(record)

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }

        # Add extra fields if enabled
        if self.include_extra_fields:
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in log_entry and not key.startswith('_'):
                    if self._is_serializable(value):
                        extra_fields[key] = value
            if extra_fields:
                log_entry["extra"] = extra_fields

        # Add AI analysis hints
        log_entry["ai_analysis"] = {
            "importance": self._calculate_importance(record),
            "actionable": self._is_actionable(record),
            "anomaly_score": self._calculate_anomaly_score(record)
        }

        return json.dumps(log_entry, default=str, separators=(',', ':'))

    def _auto_detect_category(self, record: logging.LogRecord) -> str:
        """Auto-detect log category based on content."""
        message_lower = record.getMessage().lower()

        if record.levelname in ['ERROR', 'CRITICAL'] or record.exc_info:
            return LogCategory.ERROR.value
        elif 'performance' in message_lower or 'duration' in message_lower or 'rate' in message_lower:
            return LogCategory.PERFORMANCE.value
        elif 'user' in message_lower or 'request' in message_lower:
            return LogCategory.USER_ACTION.value
        elif 'network' in message_lower or 'http' in message_lower or 'api' in message_lower:
            return LogCategory.EXTERNAL_SERVICE.value
        elif 'processing' in message_lower or 'data' in message_lower:
            return LogCategory.DATA_FLOW.value
        else:
            return LogCategory.SYSTEM.value

    def _calculate_importance(self, record: logging.LogRecord) -> float:
        """Calculate importance score for AI prioritization."""
        base_score = {
            'DEBUG': 0.1,
            'INFO': 0.3,
            'WARNING': 0.6,
            'ERROR': 0.8,
            'CRITICAL': 1.0
        }.get(record.levelname, 0.3)

        # Boost score for certain keywords
        message_lower = record.getMessage().lower()
        if any(keyword in message_lower for keyword in ['failed', 'error', 'critical', 'timeout']):
            base_score += 0.2
        if any(keyword in message_lower for keyword in ['performance', 'slow', 'memory']):
            base_score += 0.1

        return min(1.0, base_score)

    def _is_actionable(self, record: logging.LogRecord) -> bool:
        """Determine if the log entry is actionable for AI."""
        if record.levelname in ['ERROR', 'CRITICAL']:
            return True

        message_lower = record.getMessage().lower()
        actionable_keywords = ['failed', 'timeout', 'retry', 'performance', 'memory', 'slow']
        return any(keyword in message_lower for keyword in actionable_keywords)

    def _calculate_anomaly_score(self, record: logging.LogRecord) -> float:
        """Calculate anomaly score for AI monitoring."""
        # Basic anomaly detection based on log patterns
        message = record.getMessage()

        # High anomaly indicators
        if record.levelname == 'CRITICAL':
            return 0.9
        if record.levelname == 'ERROR':
            return 0.7
        if 'exception' in message.lower() or 'failed' in message.lower():
            return 0.6

        # Medium anomaly indicators
        if record.levelname == 'WARNING':
            return 0.4
        if 'slow' in message.lower() or 'timeout' in message.lower():
            return 0.3

        return 0.1

    def _is_serializable(self, value: Any) -> bool:
        """Check if a value is JSON serializable."""
        try:
            json.dumps(value, default=str)
            return True
        except (TypeError, ValueError):
            return False


class AILoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds AI-friendly context to log records."""

    def __init__(self, logger: logging.Logger, extra: Dict[str, Any] = None):
        """Initialize the adapter."""
        super().__init__(logger, extra or {})
        self.correlation_id = str(uuid.uuid4())

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Process log message with AI context."""
        # Add correlation ID to extra
        if 'extra' not in kwargs:
            kwargs['extra'] = {}

        kwargs['extra']['correlation_id'] = self.correlation_id

        # Add any adapter extra fields
        kwargs['extra'].update(self.extra)

        return msg, kwargs

    def log_performance(self, operation: str, duration_ms: float, **metrics) -> None:
        """Log performance metrics in AI-friendly format."""
        performance_metrics = PerformanceMetrics(
            operation=operation,
            duration_ms=duration_ms,
            **metrics
        )

        self.info(
            f"Performance: {operation} completed in {duration_ms:.2f}ms",
            extra={
                'category': LogCategory.PERFORMANCE,
                'performance_metrics': performance_metrics
            }
        )

    def log_error_with_ai_context(self, error: Exception, operation: str = None, **context) -> None:
        """Log error with comprehensive AI context."""
        error_metrics = ErrorMetrics(
            error_type=type(error).__name__,
            error_code=getattr(error, 'error_code', None),
            error_category=getattr(error, 'category', {}).get('value') if hasattr(error, 'category') else None,
            severity=getattr(error, 'severity', {}).get('value', 'medium') if hasattr(error, 'severity') else 'medium',
            recoverable=getattr(error, 'recoverable', False)
        )

        # If it's an AI-friendly error, get additional context
        if isinstance(error, AIFriendlyError):
            error_dict = error.to_ai_dict()
            self.error(
                f"AI Error: {operation or 'Operation'} failed: {str(error)}",
                extra={
                    'category': LogCategory.ERROR,
                    'error_metrics': error_metrics,
                    'ai_error_data': error_dict,
                    'operation': operation,
                    **context
                },
                exc_info=True
            )
        else:
            self.error(
                f"Error: {operation or 'Operation'} failed: {str(error)}",
                extra={
                    'category': LogCategory.ERROR,
                    'error_metrics': error_metrics,
                    'operation': operation,
                    **context
                },
                exc_info=True
            )

    def log_user_action(self, action: str, user_id: str = None, **details) -> None:
        """Log user action for AI behavior analysis."""
        self.info(
            f"User action: {action}",
            extra={
                'category': LogCategory.USER_ACTION,
                'user_id': user_id,
                'action': action,
                'action_details': details
            }
        )

    def log_business_event(self, event: str, **data) -> None:
        """Log business event for AI analytics."""
        self.info(
            f"Business event: {event}",
            extra={
                'category': LogCategory.BUSINESS,
                'event': event,
                'event_data': data
            }
        )


class AILogAnalyzer:
    """Real-time log analyzer for AI insights."""

    def __init__(self):
        """Initialize the analyzer."""
        self.log_buffer: List[Dict[str, Any]] = []
        self.error_patterns: Dict[str, int] = {}
        self.performance_baseline: Dict[str, float] = {}
        self.anomaly_threshold = 0.7

    def analyze_log_entry(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single log entry for AI insights."""
        analysis = {
            "timestamp": log_entry.get("timestamp"),
            "log_id": log_entry.get("correlation_id"),
            "insights": [],
            "recommendations": [],
            "alerts": []
        }

        # Analyze error patterns
        if log_entry.get("level") in ["error", "critical"]:
            self._analyze_error_patterns(log_entry, analysis)

        # Analyze performance anomalies
        if log_entry.get("category") == "performance":
            self._analyze_performance_anomalies(log_entry, analysis)

        # Check for security issues
        self._analyze_security_indicators(log_entry, analysis)

        # Detect operational issues
        self._analyze_operational_health(log_entry, analysis)

        return analysis

    def _analyze_error_patterns(self, log_entry: Dict[str, Any], analysis: Dict[str, Any]) -> None:
        """Analyze error patterns for trending issues."""
        error_type = log_entry.get("exception", {}).get("type", "unknown")
        self.error_patterns[error_type] = self.error_patterns.get(error_type, 0) + 1

        if self.error_patterns[error_type] > 5:  # Threshold for pattern detection
            analysis["alerts"].append({
                "type": "error_pattern",
                "severity": "high",
                "message": f"Frequent {error_type} errors detected ({self.error_patterns[error_type]} occurrences)",
                "recommendation": "Investigate root cause and implement preventive measures"
            })

    def _analyze_performance_anomalies(self, log_entry: Dict[str, Any], analysis: Dict[str, Any]) -> None:
        """Analyze performance metrics for anomalies."""
        perf_metrics = log_entry.get("performance_metrics", {})
        operation = perf_metrics.get("operation")
        duration = perf_metrics.get("duration_ms")

        if operation and duration:
            baseline = self.performance_baseline.get(operation, duration)

            # Update baseline (simple moving average)
            self.performance_baseline[operation] = (baseline + duration) / 2

            # Check for performance degradation
            if duration > baseline * 2:  # 2x slower than baseline
                analysis["alerts"].append({
                    "type": "performance_degradation",
                    "severity": "medium",
                    "message": f"Operation {operation} took {duration:.2f}ms (baseline: {baseline:.2f}ms)",
                    "recommendation": "Investigate performance bottleneck"
                })

    def _analyze_security_indicators(self, log_entry: Dict[str, Any], analysis: Dict[str, Any]) -> None:
        """Analyze for security-related indicators."""
        message = log_entry.get("message", "").lower()
        security_keywords = ["unauthorized", "forbidden", "invalid", "attack", "breach"]

        if any(keyword in message for keyword in security_keywords):
            analysis["alerts"].append({
                "type": "security_indicator",
                "severity": "high",
                "message": "Potential security-related event detected",
                "recommendation": "Review security logs and implement additional monitoring"
            })

    def _analyze_operational_health(self, log_entry: Dict[str, Any], analysis: Dict[str, Any]) -> None:
        """Analyze operational health indicators."""
        ai_analysis = log_entry.get("ai_analysis", {})
        anomaly_score = ai_analysis.get("anomaly_score", 0)

        if anomaly_score > self.anomaly_threshold:
            analysis["insights"].append({
                "type": "anomaly_detected",
                "score": anomaly_score,
                "message": "High anomaly score detected",
                "recommendation": "Monitor system behavior and investigate if pattern continues"
            })

    def get_system_health_summary(self) -> Dict[str, Any]:
        """Generate system health summary for AI monitoring."""
        return {
            "timestamp": time.time(),
            "error_patterns": dict(self.error_patterns),
            "performance_baselines": dict(self.performance_baseline),
            "total_errors": sum(self.error_patterns.values()),
            "health_score": self._calculate_health_score(),
            "recommendations": self._generate_health_recommendations()
        }

    def _calculate_health_score(self) -> float:
        """Calculate overall system health score."""
        total_errors = sum(self.error_patterns.values())
        if total_errors == 0:
            return 1.0

        # Simple health score calculation
        error_penalty = min(0.5, total_errors * 0.1)
        return max(0.0, 1.0 - error_penalty)

    def _generate_health_recommendations(self) -> List[str]:
        """Generate health recommendations based on current state."""
        recommendations = []

        if sum(self.error_patterns.values()) > 10:
            recommendations.append("High error rate detected - investigate error patterns")

        if len(self.error_patterns) > 5:
            recommendations.append("Multiple error types occurring - review system stability")

        return recommendations


class AILoggingManager:
    """Centralized AI logging management."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the logging manager."""
        self.config = config or {}
        self.loggers: Dict[str, AILoggerAdapter] = {}
        self.analyzer = AILogAnalyzer()
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up logging handlers with AI-friendly configuration."""
        # JSON file handler for AI consumption
        json_log_path = self.config.get('json_log_file', 'logs/ai_structured.jsonl')
        self._setup_json_handler(json_log_path)

        # Console handler for human readability
        if self.config.get('console_output', True):
            self._setup_console_handler()

        # Error-specific handler for critical issues
        error_log_path = self.config.get('error_log_file', 'logs/ai_errors.jsonl')
        self._setup_error_handler(error_log_path)

    def _setup_json_handler(self, log_path: str):
        """Set up JSON file handler."""
        log_file = Path(log_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=50*1024*1024,  # 50MB
            backupCount=10
        )
        handler.setFormatter(AIJSONFormatter())
        handler.setLevel(logging.DEBUG)

        # Add to root logger
        logging.getLogger().addHandler(handler)

    def _setup_console_handler(self):
        """Set up console handler with readable format."""
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        handler.setLevel(logging.INFO)

        logging.getLogger().addHandler(handler)

    def _setup_error_handler(self, log_path: str):
        """Set up error-specific handler."""
        log_file = Path(log_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        handler.setFormatter(AIJSONFormatter())
        handler.setLevel(logging.ERROR)

        logging.getLogger().addHandler(handler)

    def get_logger(self, name: str, **context) -> AILoggerAdapter:
        """Get an AI-enhanced logger for a specific component."""
        if name not in self.loggers:
            base_logger = logging.getLogger(name)
            self.loggers[name] = AILoggerAdapter(base_logger, context)

        return self.loggers[name]

    def create_operation_context(self, operation: str, **context) -> LogContext:
        """Create operation context for correlation tracking."""
        return LogContext(
            timestamp=time.time(),
            correlation_id=str(uuid.uuid4()),
            operation=operation,
            **context
        )

    @contextmanager
    def operation_context(self, operation: str, **context):
        """Context manager for operation logging."""
        log_context = self.create_operation_context(operation, **context)
        logger = self.get_logger(f"operation.{operation}")

        logger.info(
            f"Operation started: {operation}",
            extra={'context': log_context, 'category': LogCategory.SYSTEM}
        )

        start_time = time.time()
        try:
            yield logger
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.log_error_with_ai_context(e, operation, duration_ms=duration_ms)
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            logger.log_performance(operation, duration_ms)
            logger.info(
                f"Operation completed: {operation}",
                extra={'context': log_context, 'category': LogCategory.SYSTEM}
            )


# Global logging manager instance
_ai_logging_manager = None


def get_ai_logger(name: str, **context) -> AILoggerAdapter:
    """Get an AI-enhanced logger instance."""
    global _ai_logging_manager
    if _ai_logging_manager is None:
        _ai_logging_manager = AILoggingManager()
    return _ai_logging_manager.get_logger(name, **context)


def setup_ai_logging(config: Dict[str, Any] = None) -> AILoggingManager:
    """Set up AI logging system."""
    global _ai_logging_manager
    _ai_logging_manager = AILoggingManager(config)
    return _ai_logging_manager


@contextmanager
def ai_operation_context(operation: str, **context):
    """Context manager for AI operation logging."""
    global _ai_logging_manager
    if _ai_logging_manager is None:
        _ai_logging_manager = AILoggingManager()

    with _ai_logging_manager.operation_context(operation, **context) as logger:
        yield logger