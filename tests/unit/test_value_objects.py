"""
Unit tests for Domain Value Objects.

Tests cover:
- InvestmentScore: 0.0-100.0 investment metric
- WaterScore: 0.0-15.0+ water feature score
- PricePerAcre: Calculated price per acre
- AssessedValueRatio: Bid to assessed value ratio

All Value Objects are immutable and self-validating.
"""

import pytest
from backend_api.domain.value_objects import (
    InvestmentScore,
    WaterScore,
    PricePerAcre,
    AssessedValueRatio,
)


# =============================================================================
# INVESTMENT SCORE TESTS
# =============================================================================

class TestInvestmentScore:
    """Test suite for InvestmentScore Value Object."""

    # -------------------------------------------------------------------------
    # Construction and Validation
    # -------------------------------------------------------------------------

    def test_create_valid_score(self):
        """Test creating a valid investment score."""
        score = InvestmentScore(75.5)
        assert score.value == 75.5

    def test_create_via_factory_method(self):
        """Test factory method creates valid score."""
        score = InvestmentScore.create(85.0)
        assert score.value == 85.0

    def test_create_from_integer(self):
        """Test creation from integer input."""
        score = InvestmentScore.create(50)
        assert score.value == 50.0
        assert isinstance(score.value, float)

    def test_create_zero_score(self):
        """Test creating zero investment score."""
        score = InvestmentScore(0.0)
        assert score.value == 0.0

    def test_create_maximum_score(self):
        """Test creating maximum investment score."""
        score = InvestmentScore(100.0)
        assert score.value == 100.0

    def test_zero_factory(self):
        """Test zero() factory method."""
        score = InvestmentScore.zero()
        assert score.value == 0.0

    def test_maximum_factory(self):
        """Test maximum() factory method."""
        score = InvestmentScore.maximum()
        assert score.value == 100.0

    def test_create_or_none_with_value(self):
        """Test create_or_none with valid value."""
        score = InvestmentScore.create_or_none(65.0)
        assert score is not None
        assert score.value == 65.0

    def test_create_or_none_with_none(self):
        """Test create_or_none returns None when input is None."""
        score = InvestmentScore.create_or_none(None)
        assert score is None

    # -------------------------------------------------------------------------
    # Validation Errors
    # -------------------------------------------------------------------------

    def test_negative_score_raises_error(self):
        """Test that negative scores raise ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            InvestmentScore(-1.0)

    def test_score_exceeding_maximum_raises_error(self):
        """Test that scores over 100 raise ValueError."""
        with pytest.raises(ValueError, match="cannot exceed 100"):
            InvestmentScore(100.1)

    def test_non_numeric_raises_type_error(self):
        """Test that non-numeric values raise TypeError."""
        with pytest.raises(TypeError, match="must be numeric"):
            InvestmentScore("high")

    def test_none_value_raises_type_error(self):
        """Test that None value raises TypeError."""
        with pytest.raises(TypeError):
            InvestmentScore(None)

    # -------------------------------------------------------------------------
    # Immutability
    # -------------------------------------------------------------------------

    def test_immutability(self):
        """Test that InvestmentScore is immutable."""
        score = InvestmentScore(75.0)
        with pytest.raises(AttributeError):
            score.value = 80.0

    def test_hash_consistency(self):
        """Test that equal scores have same hash."""
        score1 = InvestmentScore(50.0)
        score2 = InvestmentScore(50.0)
        assert hash(score1) == hash(score2)

    def test_can_use_in_set(self):
        """Test that scores can be used in sets."""
        scores = {InvestmentScore(50.0), InvestmentScore(50.0), InvestmentScore(75.0)}
        assert len(scores) == 2

    def test_can_use_as_dict_key(self):
        """Test that scores can be used as dictionary keys."""
        score_map = {InvestmentScore(50.0): "medium", InvestmentScore(90.0): "high"}
        assert score_map[InvestmentScore(50.0)] == "medium"

    # -------------------------------------------------------------------------
    # Business Logic Methods
    # -------------------------------------------------------------------------

    def test_is_high_value_default_threshold(self):
        """Test is_high_value with default threshold (70)."""
        assert InvestmentScore(75.0).is_high_value() is True
        assert InvestmentScore(70.0).is_high_value() is True
        assert InvestmentScore(69.9).is_high_value() is False

    def test_is_high_value_custom_threshold(self):
        """Test is_high_value with custom threshold."""
        assert InvestmentScore(85.0).is_high_value(threshold=80.0) is True
        assert InvestmentScore(79.9).is_high_value(threshold=80.0) is False

    def test_is_low_value_default_threshold(self):
        """Test is_low_value with default threshold (30)."""
        assert InvestmentScore(25.0).is_low_value() is True
        assert InvestmentScore(30.0).is_low_value() is True
        assert InvestmentScore(30.1).is_low_value() is False

    def test_is_low_value_custom_threshold(self):
        """Test is_low_value with custom threshold."""
        assert InvestmentScore(20.0).is_low_value(threshold=25.0) is True
        assert InvestmentScore(26.0).is_low_value(threshold=25.0) is False

    @pytest.mark.parametrize("value,expected_rating", [
        (95.0, "A+"),
        (90.0, "A+"),
        (85.0, "A"),
        (80.0, "A"),
        (75.0, "B"),
        (70.0, "B"),
        (65.0, "C"),
        (60.0, "C"),
        (55.0, "D"),
        (50.0, "D"),
        (45.0, "F"),
        (0.0, "F"),
    ])
    def test_to_rating(self, value, expected_rating):
        """Test rating conversion for various scores."""
        score = InvestmentScore(value)
        assert score.to_rating() == expected_rating

    def test_to_percentage_string(self):
        """Test percentage string formatting."""
        score = InvestmentScore(75.55)
        assert score.to_percentage_string() == "75.5%"

    # -------------------------------------------------------------------------
    # Comparison Operations
    # -------------------------------------------------------------------------

    def test_equality(self):
        """Test equality comparison."""
        assert InvestmentScore(50.0) == InvestmentScore(50.0)
        assert InvestmentScore(50.0) != InvestmentScore(51.0)

    def test_less_than(self):
        """Test less than comparison."""
        assert InvestmentScore(40.0) < InvestmentScore(50.0)
        assert not InvestmentScore(50.0) < InvestmentScore(50.0)

    def test_less_than_or_equal(self):
        """Test less than or equal comparison."""
        assert InvestmentScore(40.0) <= InvestmentScore(50.0)
        assert InvestmentScore(50.0) <= InvestmentScore(50.0)
        assert not InvestmentScore(60.0) <= InvestmentScore(50.0)

    def test_greater_than(self):
        """Test greater than comparison."""
        assert InvestmentScore(60.0) > InvestmentScore(50.0)
        assert not InvestmentScore(50.0) > InvestmentScore(50.0)

    def test_greater_than_or_equal(self):
        """Test greater than or equal comparison."""
        assert InvestmentScore(60.0) >= InvestmentScore(50.0)
        assert InvestmentScore(50.0) >= InvestmentScore(50.0)
        assert not InvestmentScore(40.0) >= InvestmentScore(50.0)

    def test_sorting(self):
        """Test that scores can be sorted."""
        scores = [InvestmentScore(75.0), InvestmentScore(25.0), InvestmentScore(50.0)]
        sorted_scores = sorted(scores)
        assert [s.value for s in sorted_scores] == [25.0, 50.0, 75.0]

    # -------------------------------------------------------------------------
    # String and Float Conversion
    # -------------------------------------------------------------------------

    def test_str_representation(self):
        """Test string representation."""
        score = InvestmentScore(75.5)
        assert str(score) == "75.50"

    def test_repr_representation(self):
        """Test repr representation."""
        score = InvestmentScore(75.5)
        assert repr(score) == "InvestmentScore(75.5)"

    def test_float_conversion(self):
        """Test conversion to float."""
        score = InvestmentScore(75.5)
        assert float(score) == 75.5


# =============================================================================
# WATER SCORE TESTS
# =============================================================================

class TestWaterScore:
    """Test suite for WaterScore Value Object."""

    # -------------------------------------------------------------------------
    # Construction and Validation
    # -------------------------------------------------------------------------

    def test_create_valid_score(self):
        """Test creating a valid water score."""
        score = WaterScore(8.5)
        assert score.value == 8.5

    def test_create_via_factory_method(self):
        """Test factory method creates valid score."""
        score = WaterScore.create(12.0)
        assert score.value == 12.0

    def test_create_zero_score(self):
        """Test creating zero water score."""
        score = WaterScore(0.0)
        assert score.value == 0.0

    def test_zero_factory(self):
        """Test zero() factory method."""
        score = WaterScore.zero()
        assert score.value == 0.0

    def test_create_exceptional_score(self):
        """Test that scores can exceed 15.0 for exceptional properties."""
        score = WaterScore(18.5)
        assert score.value == 18.5

    def test_create_or_default_with_value(self):
        """Test create_or_default with valid value."""
        score = WaterScore.create_or_default(7.5)
        assert score.value == 7.5

    def test_create_or_default_with_none(self):
        """Test create_or_default returns zero when input is None."""
        score = WaterScore.create_or_default(None)
        assert score.value == 0.0

    # -------------------------------------------------------------------------
    # Validation Errors
    # -------------------------------------------------------------------------

    def test_negative_score_raises_error(self):
        """Test that negative scores raise ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            WaterScore(-0.5)

    def test_non_numeric_raises_type_error(self):
        """Test that non-numeric values raise TypeError."""
        with pytest.raises(TypeError, match="must be numeric"):
            WaterScore("high")

    # -------------------------------------------------------------------------
    # Immutability
    # -------------------------------------------------------------------------

    def test_immutability(self):
        """Test that WaterScore is immutable."""
        score = WaterScore(7.0)
        with pytest.raises(AttributeError):
            score.value = 10.0

    def test_hash_consistency(self):
        """Test that equal scores have same hash."""
        score1 = WaterScore(5.0)
        score2 = WaterScore(5.0)
        assert hash(score1) == hash(score2)

    # -------------------------------------------------------------------------
    # Business Logic Methods
    # -------------------------------------------------------------------------

    def test_has_water_features_true(self):
        """Test has_water_features returns True for positive scores."""
        assert WaterScore(0.1).has_water_features() is True
        assert WaterScore(5.0).has_water_features() is True

    def test_has_water_features_false(self):
        """Test has_water_features returns False for zero score."""
        assert WaterScore(0.0).has_water_features() is False

    @pytest.mark.parametrize("value,expected_category", [
        (0.0, "none"),
        (1.5, "minimal"),
        (2.9, "minimal"),
        (3.0, "moderate"),
        (5.0, "moderate"),
        (6.9, "moderate"),
        (7.0, "excellent"),
        (10.0, "excellent"),
        (11.9, "excellent"),
        (12.0, "exceptional"),
        (15.0, "exceptional"),
        (20.0, "exceptional"),
    ])
    def test_get_water_category(self, value, expected_category):
        """Test water category classification."""
        score = WaterScore(value)
        assert score.get_water_category() == expected_category

    def test_is_premium_water_default_threshold(self):
        """Test is_premium_water with default threshold (10)."""
        assert WaterScore(12.0).is_premium_water() is True
        assert WaterScore(10.0).is_premium_water() is True
        assert WaterScore(9.9).is_premium_water() is False

    def test_is_premium_water_custom_threshold(self):
        """Test is_premium_water with custom threshold."""
        assert WaterScore(8.0).is_premium_water(threshold=7.0) is True
        assert WaterScore(6.0).is_premium_water(threshold=7.0) is False

    def test_to_display_string(self):
        """Test display string formatting."""
        assert WaterScore(0.0).to_display_string() == "0.0 (none)"
        assert WaterScore(5.5).to_display_string() == "5.5 (moderate)"
        assert WaterScore(12.5).to_display_string() == "12.5 (exceptional)"

    # -------------------------------------------------------------------------
    # Boolean Conversion
    # -------------------------------------------------------------------------

    def test_bool_true_for_positive(self):
        """Test boolean conversion is True for positive scores."""
        assert bool(WaterScore(0.1)) is True
        assert bool(WaterScore(5.0)) is True

    def test_bool_false_for_zero(self):
        """Test boolean conversion is False for zero score."""
        assert bool(WaterScore(0.0)) is False

    # -------------------------------------------------------------------------
    # Comparison Operations
    # -------------------------------------------------------------------------

    def test_equality(self):
        """Test equality comparison."""
        assert WaterScore(5.0) == WaterScore(5.0)
        assert WaterScore(5.0) != WaterScore(6.0)

    def test_less_than(self):
        """Test less than comparison."""
        assert WaterScore(4.0) < WaterScore(5.0)

    def test_greater_than(self):
        """Test greater than comparison."""
        assert WaterScore(6.0) > WaterScore(5.0)

    def test_sorting(self):
        """Test that scores can be sorted."""
        scores = [WaterScore(10.0), WaterScore(2.0), WaterScore(7.0)]
        sorted_scores = sorted(scores)
        assert [s.value for s in sorted_scores] == [2.0, 7.0, 10.0]

    # -------------------------------------------------------------------------
    # String and Float Conversion
    # -------------------------------------------------------------------------

    def test_str_representation(self):
        """Test string representation."""
        score = WaterScore(7.5)
        assert str(score) == "7.50"

    def test_repr_representation(self):
        """Test repr representation."""
        score = WaterScore(7.5)
        assert repr(score) == "WaterScore(7.5)"

    def test_float_conversion(self):
        """Test conversion to float."""
        score = WaterScore(7.5)
        assert float(score) == 7.5


# =============================================================================
# PRICE PER ACRE TESTS
# =============================================================================

class TestPricePerAcre:
    """Test suite for PricePerAcre Value Object."""

    # -------------------------------------------------------------------------
    # Construction and Calculation
    # -------------------------------------------------------------------------

    def test_create_valid_price(self):
        """Test creating a valid price per acre."""
        ppa = PricePerAcre(500.0)
        assert ppa.value == 500.0

    def test_calculate_from_amount_and_acreage(self):
        """Test calculation from amount and acreage."""
        ppa = PricePerAcre.calculate(10000.0, 5.0)
        assert ppa.value == 2000.0

    def test_calculate_fractional_acreage(self):
        """Test calculation with fractional acreage."""
        ppa = PricePerAcre.calculate(1500.0, 0.5)
        assert ppa.value == 3000.0

    def test_calculate_or_none_valid(self):
        """Test calculate_or_none with valid inputs."""
        ppa = PricePerAcre.calculate_or_none(5000.0, 2.5)
        assert ppa is not None
        assert ppa.value == 2000.0

    def test_calculate_or_none_none_amount(self):
        """Test calculate_or_none returns None when amount is None."""
        ppa = PricePerAcre.calculate_or_none(None, 2.5)
        assert ppa is None

    def test_calculate_or_none_none_acreage(self):
        """Test calculate_or_none returns None when acreage is None."""
        ppa = PricePerAcre.calculate_or_none(5000.0, None)
        assert ppa is None

    def test_calculate_or_none_zero_acreage(self):
        """Test calculate_or_none returns None for zero acreage."""
        ppa = PricePerAcre.calculate_or_none(5000.0, 0.0)
        assert ppa is None

    def test_calculate_or_none_negative_acreage(self):
        """Test calculate_or_none returns None for negative acreage."""
        ppa = PricePerAcre.calculate_or_none(5000.0, -1.0)
        assert ppa is None

    # -------------------------------------------------------------------------
    # Validation Errors
    # -------------------------------------------------------------------------

    def test_zero_price_raises_error(self):
        """Test that zero price raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            PricePerAcre(0.0)

    def test_negative_price_raises_error(self):
        """Test that negative price raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            PricePerAcre(-100.0)

    def test_calculate_zero_acreage_raises_error(self):
        """Test that zero acreage raises ValueError."""
        with pytest.raises(ValueError, match="Cannot calculate"):
            PricePerAcre.calculate(1000.0, 0.0)

    def test_non_numeric_raises_type_error(self):
        """Test that non-numeric values raise TypeError."""
        with pytest.raises(TypeError, match="must be numeric"):
            PricePerAcre("expensive")

    # -------------------------------------------------------------------------
    # Immutability
    # -------------------------------------------------------------------------

    def test_immutability(self):
        """Test that PricePerAcre is immutable."""
        ppa = PricePerAcre(500.0)
        with pytest.raises(AttributeError):
            ppa.value = 600.0

    # -------------------------------------------------------------------------
    # Business Logic Methods
    # -------------------------------------------------------------------------

    def test_is_below_market_true(self):
        """Test is_below_market returns True for below-market prices."""
        ppa = PricePerAcre(400.0)
        assert ppa.is_below_market(500.0) is True

    def test_is_below_market_false(self):
        """Test is_below_market returns False for at/above market prices."""
        ppa = PricePerAcre(500.0)
        assert ppa.is_below_market(500.0) is False
        assert ppa.is_below_market(400.0) is False

    def test_to_currency_string(self):
        """Test currency string formatting."""
        ppa = PricePerAcre(1234.56)
        assert ppa.to_currency_string() == "$1,234.56/acre"

    def test_to_currency_string_large_amount(self):
        """Test currency string for large amounts."""
        ppa = PricePerAcre(12345.67)
        assert ppa.to_currency_string() == "$12,345.67/acre"

    # -------------------------------------------------------------------------
    # String and Float Conversion
    # -------------------------------------------------------------------------

    def test_str_representation(self):
        """Test string representation."""
        ppa = PricePerAcre(1500.50)
        assert str(ppa) == "1500.50"

    def test_repr_representation(self):
        """Test repr representation."""
        ppa = PricePerAcre(1500.50)
        assert repr(ppa) == "PricePerAcre(1500.5)"

    def test_float_conversion(self):
        """Test conversion to float."""
        ppa = PricePerAcre(1500.50)
        assert float(ppa) == 1500.50


# =============================================================================
# ASSESSED VALUE RATIO TESTS
# =============================================================================

class TestAssessedValueRatio:
    """Test suite for AssessedValueRatio Value Object."""

    # -------------------------------------------------------------------------
    # Construction and Calculation
    # -------------------------------------------------------------------------

    def test_create_valid_ratio(self):
        """Test creating a valid ratio."""
        ratio = AssessedValueRatio(0.75)
        assert ratio.value == 0.75

    def test_calculate_from_amount_and_assessed_value(self):
        """Test calculation from amount and assessed value."""
        ratio = AssessedValueRatio.calculate(5000.0, 10000.0)
        assert ratio.value == 0.5

    def test_calculate_above_assessed_value(self):
        """Test calculation when bid exceeds assessed value."""
        ratio = AssessedValueRatio.calculate(15000.0, 10000.0)
        assert ratio.value == 1.5

    def test_calculate_equal_to_assessed_value(self):
        """Test calculation when bid equals assessed value."""
        ratio = AssessedValueRatio.calculate(10000.0, 10000.0)
        assert ratio.value == 1.0

    def test_calculate_or_none_valid(self):
        """Test calculate_or_none with valid inputs."""
        ratio = AssessedValueRatio.calculate_or_none(2500.0, 5000.0)
        assert ratio is not None
        assert ratio.value == 0.5

    def test_calculate_or_none_none_amount(self):
        """Test calculate_or_none returns None when amount is None."""
        ratio = AssessedValueRatio.calculate_or_none(None, 5000.0)
        assert ratio is None

    def test_calculate_or_none_none_assessed_value(self):
        """Test calculate_or_none returns None when assessed value is None."""
        ratio = AssessedValueRatio.calculate_or_none(2500.0, None)
        assert ratio is None

    def test_calculate_or_none_zero_assessed_value(self):
        """Test calculate_or_none returns None for zero assessed value."""
        ratio = AssessedValueRatio.calculate_or_none(2500.0, 0.0)
        assert ratio is None

    # -------------------------------------------------------------------------
    # Validation Errors
    # -------------------------------------------------------------------------

    def test_zero_ratio_raises_error(self):
        """Test that zero ratio raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            AssessedValueRatio(0.0)

    def test_negative_ratio_raises_error(self):
        """Test that negative ratio raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            AssessedValueRatio(-0.5)

    def test_calculate_zero_assessed_value_raises_error(self):
        """Test that zero assessed value raises ValueError."""
        with pytest.raises(ValueError, match="Cannot calculate"):
            AssessedValueRatio.calculate(1000.0, 0.0)

    def test_non_numeric_raises_type_error(self):
        """Test that non-numeric values raise TypeError."""
        with pytest.raises(TypeError, match="must be numeric"):
            AssessedValueRatio("low")

    # -------------------------------------------------------------------------
    # Immutability
    # -------------------------------------------------------------------------

    def test_immutability(self):
        """Test that AssessedValueRatio is immutable."""
        ratio = AssessedValueRatio(0.5)
        with pytest.raises(AttributeError):
            ratio.value = 0.6

    # -------------------------------------------------------------------------
    # Business Logic Methods
    # -------------------------------------------------------------------------

    def test_is_undervalued_default_threshold(self):
        """Test is_undervalued with default threshold (0.5)."""
        assert AssessedValueRatio(0.4).is_undervalued() is True
        assert AssessedValueRatio(0.5).is_undervalued() is True
        assert AssessedValueRatio(0.6).is_undervalued() is False

    def test_is_undervalued_custom_threshold(self):
        """Test is_undervalued with custom threshold."""
        assert AssessedValueRatio(0.7).is_undervalued(threshold=0.8) is True
        assert AssessedValueRatio(0.9).is_undervalued(threshold=0.8) is False

    def test_is_overvalued_default_threshold(self):
        """Test is_overvalued with default threshold (1.5)."""
        assert AssessedValueRatio(1.6).is_overvalued() is True
        assert AssessedValueRatio(1.5).is_overvalued() is True
        assert AssessedValueRatio(1.4).is_overvalued() is False

    def test_is_overvalued_custom_threshold(self):
        """Test is_overvalued with custom threshold."""
        assert AssessedValueRatio(1.3).is_overvalued(threshold=1.2) is True
        assert AssessedValueRatio(1.1).is_overvalued(threshold=1.2) is False

    def test_to_percentage_string(self):
        """Test percentage string formatting."""
        ratio = AssessedValueRatio(0.75)
        assert ratio.to_percentage_string() == "75.0%"

    def test_to_percentage_string_above_100(self):
        """Test percentage string for ratios above 1."""
        ratio = AssessedValueRatio(1.25)
        assert ratio.to_percentage_string() == "125.0%"

    # -------------------------------------------------------------------------
    # String and Float Conversion
    # -------------------------------------------------------------------------

    def test_str_representation(self):
        """Test string representation."""
        ratio = AssessedValueRatio(0.756)
        assert str(ratio) == "0.756"

    def test_repr_representation(self):
        """Test repr representation."""
        ratio = AssessedValueRatio(0.756)
        assert repr(ratio) == "AssessedValueRatio(0.756)"

    def test_float_conversion(self):
        """Test conversion to float."""
        ratio = AssessedValueRatio(0.756)
        assert float(ratio) == 0.756


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestValueObjectIntegration:
    """Integration tests for Value Objects working together."""

    def test_property_analysis_scenario(self):
        """Test realistic property analysis using multiple value objects."""
        # Scenario: Property listed at $5,000 for 2 acres, assessed at $15,000
        amount = 5000.0
        acreage = 2.0
        assessed_value = 15000.0
        water_score_value = 8.5
        investment_score_value = 72.5

        # Create value objects
        ppa = PricePerAcre.calculate(amount, acreage)
        ratio = AssessedValueRatio.calculate(amount, assessed_value)
        water = WaterScore.create(water_score_value)
        investment = InvestmentScore.create(investment_score_value)

        # Verify calculations
        assert ppa.value == 2500.0  # $2,500/acre
        assert round(ratio.value, 4) == 0.3333  # 33% of assessed
        assert water.get_water_category() == "excellent"
        assert investment.is_high_value() is True

        # Property appears to be a good opportunity
        assert ratio.is_undervalued() is True
        assert water.has_water_features() is True
        assert investment.to_rating() == "B"

    def test_value_objects_as_dict_values(self):
        """Test using value objects as dictionary values."""
        property_metrics = {
            "investment_score": InvestmentScore.create(85.0),
            "water_score": WaterScore.create(7.5),
            "price_per_acre": PricePerAcre.calculate(10000.0, 4.0),
            "assessed_ratio": AssessedValueRatio.calculate(10000.0, 25000.0),
        }

        assert float(property_metrics["investment_score"]) == 85.0
        assert float(property_metrics["water_score"]) == 7.5
        assert float(property_metrics["price_per_acre"]) == 2500.0
        assert float(property_metrics["assessed_ratio"]) == 0.4

    def test_comparison_based_filtering(self):
        """Test using value objects for comparison-based filtering."""
        properties = [
            {"id": 1, "score": InvestmentScore(85.0)},
            {"id": 2, "score": InvestmentScore(45.0)},
            {"id": 3, "score": InvestmentScore(72.0)},
            {"id": 4, "score": InvestmentScore(91.0)},
        ]

        # Filter high-value properties
        high_value = [p for p in properties if p["score"].is_high_value()]
        assert len(high_value) == 3
        assert {p["id"] for p in high_value} == {1, 3, 4}

        # Get top-rated property
        top_rated = max(properties, key=lambda p: p["score"])
        assert top_rated["id"] == 4
        assert top_rated["score"].to_rating() == "A+"
