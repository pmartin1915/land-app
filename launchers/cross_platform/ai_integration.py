#!/usr/bin/env python3
"""
Alabama Auction Watcher - AI Monitoring Integration
Connects the desktop launcher with the existing AI testing and monitoring systems
to provide real-time insights and control capabilities.

Features:
- Integration with Enhanced AI Testing Framework
- Real-time error detection monitoring
- Performance metrics aggregation
- Predictive analytics status
- Health scoring and alerts
- Direct control of AI testing components
"""

import sys
import logging
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import threading
import time

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

@dataclass
class AISystemStatus:
    """Data class for AI system status information"""
    system_name: str
    status: str  # "active", "inactive", "error", "unknown"
    last_updated: datetime
    metrics: Dict[str, Any]
    alerts: List[str]
    performance_score: float

@dataclass
class ErrorDetectionStatus:
    """Data class for error detection system status"""
    total_patterns_detected: int
    active_alerts: int
    severity_breakdown: Dict[str, int]
    prediction_accuracy: float
    last_scan: datetime

@dataclass
class PerformanceMetrics:
    """Data class for performance monitoring metrics"""
    memory_usage_mb: float
    cpu_usage_percent: float
    cache_hit_rate: float
    response_time_ms: float
    active_connections: int
    last_measurement: datetime

class AIMonitoringIntegration:
    """Main integration class for AI monitoring systems"""

    def __init__(self):
        self.project_root = project_root
        self.is_monitoring = False
        self.monitoring_thread = None
        self.status_cache = {}
        self.cache_expiry = timedelta(seconds=30)

        # Initialize status tracking
        self.ai_systems = {
            'enhanced_testing': AISystemStatus(
                system_name="Enhanced AI Testing Framework",
                status="unknown",
                last_updated=datetime.now(),
                metrics={},
                alerts=[],
                performance_score=0.0
            ),
            'error_detection': AISystemStatus(
                system_name="Enhanced Error Detection",
                status="unknown",
                last_updated=datetime.now(),
                metrics={},
                alerts=[],
                performance_score=0.0
            ),
            'performance_monitor': AISystemStatus(
                system_name="Performance Monitor",
                status="unknown",
                last_updated=datetime.now(),
                metrics={},
                alerts=[],
                performance_score=0.0
            ),
            'predictive_analytics': AISystemStatus(
                system_name="Predictive Analytics Engine",
                status="unknown",
                last_updated=datetime.now(),
                metrics={},
                alerts=[],
                performance_score=0.0
            )
        }

    def start_monitoring(self):
        """Start background monitoring of AI systems"""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("AI monitoring integration started")

    def stop_monitoring(self):
        """Stop background monitoring"""
        self.is_monitoring = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        logger.info("AI monitoring integration stopped")

    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.is_monitoring:
            try:
                self._update_all_systems()
                time.sleep(15)  # Update every 15 seconds
            except Exception as e:
                logger.error(f"Error in AI monitoring loop: {e}")
                time.sleep(30)  # Wait longer on error

    def _update_all_systems(self):
        """Update status for all AI systems"""
        try:
            # Update each system
            self._update_enhanced_testing_status()
            self._update_error_detection_status()
            self._update_performance_monitor_status()
            self._update_predictive_analytics_status()

        except Exception as e:
            logger.error(f"Error updating AI systems: {e}")

    def _update_enhanced_testing_status(self):
        """Update Enhanced AI Testing Framework status"""
        try:
            # Try to import and check the enhanced testing system
            from streamlit_app.testing.enhanced_ai_testing import get_enhanced_ai_testing_controller

            controller = get_enhanced_ai_testing_controller()
            if controller:
                # Get test execution stats
                stats = controller.get_execution_stats()

                self.ai_systems['enhanced_testing'].status = "active"
                self.ai_systems['enhanced_testing'].metrics = {
                    'total_tests_run': stats.get('total_tests_run', 0),
                    'success_rate': stats.get('success_rate', 0.0),
                    'avg_execution_time': stats.get('avg_execution_time', 0.0),
                    'active_test_suites': stats.get('active_test_suites', 0)
                }
                self.ai_systems['enhanced_testing'].performance_score = stats.get('success_rate', 0.0)

                # Check for alerts
                alerts = []
                if stats.get('success_rate', 100) < 80:
                    alerts.append("Test success rate below 80%")
                if stats.get('avg_execution_time', 0) > 5000:
                    alerts.append("Test execution time exceeding 5 seconds")

                self.ai_systems['enhanced_testing'].alerts = alerts
                self.ai_systems['enhanced_testing'].last_updated = datetime.now()

            else:
                self.ai_systems['enhanced_testing'].status = "inactive"

        except ImportError:
            self.ai_systems['enhanced_testing'].status = "inactive"
            self.ai_systems['enhanced_testing'].alerts = ["Enhanced testing module not available"]
        except Exception as e:
            self.ai_systems['enhanced_testing'].status = "error"
            self.ai_systems['enhanced_testing'].alerts = [f"Error: {str(e)}"]
            logger.error(f"Error updating enhanced testing status: {e}")

    def _update_error_detection_status(self):
        """Update Enhanced Error Detection status"""
        try:
            # Try to import and check the error detection system
            from streamlit_app.testing.enhanced_error_detection import get_enhanced_error_detector

            detector = get_enhanced_error_detector()
            if detector:
                # Get error detection stats
                patterns = detector.get_detected_patterns()
                alerts = detector.get_active_alerts()

                self.ai_systems['error_detection'].status = "active"
                self.ai_systems['error_detection'].metrics = {
                    'patterns_detected': len(patterns),
                    'active_alerts': len(alerts),
                    'prediction_accuracy': detector.get_prediction_accuracy(),
                    'last_scan': detector.get_last_scan_time()
                }

                # Calculate performance score based on detection accuracy
                accuracy = detector.get_prediction_accuracy()
                self.ai_systems['error_detection'].performance_score = accuracy

                # Extract alert messages
                alert_messages = [alert.message for alert in alerts[:5]]  # Limit to 5 alerts
                self.ai_systems['error_detection'].alerts = alert_messages
                self.ai_systems['error_detection'].last_updated = datetime.now()

            else:
                self.ai_systems['error_detection'].status = "inactive"

        except ImportError:
            self.ai_systems['error_detection'].status = "inactive"
            self.ai_systems['error_detection'].alerts = ["Error detection module not available"]
        except Exception as e:
            self.ai_systems['error_detection'].status = "error"
            self.ai_systems['error_detection'].alerts = [f"Error: {str(e)}"]
            logger.error(f"Error updating error detection status: {e}")

    def _update_performance_monitor_status(self):
        """Update Performance Monitor status"""
        try:
            # Try to import and check the performance monitoring system
            from streamlit_app.core.performance_monitor import get_performance_monitor

            monitor = get_performance_monitor()
            if monitor:
                # Get performance metrics
                metrics = monitor.get_current_metrics()

                self.ai_systems['performance_monitor'].status = "active"
                self.ai_systems['performance_monitor'].metrics = {
                    'memory_usage_mb': metrics.get('memory_usage_mb', 0),
                    'cache_hit_rate': metrics.get('cache_hit_rate', 0.0),
                    'avg_response_time': metrics.get('avg_response_time', 0.0),
                    'active_requests': metrics.get('active_requests', 0)
                }

                # Calculate performance score
                cache_rate = metrics.get('cache_hit_rate', 0.0)
                response_time = metrics.get('avg_response_time', 1000)
                performance_score = min(100, cache_rate * 0.7 + max(0, (1000 - response_time) / 10) * 0.3)

                self.ai_systems['performance_monitor'].performance_score = performance_score

                # Check for performance alerts
                alerts = []
                if metrics.get('memory_usage_mb', 0) > 1000:
                    alerts.append("High memory usage detected")
                if metrics.get('cache_hit_rate', 100) < 50:
                    alerts.append("Low cache hit rate")
                if metrics.get('avg_response_time', 0) > 2000:
                    alerts.append("Slow response times detected")

                self.ai_systems['performance_monitor'].alerts = alerts
                self.ai_systems['performance_monitor'].last_updated = datetime.now()

            else:
                self.ai_systems['performance_monitor'].status = "inactive"

        except ImportError:
            self.ai_systems['performance_monitor'].status = "inactive"
            self.ai_systems['performance_monitor'].alerts = ["Performance monitor module not available"]
        except Exception as e:
            self.ai_systems['performance_monitor'].status = "error"
            self.ai_systems['performance_monitor'].alerts = [f"Error: {str(e)}"]
            logger.error(f"Error updating performance monitor status: {e}")

    def _update_predictive_analytics_status(self):
        """Update Predictive Analytics Engine status"""
        try:
            # Try to import and check the predictive analytics system
            from streamlit_app.components.predictive_analytics import get_prediction_engine

            engine = get_prediction_engine()
            if engine:
                # Get prediction metrics
                stats = engine.get_prediction_stats()

                self.ai_systems['predictive_analytics'].status = "active"
                self.ai_systems['predictive_analytics'].metrics = {
                    'total_predictions': stats.get('total_predictions', 0),
                    'accuracy_rate': stats.get('accuracy_rate', 0.0),
                    'active_models': stats.get('active_models', 0),
                    'last_prediction': stats.get('last_prediction', 'Never')
                }

                self.ai_systems['predictive_analytics'].performance_score = stats.get('accuracy_rate', 0.0)

                # Check for prediction alerts
                alerts = []
                if stats.get('accuracy_rate', 100) < 70:
                    alerts.append("Prediction accuracy below 70%")
                if stats.get('active_models', 0) == 0:
                    alerts.append("No active prediction models")

                self.ai_systems['predictive_analytics'].alerts = alerts
                self.ai_systems['predictive_analytics'].last_updated = datetime.now()

            else:
                self.ai_systems['predictive_analytics'].status = "inactive"

        except ImportError:
            self.ai_systems['predictive_analytics'].status = "inactive"
            self.ai_systems['predictive_analytics'].alerts = ["Predictive analytics module not available"]
        except Exception as e:
            self.ai_systems['predictive_analytics'].status = "error"
            self.ai_systems['predictive_analytics'].alerts = [f"Error: {str(e)}"]
            logger.error(f"Error updating predictive analytics status: {e}")

    # Public interface methods
    def get_ai_system_status(self, system_name: str) -> Optional[AISystemStatus]:
        """Get status for a specific AI system"""
        return self.ai_systems.get(system_name)

    def get_all_ai_systems_status(self) -> Dict[str, AISystemStatus]:
        """Get status for all AI systems"""
        return self.ai_systems.copy()

    def get_overall_ai_health_score(self) -> float:
        """Calculate overall AI system health score"""
        active_systems = [system for system in self.ai_systems.values() if system.status == "active"]

        if not active_systems:
            return 0.0

        total_score = sum(system.performance_score for system in active_systems)
        return total_score / len(active_systems)

    def get_system_alerts(self) -> List[Tuple[str, str]]:
        """Get all system alerts across AI systems"""
        alerts = []
        for system_name, system in self.ai_systems.items():
            for alert in system.alerts:
                alerts.append((system.system_name, alert))
        return alerts

    def get_ai_dashboard_summary(self) -> Dict[str, Any]:
        """Get a comprehensive AI dashboard summary"""
        total_systems = len(self.ai_systems)
        active_systems = sum(1 for system in self.ai_systems.values() if system.status == "active")
        total_alerts = sum(len(system.alerts) for system in self.ai_systems.values())
        overall_health = self.get_overall_ai_health_score()

        return {
            'total_systems': total_systems,
            'active_systems': active_systems,
            'inactive_systems': total_systems - active_systems,
            'total_alerts': total_alerts,
            'overall_health_score': overall_health,
            'health_status': self._get_health_status_text(overall_health),
            'last_updated': datetime.now().isoformat(),
            'systems': {name: {
                'status': system.status,
                'performance_score': system.performance_score,
                'alert_count': len(system.alerts),
                'last_updated': system.last_updated.isoformat()
            } for name, system in self.ai_systems.items()}
        }

    def _get_health_status_text(self, score: float) -> str:
        """Convert health score to descriptive text"""
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 60:
            return "Fair"
        elif score >= 40:
            return "Poor"
        else:
            return "Critical"

    def run_ai_health_check(self) -> Dict[str, Any]:
        """Run a comprehensive AI health check"""
        self._update_all_systems()

        health_check = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'systems': {},
            'recommendations': [],
            'critical_issues': []
        }

        critical_issues = []
        recommendations = []

        for system_name, system in self.ai_systems.items():
            system_health = {
                'name': system.system_name,
                'status': system.status,
                'performance_score': system.performance_score,
                'alerts': system.alerts,
                'metrics': system.metrics,
                'health_rating': self._get_health_status_text(system.performance_score)
            }

            health_check['systems'][system_name] = system_health

            # Check for critical issues
            if system.status == "error":
                critical_issues.append(f"{system.system_name} is in error state")
                health_check['overall_status'] = 'critical'

            if system.performance_score < 50:
                critical_issues.append(f"{system.system_name} performance is below 50%")

            # Generate recommendations
            if system.status == "inactive":
                recommendations.append(f"Consider activating {system.system_name}")

            if len(system.alerts) > 0:
                recommendations.append(f"Review alerts for {system.system_name}")

        health_check['critical_issues'] = critical_issues
        health_check['recommendations'] = recommendations

        # Determine overall status
        if len(critical_issues) > 0:
            health_check['overall_status'] = 'critical'
        elif len(recommendations) > 2:
            health_check['overall_status'] = 'warning'
        else:
            health_check['overall_status'] = 'healthy'

        return health_check

    def trigger_ai_system_action(self, system_name: str, action: str) -> bool:
        """Trigger an action on an AI system"""
        try:
            if system_name == "enhanced_testing":
                return self._trigger_testing_action(action)
            elif system_name == "error_detection":
                return self._trigger_error_detection_action(action)
            elif system_name == "performance_monitor":
                return self._trigger_performance_action(action)
            elif system_name == "predictive_analytics":
                return self._trigger_analytics_action(action)
            else:
                logger.warning(f"Unknown AI system: {system_name}")
                return False

        except Exception as e:
            logger.error(f"Error triggering AI system action: {e}")
            return False

    def _trigger_testing_action(self, action: str) -> bool:
        """Trigger Enhanced AI Testing actions"""
        try:
            from streamlit_app.testing.enhanced_ai_testing import get_enhanced_ai_testing_controller

            controller = get_enhanced_ai_testing_controller()
            if not controller:
                return False

            if action == "run_full_test_suite":
                controller.run_full_test_suite()
                return True
            elif action == "clear_test_cache":
                controller.clear_cache()
                return True
            elif action == "reset_statistics":
                controller.reset_statistics()
                return True

            return False

        except Exception as e:
            logger.error(f"Error in testing action: {e}")
            return False

    def _trigger_error_detection_action(self, action: str) -> bool:
        """Trigger Error Detection actions"""
        try:
            from streamlit_app.testing.enhanced_error_detection import get_enhanced_error_detector

            detector = get_enhanced_error_detector()
            if not detector:
                return False

            if action == "scan_for_patterns":
                detector.scan_for_new_patterns()
                return True
            elif action == "clear_alerts":
                detector.clear_active_alerts()
                return True
            elif action == "update_models":
                detector.update_prediction_models()
                return True

            return False

        except Exception as e:
            logger.error(f"Error in error detection action: {e}")
            return False

    def _trigger_performance_action(self, action: str) -> bool:
        """Trigger Performance Monitor actions"""
        try:
            from streamlit_app.core.performance_monitor import get_performance_monitor

            monitor = get_performance_monitor()
            if not monitor:
                return False

            if action == "clear_cache":
                monitor.clear_cache()
                return True
            elif action == "reset_metrics":
                monitor.reset_metrics()
                return True
            elif action == "optimize_memory":
                monitor.optimize_memory()
                return True

            return False

        except Exception as e:
            logger.error(f"Error in performance action: {e}")
            return False

    def _trigger_analytics_action(self, action: str) -> bool:
        """Trigger Predictive Analytics actions"""
        try:
            from streamlit_app.components.predictive_analytics import get_prediction_engine

            engine = get_prediction_engine()
            if not engine:
                return False

            if action == "retrain_models":
                engine.retrain_models()
                return True
            elif action == "update_predictions":
                engine.update_predictions()
                return True
            elif action == "clear_cache":
                engine.clear_prediction_cache()
                return True

            return False

        except Exception as e:
            logger.error(f"Error in analytics action: {e}")
            return False

# Global instance for easy access
_ai_integration_instance = None

def get_ai_integration() -> AIMonitoringIntegration:
    """Get or create the global AI integration instance"""
    global _ai_integration_instance
    if _ai_integration_instance is None:
        _ai_integration_instance = AIMonitoringIntegration()
    return _ai_integration_instance

def main():
    """Main entry point for testing the AI integration"""
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Create and test AI integration
    ai_integration = get_ai_integration()
    ai_integration.start_monitoring()

    try:
        # Wait a bit for monitoring to collect data
        time.sleep(5)

        # Print status summary
        summary = ai_integration.get_ai_dashboard_summary()
        print(json.dumps(summary, indent=2))

        # Run health check
        health_check = ai_integration.run_ai_health_check()
        print("\nHealth Check Results:")
        print(json.dumps(health_check, indent=2))

    finally:
        ai_integration.stop_monitoring()

if __name__ == "__main__":
    main()