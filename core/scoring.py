"""
Multi-State Investment Scoring Engine

This module handles scoring properties across different legal jurisdictions
(Tax Deed vs Tax Lien states) specifically tailored for a limited-capital
investor ($10k budget).

Scoring Strategies:
1. Buy & Hold Score: Long-term value, adjusted for time-to-ownership friction.
2. Wholesale Score: Immediate liquidity and spread potential.

Key Design Decisions:
- Effective Cost Basis: Includes quiet title costs (AL = +$4k, AR = $0)
- Time Decay: Exponential decay penalizes long waits (AL 4yr = 75% penalty)
- Capital Gates: Properties exceeding budget get zero score
- Wholesale Viability: Tax liens score 0 (can't easily flip a debt certificate)
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

from config.states import (
    get_state_config,
    get_state_quiet_title_estimate,
    get_state_time_to_ownership,
    estimate_market_value_from_assessed,
    ASSESSMENT_RATIOS
)


# Investor Constraints (configurable)
DEFAULT_CAPITAL_LIMIT = 10000.0
MIN_WHOLESALE_SPREAD_DOLLARS = 3000.0
MIN_WHOLESALE_SPREAD_PCT = 0.40  # 40% margin required

# Market reject threshold: properties delinquent before this year are penalized
# Properties sitting unsold for 10+ years indicate fundamental problems
STALE_DELINQUENCY_THRESHOLD = 2015

# Delta region counties (economic distress, poor liquidity)
# These counties have persistent economic challenges, population decline,
# and limited market liquidity - making resale difficult
DELTA_REGION_COUNTIES = {
    # Arkansas Delta counties (Mississippi River Delta)
    'PHILLIPS', 'LEE', 'CHICOT', 'MISSISSIPPI', 'CRITTENDEN',
    'ST. FRANCIS', 'ST FRANCIS', 'MONROE', 'DESHA', 'ARKANSAS'
}

# Penalty factor for Delta region properties (50% score reduction)
DELTA_REGION_PENALTY = 0.50


@dataclass
class PropertyScoreInput:
    """Standardized input for scoring calculations."""
    state: str
    sale_type: str  # 'tax_lien', 'tax_deed', 'redeemable_deed', 'hybrid'
    amount: float  # Bid/purchase price
    acreage: float
    water_score: float = 0.0
    assessed_value: Optional[float] = None
    estimated_market_value: Optional[float] = None
    description_score: float = 0.0  # Pre-computed from utils.py
    year_sold: Optional[str] = None  # Delinquency year for market reject check
    county: Optional[str] = None  # County name for regional risk scoring

    def get_effective_cost(self) -> float:
        """
        Calculate real cost to own, including mandatory legal actions.
        For AL tax liens, this adds ~$4k quiet title cost.
        For AR tax deeds, this adds $0 (state provides warranty deed).
        """
        qt_cost = get_state_quiet_title_estimate(self.state)
        # Add 10% overhead for recording fees, deed prep, etc.
        overhead = self.amount * 0.10
        return self.amount + qt_cost + overhead

    def get_effective_price_per_acre(self) -> float:
        """PPA based on effective cost, not just bid amount."""
        if self.acreage <= 0:
            return float('inf')
        return self.get_effective_cost() / self.acreage

    def get_market_value_estimate(self) -> Optional[float]:
        """
        Get market value, using assessed value fallback if needed.
        """
        if self.estimated_market_value and self.estimated_market_value > 0:
            return self.estimated_market_value

        if self.assessed_value and self.assessed_value > 0:
            return estimate_market_value_from_assessed(
                self.assessed_value,
                self.state
            )

        return None

    def is_market_reject(self) -> bool:
        """
        Check if property is a "market reject" - delinquent for too long.
        Properties sitting unsold for 10+ years indicate fundamental problems
        (landlocked, flood zone, environmental issues, clouded title, etc.)
        
        Returns True if should be penalized, False otherwise.
        "Fail open" for NULL year_sold: don't penalize if data is missing.
        """
        if not self.year_sold:
            return False  # Fail open - don't penalize missing data
        
        try:
            year_int = int(self.year_sold)
            return year_int < STALE_DELINQUENCY_THRESHOLD
        except (ValueError, TypeError):
            return False  # Handle malformed data gracefully

    def is_delta_region(self) -> bool:
        """
        Check if property is in a Delta region county.
        Delta counties have economic distress and poor market liquidity.

        Returns True if in Delta region, False otherwise.
        "Fail open" for NULL county: don't penalize if data is missing.
        """
        if not self.county:
            return False  # Fail open - don't penalize missing data

        return self.county.upper() in DELTA_REGION_COUNTIES


@dataclass
class ScoreResult:
    """Complete scoring result for a property."""
    buy_hold_score: float
    wholesale_score: float
    effective_cost: float
    estimated_market_value: Optional[float]
    wholesale_spread: Optional[float]
    time_penalty_factor: float
    capital_viable: bool
    is_market_reject: bool = False  # Pre-2015 delinquency (stale inventory)
    is_delta_region: bool = False  # Delta region county (economic distress)
    delta_penalty_factor: float = 1.0  # Multiplier applied for Delta region
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'buy_hold_score': self.buy_hold_score,
            'wholesale_score': self.wholesale_score,
            'effective_cost': self.effective_cost,
            'estimated_market_value': self.estimated_market_value,
            'wholesale_spread': self.wholesale_spread,
            'time_penalty_factor': self.time_penalty_factor,
            'capital_viable': self.capital_viable,
            'is_market_reject': self.is_market_reject,
            'is_delta_region': self.is_delta_region,
            'delta_penalty_factor': self.delta_penalty_factor,
            'notes': self.notes
        }


class ScoringEngine:
    """
    Multi-state property scoring engine.

    Usage:
        engine = ScoringEngine(capital_limit=10000)
        input_data = PropertyScoreInput(
            state='AR',
            sale_type='tax_deed',
            amount=500,
            acreage=2.5,
            water_score=3.0
        )
        result = engine.calculate_scores(input_data)
    """

    def __init__(self, capital_limit: float = DEFAULT_CAPITAL_LIMIT):
        self.capital_limit = capital_limit

    def calculate_scores(self, data: PropertyScoreInput) -> ScoreResult:
        """
        Master scoring function returning both buy-hold and wholesale scores.
        """
        notes = []
        effective_cost = data.get_effective_cost()
        market_value = data.get_market_value_estimate()

        # Market reject check (stale delinquency)
        is_reject = data.is_market_reject()
        if is_reject:
            notes.append(f"MARKET REJECT: Delinquent since {data.year_sold} (pre-{STALE_DELINQUENCY_THRESHOLD})")

        # Delta region check (economic distress)
        is_delta = data.is_delta_region()
        delta_penalty = DELTA_REGION_PENALTY if is_delta else 1.0
        if is_delta:
            notes.append(f"DELTA REGION: {data.county} county (50% score penalty)")

        # Capital viability check
        capital_viable = effective_cost <= self.capital_limit
        if not capital_viable:
            notes.append(f"Exceeds capital limit (${effective_cost:,.0f} > ${self.capital_limit:,.0f})")

        # Calculate time penalty factor
        time_penalty = self._calculate_time_penalty(data.state)

        # Calculate wholesale spread
        spread = None
        if market_value:
            spread = market_value - effective_cost

        # Calculate both scores (zeroed if market reject, reduced if Delta region)
        if is_reject:
            buy_hold = 0.0
            wholesale = 0.0
        else:
            buy_hold = self._calculate_buy_hold_score(data, effective_cost, time_penalty, capital_viable)
            wholesale = self._calculate_wholesale_score(data, effective_cost, market_value, spread)
            # Apply Delta region penalty
            buy_hold *= delta_penalty
            wholesale *= delta_penalty

        # Add context notes
        state_config = get_state_config(data.state)
        if state_config:
            if state_config.sale_type == 'tax_lien':
                notes.append(f"{data.state}: Tax lien, {state_config.redemption_period_days} day redemption")
            elif state_config.sale_type == 'tax_deed':
                notes.append(f"{data.state}: Tax deed, immediate ownership")

        return ScoreResult(
            buy_hold_score=round(buy_hold, 1),
            wholesale_score=round(wholesale, 1),
            effective_cost=round(effective_cost, 2),
            estimated_market_value=round(market_value, 2) if market_value else None,
            wholesale_spread=round(spread, 2) if spread else None,
            time_penalty_factor=round(time_penalty, 3),
            capital_viable=capital_viable,
            is_market_reject=is_reject,
            is_delta_region=is_delta,
            delta_penalty_factor=delta_penalty,
            notes=notes
        )

    def _calculate_time_penalty(self, state: str) -> float:
        """
        Calculate time decay multiplier using exponential decay.

        Formula: 0.5 ^ (years / 2)

        Results:
        - AR (0 days): 1.0 (no penalty)
        - TX (180 days): ~0.87
        - FL (730 days): 0.5
        - AL (2000 days): ~0.18
        """
        days_wait = get_state_time_to_ownership(state)
        years_wait = days_wait / 365.0
        return 0.5 ** (years_wait / 2.0)

    def _calculate_buy_hold_score(
        self,
        data: PropertyScoreInput,
        effective_cost: float,
        time_penalty: float,
        capital_viable: bool
    ) -> float:
        """
        Calculate buy-and-hold investment score.

        Score components (before time penalty):
        - Acreage utility: 0-40 points (sweet spot 2-10 acres)
        - Water features: 0-30 points
        - Value score (effective PPA): 0-30 points

        After: Score * time_penalty_factor
        """
        # Capital gate - zero score if can't afford
        if not capital_viable:
            return 0.0

        base_score = 0.0

        # 1. Acreage Utility (0-40 pts)
        # Sweet spot is 2-10 acres for recreational/residential use
        if 2.0 <= data.acreage <= 10.0:
            base_score += 40
        elif 1.0 <= data.acreage < 2.0:
            base_score += 28
        elif 10.0 < data.acreage <= 40.0:
            base_score += 35  # Large but usable
        elif data.acreage > 40.0:
            base_score += 25  # May be harder to sell
        elif data.acreage > 0.25:
            base_score += 15  # Small lots
        elif data.acreage > 0:
            base_score += 5   # Tiny lots

        # 2. Water Features (0-30 pts)
        # water_score typically ranges 0-10 from keyword matching
        base_score += min(30, data.water_score * 3)

        # 3. Value Score - Effective Price Per Acre (0-30 pts)
        # Target is <$1000/acre effective cost
        ppa = data.get_effective_price_per_acre()
        if ppa < 300:
            base_score += 30
        elif ppa < 500:
            base_score += 25
        elif ppa < 1000:
            base_score += 20
        elif ppa < 2000:
            base_score += 12
        elif ppa < 5000:
            base_score += 5

        # Cap base score at 100
        base_score = min(100, base_score)

        # Apply time penalty (the "Alabama killer")
        final_score = base_score * time_penalty

        return final_score

    def _calculate_wholesale_score(
        self,
        data: PropertyScoreInput,
        effective_cost: float,
        market_value: Optional[float],
        spread: Optional[float]
    ) -> float:
        """
        Calculate wholesale (flip) viability score.

        Key requirements:
        - Must be tax_deed or redeemable_deed (can't easily flip liens)
        - Minimum $3k spread or 40% margin
        - Immediate or near-immediate ownership

        Score components:
        - Spread strength: 0-60 points
        - Margin strength: 0-40 points
        """
        # Tax liens are poor wholesale vehicles
        if data.sale_type == 'tax_lien':
            return 0.0

        # Need market value estimate
        if not market_value or market_value <= 0:
            return 0.0

        if not spread:
            return 0.0

        # Calculate margin percentage
        margin_pct = spread / market_value if market_value > 0 else 0

        # Viability gates
        # For low-value properties (<$7.5k market), require 40% margin
        # For higher value, require $3k minimum spread
        if market_value < 7500:
            if margin_pct < MIN_WHOLESALE_SPREAD_PCT:
                return 0.0
        else:
            if spread < MIN_WHOLESALE_SPREAD_DOLLARS:
                return 0.0

        score = 0.0

        # 1. Spread Strength (0-60 pts)
        # $10k spread = max points
        score += min(60, (spread / 10000.0) * 60)

        # 2. Margin Strength (0-40 pts)
        # Higher margin = easier to find buyer
        # Margin above 40% threshold earns points
        if margin_pct > MIN_WHOLESALE_SPREAD_PCT:
            margin_bonus = (margin_pct - MIN_WHOLESALE_SPREAD_PCT) * 100
            score += min(40, margin_bonus)

        return score


# Convenience functions for direct use

def calculate_multistate_scores(
    state: str,
    sale_type: str,
    amount: float,
    acreage: float,
    water_score: float = 0.0,
    assessed_value: Optional[float] = None,
    estimated_market_value: Optional[float] = None,
    capital_limit: float = DEFAULT_CAPITAL_LIMIT
) -> ScoreResult:
    """
    Convenience function to calculate both scores for a property.

    Args:
        state: Two-letter state code (AL, AR, TX, FL)
        sale_type: tax_lien, tax_deed, redeemable_deed, hybrid
        amount: Bid/purchase price
        acreage: Property acreage
        water_score: Pre-computed water feature score (0-10)
        assessed_value: County assessed value
        estimated_market_value: Market value if known
        capital_limit: Maximum investment budget

    Returns:
        ScoreResult with buy_hold_score, wholesale_score, and metadata
    """
    engine = ScoringEngine(capital_limit=capital_limit)
    input_data = PropertyScoreInput(
        state=state,
        sale_type=sale_type,
        amount=amount,
        acreage=acreage,
        water_score=water_score,
        assessed_value=assessed_value,
        estimated_market_value=estimated_market_value
    )
    return engine.calculate_scores(input_data)


def calculate_buy_hold_score(
    state: str,
    sale_type: str,
    amount: float,
    acreage: float,
    water_score: float = 0.0,
    capital_limit: float = DEFAULT_CAPITAL_LIMIT
) -> float:
    """
    Calculate just the buy-and-hold score.

    Returns:
        Score from 0-100 (time-adjusted)
    """
    result = calculate_multistate_scores(
        state=state,
        sale_type=sale_type,
        amount=amount,
        acreage=acreage,
        water_score=water_score,
        capital_limit=capital_limit
    )
    return result.buy_hold_score


def calculate_wholesale_score(
    state: str,
    sale_type: str,
    amount: float,
    acreage: float,
    estimated_market_value: float,
    capital_limit: float = DEFAULT_CAPITAL_LIMIT
) -> float:
    """
    Calculate just the wholesale viability score.

    Returns:
        Score from 0-100 (0 if not viable for wholesale)
    """
    result = calculate_multistate_scores(
        state=state,
        sale_type=sale_type,
        amount=amount,
        acreage=acreage,
        estimated_market_value=estimated_market_value,
        capital_limit=capital_limit
    )
    return result.wholesale_score
