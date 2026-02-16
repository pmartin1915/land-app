"""
Unit tests for core/scoring.py - Multi-state investment scoring engine.

Tests PropertyScoreInput, ScoringEngine, and convenience functions.
All pure logic - uses real state configs, no mocking needed.
"""

import pytest

from core.scoring import (
    PropertyScoreInput,
    ScoreResult,
    ScoringEngine,
    calculate_multistate_scores,
    calculate_buy_hold_score,
    calculate_wholesale_score,
    DEFAULT_CAPITAL_LIMIT,
    MIN_WHOLESALE_SPREAD_DOLLARS,
    MIN_WHOLESALE_SPREAD_PCT,
    STALE_DELINQUENCY_THRESHOLD,
    DELTA_REGION_COUNTIES,
    DELTA_REGION_PENALTY,
)


# ============================================================================
# Helpers
# ============================================================================

def make_input(**overrides) -> PropertyScoreInput:
    """Create a PropertyScoreInput with sensible defaults."""
    defaults = dict(
        state="AR",
        sale_type="tax_deed",
        amount=500.0,
        acreage=5.0,
        water_score=0.0,
        assessed_value=None,
        estimated_market_value=None,
        description_score=0.0,
        year_sold=None,
        county=None,
    )
    defaults.update(overrides)
    return PropertyScoreInput(**defaults)


# ============================================================================
# PropertyScoreInput Tests
# ============================================================================

class TestEffectiveCost:

    def test_arkansas_effective_cost(self):
        """AR: $1500 quiet title + 10% overhead."""
        inp = make_input(state="AR", amount=1000.0)
        # 1000 + 1500 (QT) + 100 (10% overhead) = 2600
        assert inp.get_effective_cost() == 2600.0

    def test_alabama_effective_cost(self):
        """AL: $4000 quiet title + 10% overhead."""
        inp = make_input(state="AL", amount=1000.0, sale_type="tax_lien")
        # 1000 + 4000 (QT) + 100 (10% overhead) = 5100
        assert inp.get_effective_cost() == 5100.0

    def test_texas_effective_cost(self):
        """TX: $2000 quiet title + 10% overhead."""
        inp = make_input(state="TX", amount=1000.0, sale_type="redeemable_deed")
        # 1000 + 2000 + 100 = 3100
        assert inp.get_effective_cost() == 3100.0

    def test_florida_effective_cost(self):
        """FL: $1500 quiet title + 10% overhead."""
        inp = make_input(state="FL", amount=1000.0, sale_type="hybrid")
        # 1000 + 1500 + 100 = 2600
        assert inp.get_effective_cost() == 2600.0


class TestEffectivePricePerAcre:

    def test_normal_calculation(self):
        inp = make_input(state="AR", amount=1000.0, acreage=5.0)
        # effective_cost = 2600, PPA = 2600 / 5.0 = 520.0
        assert inp.get_effective_price_per_acre() == 520.0

    def test_zero_acreage_returns_infinity(self):
        inp = make_input(acreage=0.0)
        assert inp.get_effective_price_per_acre() == float("inf")

    def test_negative_acreage_returns_infinity(self):
        inp = make_input(acreage=-1.0)
        assert inp.get_effective_price_per_acre() == float("inf")


class TestMarketValueEstimate:

    def test_prefers_estimated_market_value(self):
        inp = make_input(
            estimated_market_value=50000.0, assessed_value=10000.0, state="AR"
        )
        assert inp.get_market_value_estimate() == 50000.0

    def test_falls_back_to_assessed_value(self):
        """AR assessed at 20% ratio -> market = assessed / 0.20."""
        inp = make_input(assessed_value=10000.0, state="AR")
        # 10000 / 0.20 = 50000
        assert inp.get_market_value_estimate() == 50000.0

    def test_alabama_assessed_ratio(self):
        """AL assessed at 10% -> market = assessed / 0.10."""
        inp = make_input(
            state="AL", sale_type="tax_lien", assessed_value=5000.0
        )
        assert inp.get_market_value_estimate() == 50000.0

    def test_texas_assessed_ratio(self):
        """TX assessed at 100% -> market = assessed."""
        inp = make_input(
            state="TX", sale_type="redeemable_deed", assessed_value=50000.0
        )
        assert inp.get_market_value_estimate() == 50000.0

    def test_no_values_returns_none(self):
        inp = make_input()
        assert inp.get_market_value_estimate() is None

    def test_zero_estimated_falls_back(self):
        inp = make_input(estimated_market_value=0.0, assessed_value=10000.0, state="AR")
        assert inp.get_market_value_estimate() == 50000.0

    def test_zero_assessed_returns_none(self):
        inp = make_input(assessed_value=0.0)
        assert inp.get_market_value_estimate() is None


class TestMarketReject:

    def test_pre_2015_is_reject(self):
        inp = make_input(year_sold="2014")
        assert inp.is_market_reject() is True

    def test_2015_is_not_reject(self):
        inp = make_input(year_sold="2015")
        assert inp.is_market_reject() is False

    def test_recent_year_not_reject(self):
        inp = make_input(year_sold="2024")
        assert inp.is_market_reject() is False

    def test_none_fails_open(self):
        inp = make_input(year_sold=None)
        assert inp.is_market_reject() is False

    def test_malformed_year_fails_open(self):
        inp = make_input(year_sold="N/A")
        assert inp.is_market_reject() is False


class TestDeltaRegion:

    def test_delta_county_detected(self):
        inp = make_input(county="PHILLIPS")
        assert inp.is_delta_region() is True

    def test_delta_county_case_insensitive(self):
        inp = make_input(county="phillips")
        assert inp.is_delta_region() is True

    def test_non_delta_county(self):
        inp = make_input(county="PULASKI")
        assert inp.is_delta_region() is False

    def test_none_county_fails_open(self):
        inp = make_input(county=None)
        assert inp.is_delta_region() is False

    def test_st_francis_variant(self):
        """Both 'ST. FRANCIS' and 'ST FRANCIS' should match."""
        assert make_input(county="ST. FRANCIS").is_delta_region() is True
        assert make_input(county="ST FRANCIS").is_delta_region() is True


# ============================================================================
# ScoringEngine Tests
# ============================================================================

class TestCapitalGate:

    def test_over_capital_limit_zeroes_buy_hold(self):
        """Effective cost > $10k -> buy_hold = 0."""
        engine = ScoringEngine()
        inp = make_input(state="AL", sale_type="tax_lien", amount=6000.0)
        # effective = 6000 + 4000 + 600 = 10600 > 10000
        result = engine.calculate_scores(inp)
        assert result.buy_hold_score == 0.0
        assert result.capital_viable is False

    def test_under_capital_limit_scores_positive(self):
        engine = ScoringEngine()
        inp = make_input(state="AR", amount=500.0, acreage=5.0)
        # effective = 500 + 1500 + 50 = 2050 < 10000
        result = engine.calculate_scores(inp)
        assert result.buy_hold_score > 0
        assert result.capital_viable is True

    def test_custom_capital_limit(self):
        engine = ScoringEngine(capital_limit=50000.0)
        inp = make_input(state="AL", sale_type="tax_lien", amount=6000.0)
        result = engine.calculate_scores(inp)
        assert result.capital_viable is True


class TestMarketRejectScoring:

    def test_market_reject_zeroes_both_scores(self):
        engine = ScoringEngine()
        inp = make_input(
            year_sold="2010",
            acreage=5.0,
            water_score=5.0,
            estimated_market_value=50000.0,
        )
        result = engine.calculate_scores(inp)
        assert result.buy_hold_score == 0.0
        assert result.wholesale_score == 0.0
        assert result.is_market_reject is True

    def test_non_reject_scores_normally(self):
        engine = ScoringEngine()
        inp = make_input(year_sold="2023", acreage=5.0, water_score=5.0)
        result = engine.calculate_scores(inp)
        assert result.buy_hold_score > 0
        assert result.is_market_reject is False


class TestDeltaRegionScoring:

    def test_delta_region_halves_scores(self):
        engine = ScoringEngine()
        # Same property, with and without delta region
        base = dict(state="AR", amount=500.0, acreage=5.0, water_score=5.0)
        normal = engine.calculate_scores(make_input(**base, county="PULASKI"))
        delta = engine.calculate_scores(make_input(**base, county="PHILLIPS"))

        assert delta.is_delta_region is True
        assert delta.delta_penalty_factor == DELTA_REGION_PENALTY
        assert delta.buy_hold_score == pytest.approx(
            normal.buy_hold_score * DELTA_REGION_PENALTY, abs=0.2
        )


class TestTimePenalty:

    def test_arkansas_no_penalty(self):
        """AR: 180 days -> ~0.95 penalty."""
        engine = ScoringEngine()
        factor = engine._calculate_time_penalty("AR")
        # 180/365 = 0.493 years, 0.5^(0.493/2) = 0.5^0.246 ~ 0.84
        assert factor > 0.8

    def test_alabama_heavy_penalty(self):
        """AL: 2000 days -> ~0.18 penalty."""
        engine = ScoringEngine()
        factor = engine._calculate_time_penalty("AL")
        assert factor < 0.25

    def test_florida_no_penalty(self):
        """FL: 0 days -> 1.0 (no penalty)."""
        engine = ScoringEngine()
        factor = engine._calculate_time_penalty("FL")
        assert factor == 1.0

    def test_texas_moderate_penalty(self):
        """TX: 180 days -> same as AR."""
        engine = ScoringEngine()
        factor = engine._calculate_time_penalty("TX")
        assert 0.8 < factor < 1.0


# ============================================================================
# Buy-Hold Score Component Tests
# ============================================================================

class TestBuyHoldAcreage:
    """
    Note: PPA varies with acreage (same cost / different acres), so
    we test acreage bands by comparing properties at the same PPA tier
    or by verifying relative ordering.
    """

    def test_sweet_spot_highest_acreage_points(self):
        """2-10 acres = 40 pts acreage (highest tier)."""
        engine = ScoringEngine()
        # FL, amount=100 -> effective=1610
        # 5 acres: PPA=322 (<500 = 25 pts), acreage=40 -> total=65
        sweet = engine.calculate_scores(
            make_input(state="FL", amount=100.0, acreage=5.0)
        ).buy_hold_score
        # 0.3 acres: PPA=5366 (>=5000 = 0 pts), acreage=15 -> total=15
        small_lot = engine.calculate_scores(
            make_input(state="FL", amount=100.0, acreage=0.3)
        ).buy_hold_score
        assert sweet > small_lot

    def test_large_vs_huge_ordering(self):
        """10-40 acres (35 pts) > 40+ acres (25 pts)."""
        engine = ScoringEngine()
        large = engine.calculate_scores(
            make_input(state="FL", amount=100.0, acreage=20.0)
        ).buy_hold_score
        huge = engine.calculate_scores(
            make_input(state="FL", amount=100.0, acreage=80.0)
        ).buy_hold_score
        # Same PPA tier for both (very low), so acreage points determine order
        assert large > huge

    def test_tiny_lot_lowest_score(self):
        """< 0.25 acres gets lowest acreage score."""
        engine = ScoringEngine()
        tiny = engine.calculate_scores(
            make_input(state="FL", amount=100.0, acreage=0.1)
        ).buy_hold_score
        small = engine.calculate_scores(
            make_input(state="FL", amount=100.0, acreage=0.5)
        ).buy_hold_score
        assert tiny < small


class TestBuyHoldWater:

    def test_water_score_scales(self):
        engine = ScoringEngine()
        no_water = engine.calculate_scores(
            make_input(state="FL", amount=100.0, acreage=5.0, water_score=0.0)
        )
        has_water = engine.calculate_scores(
            make_input(state="FL", amount=100.0, acreage=5.0, water_score=5.0)
        )
        # water_score * 3 = 15 additional points
        assert has_water.buy_hold_score == no_water.buy_hold_score + 15.0

    def test_water_capped_at_30(self):
        engine = ScoringEngine()
        max_water = engine.calculate_scores(
            make_input(state="FL", amount=100.0, acreage=5.0, water_score=10.0)
        )
        over_water = engine.calculate_scores(
            make_input(state="FL", amount=100.0, acreage=5.0, water_score=15.0)
        )
        # Both should have 30 pts water (capped)
        assert max_water.buy_hold_score == over_water.buy_hold_score


class TestBuyHoldPPA:

    def test_cheap_ppa_gets_max_points(self):
        """PPA < $300 = 30 pts."""
        engine = ScoringEngine()
        # FL: effective = 100 + 1500 + 10 = 1610, PPA = 1610/10 = 161
        result = engine.calculate_scores(
            make_input(state="FL", amount=100.0, acreage=10.0)
        )
        # acreage(40) + water(0) + ppa(30) = 70
        assert result.buy_hold_score == 70.0

    def test_expensive_ppa_gets_fewer_points(self):
        engine = ScoringEngine()
        # FL: effective = 5000 + 1500 + 500 = 7000, PPA = 7000/1 = 7000
        result = engine.calculate_scores(
            make_input(state="FL", amount=5000.0, acreage=1.0)
        )
        # acreage(28) + water(0) + ppa(0 for PPA >= 5000) = 28
        assert result.buy_hold_score < 40.0


# ============================================================================
# Wholesale Score Tests
# ============================================================================

class TestWholesaleScore:

    def test_tax_lien_returns_zero(self):
        engine = ScoringEngine()
        inp = make_input(
            state="AL",
            sale_type="tax_lien",
            estimated_market_value=50000.0,
        )
        result = engine.calculate_scores(inp)
        assert result.wholesale_score == 0.0

    def test_no_market_value_returns_zero(self):
        engine = ScoringEngine()
        inp = make_input(sale_type="tax_deed")
        result = engine.calculate_scores(inp)
        assert result.wholesale_score == 0.0

    def test_insufficient_spread_returns_zero(self):
        """High-value property (>=$7500) needs $3k min spread."""
        engine = ScoringEngine()
        # AR: effective = 5000 + 1500 + 500 = 7000
        # market=9000 (>= 7500), spread = 9000 - 7000 = 2000 < 3000
        inp = make_input(
            state="AR",
            amount=5000.0,
            acreage=5.0,
            estimated_market_value=9000.0,
        )
        result = engine.calculate_scores(inp)
        assert result.wholesale_score == 0.0

    def test_insufficient_margin_low_value(self):
        """Low-value property (<$7500) needs 40% margin."""
        engine = ScoringEngine()
        # AR: effective = 2000 + 1500 + 200 = 3700
        # market=5000 (< 7500), spread = 5000 - 3700 = 1300
        # margin = 1300/5000 = 0.26 < 0.40
        inp = make_input(
            state="AR",
            amount=2000.0,
            acreage=5.0,
            estimated_market_value=5000.0,
        )
        result = engine.calculate_scores(inp)
        assert result.wholesale_score == 0.0

    def test_good_spread_scores_positive(self):
        engine = ScoringEngine()
        inp = make_input(
            state="AR",
            amount=500.0,
            acreage=5.0,
            estimated_market_value=20000.0,
        )
        result = engine.calculate_scores(inp)
        # spread = 20000 - 2050 = 17950, margin = 17950/20000 = 0.8975
        assert result.wholesale_score > 0
        assert result.wholesale_spread == pytest.approx(20000.0 - 2050.0, abs=1.0)


class TestWholesaleViabilityGates:

    def test_high_value_3k_spread_gate(self):
        """For market >= $7500, need $3k minimum spread."""
        engine = ScoringEngine()
        # FL: effective = amount + 1500 + amount*0.10
        # Need spread < 3000: market - effective < 3000
        # market=8000, amount=5000 -> effective=5000+1500+500=7000
        # spread = 8000 - 7000 = 1000 < 3000 -> fail
        inp = make_input(
            state="FL",
            sale_type="hybrid",
            amount=5000.0,
            acreage=1.0,
            estimated_market_value=8000.0,
        )
        result = engine.calculate_scores(inp)
        assert result.wholesale_score == 0.0

    def test_redeemable_deed_can_wholesale(self):
        """TX redeemable_deed should be eligible for wholesale."""
        engine = ScoringEngine()
        inp = make_input(
            state="TX",
            sale_type="redeemable_deed",
            amount=500.0,
            acreage=5.0,
            estimated_market_value=20000.0,
        )
        result = engine.calculate_scores(inp)
        assert result.wholesale_score > 0


# ============================================================================
# Integration: Full Scoring Path
# ============================================================================

class TestFullScoringPath:

    def test_ar_tax_deed_happy_path(self):
        """AR cheap land with water = high scores."""
        engine = ScoringEngine()
        inp = make_input(
            state="AR",
            sale_type="tax_deed",
            amount=300.0,
            acreage=5.0,
            water_score=8.0,
            estimated_market_value=25000.0,
            year_sold="2023",
            county="PULASKI",
        )
        result = engine.calculate_scores(inp)
        assert result.buy_hold_score > 50
        assert result.wholesale_score > 0
        assert result.capital_viable is True
        assert result.is_market_reject is False
        assert result.is_delta_region is False
        assert isinstance(result.notes, list)

    def test_al_tax_lien_penalized(self):
        """AL has heavy time penalty + no wholesale for liens."""
        engine = ScoringEngine()
        inp = make_input(
            state="AL",
            sale_type="tax_lien",
            amount=500.0,
            acreage=5.0,
            water_score=5.0,
        )
        result = engine.calculate_scores(inp)
        # AL time penalty ~0.18 crushes buy_hold
        assert result.buy_hold_score < 20
        assert result.wholesale_score == 0.0
        assert result.time_penalty_factor < 0.25

    def test_score_result_to_dict(self):
        engine = ScoringEngine()
        inp = make_input(state="AR", amount=500.0, acreage=5.0)
        result = engine.calculate_scores(inp)
        d = result.to_dict()
        assert "buy_hold_score" in d
        assert "wholesale_score" in d
        assert "capital_viable" in d
        assert "is_market_reject" in d
        assert "is_delta_region" in d
        assert "notes" in d


# ============================================================================
# Convenience Functions
# ============================================================================

class TestConvenienceFunctions:

    def test_calculate_multistate_scores(self):
        result = calculate_multistate_scores(
            state="AR", sale_type="tax_deed", amount=500.0, acreage=5.0
        )
        assert isinstance(result, ScoreResult)
        assert result.buy_hold_score >= 0

    def test_calculate_buy_hold_score(self):
        score = calculate_buy_hold_score(
            state="AR", sale_type="tax_deed", amount=500.0, acreage=5.0
        )
        assert isinstance(score, float)
        assert score >= 0

    def test_calculate_wholesale_score(self):
        score = calculate_wholesale_score(
            state="AR",
            sale_type="tax_deed",
            amount=500.0,
            acreage=5.0,
            estimated_market_value=20000.0,
        )
        assert isinstance(score, float)
        assert score >= 0

    def test_custom_capital_limit(self):
        result = calculate_multistate_scores(
            state="AL",
            sale_type="tax_lien",
            amount=8000.0,
            acreage=5.0,
            capital_limit=50000.0,
        )
        assert result.capital_viable is True


class TestConstants:

    def test_default_capital_limit(self):
        assert DEFAULT_CAPITAL_LIMIT == 10000.0

    def test_wholesale_spread_minimum(self):
        assert MIN_WHOLESALE_SPREAD_DOLLARS == 3000.0

    def test_wholesale_margin_minimum(self):
        assert MIN_WHOLESALE_SPREAD_PCT == 0.40

    def test_stale_threshold(self):
        assert STALE_DELINQUENCY_THRESHOLD == 2015

    def test_delta_penalty(self):
        assert DELTA_REGION_PENALTY == 0.50

    def test_delta_counties_non_empty(self):
        assert len(DELTA_REGION_COUNTIES) > 0
        assert "PHILLIPS" in DELTA_REGION_COUNTIES
