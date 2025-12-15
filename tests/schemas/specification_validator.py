"""
Machine-readable test specification validator and loader.

This module provides validation and loading functionality for AI-testable
test specifications, ensuring they follow the required schema and can be
safely consumed by AI systems.
"""

import json
import jsonschema
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum


class TestCategory(Enum):
    """Enumeration of test categories for AI classification."""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    BENCHMARK = "benchmark"
    ERROR_HANDLING = "error_handling"
    AI_GENERATED = "ai_generated"


class Priority(Enum):
    """Test priority levels for AI execution planning."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Severity(Enum):
    """Error severity levels for AI error classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TestCase:
    """Structured representation of a test case."""
    id: str
    description: str
    category: TestCategory
    priority: Priority
    input_data: Dict[str, Any]
    expected_output: Dict[str, Any]
    ai_instructions: Optional[Dict[str, Any]] = None
    dependencies: List[str] = None
    tags: List[str] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []


@dataclass
class ErrorSpecification:
    """Structured representation of an error specification."""
    code: str
    category: str
    severity: Severity
    recoverable: bool
    context: Dict[str, Any]
    suggested_actions: List[str]
    documentation_reference: Optional[str] = None


@dataclass
class PerformanceThresholds:
    """Performance thresholds for AI validation."""
    max_duration_seconds: Optional[float] = None
    min_records_per_second: Optional[float] = None
    max_memory_usage_mb: Optional[float] = None
    max_cpu_usage_percent: Optional[float] = None
    success_rate_percent: Optional[float] = None


class SpecificationValidator:
    """Validator for test specifications using JSON Schema."""

    def __init__(self, schema_path: Optional[Path] = None):
        """Initialize the validator with schema."""
        if schema_path is None:
            schema_path = Path(__file__).parent / "test_specifications.json"

        self.schema_path = schema_path
        self.schema = self._load_schema()

    def _load_schema(self) -> Dict[str, Any]:
        """Load the JSON schema for validation."""
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")

        with open(self.schema_path, 'r') as f:
            return json.load(f)

    def validate_test_case(self, test_case_data: Dict[str, Any]) -> bool:
        """
        Validate a test case against the schema.

        Args:
            test_case_data: Test case data to validate

        Returns:
            True if valid, raises exception if invalid
        """
        test_case_schema = self.schema.get("definitions", {}).get("test_case")
        if not test_case_schema:
            raise ValueError("Test case schema not found in specifications")

        try:
            jsonschema.validate(test_case_data, test_case_schema)
            return True
        except jsonschema.ValidationError as e:
            raise ValueError(f"Test case validation failed: {e.message}")

    def validate_error_specification(self, error_spec_data: Dict[str, Any]) -> bool:
        """
        Validate an error specification against the schema.

        Args:
            error_spec_data: Error specification data to validate

        Returns:
            True if valid, raises exception if invalid
        """
        error_schema = self.schema.get("definitions", {}).get("error_specification")
        if not error_schema:
            raise ValueError("Error specification schema not found")

        try:
            jsonschema.validate(error_spec_data, error_schema)
            return True
        except jsonschema.ValidationError as e:
            raise ValueError(f"Error specification validation failed: {e.message}")

    def validate_performance_thresholds(self, perf_data: Dict[str, Any]) -> bool:
        """
        Validate performance thresholds against the schema.

        Args:
            perf_data: Performance threshold data to validate

        Returns:
            True if valid, raises exception if invalid
        """
        perf_schema = self.schema.get("definitions", {}).get("performance_thresholds")
        if not perf_schema:
            raise ValueError("Performance thresholds schema not found")

        try:
            jsonschema.validate(perf_data, perf_schema)
            return True
        except jsonschema.ValidationError as e:
            raise ValueError(f"Performance thresholds validation failed: {e.message}")

    def validate_full_specification(self, spec_data: Dict[str, Any]) -> bool:
        """
        Validate a complete specification file.

        Args:
            spec_data: Complete specification data to validate

        Returns:
            True if valid, raises exception if invalid
        """
        try:
            jsonschema.validate(spec_data, self.schema)
            return True
        except jsonschema.ValidationError as e:
            raise ValueError(f"Specification validation failed: {e.message}")


class SpecificationLoader:
    """Loader for AI-testable specifications."""

    def __init__(self, validator: Optional[SpecificationValidator] = None):
        """Initialize the loader with optional validator."""
        self.validator = validator or SpecificationValidator()

    def load_specifications(self, spec_path: Path) -> Dict[str, Any]:
        """
        Load and validate test specifications from file.

        Args:
            spec_path: Path to specifications file

        Returns:
            Validated specifications data
        """
        if not spec_path.exists():
            raise FileNotFoundError(f"Specifications file not found: {spec_path}")

        with open(spec_path, 'r') as f:
            spec_data = json.load(f)

        # Validate the loaded specifications
        self.validator.validate_full_specification(spec_data)

        return spec_data

    def load_test_suite(self, spec_path: Path, suite_name: str) -> Dict[str, Any]:
        """
        Load a specific test suite from specifications.

        Args:
            spec_path: Path to specifications file
            suite_name: Name of the test suite to load

        Returns:
            Test suite data
        """
        specifications = self.load_specifications(spec_path)
        test_suites = specifications.get("test_suites", {})

        if suite_name not in test_suites:
            available_suites = list(test_suites.keys())
            raise ValueError(f"Test suite '{suite_name}' not found. Available: {available_suites}")

        return test_suites[suite_name]

    def parse_test_case(self, test_case_data: Dict[str, Any]) -> TestCase:
        """
        Parse raw test case data into structured TestCase object.

        Args:
            test_case_data: Raw test case data from JSON

        Returns:
            Structured TestCase object
        """
        # Validate the test case data
        self.validator.validate_test_case(test_case_data)

        return TestCase(
            id=test_case_data["id"],
            description=test_case_data["description"],
            category=TestCategory(test_case_data["category"]),
            priority=Priority(test_case_data.get("priority", "medium")),
            input_data=test_case_data["input"],
            expected_output=test_case_data["expected_output"],
            ai_instructions=test_case_data.get("ai_instructions"),
            dependencies=test_case_data.get("dependencies", []),
            tags=test_case_data.get("tags", [])
        )

    def parse_error_specification(self, error_data: Dict[str, Any]) -> ErrorSpecification:
        """
        Parse raw error specification data into structured object.

        Args:
            error_data: Raw error specification data

        Returns:
            Structured ErrorSpecification object
        """
        # Validate the error specification data
        self.validator.validate_error_specification(error_data)

        return ErrorSpecification(
            code=error_data["code"],
            category=error_data["category"],
            severity=Severity(error_data["severity"]),
            recoverable=error_data["recoverable"],
            context=error_data["context"],
            suggested_actions=error_data["suggested_actions"],
            documentation_reference=error_data.get("documentation_reference")
        )

    def parse_performance_thresholds(self, perf_data: Dict[str, Any]) -> PerformanceThresholds:
        """
        Parse performance threshold data into structured object.

        Args:
            perf_data: Raw performance threshold data

        Returns:
            Structured PerformanceThresholds object
        """
        # Validate the performance data
        self.validator.validate_performance_thresholds(perf_data)

        return PerformanceThresholds(
            max_duration_seconds=perf_data.get("max_duration_seconds"),
            min_records_per_second=perf_data.get("min_records_per_second"),
            max_memory_usage_mb=perf_data.get("max_memory_usage_mb"),
            max_cpu_usage_percent=perf_data.get("max_cpu_usage_percent"),
            success_rate_percent=perf_data.get("success_rate_percent")
        )

    def get_test_cases_by_category(self, spec_path: Path, category: TestCategory) -> List[TestCase]:
        """
        Get all test cases of a specific category.

        Args:
            spec_path: Path to specifications file
            category: Test category to filter by

        Returns:
            List of test cases in the specified category
        """
        specifications = self.load_specifications(spec_path)
        test_suites = specifications.get("test_suites", {})

        test_cases = []
        for suite_name, suite_data in test_suites.items():
            for test_case_data in suite_data.get("test_cases", []):
                if test_case_data.get("category") == category.value:
                    test_cases.append(self.parse_test_case(test_case_data))

        return test_cases

    def get_test_cases_by_priority(self, spec_path: Path, priority: Priority) -> List[TestCase]:
        """
        Get all test cases of a specific priority.

        Args:
            spec_path: Path to specifications file
            priority: Priority level to filter by

        Returns:
            List of test cases with the specified priority
        """
        specifications = self.load_specifications(spec_path)
        test_suites = specifications.get("test_suites", {})

        test_cases = []
        for suite_name, suite_data in test_suites.items():
            for test_case_data in suite_data.get("test_cases", []):
                test_priority = test_case_data.get("priority", "medium")
                if test_priority == priority.value:
                    test_cases.append(self.parse_test_case(test_case_data))

        return test_cases

    def get_ai_executable_tests(self, spec_path: Path) -> List[TestCase]:
        """
        Get all test cases that can be executed automatically by AI.

        Args:
            spec_path: Path to specifications file

        Returns:
            List of AI-executable test cases
        """
        specifications = self.load_specifications(spec_path)
        test_suites = specifications.get("test_suites", {})

        ai_executable_tests = []
        for suite_name, suite_data in test_suites.items():
            for test_case_data in suite_data.get("test_cases", []):
                ai_instructions = test_case_data.get("ai_instructions", {})

                # Check if test requires human validation
                requires_human = ai_instructions.get("requires_human_validation", False)

                if not requires_human:
                    ai_executable_tests.append(self.parse_test_case(test_case_data))

        return ai_executable_tests


class AITestSpecificationGenerator:
    """Generator for AI-testable specifications from code analysis."""

    def __init__(self, loader: Optional[SpecificationLoader] = None):
        """Initialize the generator."""
        self.loader = loader or SpecificationLoader()

    def generate_unit_test_spec(self, function_name: str, module_name: str,
                              input_parameters: Dict[str, Any],
                              expected_output: Any,
                              **kwargs) -> Dict[str, Any]:
        """
        Generate a unit test specification.

        Args:
            function_name: Name of function to test
            module_name: Module containing the function
            input_parameters: Input parameters for the test
            expected_output: Expected output from the function
            **kwargs: Additional test configuration

        Returns:
            AI-testable test specification
        """
        test_id = f"{module_name}_{function_name}_test_{kwargs.get('test_number', '001')}"

        return {
            "id": test_id,
            "description": f"Test {function_name} function with specified inputs",
            "category": "unit",
            "priority": kwargs.get("priority", "medium"),
            "input": {
                "function_name": function_name,
                "module_name": module_name,
                "parameters": input_parameters
            },
            "expected_output": {
                "return_value": expected_output,
                "side_effects": kwargs.get("side_effects", []),
                "exceptions": kwargs.get("exceptions", {})
            },
            "ai_instructions": {
                "can_auto_retry": kwargs.get("can_retry", True),
                "max_retries": kwargs.get("max_retries", 3),
                "escalate_on_failure": kwargs.get("escalate_on_failure", False),
                "requires_human_validation": kwargs.get("requires_human", False)
            },
            "tags": kwargs.get("tags", ["unit", "auto_generated"])
        }

    def generate_integration_test_spec(self, workflow_name: str,
                                     components: List[str],
                                     input_data: Dict[str, Any],
                                     expected_outcome: Dict[str, Any],
                                     **kwargs) -> Dict[str, Any]:
        """
        Generate an integration test specification.

        Args:
            workflow_name: Name of the workflow being tested
            components: List of components involved in the workflow
            input_data: Input data for the workflow
            expected_outcome: Expected outcome of the workflow
            **kwargs: Additional test configuration

        Returns:
            AI-testable integration test specification
        """
        test_id = f"{workflow_name}_integration_test_{kwargs.get('test_number', '001')}"

        return {
            "id": test_id,
            "description": f"Integration test for {workflow_name} workflow",
            "category": "integration",
            "priority": kwargs.get("priority", "high"),
            "input": {
                "workflow_name": workflow_name,
                "components": components,
                "test_data": input_data,
                "environment": kwargs.get("environment", {})
            },
            "expected_output": {
                "workflow_result": expected_outcome,
                "performance_criteria": kwargs.get("performance_criteria", {}),
                "component_interactions": kwargs.get("component_interactions", [])
            },
            "ai_instructions": {
                "can_auto_retry": kwargs.get("can_retry", True),
                "max_retries": kwargs.get("max_retries", 2),
                "escalate_on_failure": kwargs.get("escalate_on_failure", True),
                "requires_human_validation": kwargs.get("requires_human", False)
            },
            "tags": kwargs.get("tags", ["integration", "workflow", "auto_generated"])
        }

    def generate_error_handling_spec(self, error_scenario: str,
                                   trigger_conditions: Dict[str, Any],
                                   expected_behavior: Dict[str, Any],
                                   **kwargs) -> Dict[str, Any]:
        """
        Generate an error handling test specification.

        Args:
            error_scenario: Description of the error scenario
            trigger_conditions: Conditions that trigger the error
            expected_behavior: Expected system behavior when error occurs
            **kwargs: Additional test configuration

        Returns:
            AI-testable error handling test specification
        """
        test_id = f"error_handling_{error_scenario.lower().replace(' ', '_')}_test_{kwargs.get('test_number', '001')}"

        return {
            "id": test_id,
            "description": f"Test error handling for: {error_scenario}",
            "category": "error_handling",
            "priority": kwargs.get("priority", "high"),
            "input": {
                "error_scenario": error_scenario,
                "trigger_conditions": trigger_conditions,
                "mock_conditions": kwargs.get("mock_conditions", {})
            },
            "expected_output": {
                "error_behavior": expected_behavior,
                "recovery_actions": kwargs.get("recovery_actions", []),
                "error_logging": kwargs.get("error_logging", {})
            },
            "ai_instructions": {
                "can_auto_retry": False,  # Error tests typically shouldn't auto-retry
                "max_retries": 0,
                "escalate_on_failure": kwargs.get("escalate_on_failure", True),
                "requires_human_validation": kwargs.get("requires_human", False)
            },
            "tags": kwargs.get("tags", ["error_handling", "reliability", "auto_generated"])
        }


# Utility functions for AI interaction
def load_ai_test_specifications(spec_file: str = "test_specifications.json") -> Dict[str, Any]:
    """
    Convenience function to load AI test specifications.

    Args:
        spec_file: Name of the specification file

    Returns:
        Loaded and validated specifications
    """
    spec_path = Path(__file__).parent / spec_file
    loader = SpecificationLoader()
    return loader.load_specifications(spec_path)


def get_ai_executable_test_plan(spec_file: str = "test_specifications.json") -> List[TestCase]:
    """
    Get a list of all tests that can be executed by AI systems.

    Args:
        spec_file: Name of the specification file

    Returns:
        List of AI-executable test cases
    """
    spec_path = Path(__file__).parent / spec_file
    loader = SpecificationLoader()
    return loader.get_ai_executable_tests(spec_path)


def validate_test_specification(spec_data: Dict[str, Any]) -> bool:
    """
    Validate a test specification for AI consumption.

    Args:
        spec_data: Test specification data to validate

    Returns:
        True if valid, raises exception if invalid
    """
    validator = SpecificationValidator()
    return validator.validate_full_specification(spec_data)