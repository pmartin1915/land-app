"""
Algorithm Validator for scoring consistency.
Ensures mathematical consistency across calculation methods.
"""

import logging
from typing import Tuple, List
from dataclasses import dataclass

from ...config import settings

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of algorithm validation."""
    is_compatible: bool
    message: str
    investment_score: float = 0.0
    water_score: float = 0.0


class AlgorithmValidator:
    """
    Validates algorithm compatibility across versions.
    Ensures mathematical consistency across calculation methods.
    """

    def __init__(
        self,
        compatible_versions: List[str] = None,
        expected_investment_score: float = None,
        expected_water_score: float = None,
        score_tolerance: float = None
    ):
        """
        Initialize validator with configuration.

        Args:
            compatible_versions: List of compatible algorithm versions
            expected_investment_score: Expected investment score for test case
            expected_water_score: Expected water score for test case
            score_tolerance: Tolerance for score comparison
        """
        self.compatible_versions = compatible_versions or settings.algorithm_versions_list
        self.expected_investment_score = expected_investment_score or settings.expected_investment_score
        self.expected_water_score = expected_water_score or settings.expected_water_score
        self.score_tolerance = score_tolerance or settings.score_tolerance

    def validate(
        self,
        algorithm_version: str,
        app_version: str
    ) -> ValidationResult:
        """
        Validate algorithm compatibility.

        Args:
            algorithm_version: Algorithm version string
            app_version: Client app version string

        Returns:
            ValidationResult with compatibility status and message
        """
        try:
            # Import and test algorithms
            from scripts.utils import calculate_investment_score, calculate_water_score
            from config.settings import INVESTMENT_SCORE_WEIGHTS

            # Test with known values
            test_investment_score = calculate_investment_score(
                5000.0, 3.0, 6.0, 0.8, INVESTMENT_SCORE_WEIGHTS
            )
            test_water_score = calculate_water_score('Beautiful creek frontage')

            # Validate investment score
            if abs(test_investment_score - self.expected_investment_score) > self.score_tolerance:
                return ValidationResult(
                    is_compatible=False,
                    message=(
                        f"Investment score algorithm mismatch: "
                        f"expected {self.expected_investment_score}, got {test_investment_score}"
                    ),
                    investment_score=test_investment_score,
                    water_score=test_water_score
                )

            # Validate water score
            if abs(test_water_score - self.expected_water_score) > self.score_tolerance:
                return ValidationResult(
                    is_compatible=False,
                    message=(
                        f"Water score algorithm mismatch: "
                        f"expected {self.expected_water_score}, got {test_water_score}"
                    ),
                    investment_score=test_investment_score,
                    water_score=test_water_score
                )

            # Version compatibility check
            if algorithm_version not in self.compatible_versions:
                return ValidationResult(
                    is_compatible=False,
                    message=f"Algorithm version {algorithm_version} not supported. "
                            f"Compatible versions: {', '.join(self.compatible_versions)}",
                    investment_score=test_investment_score,
                    water_score=test_water_score
                )

            return ValidationResult(
                is_compatible=True,
                message="Algorithms compatible",
                investment_score=test_investment_score,
                water_score=test_water_score
            )

        except ImportError as e:
            logger.error(f"Failed to import algorithm modules: {e}")
            return ValidationResult(
                is_compatible=False,
                message=f"Algorithm import failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Algorithm validation failed: {e}")
            return ValidationResult(
                is_compatible=False,
                message=f"Algorithm validation failed: {str(e)}"
            )


# Module-level convenience function
_validator_instance = None


def get_validator() -> AlgorithmValidator:
    """Get singleton validator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = AlgorithmValidator()
    return _validator_instance


def validate_algorithm_compatibility(
    algorithm_version: str,
    app_version: str
) -> Tuple[bool, str]:
    """
    Convenience function for algorithm validation.

    Args:
        algorithm_version: Algorithm version string
        app_version: Client app version string

    Returns:
        Tuple of (is_compatible, message)
    """
    result = get_validator().validate(algorithm_version, app_version)
    return result.is_compatible, result.message
