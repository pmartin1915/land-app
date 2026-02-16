"""
Unit tests for core/guardrails.py - Investment bid decision logic.

Tests evaluate_parcel() which determines whether to bid on a property
based on LTV ratio, market value, property type, and equity margin.
"""

import pytest
from core.models import Parcel, Lien
from core.guardrails import evaluate_parcel, MAX_LTV, MIN_VALUE, BANNED_TYPES


def make_parcel(
    parcel_id="TEST-001",
    county="Pulaski",
    assessed_value=20000.0,
    market_value_estimate=50000.0,
    property_type="RESIDENTIAL",
    tax_due=1000.0,
    other_liens=None,
):
    return Parcel(
        parcel_id=parcel_id,
        county=county,
        assessed_value=assessed_value,
        market_value_estimate=market_value_estimate,
        property_type=property_type,
        tax_due=tax_due,
        other_liens=other_liens or [],
    )


class TestBannedPropertyTypes:

    @pytest.mark.parametrize("banned_type", BANNED_TYPES)
    def test_banned_types_rejected(self, banned_type):
        parcel = make_parcel(property_type=banned_type)
        decision = evaluate_parcel(parcel)
        assert decision.should_bid is False
        assert decision.max_bid_amount == 0.0
        assert "Banned Property Type" in decision.reason

    def test_banned_type_case_insensitive(self):
        parcel = make_parcel(property_type="common area")
        decision = evaluate_parcel(parcel)
        assert decision.should_bid is False

    def test_banned_type_partial_match(self):
        """Banned substring within a longer type string is still caught."""
        parcel = make_parcel(property_type="RESIDENTIAL COMMON AREA LOT")
        decision = evaluate_parcel(parcel)
        assert decision.should_bid is False

    def test_non_banned_type_accepted(self):
        parcel = make_parcel(property_type="RESIDENTIAL")
        decision = evaluate_parcel(parcel)
        assert decision.should_bid is True


class TestLTVRatio:

    def test_ltv_above_max_rejected(self):
        """LTV > 0.60 is rejected."""
        # tax_due=35000 on market_value=50000 -> LTV = 0.70
        parcel = make_parcel(tax_due=35000.0, market_value_estimate=50000.0)
        decision = evaluate_parcel(parcel)
        assert decision.should_bid is False
        assert "LTV too high" in decision.reason

    def test_ltv_at_boundary_accepted(self):
        """LTV == 0.60 exactly passes (guard is strict >)."""
        # tax_due=30000 on market_value=50000 -> LTV = 0.60
        parcel = make_parcel(tax_due=30000.0, market_value_estimate=50000.0)
        decision = evaluate_parcel(parcel)
        assert decision.should_bid is True

    def test_ltv_just_above_boundary_rejected(self):
        # tax_due=30001 on market_value=50000 -> LTV = 0.60002
        parcel = make_parcel(tax_due=30001.0, market_value_estimate=50000.0)
        decision = evaluate_parcel(parcel)
        assert decision.should_bid is False

    def test_ltv_with_liens(self):
        """Other liens add to total encumbrance."""
        liens = [Lien(amount=25000.0, holder="County")]
        # tax_due=1000 + lien=25000 = 26000 on 50000 -> LTV = 0.52
        parcel = make_parcel(tax_due=1000.0, other_liens=liens)
        decision = evaluate_parcel(parcel)
        assert decision.should_bid is True

    def test_ltv_with_liens_over_threshold(self):
        liens = [Lien(amount=29000.0, holder="County")]
        # tax_due=1000 + lien=29000 = 30000 on 50000 -> LTV = 0.60 (passes)
        parcel = make_parcel(tax_due=1000.0, other_liens=liens)
        decision = evaluate_parcel(parcel)
        assert decision.should_bid is True

        liens2 = [Lien(amount=30000.0, holder="County")]
        # tax_due=1000 + lien=30000 = 31000 on 50000 -> LTV = 0.62 (fails)
        parcel2 = make_parcel(tax_due=1000.0, other_liens=liens2)
        decision2 = evaluate_parcel(parcel2)
        assert decision2.should_bid is False


class TestMinimumValue:

    def test_value_below_minimum_rejected(self):
        parcel = make_parcel(market_value_estimate=4999.0)
        decision = evaluate_parcel(parcel)
        assert decision.should_bid is False
        assert "Value too low" in decision.reason

    def test_value_at_minimum_accepted(self):
        parcel = make_parcel(market_value_estimate=5000.0)
        decision = evaluate_parcel(parcel)
        assert decision.should_bid is True

    def test_value_well_above_minimum(self):
        parcel = make_parcel(market_value_estimate=100000.0)
        decision = evaluate_parcel(parcel)
        assert decision.should_bid is True


class TestNegativeEquity:
    """
    With current constants (MAX_LTV=0.60, margin=0.30), negative equity
    requires encumbrance >= 70% of market value, but LTV rejects at 60%.
    So this path is unreachable under normal constants. We patch MAX_LTV
    to test the code path as a safety net.
    """

    def test_negative_equity_rejected(self, monkeypatch):
        """safe_bid = (market * 0.70) - encumbrance <= 0 -> rejected."""
        import core.guardrails as g
        monkeypatch.setattr(g, "MAX_LTV", 1.0)  # Disable LTV gate
        # market=50000, target = 35000, encumbrance = 35000 -> safe_bid = 0
        liens = [Lien(amount=30000.0, holder="County")]
        parcel = make_parcel(
            market_value_estimate=50000.0, tax_due=5000.0, other_liens=liens
        )
        decision = evaluate_parcel(parcel)
        assert decision.should_bid is False
        assert "Negative Equity" in decision.reason

    def test_barely_positive_equity_accepted(self, monkeypatch):
        import core.guardrails as g
        monkeypatch.setattr(g, "MAX_LTV", 1.0)
        # market=50000, target = 35000, encumbrance = 34999 -> safe_bid = 1.0
        liens = [Lien(amount=29999.0, holder="County")]
        parcel = make_parcel(
            market_value_estimate=50000.0, tax_due=5000.0, other_liens=liens
        )
        decision = evaluate_parcel(parcel)
        assert decision.should_bid is True
        assert decision.max_bid_amount == 1.0


class TestHappyPath:

    def test_clean_parcel_passes(self):
        parcel = make_parcel(
            market_value_estimate=50000.0,
            tax_due=1000.0,
            property_type="RESIDENTIAL",
        )
        decision = evaluate_parcel(parcel)
        assert decision.should_bid is True
        assert decision.reason == "Passed all guardrails"
        assert decision.parcel_id == "TEST-001"

    def test_max_bid_calculation(self):
        """max_bid = (market_value * 0.70) - total_encumbrance, rounded to 2 dp."""
        parcel = make_parcel(market_value_estimate=50000.0, tax_due=1000.0)
        decision = evaluate_parcel(parcel)
        # (50000 * 0.70) - 1000 = 35000 - 1000 = 34000.0
        assert decision.max_bid_amount == 34000.0

    def test_max_bid_with_multiple_liens(self):
        liens = [
            Lien(amount=500.0, holder="County"),
            Lien(amount=1500.0, holder="City"),
        ]
        parcel = make_parcel(
            market_value_estimate=50000.0,
            tax_due=1000.0,
            other_liens=liens,
        )
        decision = evaluate_parcel(parcel)
        # (50000 * 0.70) - (1000 + 500 + 1500) = 35000 - 3000 = 32000.0
        assert decision.max_bid_amount == 32000.0

    def test_max_bid_rounding(self):
        """Verify 2 decimal place rounding."""
        # market=7777.0, tax=100.0
        # (7777.0 * 0.70) - 100 = 5443.9 - 100 = 5343.9
        parcel = make_parcel(market_value_estimate=7777.0, tax_due=100.0)
        decision = evaluate_parcel(parcel)
        assert decision.max_bid_amount == 5343.9


class TestCheckOrder:
    """Verify guardrail checks execute in priority order."""

    def test_banned_type_checked_before_ltv(self):
        """A banned type with high LTV still reports banned type, not LTV."""
        parcel = make_parcel(
            property_type="ROAD",
            tax_due=40000.0,
            market_value_estimate=50000.0,
        )
        decision = evaluate_parcel(parcel)
        assert "Banned Property Type" in decision.reason

    def test_ltv_checked_before_value(self):
        """High LTV on low-value property reports LTV, not low value."""
        parcel = make_parcel(
            market_value_estimate=3000.0,
            assessed_value=1000.0,
            tax_due=2500.0,  # LTV = 2500/3000 = 0.833
        )
        decision = evaluate_parcel(parcel)
        assert "LTV too high" in decision.reason


class TestConstants:
    """Verify guardrail constants match documented values."""

    def test_max_ltv(self):
        assert MAX_LTV == 0.60

    def test_min_value(self):
        assert MIN_VALUE == 5000.0

    def test_banned_types(self):
        assert "COMMON AREA" in BANNED_TYPES
        assert "ROAD" in BANNED_TYPES
        assert "RETENTION POND" in BANNED_TYPES
        assert "UNKNOWN" in BANNED_TYPES
