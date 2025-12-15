"""
Smart Error Recovery System for Alabama Auction Watcher Launcher
Advanced error recovery mechanisms specifically designed for launcher systems
with AI-driven decision making and automated remediation capabilities.

Features:
- Intelligent launcher fault detection
- Automated error recovery workflows
- Self-healing system components
- Predictive failure prevention
- Integration with existing AI diagnostics
"""

import time
import threading
import subprocess
import psutil
import asyncio
import logging
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.ai_logging import get_ai_logger, LogCategory
from config.ai_diagnostics import get_diagnostic_manager, get_enhanced_pattern_recognition
from config.enhanced_error_handling import ErrorSeverity, ErrorCategory, ErrorContext
from scripts.ai_exceptions import RecoveryAction, RecoveryInstruction


logger = get_ai_logger(__name__)


class LauncherComponent(Enum):
    """Launcher system components for recovery management."""
    SMART_LAUNCHER = "smart_launcher"
    SYSTEM_TRAY = "system_tray"
    WINDOWS_BATCH = "windows_batch"
    MACOS_COMMAND = "macos_command"
    LINUX_DESKTOP = "linux_desktop"
    GUI_INTERFACE = "gui_interface"
    PROCESS_MONITOR = "process_monitor"
    AI_INTEGRATION = "ai_integration"


class RecoveryStrategy(Enum):
    """Recovery strategies for different failure scenarios."""
    RESTART_COMPONENT = "restart_component"
    RESET_CONFIGURATION = "reset_configuration"
    FALLBACK_MODE = "fallback_mode"
    SAFE_MODE = "safe_mode"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"
    DEPENDENCY_REPAIR = "dependency_repair"
    RESOURCE_CLEANUP = "resource_cleanup"
    CONFIG_ROLLBACK = "config_rollback"


@dataclass
class LauncherError:
    """Comprehensive launcher error information."""
    error_id: str
    component: LauncherComponent
    severity: ErrorSeverity
    category: ErrorCategory
    timestamp: datetime
    error_type: str
    error_message: str
    stack_trace: Optional[str]
    system_context: Dict[str, Any]
    recovery_attempts: int
    max_recovery_attempts: int
    is_recoverable: bool
    suggested_strategy: RecoveryStrategy
    confidence_score: float


@dataclass
class RecoveryAction:
    """Individual recovery action with context."""
    action_id: str
    strategy: RecoveryStrategy
    component: LauncherComponent
    description: str
    execution_time_ms: float
    success: bool
    error_details: Optional[str]
    system_impact: str  # "none", "low", "medium", "high"
    rollback_required: bool


class SmartLauncherRecovery:
    """
    Smart error recovery system for launcher components.
    Provides intelligent, automated error recovery with learning capabilities.
    """

    def __init__(self):
        self.logger = get_ai_logger(__name__)
        self.recovery_history = []
        self.active_recoveries = {}
        self.recovery_strategies = self._initialize_recovery_strategies()
        self.component_health = {}
        self.recovery_lock = threading.Lock()
        self.learning_data = {}

        # Integration with existing AI systems
        self.diagnostic_manager = get_diagnostic_manager()
        self.pattern_recognition = get_enhanced_pattern_recognition()

    def _initialize_recovery_strategies(self) -> Dict[LauncherComponent, Dict[str, Any]]:
        """Initialize recovery strategies for each launcher component."""
        return {
            LauncherComponent.SMART_LAUNCHER: {
                'restart_command': ['python', 'launchers/cross_platform/smart_launcher.py'],
                'config_path': 'launchers/config/smart_launcher.json',
                'dependencies': ['tkinter', 'requests', 'psutil'],
                'fallback_mode': True,
                'max_recovery_attempts': 3,
                'recovery_timeout_seconds': 30
            },
            LauncherComponent.SYSTEM_TRAY: {
                'restart_command': ['python', 'launchers/cross_platform/system_tray.py'],
                'config_path': 'launchers/config/system_tray.json',
                'dependencies': ['pystray', 'pillow'],
                'fallback_mode': False,
                'max_recovery_attempts': 2,
                'recovery_timeout_seconds': 15
            },
            LauncherComponent.WINDOWS_BATCH: {
                'restart_command': ['cmd', '/c', 'launchers/windows/launch_main_app.bat'],
                'config_path': None,
                'dependencies': ['python.exe'],
                'fallback_mode': True,
                'max_recovery_attempts': 2,
                'recovery_timeout_seconds': 20
            },
            LauncherComponent.GUI_INTERFACE: {
                'restart_command': None,  # Handled by parent process
                'config_path': 'launchers/config/gui_interface.json',
                'dependencies': ['tkinter'],
                'fallback_mode': True,
                'max_recovery_attempts': 3,
                'recovery_timeout_seconds': 10
            },
            LauncherComponent.AI_INTEGRATION: {
                'restart_command': None,  # Module restart
                'config_path': 'launchers/config/ai_integration.json',
                'dependencies': ['streamlit_app', 'config.ai_diagnostics'],
                'fallback_mode': True,
                'max_recovery_attempts': 2,
                'recovery_timeout_seconds': 25
            }
        }

    async def handle_launcher_error(self, error: LauncherError) -> Dict[str, Any]:
        """
        Main entry point for handling launcher errors with intelligent recovery.
        """
        recovery_id = f"recovery_{error.component.value}_{int(time.time())}"

        self.logger.info(
            f"Starting smart recovery for {error.component.value}",
            extra={
                "category": LogCategory.SYSTEM,
                "recovery_id": recovery_id,
                "error_severity": error.severity.value,
                "error_category": error.category.value
            }
        )

        # Check if component is already undergoing recovery
        with self.recovery_lock:
            if error.component in self.active_recoveries:
                return {
                    'recovery_id': recovery_id,
                    'status': 'skipped',
                    'reason': f'Recovery already in progress for {error.component.value}'
                }

            self.active_recoveries[error.component] = recovery_id

        try:
            # Analyze error and determine best recovery strategy
            recovery_plan = await self._analyze_and_plan_recovery(error)

            # Execute recovery plan
            recovery_result = await self._execute_recovery_plan(recovery_plan, error)

            # Learn from recovery outcome
            self._update_learning_data(error, recovery_result)

            # Update component health status
            await self._update_component_health(error.component, recovery_result)

            return recovery_result

        except Exception as e:
            self.logger.error(
                f"Recovery failed with unexpected error: {e}",
                extra={
                    "category": LogCategory.ERROR,
                    "recovery_id": recovery_id,
                    "component": error.component.value
                }
            )
            return {
                'recovery_id': recovery_id,
                'status': 'failed',
                'error': str(e)
            }
        finally:
            with self.recovery_lock:
                self.active_recoveries.pop(error.component, None)

    async def _analyze_and_plan_recovery(self, error: LauncherError) -> Dict[str, Any]:
        """Analyze error and create intelligent recovery plan."""

        # Get historical data for this component
        historical_errors = [r for r in self.recovery_history
                           if r.get('component') == error.component]

        # Use pattern recognition to understand error context
        similar_patterns = await self._find_similar_error_patterns(error)

        # Determine optimal recovery strategy
        strategy = await self._select_recovery_strategy(error, historical_errors, similar_patterns)

        # Create recovery plan
        recovery_plan = {
            'recovery_id': f"plan_{error.component.value}_{int(time.time())}",
            'component': error.component,
            'strategy': strategy,
            'priority': self._calculate_recovery_priority(error),
            'estimated_time_seconds': self._estimate_recovery_time(strategy, error),
            'actions': await self._generate_recovery_actions(strategy, error),
            'success_criteria': self._define_success_criteria(error),
            'rollback_plan': await self._create_rollback_plan(strategy, error),
            'monitoring_requirements': self._define_monitoring_requirements(error)
        }

        self.logger.info(
            f"Recovery plan created for {error.component.value}",
            extra={
                "category": LogCategory.SYSTEM,
                "strategy": strategy.value,
                "estimated_time": recovery_plan['estimated_time_seconds'],
                "action_count": len(recovery_plan['actions'])
            }
        )

        return recovery_plan

    async def _find_similar_error_patterns(self, error: LauncherError) -> List[Dict[str, Any]]:
        """Find similar error patterns using AI pattern recognition."""
        try:
            # Convert error to pattern recognition format
            error_signature = f"{error.component.value}:{error.error_type}:{error.category.value}"

            # Search for similar patterns
            similar_patterns = []

            for historical_record in self.recovery_history[-100:]:  # Last 100 records
                if historical_record.get('error_signature') == error_signature:
                    similar_patterns.append(historical_record)
                elif self._calculate_error_similarity(error, historical_record) > 0.7:
                    similar_patterns.append(historical_record)

            return similar_patterns

        except Exception as e:
            self.logger.warning(f"Pattern recognition failed: {e}")
            return []

    def _calculate_error_similarity(self, error1: LauncherError, historical_record: Dict[str, Any]) -> float:
        """Calculate similarity score between errors."""
        similarity = 0.0

        # Component match (high weight)
        if error1.component.value == historical_record.get('component'):
            similarity += 0.4

        # Error category match
        if error1.category.value == historical_record.get('error_category'):
            similarity += 0.3

        # Error type similarity (simple string matching)
        error_type_similarity = self._calculate_string_similarity(
            error1.error_type, historical_record.get('error_type', '')
        )
        similarity += error_type_similarity * 0.2

        # Severity match
        if error1.severity.value == historical_record.get('error_severity'):
            similarity += 0.1

        return min(1.0, similarity)

    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Simple string similarity calculation."""
        if not str1 or not str2:
            return 0.0

        # Simple word overlap calculation
        words1 = set(str1.lower().split())
        words2 = set(str2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)

    async def _select_recovery_strategy(self, error: LauncherError,
                                      historical_errors: List[Dict[str, Any]],
                                      similar_patterns: List[Dict[str, Any]]) -> RecoveryStrategy:
        """Select optimal recovery strategy using AI-driven decision making."""

        # Calculate success rates for different strategies
        strategy_success_rates = {}

        for strategy in RecoveryStrategy:
            successes = sum(1 for record in historical_errors
                          if record.get('strategy') == strategy.value and record.get('success', False))
            total = sum(1 for record in historical_errors if record.get('strategy') == strategy.value)

            if total > 0:
                strategy_success_rates[strategy] = successes / total
            else:
                strategy_success_rates[strategy] = 0.5  # Default neutral probability

        # Factor in error severity and component characteristics
        component_config = self.recovery_strategies.get(error.component, {})

        if error.severity == ErrorSeverity.CRITICAL:
            # For critical errors, prefer safe strategies
            if error.component in [LauncherComponent.SMART_LAUNCHER, LauncherComponent.GUI_INTERFACE]:
                return RecoveryStrategy.RESTART_COMPONENT
            else:
                return RecoveryStrategy.SAFE_MODE

        elif error.severity == ErrorSeverity.HIGH:
            # For high severity, try restart first, then fallback
            if strategy_success_rates[RecoveryStrategy.RESTART_COMPONENT] > 0.6:
                return RecoveryStrategy.RESTART_COMPONENT
            else:
                return RecoveryStrategy.FALLBACK_MODE

        else:
            # For medium/low severity, use learning from similar patterns
            if similar_patterns:
                # Use the most successful strategy from similar patterns
                strategy_counts = {}
                for pattern in similar_patterns:
                    if pattern.get('success', False):
                        strategy = pattern.get('strategy')
                        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

                if strategy_counts:
                    best_strategy = max(strategy_counts, key=strategy_counts.get)
                    return RecoveryStrategy(best_strategy)

            # Default fallback logic
            return RecoveryStrategy.RESET_CONFIGURATION

    def _calculate_recovery_priority(self, error: LauncherError) -> int:
        """Calculate recovery priority (1-10, higher = more urgent)."""
        priority = 5  # Base priority

        # Adjust based on severity
        severity_adjustments = {
            ErrorSeverity.CRITICAL: 4,
            ErrorSeverity.HIGH: 2,
            ErrorSeverity.MEDIUM: 0,
            ErrorSeverity.LOW: -2
        }
        priority += severity_adjustments.get(error.severity, 0)

        # Adjust based on component importance
        component_importance = {
            LauncherComponent.SMART_LAUNCHER: 3,
            LauncherComponent.GUI_INTERFACE: 2,
            LauncherComponent.AI_INTEGRATION: 2,
            LauncherComponent.SYSTEM_TRAY: 1,
            LauncherComponent.WINDOWS_BATCH: 1,
            LauncherComponent.PROCESS_MONITOR: 1
        }
        priority += component_importance.get(error.component, 0)

        # Adjust based on recovery attempts
        if error.recovery_attempts > error.max_recovery_attempts / 2:
            priority += 2

        return min(10, max(1, priority))

    def _estimate_recovery_time(self, strategy: RecoveryStrategy, error: LauncherError) -> int:
        """Estimate recovery time in seconds."""
        base_times = {
            RecoveryStrategy.RESTART_COMPONENT: 15,
            RecoveryStrategy.RESET_CONFIGURATION: 10,
            RecoveryStrategy.FALLBACK_MODE: 20,
            RecoveryStrategy.SAFE_MODE: 30,
            RecoveryStrategy.EMERGENCY_SHUTDOWN: 5,
            RecoveryStrategy.DEPENDENCY_REPAIR: 60,
            RecoveryStrategy.RESOURCE_CLEANUP: 25,
            RecoveryStrategy.CONFIG_ROLLBACK: 15
        }

        base_time = base_times.get(strategy, 20)

        # Adjust based on component complexity
        component_multipliers = {
            LauncherComponent.SMART_LAUNCHER: 1.5,
            LauncherComponent.AI_INTEGRATION: 2.0,
            LauncherComponent.SYSTEM_TRAY: 0.8,
            LauncherComponent.GUI_INTERFACE: 1.2
        }

        multiplier = component_multipliers.get(error.component, 1.0)
        return int(base_time * multiplier)

    async def _generate_recovery_actions(self, strategy: RecoveryStrategy,
                                       error: LauncherError) -> List[Dict[str, Any]]:
        """Generate specific recovery actions for the strategy."""
        actions = []
        component_config = self.recovery_strategies.get(error.component, {})

        if strategy == RecoveryStrategy.RESTART_COMPONENT:
            actions.extend([
                {
                    'type': 'stop_process',
                    'description': f'Stop {error.component.value} process',
                    'timeout_seconds': 10,
                    'required': True
                },
                {
                    'type': 'cleanup_resources',
                    'description': 'Clean up component resources',
                    'timeout_seconds': 5,
                    'required': False
                },
                {
                    'type': 'start_process',
                    'description': f'Restart {error.component.value}',
                    'command': component_config.get('restart_command'),
                    'timeout_seconds': component_config.get('recovery_timeout_seconds', 30),
                    'required': True
                }
            ])

        elif strategy == RecoveryStrategy.RESET_CONFIGURATION:
            config_path = component_config.get('config_path')
            if config_path:
                actions.extend([
                    {
                        'type': 'backup_config',
                        'description': 'Backup current configuration',
                        'config_path': config_path,
                        'timeout_seconds': 5,
                        'required': False
                    },
                    {
                        'type': 'reset_config',
                        'description': 'Reset to default configuration',
                        'config_path': config_path,
                        'timeout_seconds': 5,
                        'required': True
                    },
                    {
                        'type': 'validate_config',
                        'description': 'Validate new configuration',
                        'timeout_seconds': 10,
                        'required': True
                    }
                ])

        elif strategy == RecoveryStrategy.FALLBACK_MODE:
            if component_config.get('fallback_mode'):
                actions.append({
                    'type': 'enable_fallback',
                    'description': f'Enable fallback mode for {error.component.value}',
                    'timeout_seconds': 15,
                    'required': True
                })

        elif strategy == RecoveryStrategy.DEPENDENCY_REPAIR:
            dependencies = component_config.get('dependencies', [])
            for dep in dependencies:
                actions.append({
                    'type': 'check_dependency',
                    'description': f'Verify and repair dependency: {dep}',
                    'dependency': dep,
                    'timeout_seconds': 30,
                    'required': True
                })

        return actions

    def _define_success_criteria(self, error: LauncherError) -> List[str]:
        """Define success criteria for recovery validation."""
        return [
            f'{error.component.value} process is running',
            f'{error.component.value} responds to health checks',
            'No error patterns detected for 5 minutes',
            'System resources within normal ranges'
        ]

    async def _create_rollback_plan(self, strategy: RecoveryStrategy,
                                  error: LauncherError) -> Dict[str, Any]:
        """Create rollback plan in case recovery fails."""
        return {
            'enabled': True,
            'timeout_seconds': 60,
            'actions': [
                {
                    'type': 'restore_previous_state',
                    'description': f'Restore {error.component.value} to previous working state'
                },
                {
                    'type': 'enable_safe_mode',
                    'description': 'Enable safe mode operation'
                }
            ]
        }

    def _define_monitoring_requirements(self, error: LauncherError) -> Dict[str, Any]:
        """Define monitoring requirements post-recovery."""
        return {
            'duration_minutes': 30,
            'metrics': [
                'process_health',
                'response_time',
                'error_rate',
                'resource_usage'
            ],
            'alert_thresholds': {
                'error_rate': 0.05,  # 5% error rate
                'response_time_ms': 1000
            }
        }

    async def _execute_recovery_plan(self, plan: Dict[str, Any],
                                   error: LauncherError) -> Dict[str, Any]:
        """Execute the recovery plan with monitoring and rollback capabilities."""
        recovery_start = time.time()
        recovery_result = {
            'recovery_id': plan['recovery_id'],
            'component': error.component.value,
            'strategy': plan['strategy'].value,
            'start_time': recovery_start,
            'actions_executed': [],
            'success': False,
            'execution_time_seconds': 0,
            'error_details': None
        }

        try:
            # Execute recovery actions
            for action in plan['actions']:
                action_result = await self._execute_recovery_action(action, error)
                recovery_result['actions_executed'].append(action_result)

                if action.get('required', False) and not action_result['success']:
                    # Required action failed - abort recovery
                    recovery_result['error_details'] = f"Required action failed: {action['description']}"
                    break

            # Validate recovery success
            if not recovery_result.get('error_details'):
                success = await self._validate_recovery_success(plan, error)
                recovery_result['success'] = success

                if not success:
                    recovery_result['error_details'] = 'Recovery validation failed'

        except Exception as e:
            recovery_result['error_details'] = f'Recovery execution failed: {str(e)}'
            self.logger.error(f"Recovery execution error: {e}")

        recovery_result['execution_time_seconds'] = time.time() - recovery_start

        # Record recovery in history
        self.recovery_history.append({
            **asdict(error),
            **recovery_result,
            'timestamp': datetime.now().isoformat()
        })

        self.logger.info(
            f"Recovery completed for {error.component.value}",
            extra={
                "category": LogCategory.SYSTEM,
                "recovery_id": plan['recovery_id'],
                "success": recovery_result['success'],
                "execution_time": recovery_result['execution_time_seconds']
            }
        )

        return recovery_result

    async def _execute_recovery_action(self, action: Dict[str, Any],
                                     error: LauncherError) -> Dict[str, Any]:
        """Execute a single recovery action."""
        action_start = time.time()
        action_result = {
            'action_type': action['type'],
            'description': action['description'],
            'start_time': action_start,
            'success': False,
            'execution_time_seconds': 0,
            'error_details': None
        }

        try:
            action_type = action['type']
            timeout = action.get('timeout_seconds', 30)

            if action_type == 'stop_process':
                await self._stop_component_process(error.component)
                action_result['success'] = True

            elif action_type == 'start_process':
                command = action.get('command')
                if command:
                    await self._start_component_process(command, timeout)
                    action_result['success'] = True

            elif action_type == 'cleanup_resources':
                await self._cleanup_component_resources(error.component)
                action_result['success'] = True

            elif action_type == 'reset_config':
                config_path = action.get('config_path')
                if config_path:
                    await self._reset_component_config(config_path)
                    action_result['success'] = True

            elif action_type == 'check_dependency':
                dependency = action.get('dependency')
                if dependency:
                    success = await self._check_and_repair_dependency(dependency)
                    action_result['success'] = success

            else:
                action_result['error_details'] = f'Unknown action type: {action_type}'

        except Exception as e:
            action_result['error_details'] = str(e)
            self.logger.error(f"Action execution failed: {e}")

        action_result['execution_time_seconds'] = time.time() - action_start
        return action_result

    async def _stop_component_process(self, component: LauncherComponent):
        """Stop a component process gracefully."""
        # Implementation would depend on component type and process management
        # This is a placeholder for the actual implementation
        await asyncio.sleep(0.1)  # Simulate process stop

    async def _start_component_process(self, command: List[str], timeout: int):
        """Start a component process."""
        # Implementation would spawn the actual process
        # This is a placeholder for the actual implementation
        await asyncio.sleep(0.1)  # Simulate process start

    async def _cleanup_component_resources(self, component: LauncherComponent):
        """Clean up component resources."""
        # Implementation would clean up temporary files, connections, etc.
        await asyncio.sleep(0.1)  # Simulate cleanup

    async def _reset_component_config(self, config_path: str):
        """Reset component configuration to defaults."""
        # Implementation would reset configuration files
        await asyncio.sleep(0.1)  # Simulate config reset

    async def _check_and_repair_dependency(self, dependency: str) -> bool:
        """Check and repair a component dependency."""
        # Implementation would verify and repair dependencies
        await asyncio.sleep(0.1)  # Simulate dependency check
        return True

    async def _validate_recovery_success(self, plan: Dict[str, Any],
                                       error: LauncherError) -> bool:
        """Validate that recovery was successful."""
        success_criteria = plan['success_criteria']

        for criterion in success_criteria:
            if not await self._check_success_criterion(criterion, error.component):
                return False

        return True

    async def _check_success_criterion(self, criterion: str,
                                     component: LauncherComponent) -> bool:
        """Check a specific success criterion."""
        # Implementation would check actual success criteria
        # This is a placeholder for the actual validation
        await asyncio.sleep(0.1)
        return True

    async def _update_component_health(self, component: LauncherComponent,
                                     recovery_result: Dict[str, Any]):
        """Update component health status after recovery."""
        self.component_health[component] = {
            'last_recovery': datetime.now().isoformat(),
            'recovery_success': recovery_result['success'],
            'status': 'healthy' if recovery_result['success'] else 'degraded'
        }

    def _update_learning_data(self, error: LauncherError,
                            recovery_result: Dict[str, Any]):
        """Update learning data for improved future recoveries."""
        learning_key = f"{error.component.value}:{error.category.value}"

        if learning_key not in self.learning_data:
            self.learning_data[learning_key] = {
                'attempts': 0,
                'successes': 0,
                'strategies': {},
                'avg_recovery_time': 0
            }

        data = self.learning_data[learning_key]
        data['attempts'] += 1

        if recovery_result['success']:
            data['successes'] += 1

        strategy = recovery_result['strategy']
        if strategy not in data['strategies']:
            data['strategies'][strategy] = {'attempts': 0, 'successes': 0}

        data['strategies'][strategy]['attempts'] += 1
        if recovery_result['success']:
            data['strategies'][strategy]['successes'] += 1

        # Update average recovery time
        execution_time = recovery_result['execution_time_seconds']
        data['avg_recovery_time'] = (data['avg_recovery_time'] * (data['attempts'] - 1) + execution_time) / data['attempts']

    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get comprehensive recovery statistics."""
        total_recoveries = len(self.recovery_history)
        successful_recoveries = sum(1 for r in self.recovery_history if r.get('success', False))

        if total_recoveries == 0:
            return {
                'total_recoveries': 0,
                'success_rate': 0.0,
                'average_recovery_time': 0.0,
                'component_statistics': {},
                'strategy_effectiveness': {}
            }

        # Component statistics
        component_stats = {}
        for record in self.recovery_history:
            component = record.get('component')
            if component not in component_stats:
                component_stats[component] = {'attempts': 0, 'successes': 0}

            component_stats[component]['attempts'] += 1
            if record.get('success', False):
                component_stats[component]['successes'] += 1

        # Strategy effectiveness
        strategy_stats = {}
        for record in self.recovery_history:
            strategy = record.get('strategy')
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {'attempts': 0, 'successes': 0, 'avg_time': 0}

            strategy_stats[strategy]['attempts'] += 1
            if record.get('success', False):
                strategy_stats[strategy]['successes'] += 1

            # Update average time
            execution_time = record.get('execution_time_seconds', 0)
            current_attempts = strategy_stats[strategy]['attempts']
            strategy_stats[strategy]['avg_time'] = (
                (strategy_stats[strategy]['avg_time'] * (current_attempts - 1) + execution_time)
                / current_attempts
            )

        return {
            'total_recoveries': total_recoveries,
            'success_rate': successful_recoveries / total_recoveries,
            'average_recovery_time': sum(r.get('execution_time_seconds', 0) for r in self.recovery_history) / total_recoveries,
            'component_statistics': {
                comp: {
                    **stats,
                    'success_rate': stats['successes'] / stats['attempts'] if stats['attempts'] > 0 else 0
                }
                for comp, stats in component_stats.items()
            },
            'strategy_effectiveness': {
                strategy: {
                    **stats,
                    'success_rate': stats['successes'] / stats['attempts'] if stats['attempts'] > 0 else 0
                }
                for strategy, stats in strategy_stats.items()
            }
        }


# Global smart launcher recovery instance
_smart_launcher_recovery: Optional[SmartLauncherRecovery] = None


def get_smart_launcher_recovery() -> SmartLauncherRecovery:
    """Get the global smart launcher recovery instance."""
    global _smart_launcher_recovery
    if _smart_launcher_recovery is None:
        _smart_launcher_recovery = SmartLauncherRecovery()
    return _smart_launcher_recovery


async def handle_launcher_error(component: str, error_message: str,
                              severity: str = 'medium',
                              category: str = 'system') -> Dict[str, Any]:
    """
    Convenient function to handle launcher errors.

    Args:
        component: Component name (will be mapped to LauncherComponent enum)
        error_message: Error description
        severity: Error severity (critical, high, medium, low)
        category: Error category (system, network, validation, etc.)

    Returns:
        Recovery result dictionary
    """
    recovery_system = get_smart_launcher_recovery()

    # Map string component to enum
    component_mapping = {
        'smart_launcher': LauncherComponent.SMART_LAUNCHER,
        'system_tray': LauncherComponent.SYSTEM_TRAY,
        'windows_batch': LauncherComponent.WINDOWS_BATCH,
        'macos_command': LauncherComponent.MACOS_COMMAND,
        'linux_desktop': LauncherComponent.LINUX_DESKTOP,
        'gui_interface': LauncherComponent.GUI_INTERFACE,
        'process_monitor': LauncherComponent.PROCESS_MONITOR,
        'ai_integration': LauncherComponent.AI_INTEGRATION
    }

    launcher_component = component_mapping.get(component.lower(), LauncherComponent.SMART_LAUNCHER)

    # Map string severity to enum
    severity_mapping = {
        'critical': ErrorSeverity.CRITICAL,
        'high': ErrorSeverity.HIGH,
        'medium': ErrorSeverity.MEDIUM,
        'low': ErrorSeverity.LOW
    }

    error_severity = severity_mapping.get(severity.lower(), ErrorSeverity.MEDIUM)

    # Map string category to enum
    category_mapping = {
        'system': ErrorCategory.SYSTEM,
        'network': ErrorCategory.NETWORK,
        'validation': ErrorCategory.VALIDATION,
        'configuration': ErrorCategory.CONFIGURATION,
        'business_logic': ErrorCategory.BUSINESS_LOGIC,
        'external_service': ErrorCategory.EXTERNAL_SERVICE,
        'user_input': ErrorCategory.USER_INPUT,
        'parsing': ErrorCategory.PARSING
    }

    error_category = category_mapping.get(category.lower(), ErrorCategory.SYSTEM)

    # Create launcher error object
    launcher_error = LauncherError(
        error_id=f"error_{int(time.time())}",
        component=launcher_component,
        severity=error_severity,
        category=error_category,
        timestamp=datetime.now(),
        error_type=type(Exception()).__name__,
        error_message=error_message,
        stack_trace=None,
        system_context={},
        recovery_attempts=0,
        max_recovery_attempts=3,
        is_recoverable=True,
        suggested_strategy=RecoveryStrategy.RESTART_COMPONENT,
        confidence_score=0.8
    )

    # Execute recovery
    return await recovery_system.handle_launcher_error(launcher_error)