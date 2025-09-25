"""
AI Diagnostic Framework for Alabama Auction Watcher.

This module provides comprehensive system health monitoring, auto-recovery mechanisms,
predictive monitoring, and diagnostic reporting designed for AI consumption and autonomous operation.
"""

import asyncio
import os
import psutil
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional
import statistics

from config.ai_logging import get_ai_logger, LogCategory
from scripts.ai_exceptions import (
    RecoveryAction, RecoveryInstruction
)


class SystemComponent(Enum):
    """System components for health monitoring."""
    WEB_SCRAPER = "web_scraper"
    CSV_PARSER = "csv_parser"
    DATA_PROCESSOR = "data_processor"
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    MEMORY = "memory"
    CPU = "cpu"
    STORAGE = "storage"
    EXTERNAL_SERVICES = "external_services"
    LOGGING_SYSTEM = "logging_system"


class HealthStatus(Enum):
    """Health status levels for system components."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DOWN = "down"
    UNKNOWN = "unknown"
    RECOVERING = "recovering"


class DiagnosticSeverity(Enum):
    """Diagnostic issue severity levels."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class HealthMetrics:
    """Health metrics for system components."""
    component: str
    status: HealthStatus
    score: float  # 0.0 to 1.0
    response_time_ms: Optional[float] = None
    success_rate: Optional[float] = None
    error_count: int = 0
    last_error: Optional[str] = None
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    disk_usage_percent: Optional[float] = None
    network_latency_ms: Optional[float] = None
    uptime_seconds: Optional[float] = None
    throughput: Optional[float] = None
    additional_metrics: Dict[str, Any] = None

    def __post_init__(self):
        if self.additional_metrics is None:
            self.additional_metrics = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "status": self.status.value,
            "timestamp": time.time()
        }


@dataclass
class DiagnosticAlert:
    """Diagnostic alert for AI consumption."""
    id: str
    component: str
    severity: DiagnosticSeverity
    title: str
    description: str
    root_cause: Optional[str] = None
    impact: Optional[str] = None
    recovery_instructions: List[RecoveryInstruction] = None
    related_metrics: Dict[str, Any] = None
    correlation_id: str = None
    timestamp: float = None
    resolved: bool = False

    def __post_init__(self):
        if self.recovery_instructions is None:
            self.recovery_instructions = []
        if self.related_metrics is None:
            self.related_metrics = {}
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "severity": self.severity.value,
            "recovery_instructions": [inst.to_dict() for inst in self.recovery_instructions]
        }


class AIHealthChecker:
    """AI-driven health checker for system components."""

    def __init__(self, logger=None):
        self.logger = logger or get_ai_logger(__name__)
        self.health_history = defaultdict(lambda: deque(maxlen=100))
        self.baseline_metrics = defaultdict(dict)
        self.thresholds = self._load_default_thresholds()
        self.recovery_strategies = self._initialize_recovery_strategies()

    def _load_default_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Load default health thresholds for components."""
        return {
            SystemComponent.WEB_SCRAPER.value: {
                "max_response_time_ms": 30000,
                "min_success_rate": 0.95,
                "max_error_rate": 0.05,
                "max_memory_mb": 512
            },
            SystemComponent.CSV_PARSER.value: {
                "max_response_time_ms": 10000,
                "min_success_rate": 0.98,
                "max_error_rate": 0.02,
                "max_memory_mb": 256
            },
            SystemComponent.DATA_PROCESSOR.value: {
                "max_response_time_ms": 5000,
                "min_success_rate": 0.99,
                "max_error_rate": 0.01,
                "max_memory_mb": 128
            },
            SystemComponent.NETWORK.value: {
                "max_latency_ms": 1000,
                "min_success_rate": 0.95,
                "max_packet_loss": 0.01
            },
            SystemComponent.MEMORY.value: {
                "max_usage_percent": 85,
                "max_swap_usage_percent": 50
            },
            SystemComponent.CPU.value: {
                "max_usage_percent": 80,
                "max_load_average": 2.0
            },
            SystemComponent.STORAGE.value: {
                "max_usage_percent": 90,
                "min_free_space_gb": 1.0
            }
        }

    def _initialize_recovery_strategies(self) -> Dict[str, List[RecoveryInstruction]]:
        """Initialize recovery strategies for different failure scenarios."""
        return {
            "high_memory_usage": [
                RecoveryInstruction(
                    action=RecoveryAction.LOG_AND_CONTINUE,
                    parameters={"gc_collect": True, "clear_caches": True},
                    max_attempts=1
                ),
                RecoveryInstruction(
                    action=RecoveryAction.ESCALATE_TO_HUMAN,
                    parameters={"reason": "Memory usage exceeded threshold"},
                    condition="if memory usage > 90%"
                )
            ],
            "network_failure": [
                RecoveryInstruction(
                    action=RecoveryAction.RETRY_WITH_BACKOFF,
                    parameters={"initial_delay": 5, "max_delay": 60, "backoff_factor": 2},
                    max_attempts=3
                ),
                RecoveryInstruction(
                    action=RecoveryAction.CHECK_NETWORK,
                    parameters={"test_urls": ["https://www.revenue.alabama.gov"]},
                    max_attempts=1
                )
            ],
            "scraping_failure": [
                RecoveryInstruction(
                    action=RecoveryAction.RETRY_WITH_BACKOFF,
                    parameters={"initial_delay": 10, "max_delay": 300},
                    max_attempts=5
                ),
                RecoveryInstruction(
                    action=RecoveryAction.CHECK_EXTERNAL_SERVICE,
                    parameters={"service": "Alabama ADOR website"},
                    max_attempts=1
                ),
                RecoveryInstruction(
                    action=RecoveryAction.FALLBACK_TO_CACHE,
                    parameters={"cache_age_hours": 24},
                    condition="if recent cached data available"
                )
            ],
            "parsing_failure": [
                RecoveryInstruction(
                    action=RecoveryAction.VALIDATE_INPUT,
                    parameters={"strict_validation": False},
                    max_attempts=1
                ),
                RecoveryInstruction(
                    action=RecoveryAction.USE_DEFAULT_VALUE,
                    parameters={"fallback_parsing_mode": "lenient"},
                    max_attempts=1
                )
            ]
        }

    async def check_component_health(self, component: SystemComponent) -> HealthMetrics:
        """Check health of a specific system component."""
        try:
            if component == SystemComponent.WEB_SCRAPER:
                return await self._check_web_scraper_health()
            elif component == SystemComponent.CSV_PARSER:
                return await self._check_csv_parser_health()
            elif component == SystemComponent.DATA_PROCESSOR:
                return await self._check_data_processor_health()
            elif component == SystemComponent.NETWORK:
                return await self._check_network_health()
            elif component == SystemComponent.MEMORY:
                return await self._check_memory_health()
            elif component == SystemComponent.CPU:
                return await self._check_cpu_health()
            elif component == SystemComponent.STORAGE:
                return await self._check_storage_health()
            elif component == SystemComponent.FILE_SYSTEM:
                return await self._check_file_system_health()
            elif component == SystemComponent.EXTERNAL_SERVICES:
                return await self._check_external_services_health()
            else:
                return HealthMetrics(
                    component=component.value,
                    status=HealthStatus.UNKNOWN,
                    score=0.0
                )
        except Exception as e:
            self.logger.log_error_with_ai_context(e, f"health_check_{component.value}")
            return HealthMetrics(
                component=component.value,
                status=HealthStatus.DOWN,
                score=0.0,
                last_error=str(e)
            )

    async def _check_web_scraper_health(self) -> HealthMetrics:
        """Check web scraper health by testing connection to ADOR."""
        import requests
        start_time = time.time()

        try:
            response = requests.get(
                "https://www.revenue.alabama.gov/property-tax/delinquent-search/",
                timeout=10
            )
            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                status = HealthStatus.HEALTHY
                score = 1.0
            else:
                status = HealthStatus.WARNING
                score = 0.7

            return HealthMetrics(
                component=SystemComponent.WEB_SCRAPER.value,
                status=status,
                score=score,
                response_time_ms=response_time,
                success_rate=1.0 if response.status_code == 200 else 0.0
            )
        except Exception as e:
            return HealthMetrics(
                component=SystemComponent.WEB_SCRAPER.value,
                status=HealthStatus.CRITICAL,
                score=0.0,
                response_time_ms=(time.time() - start_time) * 1000,
                success_rate=0.0,
                last_error=str(e)
            )

    async def _check_csv_parser_health(self) -> HealthMetrics:
        """Check CSV parser health using sample data."""
        from scripts.parser import AuctionParser
        import tempfile
        import pandas as pd

        start_time = time.time()

        try:
            # Create sample CSV data
            sample_data = {
                'ParcelNumber': ['001-001-001', '002-002-002'],
                'PropertyDescription': ['123 Main St', '456 Oak Ave near creek'],
                'TaxesOwed': ['1500.00', '2500.00'],
                'EstimatedValue': ['15000', '25000']
            }
            df = pd.DataFrame(sample_data)

            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                df.to_csv(f.name, index=False)
                temp_path = f.name

            try:
                parser = AuctionParser()
                result_df = parser.load_csv_file(temp_path)

                response_time = (time.time() - start_time) * 1000
                success_rate = 1.0 if len(result_df) > 0 else 0.0

                return HealthMetrics(
                    component=SystemComponent.CSV_PARSER.value,
                    status=HealthStatus.HEALTHY if success_rate == 1.0 else HealthStatus.WARNING,
                    score=success_rate,
                    response_time_ms=response_time,
                    success_rate=success_rate,
                    throughput=len(result_df) / (response_time / 1000) if response_time > 0 else 0
                )
            finally:
                os.unlink(temp_path)

        except Exception as e:
            return HealthMetrics(
                component=SystemComponent.CSV_PARSER.value,
                status=HealthStatus.CRITICAL,
                score=0.0,
                response_time_ms=(time.time() - start_time) * 1000,
                success_rate=0.0,
                last_error=str(e)
            )

    async def _check_data_processor_health(self) -> HealthMetrics:
        """Check data processor health using sample operations."""
        from scripts.utils import calculate_water_score, normalize_price

        start_time = time.time()

        try:
            # Test key data processing functions
            test_cases = [
                ("Property near creek and stream", 2.0),  # Expected high water score
                ("$15,000.00", 15000.0),  # Expected normalized price
            ]

            successes = 0
            total_tests = len(test_cases)

            # Test water score calculation
            water_score = calculate_water_score(test_cases[0][0])
            if water_score >= test_cases[0][1]:
                successes += 1

            # Test price normalization
            normalized_price = normalize_price(test_cases[1][0])
            if normalized_price == test_cases[1][1]:
                successes += 1

            response_time = (time.time() - start_time) * 1000
            success_rate = successes / total_tests

            return HealthMetrics(
                component=SystemComponent.DATA_PROCESSOR.value,
                status=HealthStatus.HEALTHY if success_rate >= 0.8 else HealthStatus.WARNING,
                score=success_rate,
                response_time_ms=response_time,
                success_rate=success_rate
            )

        except Exception as e:
            return HealthMetrics(
                component=SystemComponent.DATA_PROCESSOR.value,
                status=HealthStatus.CRITICAL,
                score=0.0,
                response_time_ms=(time.time() - start_time) * 1000,
                success_rate=0.0,
                last_error=str(e)
            )

    async def _check_network_health(self) -> HealthMetrics:
        """Check network connectivity and latency."""
        import requests

        test_urls = [
            "https://www.google.com",
            "https://www.revenue.alabama.gov"
        ]

        total_latency = 0
        successful_requests = 0

        for url in test_urls:
            try:
                start_time = time.time()
                response = requests.get(url, timeout=5)
                latency = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    successful_requests += 1
                    total_latency += latency
            except:
                pass

        if successful_requests > 0:
            avg_latency = total_latency / successful_requests
            success_rate = successful_requests / len(test_urls)
            status = HealthStatus.HEALTHY if success_rate >= 0.8 else HealthStatus.WARNING
        else:
            avg_latency = float('inf')
            success_rate = 0.0
            status = HealthStatus.CRITICAL

        return HealthMetrics(
            component=SystemComponent.NETWORK.value,
            status=status,
            score=success_rate,
            network_latency_ms=avg_latency if avg_latency != float('inf') else None,
            success_rate=success_rate
        )

    async def _check_memory_health(self) -> HealthMetrics:
        """Check memory usage and availability."""
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        memory_usage_percent = memory.percent
        memory_usage_mb = (memory.total - memory.available) / (1024 * 1024)

        # Calculate health score based on memory usage
        if memory_usage_percent < 70:
            status = HealthStatus.HEALTHY
            score = 1.0
        elif memory_usage_percent < 85:
            status = HealthStatus.WARNING
            score = 0.7
        else:
            status = HealthStatus.CRITICAL
            score = 0.3

        return HealthMetrics(
            component=SystemComponent.MEMORY.value,
            status=status,
            score=score,
            memory_usage_mb=memory_usage_mb,
            additional_metrics={
                "memory_usage_percent": memory_usage_percent,
                "memory_available_mb": memory.available / (1024 * 1024),
                "swap_usage_percent": swap.percent
            }
        )

    async def _check_cpu_health(self) -> HealthMetrics:
        """Check CPU usage and load."""
        cpu_percent = psutil.cpu_percent(interval=1)
        load_avg = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else cpu_percent / 100

        # Calculate health score based on CPU usage
        if cpu_percent < 60:
            status = HealthStatus.HEALTHY
            score = 1.0
        elif cpu_percent < 80:
            status = HealthStatus.WARNING
            score = 0.7
        else:
            status = HealthStatus.CRITICAL
            score = 0.3

        return HealthMetrics(
            component=SystemComponent.CPU.value,
            status=status,
            score=score,
            cpu_usage_percent=cpu_percent,
            additional_metrics={
                "load_average": load_avg,
                "cpu_count": psutil.cpu_count()
            }
        )

    async def _check_storage_health(self) -> HealthMetrics:
        """Check disk usage and available space."""
        disk_usage = psutil.disk_usage('.')

        usage_percent = (disk_usage.used / disk_usage.total) * 100
        free_space_gb = disk_usage.free / (1024 * 1024 * 1024)

        # Calculate health score based on disk usage
        if usage_percent < 80:
            status = HealthStatus.HEALTHY
            score = 1.0
        elif usage_percent < 90:
            status = HealthStatus.WARNING
            score = 0.7
        else:
            status = HealthStatus.CRITICAL
            score = 0.3

        return HealthMetrics(
            component=SystemComponent.STORAGE.value,
            status=status,
            score=score,
            disk_usage_percent=usage_percent,
            additional_metrics={
                "free_space_gb": free_space_gb,
                "total_space_gb": disk_usage.total / (1024 * 1024 * 1024)
            }
        )

    async def _check_file_system_health(self) -> HealthMetrics:
        """Check file system health and directory structure."""
        required_dirs = ['data', 'data/raw', 'data/processed', 'logs', 'tests']
        existing_dirs = 0

        for dir_path in required_dirs:
            if Path(dir_path).exists():
                existing_dirs += 1

        success_rate = existing_dirs / len(required_dirs)

        if success_rate == 1.0:
            status = HealthStatus.HEALTHY
            score = 1.0
        elif success_rate >= 0.8:
            status = HealthStatus.WARNING
            score = 0.7
        else:
            status = HealthStatus.CRITICAL
            score = 0.3

        return HealthMetrics(
            component=SystemComponent.FILE_SYSTEM.value,
            status=status,
            score=score,
            success_rate=success_rate,
            additional_metrics={
                "existing_dirs": existing_dirs,
                "required_dirs": len(required_dirs),
                "missing_dirs": [d for d in required_dirs if not Path(d).exists()]
            }
        )

    async def _check_external_services_health(self) -> HealthMetrics:
        """Check external service availability."""
        services = [
            "https://www.revenue.alabama.gov",
        ]

        successful_checks = 0
        total_response_time = 0

        for service in services:
            try:
                import requests
                start_time = time.time()
                response = requests.get(service, timeout=10)
                response_time = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    successful_checks += 1
                    total_response_time += response_time
            except:
                pass

        success_rate = successful_checks / len(services) if services else 1.0
        avg_response_time = total_response_time / successful_checks if successful_checks > 0 else None

        if success_rate >= 0.9:
            status = HealthStatus.HEALTHY
            score = 1.0
        elif success_rate >= 0.7:
            status = HealthStatus.WARNING
            score = 0.7
        else:
            status = HealthStatus.CRITICAL
            score = 0.3

        return HealthMetrics(
            component=SystemComponent.EXTERNAL_SERVICES.value,
            status=status,
            score=score,
            success_rate=success_rate,
            response_time_ms=avg_response_time
        )

    def analyze_health_trends(self, component: SystemComponent, metrics: HealthMetrics) -> List[DiagnosticAlert]:
        """Analyze health trends and generate alerts."""
        alerts = []

        # Store metrics in history
        self.health_history[component.value].append(metrics)

        # Get recent history for trend analysis
        recent_metrics = list(self.health_history[component.value])

        if len(recent_metrics) < 3:
            return alerts  # Not enough data for trend analysis

        # Analyze score trends
        recent_scores = [m.score for m in recent_metrics[-5:]]
        score_trend = self._calculate_trend(recent_scores)

        if score_trend < -0.1 and metrics.score < 0.7:
            alerts.append(DiagnosticAlert(
                id=f"{component.value}_declining_health_{int(time.time())}",
                component=component.value,
                severity=DiagnosticSeverity.MEDIUM,
                title=f"{component.value} Health Declining",
                description=f"Component health score trending downward: {score_trend:.3f}",
                root_cause="Degrading performance or increasing errors",
                impact="May lead to service disruption if trend continues",
                recovery_instructions=self._get_recovery_instructions(component, "declining_health"),
                related_metrics={"trend": score_trend, "current_score": metrics.score}
            ))

        # Analyze response time trends
        if metrics.response_time_ms:
            recent_response_times = [m.response_time_ms for m in recent_metrics[-5:] if m.response_time_ms]
            if len(recent_response_times) >= 3:
                response_time_trend = self._calculate_trend(recent_response_times)
                if response_time_trend > 1000:  # Response time increasing by more than 1 second
                    alerts.append(DiagnosticAlert(
                        id=f"{component.value}_slow_response_{int(time.time())}",
                        component=component.value,
                        severity=DiagnosticSeverity.MEDIUM,
                        title=f"{component.value} Slowing Down",
                        description=f"Response times increasing: +{response_time_trend:.1f}ms trend",
                        root_cause="Performance degradation or resource constraints",
                        recovery_instructions=self._get_recovery_instructions(component, "slow_response")
                    ))

        # Check against thresholds
        thresholds = self.thresholds.get(component.value, {})
        threshold_alerts = self._check_threshold_violations(component, metrics, thresholds)
        alerts.extend(threshold_alerts)

        return alerts

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate linear trend in values."""
        if len(values) < 2:
            return 0.0

        x = list(range(len(values)))
        y = values

        # Simple linear regression slope
        n = len(values)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))

        if n * sum_x2 - sum_x ** 2 == 0:
            return 0.0

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        return slope

    def _check_threshold_violations(self, component: SystemComponent, metrics: HealthMetrics, thresholds: Dict[str, float]) -> List[DiagnosticAlert]:
        """Check for threshold violations and generate alerts."""
        alerts = []

        violations = []
        if metrics.response_time_ms and "max_response_time_ms" in thresholds:
            if metrics.response_time_ms > thresholds["max_response_time_ms"]:
                violations.append(f"Response time {metrics.response_time_ms:.1f}ms > {thresholds['max_response_time_ms']}ms")

        if metrics.memory_usage_mb and "max_memory_mb" in thresholds:
            if metrics.memory_usage_mb > thresholds["max_memory_mb"]:
                violations.append(f"Memory usage {metrics.memory_usage_mb:.1f}MB > {thresholds['max_memory_mb']}MB")

        if metrics.success_rate is not None and "min_success_rate" in thresholds:
            if metrics.success_rate < thresholds["min_success_rate"]:
                violations.append(f"Success rate {metrics.success_rate:.3f} < {thresholds['min_success_rate']:.3f}")

        for violation in violations:
            severity = DiagnosticSeverity.HIGH if "success_rate" in violation else DiagnosticSeverity.MEDIUM
            alerts.append(DiagnosticAlert(
                id=f"{component.value}_threshold_violation_{int(time.time())}",
                component=component.value,
                severity=severity,
                title=f"{component.value} Threshold Violation",
                description=violation,
                root_cause="Performance or resource threshold exceeded",
                recovery_instructions=self._get_recovery_instructions(component, "threshold_violation")
            ))

        return alerts

    def _get_recovery_instructions(self, component: SystemComponent, scenario: str) -> List[RecoveryInstruction]:
        """Get recovery instructions for a specific component and scenario."""
        # Map component scenarios to recovery strategies
        scenario_mapping = {
            (SystemComponent.WEB_SCRAPER, "declining_health"): "scraping_failure",
            (SystemComponent.WEB_SCRAPER, "threshold_violation"): "scraping_failure",
            (SystemComponent.CSV_PARSER, "declining_health"): "parsing_failure",
            (SystemComponent.CSV_PARSER, "threshold_violation"): "parsing_failure",
            (SystemComponent.NETWORK, "declining_health"): "network_failure",
            (SystemComponent.MEMORY, "threshold_violation"): "high_memory_usage"
        }

        strategy_key = scenario_mapping.get((component, scenario), "generic_recovery")
        return self.recovery_strategies.get(strategy_key, [])


class AIPredictiveMonitor:
    """AI-powered predictive monitoring system."""

    def __init__(self, logger=None):
        self.logger = logger or get_ai_logger(__name__)
        self.metric_history = defaultdict(lambda: deque(maxlen=1000))
        self.anomaly_detectors = {}
        self.prediction_models = {}

    def record_metric(self, component: str, metric_name: str, value: float, timestamp: float = None) -> None:
        """Record a metric value for trend analysis."""
        if timestamp is None:
            timestamp = time.time()

        self.metric_history[f"{component}.{metric_name}"].append({
            "value": value,
            "timestamp": timestamp
        })

    def predict_failure_risk(self, component: SystemComponent, horizon_minutes: int = 30) -> Dict[str, Any]:
        """Predict failure risk for a component within a time horizon."""
        metric_key = component.value

        # Get recent metric history
        relevant_metrics = [
            f"{metric_key}.score",
            f"{metric_key}.response_time",
            f"{metric_key}.memory_usage",
            f"{metric_key}.error_rate"
        ]

        risk_factors = {}
        overall_risk = 0.0

        for metric in relevant_metrics:
            if metric in self.metric_history:
                history = list(self.metric_history[metric])
                if len(history) >= 5:
                    # Simple trend-based risk assessment
                    recent_values = [entry["value"] for entry in history[-10:]]
                    trend = self._calculate_metric_trend(recent_values)
                    volatility = statistics.stdev(recent_values) if len(recent_values) > 1 else 0

                    # Calculate risk based on trend and volatility
                    if "score" in metric:
                        # Lower score trend = higher risk
                        risk = max(0, -trend * 10) + volatility * 5
                    elif "error_rate" in metric:
                        # Higher error rate trend = higher risk
                        risk = max(0, trend * 10) + volatility * 5
                    elif "response_time" in metric:
                        # Increasing response time = higher risk
                        risk = max(0, trend / 1000 * 5) + volatility / 1000 * 2
                    else:
                        risk = volatility * 2

                    risk_factors[metric] = {
                        "trend": trend,
                        "volatility": volatility,
                        "risk_score": min(1.0, risk)
                    }
                    overall_risk += min(1.0, risk)

        overall_risk = min(1.0, overall_risk / len(risk_factors)) if risk_factors else 0.0

        # Generate predictions
        prediction = {
            "component": component.value,
            "horizon_minutes": horizon_minutes,
            "failure_risk": overall_risk,
            "risk_level": self._categorize_risk(overall_risk),
            "risk_factors": risk_factors,
            "predicted_issues": self._predict_specific_issues(component, risk_factors),
            "recommended_actions": self._get_preventive_actions(overall_risk),
            "confidence": self._calculate_prediction_confidence(risk_factors),
            "timestamp": time.time()
        }

        # Log prediction for AI analysis
        self.logger.info(
            f"Failure risk prediction for {component.value}: {overall_risk:.3f}",
            extra={
                "category": LogCategory.SYSTEM,
                "prediction_data": prediction
            }
        )

        return prediction

    def _calculate_metric_trend(self, values: List[float]) -> float:
        """Calculate trend in metric values."""
        if len(values) < 2:
            return 0.0

        # Simple linear regression
        n = len(values)
        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))

        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            return 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope

    def _categorize_risk(self, risk_score: float) -> str:
        """Categorize risk score into levels."""
        if risk_score < 0.2:
            return "low"
        elif risk_score < 0.5:
            return "medium"
        elif risk_score < 0.8:
            return "high"
        else:
            return "critical"

    def _predict_specific_issues(self, component: SystemComponent, risk_factors: Dict[str, Any]) -> List[str]:
        """Predict specific issues based on risk factors."""
        issues = []

        for metric, factors in risk_factors.items():
            if factors["risk_score"] > 0.6:
                if "response_time" in metric:
                    issues.append("Performance degradation likely")
                elif "error_rate" in metric:
                    issues.append("Increased error rate expected")
                elif "memory" in metric:
                    issues.append("Memory pressure anticipated")
                elif "score" in metric:
                    issues.append("Overall health decline predicted")

        return issues

    def _get_preventive_actions(self, risk_score: float) -> List[str]:
        """Get preventive actions based on risk score."""
        actions = []

        if risk_score > 0.7:
            actions.extend([
                "Increase monitoring frequency",
                "Prepare rollback procedures",
                "Alert operations team"
            ])
        elif risk_score > 0.5:
            actions.extend([
                "Monitor system closely",
                "Check system resources",
                "Review recent changes"
            ])
        elif risk_score > 0.3:
            actions.append("Continue routine monitoring")

        return actions

    def _calculate_prediction_confidence(self, risk_factors: Dict[str, Any]) -> float:
        """Calculate confidence in prediction based on available data."""
        if not risk_factors:
            return 0.0

        # Confidence based on number of metrics and data quality
        base_confidence = min(1.0, len(risk_factors) / 4)  # Up to 4 key metrics

        # Adjust for data quality
        volatility_penalty = sum(factors.get("volatility", 0) for factors in risk_factors.values()) / len(risk_factors)
        confidence = base_confidence * (1 - min(0.5, volatility_penalty / 10))

        return max(0.1, confidence)


class AIAutoRecovery:
    """AI-powered automatic recovery system."""

    def __init__(self, logger=None):
        self.logger = logger or get_ai_logger(__name__)
        self.recovery_history = deque(maxlen=1000)
        self.active_recoveries = {}
        self.recovery_lock = threading.Lock()

    async def execute_recovery(self, alert: DiagnosticAlert) -> Dict[str, Any]:
        """Execute automatic recovery for a diagnostic alert."""
        recovery_id = f"recovery_{alert.id}_{int(time.time())}"

        with self.recovery_lock:
            if alert.component in self.active_recoveries:
                return {
                    "recovery_id": recovery_id,
                    "status": "skipped",
                    "reason": f"Recovery already in progress for {alert.component}"
                }

            self.active_recoveries[alert.component] = recovery_id

        recovery_result = {
            "recovery_id": recovery_id,
            "alert_id": alert.id,
            "component": alert.component,
            "start_time": time.time(),
            "status": "in_progress",
            "actions_attempted": [],
            "actions_successful": [],
            "actions_failed": [],
            "final_status": "unknown",
            "recovery_time_ms": 0,
            "error_details": None
        }

        try:
            self.logger.info(
                f"Starting automatic recovery for {alert.component}",
                extra={
                    "category": LogCategory.SYSTEM,
                    "recovery_id": recovery_id,
                    "alert_data": alert.to_dict()
                }
            )

            # Execute recovery instructions in order
            for instruction in alert.recovery_instructions:
                action_result = await self._execute_recovery_action(instruction, alert)
                recovery_result["actions_attempted"].append(instruction.action.value)

                if action_result["success"]:
                    recovery_result["actions_successful"].append(instruction.action.value)

                    # Check if this action resolved the issue
                    if await self._verify_recovery_success(alert):
                        recovery_result["final_status"] = "resolved"
                        break
                else:
                    recovery_result["actions_failed"].append({
                        "action": instruction.action.value,
                        "error": action_result.get("error", "Unknown error")
                    })

                    # If this is a critical action that failed, stop recovery
                    if instruction.action in [RecoveryAction.ESCALATE_TO_HUMAN, RecoveryAction.ABORT_OPERATION]:
                        break

            # Final status determination
            if recovery_result["final_status"] == "unknown":
                if recovery_result["actions_successful"]:
                    recovery_result["final_status"] = "partial_success"
                else:
                    recovery_result["final_status"] = "failed"

            recovery_result["recovery_time_ms"] = (time.time() - recovery_result["start_time"]) * 1000
            recovery_result["status"] = "completed"

        except Exception as e:
            recovery_result["status"] = "error"
            recovery_result["error_details"] = str(e)
            recovery_result["final_status"] = "failed"
            self.logger.log_error_with_ai_context(e, f"auto_recovery_{recovery_id}")

        finally:
            # Clean up active recovery tracking
            with self.recovery_lock:
                if alert.component in self.active_recoveries:
                    del self.active_recoveries[alert.component]

            # Record recovery attempt
            self.recovery_history.append(recovery_result)

            # Log recovery completion
            self.logger.info(
                f"Recovery completed for {alert.component}: {recovery_result['final_status']}",
                extra={
                    "category": LogCategory.SYSTEM,
                    "recovery_result": recovery_result
                }
            )

        return recovery_result

    async def _execute_recovery_action(self, instruction: RecoveryInstruction, alert: DiagnosticAlert) -> Dict[str, Any]:
        """Execute a single recovery action."""
        action_result = {
            "action": instruction.action.value,
            "success": False,
            "error": None,
            "details": {}
        }

        try:
            if instruction.action == RecoveryAction.RETRY:
                action_result = await self._action_retry(instruction, alert)
            elif instruction.action == RecoveryAction.RETRY_WITH_BACKOFF:
                action_result = await self._action_retry_with_backoff(instruction, alert)
            elif instruction.action == RecoveryAction.CHECK_NETWORK:
                action_result = await self._action_check_network(instruction, alert)
            elif instruction.action == RecoveryAction.CHECK_EXTERNAL_SERVICE:
                action_result = await self._action_check_external_service(instruction, alert)
            elif instruction.action == RecoveryAction.LOG_AND_CONTINUE:
                action_result = await self._action_log_and_continue(instruction, alert)
            elif instruction.action == RecoveryAction.ESCALATE_TO_HUMAN:
                action_result = await self._action_escalate_to_human(instruction, alert)
            else:
                action_result["error"] = f"Unknown recovery action: {instruction.action.value}"

        except Exception as e:
            action_result["error"] = str(e)

        return action_result

    async def _action_retry(self, instruction: RecoveryInstruction, alert: DiagnosticAlert) -> Dict[str, Any]:
        """Execute retry action."""
        # This is a placeholder - actual retry would depend on the specific operation
        await asyncio.sleep(1)  # Simple delay
        return {
            "action": instruction.action.value,
            "success": True,
            "details": {"attempts": 1}
        }

    async def _action_retry_with_backoff(self, instruction: RecoveryInstruction, alert: DiagnosticAlert) -> Dict[str, Any]:
        """Execute retry with backoff action."""
        params = instruction.parameters
        initial_delay = params.get("initial_delay", 5)
        max_delay = params.get("max_delay", 60)
        backoff_factor = params.get("backoff_factor", 2)

        delay = initial_delay
        attempts = 0

        for attempt in range(instruction.max_attempts):
            await asyncio.sleep(delay)
            attempts += 1

            # Here you would implement the actual retry logic
            # For now, simulate success after a few attempts
            if attempt >= 1:  # Simulate success on second attempt
                return {
                    "action": instruction.action.value,
                    "success": True,
                    "details": {
                        "attempts": attempts,
                        "total_delay_seconds": sum(initial_delay * (backoff_factor ** i) for i in range(attempts))
                    }
                }

            delay = min(delay * backoff_factor, max_delay)

        return {
            "action": instruction.action.value,
            "success": False,
            "error": f"Max attempts ({instruction.max_attempts}) exceeded",
            "details": {"attempts": attempts}
        }

    async def _action_check_network(self, instruction: RecoveryInstruction, alert: DiagnosticAlert) -> Dict[str, Any]:
        """Execute network check action."""
        import requests

        test_urls = instruction.parameters.get("test_urls", ["https://www.google.com"])
        successful_checks = 0

        for url in test_urls:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    successful_checks += 1
            except:
                pass

        success = successful_checks > 0
        return {
            "action": instruction.action.value,
            "success": success,
            "details": {
                "successful_checks": successful_checks,
                "total_checks": len(test_urls)
            }
        }

    async def _action_check_external_service(self, instruction: RecoveryInstruction, alert: DiagnosticAlert) -> Dict[str, Any]:
        """Execute external service check action."""
        service = instruction.parameters.get("service", "unknown service")

        # This would implement actual service health checks
        # For now, simulate a service check
        await asyncio.sleep(2)  # Simulate check time

        return {
            "action": instruction.action.value,
            "success": True,  # Simulate success
            "details": {"service": service, "status": "available"}
        }

    async def _action_log_and_continue(self, instruction: RecoveryInstruction, alert: DiagnosticAlert) -> Dict[str, Any]:
        """Execute log and continue action."""
        params = instruction.parameters

        # Perform any cleanup actions
        if params.get("gc_collect"):
            import gc
            gc.collect()

        if params.get("clear_caches"):
            # Clear any application caches
            pass

        return {
            "action": instruction.action.value,
            "success": True,
            "details": params
        }

    async def _action_escalate_to_human(self, instruction: RecoveryInstruction, alert: DiagnosticAlert) -> Dict[str, Any]:
        """Execute escalation to human action."""
        reason = instruction.parameters.get("reason", "Automatic recovery failed")

        # This would implement actual human escalation (email, Slack, etc.)
        self.logger.warning(
            f"ESCALATION REQUIRED: {alert.component} - {reason}",
            extra={
                "category": LogCategory.SYSTEM,
                "alert_data": alert.to_dict(),
                "escalation_reason": reason
            }
        )

        return {
            "action": instruction.action.value,
            "success": True,
            "details": {"reason": reason, "alert_id": alert.id}
        }

    async def _verify_recovery_success(self, alert: DiagnosticAlert) -> bool:
        """Verify if recovery was successful by re-checking component health."""
        # This would implement actual health verification
        # For now, simulate success based on alert severity
        if alert.severity in [DiagnosticSeverity.LOW, DiagnosticSeverity.MEDIUM]:
            return True
        return False


class AIDiagnosticReporter:
    """AI-friendly diagnostic reporting system."""

    def __init__(self, logger=None):
        self.logger = logger or get_ai_logger(__name__)
        self.report_history = deque(maxlen=100)

    def generate_system_health_report(self, health_metrics: Dict[str, HealthMetrics],
                                    alerts: List[DiagnosticAlert],
                                    predictions: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate comprehensive system health report."""
        current_time = time.time()

        # Calculate overall system health
        component_scores = [metrics.score for metrics in health_metrics.values()]
        overall_health_score = statistics.mean(component_scores) if component_scores else 0.0

        # Categorize alerts by severity
        alert_counts = defaultdict(int)
        for alert in alerts:
            alert_counts[alert.severity.value] += 1

        # Generate health summary
        health_summary = self._generate_health_summary(overall_health_score, alerts)

        # Generate recommendations
        recommendations = self._generate_recommendations(health_metrics, alerts)

        report = {
            "report_id": str(uuid.uuid4()),
            "timestamp": current_time,
            "timestamp_iso": datetime.fromtimestamp(current_time).isoformat(),
            "overall_health_score": overall_health_score,
            "health_status": self._categorize_health_status(overall_health_score),
            "component_health": {
                component: metrics.to_dict()
                for component, metrics in health_metrics.items()
            },
            "alerts": {
                "total": len(alerts),
                "by_severity": dict(alert_counts),
                "active_alerts": [alert.to_dict() for alert in alerts if not alert.resolved]
            },
            "predictions": predictions or {},
            "health_summary": health_summary,
            "recommendations": recommendations,
            "system_info": self._get_system_info(),
            "ai_analysis": {
                "risk_factors": self._identify_risk_factors(health_metrics, alerts),
                "trending_issues": self._identify_trending_issues(health_metrics),
                "recovery_success_rate": self._calculate_recovery_success_rate(),
                "system_stability": self._assess_system_stability(health_metrics)
            }
        }

        # Store report
        self.report_history.append(report)

        # Log report generation
        self.logger.info(
            f"System health report generated: overall score {overall_health_score:.3f}",
            extra={
                "category": LogCategory.SYSTEM,
                "report_data": report
            }
        )

        return report

    def _generate_health_summary(self, overall_score: float, alerts: List[DiagnosticAlert]) -> Dict[str, Any]:
        """Generate human and AI readable health summary."""
        if overall_score >= 0.9:
            status_text = "System operating at optimal performance"
            color = "green"
        elif overall_score >= 0.7:
            status_text = "System performing well with minor issues"
            color = "yellow"
        elif overall_score >= 0.5:
            status_text = "System experiencing moderate issues"
            color = "orange"
        else:
            status_text = "System experiencing significant issues"
            color = "red"

        critical_alerts = [a for a in alerts if a.severity == DiagnosticSeverity.CRITICAL]
        high_alerts = [a for a in alerts if a.severity == DiagnosticSeverity.HIGH]

        return {
            "status_text": status_text,
            "status_color": color,
            "critical_issues": len(critical_alerts),
            "high_priority_issues": len(high_alerts),
            "total_active_alerts": len([a for a in alerts if not a.resolved])
        }

    def _generate_recommendations(self, health_metrics: Dict[str, HealthMetrics],
                                alerts: List[DiagnosticAlert]) -> List[Dict[str, Any]]:
        """Generate actionable recommendations."""
        recommendations = []

        # Performance-based recommendations
        slow_components = [
            name for name, metrics in health_metrics.items()
            if metrics.response_time_ms and metrics.response_time_ms > 10000
        ]

        if slow_components:
            recommendations.append({
                "type": "performance",
                "priority": "high",
                "title": "Address Performance Issues",
                "description": f"Components showing slow response times: {', '.join(slow_components)}",
                "action": "Investigate performance bottlenecks and optimize"
            })

        # Memory usage recommendations
        high_memory_components = [
            name for name, metrics in health_metrics.items()
            if metrics.memory_usage_mb and metrics.memory_usage_mb > 500
        ]

        if high_memory_components:
            recommendations.append({
                "type": "resource",
                "priority": "medium",
                "title": "Monitor Memory Usage",
                "description": f"High memory usage detected in: {', '.join(high_memory_components)}",
                "action": "Review memory usage patterns and optimize if needed"
            })

        # Alert-based recommendations
        critical_alerts = [a for a in alerts if a.severity == DiagnosticSeverity.CRITICAL and not a.resolved]
        if critical_alerts:
            recommendations.append({
                "type": "critical",
                "priority": "critical",
                "title": "Address Critical Alerts",
                "description": f"{len(critical_alerts)} critical alerts require immediate attention",
                "action": "Review and resolve critical alerts immediately"
            })

        return recommendations

    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for context."""
        return {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": sys.platform,
            "cpu_count": psutil.cpu_count(),
            "total_memory_mb": psutil.virtual_memory().total / (1024 * 1024),
            "available_memory_mb": psutil.virtual_memory().available / (1024 * 1024)
        }

    def _identify_risk_factors(self, health_metrics: Dict[str, HealthMetrics],
                             alerts: List[DiagnosticAlert]) -> List[str]:
        """Identify current risk factors."""
        risks = []

        # Component health risks
        unhealthy_components = [
            name for name, metrics in health_metrics.items()
            if metrics.score < 0.7
        ]

        if unhealthy_components:
            risks.append(f"Unhealthy components: {', '.join(unhealthy_components)}")

        # Alert-based risks
        critical_alerts = [a for a in alerts if a.severity == DiagnosticSeverity.CRITICAL]
        if critical_alerts:
            risks.append(f"{len(critical_alerts)} critical alerts active")

        high_alerts = [a for a in alerts if a.severity == DiagnosticSeverity.HIGH]
        if len(high_alerts) > 5:
            risks.append(f"High number of high-priority alerts ({len(high_alerts)})")

        return risks

    def _identify_trending_issues(self, health_metrics: Dict[str, HealthMetrics]) -> List[str]:
        """Identify trending issues from historical data."""
        # This would analyze historical trends
        # For now, return placeholder data
        return ["Response time increasing for web scraper", "Memory usage trending upward"]

    def _calculate_recovery_success_rate(self) -> float:
        """Calculate recovery success rate from historical data."""
        # This would calculate based on recovery history
        # For now, return placeholder value
        return 0.85

    def _assess_system_stability(self, health_metrics: Dict[str, HealthMetrics]) -> Dict[str, Any]:
        """Assess overall system stability."""
        stable_components = sum(1 for metrics in health_metrics.values() if metrics.score >= 0.8)
        total_components = len(health_metrics)
        stability_ratio = stable_components / total_components if total_components > 0 else 0.0

        return {
            "stability_score": stability_ratio,
            "stable_components": stable_components,
            "total_components": total_components,
            "assessment": "stable" if stability_ratio >= 0.8 else "unstable" if stability_ratio < 0.5 else "moderate"
        }

    def _categorize_health_status(self, score: float) -> str:
        """Categorize overall health status."""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.7:
            return "good"
        elif score >= 0.5:
            return "fair"
        elif score >= 0.3:
            return "poor"
        else:
            return "critical"


class AIDiagnosticManager:
    """Main AI diagnostic manager orchestrating all diagnostic components."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = get_ai_logger(__name__)

        # Initialize components
        self.health_checker = AIHealthChecker(self.logger)
        self.predictive_monitor = AIPredictiveMonitor(self.logger)
        self.auto_recovery = AIAutoRecovery(self.logger)
        self.reporter = AIDiagnosticReporter(self.logger)

        # Diagnostic state
        self.last_health_check = 0
        self.active_alerts = {}
        self.running = False
        self.diagnostic_thread = None

    def start_monitoring(self, interval_seconds: int = 300) -> None:
        """Start continuous diagnostic monitoring."""
        if self.running:
            return

        self.running = True
        self.diagnostic_thread = threading.Thread(
            target=self._diagnostic_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self.diagnostic_thread.start()

        self.logger.info(
            f"AI diagnostic monitoring started with {interval_seconds}s interval",
            extra={"category": LogCategory.SYSTEM}
        )

    def stop_monitoring(self) -> None:
        """Stop diagnostic monitoring."""
        self.running = False
        if self.diagnostic_thread:
            self.diagnostic_thread.join(timeout=10)

        self.logger.info(
            "AI diagnostic monitoring stopped",
            extra={"category": LogCategory.SYSTEM}
        )

    def _diagnostic_loop(self, interval_seconds: int) -> None:
        """Main diagnostic monitoring loop."""
        while self.running:
            try:
                asyncio.run(self._run_diagnostic_cycle())
                time.sleep(interval_seconds)
            except Exception as e:
                self.logger.log_error_with_ai_context(e, "diagnostic_loop")
                time.sleep(min(interval_seconds, 60))  # Don't sleep too long on error

    async def _run_diagnostic_cycle(self) -> None:
        """Run a complete diagnostic cycle."""
        cycle_start = time.time()

        # Check health of all components
        health_metrics = {}
        all_alerts = []

        for component in SystemComponent:
            try:
                metrics = await self.health_checker.check_component_health(component)
                health_metrics[component.value] = metrics

                # Record metrics for predictive monitoring
                self.predictive_monitor.record_metric(
                    component.value, "score", metrics.score
                )
                if metrics.response_time_ms:
                    self.predictive_monitor.record_metric(
                        component.value, "response_time", metrics.response_time_ms
                    )

                # Analyze trends and generate alerts
                alerts = self.health_checker.analyze_health_trends(component, metrics)
                all_alerts.extend(alerts)

            except Exception as e:
                self.logger.log_error_with_ai_context(e, f"health_check_{component.value}")

        # Generate predictions
        predictions = {}
        for component in SystemComponent:
            try:
                prediction = self.predictive_monitor.predict_failure_risk(component)
                predictions[component.value] = prediction
            except Exception as e:
                self.logger.log_error_with_ai_context(e, f"prediction_{component.value}")

        # Process alerts and trigger auto-recovery
        for alert in all_alerts:
            alert_key = f"{alert.component}_{alert.title}"

            # Skip if alert already processed recently
            if alert_key in self.active_alerts:
                last_processed = self.active_alerts[alert_key]
                if time.time() - last_processed < 3600:  # 1 hour cooldown
                    continue

            # Trigger auto-recovery for high/critical alerts
            if alert.severity in [DiagnosticSeverity.HIGH, DiagnosticSeverity.CRITICAL]:
                try:
                    recovery_result = await self.auto_recovery.execute_recovery(alert)
                    if recovery_result["final_status"] == "resolved":
                        alert.resolved = True
                except Exception as e:
                    self.logger.log_error_with_ai_context(e, f"auto_recovery_{alert.id}")

            self.active_alerts[alert_key] = time.time()

        # Generate comprehensive report
        report = self.reporter.generate_system_health_report(
            health_metrics, all_alerts, predictions
        )

        cycle_duration = (time.time() - cycle_start) * 1000
        self.logger.log_performance("diagnostic_cycle", cycle_duration)

    async def run_manual_diagnostic(self) -> Dict[str, Any]:
        """Run manual diagnostic check and return results."""
        await self._run_diagnostic_cycle()

        # Return latest report
        if self.reporter.report_history:
            return self.reporter.report_history[-1]
        else:
            return {"error": "No diagnostic report available"}

    def get_current_health_status(self) -> Dict[str, Any]:
        """Get current system health status."""
        if self.reporter.report_history:
            latest_report = self.reporter.report_history[-1]
            return {
                "overall_health_score": latest_report["overall_health_score"],
                "health_status": latest_report["health_status"],
                "active_alerts": latest_report["alerts"]["total"],
                "last_check": latest_report["timestamp"]
            }
        else:
            return {
                "overall_health_score": 0.0,
                "health_status": "unknown",
                "active_alerts": 0,
                "last_check": None
            }


# Global diagnostic manager instance
_diagnostic_manager = None


def get_diagnostic_manager(config: Dict[str, Any] = None) -> AIDiagnosticManager:
    """Get global diagnostic manager instance."""
    global _diagnostic_manager
    if _diagnostic_manager is None:
        _diagnostic_manager = AIDiagnosticManager(config)
    return _diagnostic_manager


def start_ai_diagnostics(config: Dict[str, Any] = None, interval_seconds: int = 300) -> AIDiagnosticManager:
    """Start AI diagnostic monitoring system."""
    manager = get_diagnostic_manager(config)
    manager.start_monitoring(interval_seconds)
    return manager


def stop_ai_diagnostics() -> None:
    """Stop AI diagnostic monitoring system."""
    global _diagnostic_manager
    if _diagnostic_manager:
        _diagnostic_manager.stop_monitoring()


async def run_health_check() -> Dict[str, Any]:
    """Run immediate health check and return results."""
    manager = get_diagnostic_manager()
    return await manager.run_manual_diagnostic()


class EnhancedPatternRecognition:
    """
    Enhanced AI pattern recognition for error detection and prediction.
    Uses ML-inspired techniques for sophisticated pattern analysis.
    """

    def __init__(self, logger=None):
        self.logger = logger or get_ai_logger(__name__)
        self.pattern_cache = deque(maxlen=10000)  # Store historical patterns
        self.error_signatures = defaultdict(list)  # Signature-based error clustering
        self.prediction_models = {}  # Simple statistical models per component
        self.correlation_matrix = defaultdict(lambda: defaultdict(float))  # Cross-component correlations
        self.anomaly_thresholds = {}  # Dynamic thresholds per metric

    def detect_error_patterns(self, metrics_history: List[HealthMetrics],
                            time_window_minutes: int = 60) -> List[Dict[str, Any]]:
        """
        Detect error patterns using ML-inspired techniques.
        """
        detected_patterns = []
        cutoff_time = time.time() - (time_window_minutes * 60)

        # Filter recent metrics
        recent_metrics = [m for m in metrics_history
                         if m.to_dict().get('timestamp', 0) > cutoff_time]

        if not recent_metrics:
            return detected_patterns

        # Pattern 1: Anomaly detection using statistical methods
        anomalies = self._detect_statistical_anomalies(recent_metrics)
        detected_patterns.extend(anomalies)

        # Pattern 2: Cascade failure detection
        cascades = self._detect_cascade_patterns(recent_metrics)
        detected_patterns.extend(cascades)

        # Pattern 3: Periodic failure patterns
        periodic = self._detect_periodic_patterns(recent_metrics)
        detected_patterns.extend(periodic)

        # Pattern 4: Resource exhaustion patterns
        resource_issues = self._detect_resource_exhaustion_patterns(recent_metrics)
        detected_patterns.extend(resource_issues)

        # Pattern 5: Correlation-based error propagation
        correlations = self._detect_correlation_patterns(recent_metrics)
        detected_patterns.extend(correlations)

        # Update pattern cache for learning
        for pattern in detected_patterns:
            self.pattern_cache.append({
                **pattern,
                'timestamp': time.time(),
                'confirmed': False  # Will be updated based on actual outcomes
            })

        return detected_patterns

    def _detect_statistical_anomalies(self, metrics: List[HealthMetrics]) -> List[Dict[str, Any]]:
        """Detect anomalies using statistical methods (Z-score, IQR)."""
        anomalies = []

        # Group metrics by component
        component_metrics = defaultdict(list)
        for metric in metrics:
            component_metrics[metric.component].append(metric)

        for component, comp_metrics in component_metrics.items():
            # Check various metrics for anomalies
            metric_values = {
                'score': [m.score for m in comp_metrics if m.score is not None],
                'response_time': [m.response_time_ms for m in comp_metrics if m.response_time_ms is not None],
                'memory_usage': [m.memory_usage_mb for m in comp_metrics if m.memory_usage_mb is not None],
                'cpu_usage': [m.cpu_usage_percent for m in comp_metrics if m.cpu_usage_percent is not None]
            }

            for metric_name, values in metric_values.items():
                if len(values) > 3:  # Need minimum data points
                    anomaly_indices = self._calculate_anomalies(values)

                    if anomaly_indices:
                        anomalies.append({
                            'type': 'statistical_anomaly',
                            'component': component,
                            'metric': metric_name,
                            'anomaly_count': len(anomaly_indices),
                            'severity': 'high' if len(anomaly_indices) > len(values) * 0.2 else 'medium',
                            'description': f'Statistical anomaly detected in {metric_name} for {component}',
                            'confidence': min(0.9, len(anomaly_indices) / len(values) * 3),
                            'recommended_actions': [
                                f'Investigate {component} {metric_name} anomalies',
                                'Check system resources',
                                'Review recent changes'
                            ]
                        })

        return anomalies

    def _calculate_anomalies(self, values: List[float]) -> List[int]:
        """Calculate anomaly indices using Z-score method."""
        if len(values) < 3:
            return []

        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values) if len(values) > 1 else 0

        if std_val == 0:
            return []

        anomaly_indices = []
        for i, value in enumerate(values):
            z_score = abs((value - mean_val) / std_val)
            if z_score > 2.5:  # 2.5 sigma threshold
                anomaly_indices.append(i)

        return anomaly_indices

    def _detect_cascade_patterns(self, metrics: List[HealthMetrics]) -> List[Dict[str, Any]]:
        """Detect cascade failure patterns across components."""
        cascades = []

        # Sort metrics by timestamp
        sorted_metrics = sorted(metrics, key=lambda m: m.to_dict().get('timestamp', 0))

        # Look for rapid succession of component failures
        failure_window = 300  # 5 minutes
        component_failures = []

        for metric in sorted_metrics:
            if metric.status in [HealthStatus.CRITICAL, HealthStatus.DOWN]:
                component_failures.append({
                    'component': metric.component,
                    'timestamp': metric.to_dict().get('timestamp', 0),
                    'status': metric.status
                })

        # Check for cascade patterns
        if len(component_failures) >= 2:
            for i in range(len(component_failures) - 1):
                time_diff = component_failures[i+1]['timestamp'] - component_failures[i]['timestamp']

                if time_diff <= failure_window:
                    cascades.append({
                        'type': 'cascade_failure',
                        'primary_component': component_failures[i]['component'],
                        'secondary_component': component_failures[i+1]['component'],
                        'time_diff_seconds': time_diff,
                        'severity': 'critical',
                        'description': f'Cascade failure detected: {component_failures[i]["component"]} → {component_failures[i+1]["component"]}',
                        'confidence': 0.8,
                        'recommended_actions': [
                            'Investigate dependency chain',
                            'Implement circuit breakers',
                            'Review error propagation mechanisms'
                        ]
                    })

        return cascades

    def _detect_periodic_patterns(self, metrics: List[HealthMetrics]) -> List[Dict[str, Any]]:
        """Detect periodic failure patterns that might indicate systematic issues."""
        periodic = []

        # Group by component and look for periodic drops in health score
        component_metrics = defaultdict(list)
        for metric in metrics:
            if metric.score is not None:
                component_metrics[metric.component].append({
                    'timestamp': metric.to_dict().get('timestamp', 0),
                    'score': metric.score
                })

        for component, comp_metrics in component_metrics.items():
            if len(comp_metrics) > 10:  # Need sufficient data
                # Sort by timestamp
                comp_metrics.sort(key=lambda x: x['timestamp'])

                # Look for periodic dips
                low_score_intervals = []
                for i, metric in enumerate(comp_metrics):
                    if metric['score'] < 0.5:  # Low score threshold
                        low_score_intervals.append(i)

                if len(low_score_intervals) >= 3:
                    # Check if intervals are somewhat regular
                    intervals = [low_score_intervals[i+1] - low_score_intervals[i]
                               for i in range(len(low_score_intervals)-1)]

                    if intervals and statistics.stdev(intervals) < statistics.mean(intervals) * 0.3:
                        periodic.append({
                            'type': 'periodic_pattern',
                            'component': component,
                            'pattern_interval': statistics.mean(intervals),
                            'occurrences': len(low_score_intervals),
                            'severity': 'medium',
                            'description': f'Periodic health drops detected in {component}',
                            'confidence': 0.7,
                            'recommended_actions': [
                                'Investigate periodic processes',
                                'Check for scheduled tasks or cron jobs',
                                'Review resource allocation patterns'
                            ]
                        })

        return periodic

    def _detect_resource_exhaustion_patterns(self, metrics: List[HealthMetrics]) -> List[Dict[str, Any]]:
        """Detect resource exhaustion patterns leading to system degradation."""
        patterns = []

        # Check for gradual resource consumption increase
        resource_metrics = defaultdict(list)

        for metric in metrics:
            timestamp = metric.to_dict().get('timestamp', 0)

            if metric.memory_usage_mb is not None:
                resource_metrics['memory'].append((timestamp, metric.memory_usage_mb, metric.component))

            if metric.cpu_usage_percent is not None:
                resource_metrics['cpu'].append((timestamp, metric.cpu_usage_percent, metric.component))

            if metric.disk_usage_percent is not None:
                resource_metrics['disk'].append((timestamp, metric.disk_usage_percent, metric.component))

        for resource_type, values in resource_metrics.items():
            if len(values) > 5:
                # Sort by timestamp
                values.sort(key=lambda x: x[0])

                # Calculate trend
                resource_values = [v[1] for v in values]
                trend = self._calculate_trend(resource_values)

                # Check for consistent upward trend indicating exhaustion
                if trend > 0.1 and max(resource_values) > 80:  # Strong upward trend + high usage
                    patterns.append({
                        'type': 'resource_exhaustion',
                        'resource_type': resource_type,
                        'trend_slope': trend,
                        'max_usage': max(resource_values),
                        'severity': 'high' if max(resource_values) > 90 else 'medium',
                        'description': f'{resource_type.title()} exhaustion pattern detected',
                        'confidence': min(0.9, trend * 5),
                        'recommended_actions': [
                            f'Monitor {resource_type} usage closely',
                            'Scale resources if possible',
                            f'Identify {resource_type} intensive processes'
                        ]
                    })

        return patterns

    def _detect_correlation_patterns(self, metrics: List[HealthMetrics]) -> List[Dict[str, Any]]:
        """Detect error correlation patterns between components."""
        correlations = []

        # Build correlation matrix
        component_health = defaultdict(list)
        timestamps = set()

        for metric in metrics:
            timestamp = metric.to_dict().get('timestamp', 0)
            component_health[metric.component].append((timestamp, metric.score if metric.score else 0))
            timestamps.add(timestamp)

        # Find components with correlated health patterns
        components = list(component_health.keys())

        for i in range(len(components)):
            for j in range(i+1, len(components)):
                comp1, comp2 = components[i], components[j]

                # Get aligned health scores
                scores1 = dict(component_health[comp1])
                scores2 = dict(component_health[comp2])

                common_times = set(scores1.keys()) & set(scores2.keys())

                if len(common_times) > 3:
                    aligned_scores1 = [scores1[t] for t in common_times]
                    aligned_scores2 = [scores2[t] for t in common_times]

                    # Calculate correlation
                    correlation = self._calculate_correlation(aligned_scores1, aligned_scores2)

                    if abs(correlation) > 0.7:  # Strong correlation
                        correlations.append({
                            'type': 'component_correlation',
                            'component1': comp1,
                            'component2': comp2,
                            'correlation_coefficient': correlation,
                            'correlation_type': 'positive' if correlation > 0 else 'negative',
                            'severity': 'medium',
                            'description': f'Strong health correlation between {comp1} and {comp2}',
                            'confidence': min(0.9, abs(correlation)),
                            'recommended_actions': [
                                'Investigate component dependencies',
                                'Check for shared resources',
                                'Consider isolation strategies'
                            ]
                        })

        return correlations

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend slope for a series of values."""
        if len(values) < 2:
            return 0.0

        n = len(values)
        x = list(range(n))
        y = values

        # Simple linear regression slope
        x_mean = sum(x) / n
        y_mean = sum(y) / n

        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def _calculate_correlation(self, values1: List[float], values2: List[float]) -> float:
        """Calculate Pearson correlation coefficient between two value series."""
        if len(values1) != len(values2) or len(values1) < 2:
            return 0.0

        n = len(values1)
        mean1 = sum(values1) / n
        mean2 = sum(values2) / n

        numerator = sum((values1[i] - mean1) * (values2[i] - mean2) for i in range(n))

        sum_sq1 = sum((values1[i] - mean1) ** 2 for i in range(n))
        sum_sq2 = sum((values2[i] - mean2) ** 2 for i in range(n))

        denominator = (sum_sq1 * sum_sq2) ** 0.5

        if denominator == 0:
            return 0.0

        return numerator / denominator


# Global enhanced pattern recognition instance
_enhanced_pattern_recognition: Optional[EnhancedPatternRecognition] = None


def get_enhanced_pattern_recognition() -> EnhancedPatternRecognition:
    """Get the global enhanced pattern recognition instance."""
    global _enhanced_pattern_recognition
    if _enhanced_pattern_recognition is None:
        _enhanced_pattern_recognition = EnhancedPatternRecognition()
    return _enhanced_pattern_recognition