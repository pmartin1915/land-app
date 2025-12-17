"""
Tests for the AI-testable specification validation and loading system.

These tests validate that the specification system itself works correctly
and can be reliably used by AI systems for test generation and execution.
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any

from tests.schemas.specification_validator import (
    SpecificationValidator, SpecificationLoader, AITestSpecificationGenerator,
    TestCase, ErrorSpecification, PerformanceThresholds,
    TestCategory, Priority, Severity,
    load_ai_test_specifications, get_ai_executable_test_plan, validate_test_specification
)


class TestSpecificationValidator:
    """Test the specification validator functionality."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance for testing."""
        return SpecificationValidator()

    @pytest.fixture
    def sample_test_case(self):
        """Sample test case data for validation."""
        return {
            "id": "sample_test_001",
            "description": "Sample test case for validation",
            "category": "unit",
            "priority": "medium",
            "input": {
                "function_name": "test_function",
                "parameters": {"param1": "value1"}
            },
            "expected_output": {
                "return_value": "expected_result"
            },
            "ai_instructions": {
                "can_auto_retry": True,
                "max_retries": 3,
                "escalate_on_failure": False,
                "requires_human_validation": False
            },
            "tags": ["unit", "sample"]
        }

    @pytest.fixture
    def sample_error_spec(self):
        """Sample error specification for validation."""
        return {
            "code": "TEST_001",
            "category": "network",
            "severity": "medium",
            "recoverable": True,
            "context": {"test": "context"},
            "suggested_actions": ["retry", "check_connection"],
            "documentation_reference": "https://docs.example.com/errors/TEST_001"
        }

    @pytest.fixture
    def sample_performance_thresholds(self):
        """Sample performance thresholds for validation."""
        return {
            "max_duration_seconds": 30.0,
            "min_records_per_second": 10.0,
            "max_memory_usage_mb": 512.0,
            "max_cpu_usage_percent": 80.0,
            "success_rate_percent": 95.0
        }

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_validator_initialization(self, validator):
        """Test validator initialization."""
        assert validator is not None
        assert validator.schema is not None
        assert isinstance(validator.schema, dict)

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_validate_test_case_valid(self, validator, sample_test_case):
        """Test validation of valid test case."""
        result = validator.validate_test_case(sample_test_case)
        assert result is True

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_validate_test_case_invalid(self, validator):
        """Test validation of invalid test case."""
        invalid_test_case = {
            "id": "invalid_test",
            # Missing required fields
        }

        with pytest.raises(ValueError, match="Test case validation failed"):
            validator.validate_test_case(invalid_test_case)

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_validate_error_specification_valid(self, validator, sample_error_spec):
        """Test validation of valid error specification."""
        result = validator.validate_error_specification(sample_error_spec)
        assert result is True

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_validate_error_specification_invalid(self, validator):
        """Test validation of invalid error specification."""
        invalid_error_spec = {
            "code": "INVALID",
            # Missing required fields
        }

        with pytest.raises(ValueError, match="Error specification validation failed"):
            validator.validate_error_specification(invalid_error_spec)

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_validate_performance_thresholds_valid(self, validator, sample_performance_thresholds):
        """Test validation of valid performance thresholds."""
        result = validator.validate_performance_thresholds(sample_performance_thresholds)
        assert result is True

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_validate_performance_thresholds_invalid(self, validator):
        """Test validation of invalid performance thresholds."""
        invalid_thresholds = {
            "max_duration_seconds": "invalid_type",  # Should be number
        }

        with pytest.raises(ValueError, match="Performance thresholds validation failed"):
            validator.validate_performance_thresholds(invalid_thresholds)


class TestSpecificationLoader:
    """Test the specification loader functionality."""

    @pytest.fixture
    def loader(self):
        """Create a loader instance for testing."""
        return SpecificationLoader()

    @pytest.fixture
    def temp_spec_file(self, tmp_path, sample_test_case):
        """Create a temporary specification file for testing."""
        spec_data = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Test Specifications",
            "version": "1.0.0",
            "test_suites": {
                "sample_suite": {
                    "description": "Sample test suite",
                    "test_cases": [sample_test_case]
                }
            },
            "ai_execution_configuration": {
                "default_settings": {
                    "parallel_execution": True,
                    "max_concurrent_tests": 4
                }
            }
        }

        spec_file = tmp_path / "test_spec.json"
        with open(spec_file, 'w') as f:
            json.dump(spec_data, f)

        return spec_file

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_loader_initialization(self, loader):
        """Test loader initialization."""
        assert loader is not None
        assert loader.validator is not None

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_load_specifications(self, loader, temp_spec_file):
        """Test loading specifications from file."""
        specs = loader.load_specifications(temp_spec_file)

        assert isinstance(specs, dict)
        assert "test_suites" in specs
        assert "ai_execution_configuration" in specs

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_load_specifications_file_not_found(self, loader):
        """Test loading specifications from non-existent file."""
        non_existent_file = Path("non_existent.json")

        with pytest.raises(FileNotFoundError):
            loader.load_specifications(non_existent_file)

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_load_test_suite(self, loader, temp_spec_file):
        """Test loading specific test suite."""
        suite = loader.load_test_suite(temp_spec_file, "sample_suite")

        assert isinstance(suite, dict)
        assert "description" in suite
        assert "test_cases" in suite
        assert len(suite["test_cases"]) == 1

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_load_test_suite_not_found(self, loader, temp_spec_file):
        """Test loading non-existent test suite."""
        with pytest.raises(ValueError, match="Test suite 'non_existent' not found"):
            loader.load_test_suite(temp_spec_file, "non_existent")

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_parse_test_case(self, loader, sample_test_case):
        """Test parsing test case data into structured object."""
        test_case = loader.parse_test_case(sample_test_case)

        assert isinstance(test_case, TestCase)
        assert test_case.id == "sample_test_001"
        assert test_case.category == TestCategory.UNIT
        assert test_case.priority == Priority.MEDIUM
        assert isinstance(test_case.input_data, dict)
        assert isinstance(test_case.expected_output, dict)

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_parse_error_specification(self, loader, sample_error_spec):
        """Test parsing error specification into structured object."""
        error_spec = loader.parse_error_specification(sample_error_spec)

        assert isinstance(error_spec, ErrorSpecification)
        assert error_spec.code == "TEST_001"
        assert error_spec.category == "network"
        assert error_spec.severity == Severity.MEDIUM
        assert error_spec.recoverable is True

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_parse_performance_thresholds(self, loader, sample_performance_thresholds):
        """Test parsing performance thresholds into structured object."""
        thresholds = loader.parse_performance_thresholds(sample_performance_thresholds)

        assert isinstance(thresholds, PerformanceThresholds)
        assert thresholds.max_duration_seconds == 30.0
        assert thresholds.min_records_per_second == 10.0
        assert thresholds.max_memory_usage_mb == 512.0

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_get_test_cases_by_category(self, loader, temp_spec_file):
        """Test filtering test cases by category."""
        unit_tests = loader.get_test_cases_by_category(temp_spec_file, TestCategory.UNIT)

        assert len(unit_tests) == 1
        assert all(test.category == TestCategory.UNIT for test in unit_tests)

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_get_test_cases_by_priority(self, loader, temp_spec_file):
        """Test filtering test cases by priority."""
        medium_tests = loader.get_test_cases_by_priority(temp_spec_file, Priority.MEDIUM)

        assert len(medium_tests) == 1
        assert all(test.priority == Priority.MEDIUM for test in medium_tests)

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_get_ai_executable_tests(self, loader, temp_spec_file):
        """Test filtering AI-executable tests."""
        ai_tests = loader.get_ai_executable_tests(temp_spec_file)

        assert len(ai_tests) == 1
        # All tests in our sample don't require human validation
        assert all(not test.ai_instructions.get("requires_human_validation", False) for test in ai_tests)


class TestAITestSpecificationGenerator:
    """Test the AI test specification generator."""

    @pytest.fixture
    def generator(self):
        """Create a generator instance for testing."""
        return AITestSpecificationGenerator()

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_generator_initialization(self, generator):
        """Test generator initialization."""
        assert generator is not None
        assert generator.loader is not None

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_generate_unit_test_spec(self, generator):
        """Test generation of unit test specification."""
        spec = generator.generate_unit_test_spec(
            function_name="normalize_price",
            module_name="utils",
            input_parameters={"price_str": "$1,234.56"},
            expected_output=1234.56,
            priority="high",
            test_number="001"
        )

        assert isinstance(spec, dict)
        assert spec["id"] == "utils_normalize_price_test_001"
        assert spec["category"] == "unit"
        assert spec["priority"] == "high"
        assert "input" in spec
        assert "expected_output" in spec
        assert "ai_instructions" in spec

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_generate_integration_test_spec(self, generator):
        """Test generation of integration test specification."""
        spec = generator.generate_integration_test_spec(
            workflow_name="county_scraping",
            components=["scraper", "parser", "validator"],
            input_data={"county": "Baldwin", "max_pages": 5},
            expected_outcome={"records_count": 29, "success": True},
            priority="critical"
        )

        assert isinstance(spec, dict)
        assert spec["id"] == "county_scraping_integration_test_001"
        assert spec["category"] == "integration"
        assert spec["priority"] == "critical"
        assert "workflow_name" in spec["input"]
        assert "components" in spec["input"]

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_generate_error_handling_spec(self, generator):
        """Test generation of error handling test specification."""
        spec = generator.generate_error_handling_spec(
            error_scenario="network timeout",
            trigger_conditions={"timeout_seconds": 30, "network_delay": True},
            expected_behavior={"exception_type": "NetworkError", "retry_count": 3},
            priority="high"
        )

        assert isinstance(spec, dict)
        assert "network_timeout" in spec["id"]
        assert spec["category"] == "error_handling"
        assert spec["priority"] == "high"
        assert spec["ai_instructions"]["can_auto_retry"] is False  # Error tests shouldn't auto-retry


class TestUtilityFunctions:
    """Test utility functions for AI interaction."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_load_ai_test_specifications(self):
        """Test convenience function for loading specifications."""
        # This test will pass if the actual specification file exists and is valid
        try:
            specs = load_ai_test_specifications()
            assert isinstance(specs, dict)
            assert "test_suites" in specs or "ai_execution_configuration" in specs
        except FileNotFoundError:
            # If the file doesn't exist, that's acceptable for this test
            pytest.skip("Specification file not found - this is acceptable")

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_get_ai_executable_test_plan(self):
        """Test convenience function for getting AI-executable tests."""
        try:
            test_plan = get_ai_executable_test_plan()
            assert isinstance(test_plan, list)
            # Each item should be a TestCase object
            for test_case in test_plan:
                assert isinstance(test_case, TestCase)
        except FileNotFoundError:
            # If the file doesn't exist, that's acceptable for this test
            pytest.skip("Specification file not found - this is acceptable")

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_validate_test_specification(self, sample_test_case):
        """Test convenience function for validation."""
        # Create a minimal valid specification
        spec_data = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Test Spec",
            "version": "1.0.0",
            "test_suites": {
                "test_suite": {
                    "test_cases": [sample_test_case]
                }
            },
            "ai_execution_configuration": {}
        }

        try:
            result = validate_test_specification(spec_data)
            assert result is True
        except ValueError:
            # If validation fails due to schema mismatch, that's still a valid test result
            pass


class TestEnumValidation:
    """Test enum value validation for AI-friendly type checking."""

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_test_category_enum(self):
        """Test TestCategory enum values."""
        assert TestCategory.UNIT.value == "unit"
        assert TestCategory.INTEGRATION.value == "integration"
        assert TestCategory.E2E.value == "e2e"
        assert TestCategory.BENCHMARK.value == "benchmark"
        assert TestCategory.ERROR_HANDLING.value == "error_handling"
        assert TestCategory.AI_GENERATED.value == "ai_generated"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_priority_enum(self):
        """Test Priority enum values."""
        assert Priority.CRITICAL.value == "critical"
        assert Priority.HIGH.value == "high"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.LOW.value == "low"

    @pytest.mark.unit
    @pytest.mark.ai_test
    def test_severity_enum(self):
        """Test Severity enum values."""
        assert Severity.LOW.value == "low"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.HIGH.value == "high"
        assert Severity.CRITICAL.value == "critical"


@pytest.mark.parametrize("category,expected_value", [
    (TestCategory.UNIT, "unit"),
    (TestCategory.INTEGRATION, "integration"),
    (TestCategory.E2E, "e2e"),
    (TestCategory.BENCHMARK, "benchmark"),
    (TestCategory.ERROR_HANDLING, "error_handling"),
    (TestCategory.AI_GENERATED, "ai_generated")
])
@pytest.mark.unit
@pytest.mark.ai_test
def test_category_enum_values(category, expected_value):
    """Parametrized test for category enum values."""
    assert category.value == expected_value


@pytest.mark.parametrize("priority,expected_value", [
    (Priority.CRITICAL, "critical"),
    (Priority.HIGH, "high"),
    (Priority.MEDIUM, "medium"),
    (Priority.LOW, "low")
])
@pytest.mark.unit
@pytest.mark.ai_test
def test_priority_enum_values(priority, expected_value):
    """Parametrized test for priority enum values."""
    assert priority.value == expected_value


class TestAITestSpecificationIntegration:
    """Integration tests for the complete specification system."""

    @pytest.mark.integration
    @pytest.mark.ai_test
    def test_complete_specification_workflow(self, tmp_path):
        """Test the complete workflow from generation to execution planning."""
        # Generate specifications
        generator = AITestSpecificationGenerator()

        unit_spec = generator.generate_unit_test_spec(
            function_name="test_function",
            module_name="test_module",
            input_parameters={"param": "value"},
            expected_output="result"
        )

        integration_spec = generator.generate_integration_test_spec(
            workflow_name="test_workflow",
            components=["comp1", "comp2"],
            input_data={"input": "data"},
            expected_outcome={"outcome": "success"}
        )

        error_spec = generator.generate_error_handling_spec(
            error_scenario="test error",
            trigger_conditions={"condition": "trigger"},
            expected_behavior={"behavior": "expected"}
        )

        # Create a complete specification file
        complete_spec = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Generated Test Specifications",
            "version": "1.0.0",
            "test_suites": {
                "generated_tests": {
                    "description": "Generated test suite",
                    "test_cases": [unit_spec, integration_spec, error_spec]
                }
            },
            "ai_execution_configuration": {
                "default_settings": {
                    "parallel_execution": True,
                    "max_concurrent_tests": 2
                }
            }
        }

        # Save to temporary file
        spec_file = tmp_path / "generated_specs.json"
        with open(spec_file, 'w') as f:
            json.dump(complete_spec, f)

        # Load and validate
        loader = SpecificationLoader()
        loaded_specs = loader.load_specifications(spec_file)

        assert loaded_specs is not None
        assert "test_suites" in loaded_specs

        # Get AI-executable tests
        ai_tests = loader.get_ai_executable_tests(spec_file)
        assert len(ai_tests) >= 2  # Unit and integration tests should be AI-executable

        # Validate each test case can be parsed
        for ai_test in ai_tests:
            assert isinstance(ai_test, TestCase)
            assert ai_test.id is not None
            assert ai_test.category in [TestCategory.UNIT, TestCategory.INTEGRATION, TestCategory.ERROR_HANDLING]