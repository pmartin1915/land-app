"""
Multi-state configuration for tax deed/lien support.
Provides state-specific rules, costs, and platform information.

This module contains the same data as the state_configs database table,
but in Python for quick lookups without database queries.
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class StateConfig:
    """State-specific configuration for tax sales."""
    state_code: str
    state_name: str
    sale_type: str  # 'tax_lien', 'tax_deed', 'redeemable_deed', 'hybrid'
    redemption_period_days: int
    interest_rate: Optional[float]  # As decimal (0.12 = 12%)
    quiet_title_cost_estimate: float
    time_to_ownership_days: int
    auction_platform: str
    scraper_module: str
    is_active: bool
    recommended_for_beginners: bool
    notes: str


# State configurations - should match database seed data
STATE_CONFIGS: Dict[str, StateConfig] = {
    'AL': StateConfig(
        state_code='AL',
        state_name='Alabama',
        sale_type='tax_lien',
        redemption_period_days=1460,  # 4 years
        interest_rate=0.12,
        quiet_title_cost_estimate=4000.0,
        time_to_ownership_days=2000,  # ~5.5 years total
        auction_platform='GovEase',
        scraper_module='core.scrapers.alabama_dor',
        is_active=True,
        recommended_for_beginners=False,
        notes='Long hold period (4 years), expensive quiet title. Not recommended for <$25k investors.'
    ),
    'AR': StateConfig(
        state_code='AR',
        state_name='Arkansas',
        sale_type='tax_deed',
        redemption_period_days=30,  # 30-day post-sale redemption
        interest_rate=None,
        quiet_title_cost_estimate=1500.0,  # $1,000-2,000 for marketable title
        time_to_ownership_days=180,  # ~6 months for quiet title action
        auction_platform='COSL Website',
        scraper_module='core.scrapers.arkansas_cosl',
        is_active=True,
        recommended_for_beginners=True,
        notes='Limited warranty deed from COSL. Quiet title required for title insurance. 30-day redemption. Alternative: 15 years of tax payments = marketable title.'
    ),
    'TX': StateConfig(
        state_code='TX',
        state_name='Texas',
        sale_type='redeemable_deed',
        redemption_period_days=180,  # 6 months standard, 2 years for homestead
        interest_rate=0.25,  # 25% penalty
        quiet_title_cost_estimate=2000.0,
        time_to_ownership_days=180,
        auction_platform='County-specific',
        scraper_module='core.scrapers.texas_counties',
        is_active=False,  # Not yet implemented
        recommended_for_beginners=True,
        notes='Can take possession during 6-month redemption. 25% penalty if owner redeems.'
    ),
    'FL': StateConfig(
        state_code='FL',
        state_name='Florida',
        sale_type='hybrid',  # Lien first, then deed
        redemption_period_days=0,  # After tax deed auction
        interest_rate=0.18,  # On lien phase
        quiet_title_cost_estimate=1500.0,
        time_to_ownership_days=730,  # ~2 years through lien phase
        auction_platform='County + tax-sale.info',
        scraper_module='core.scrapers.florida_counties',
        is_active=False,  # Not yet implemented
        recommended_for_beginners=False,
        notes='Complex hybrid system (lien then deed). Requires understanding both phases.'
    )
}


def get_state_config(state_code: str) -> Optional[StateConfig]:
    """
    Get configuration for a specific state.

    Args:
        state_code: Two-letter state code (e.g., 'AL', 'AR')

    Returns:
        StateConfig if found, None otherwise
    """
    return STATE_CONFIGS.get(state_code.upper())


def get_active_states() -> Dict[str, StateConfig]:
    """
    Get all active state configurations.

    Returns:
        Dictionary of state_code -> StateConfig for active states
    """
    return {k: v for k, v in STATE_CONFIGS.items() if v.is_active}


def get_beginner_friendly_states() -> Dict[str, StateConfig]:
    """
    Get states recommended for beginner investors.

    Returns:
        Dictionary of state_code -> StateConfig for beginner-friendly states
    """
    return {k: v for k, v in STATE_CONFIGS.items() if v.recommended_for_beginners}


def get_tax_deed_states() -> Dict[str, StateConfig]:
    """
    Get states with tax deed sales (immediate or near-immediate ownership).

    Returns:
        Dictionary of state_code -> StateConfig for tax deed states
    """
    return {k: v for k, v in STATE_CONFIGS.items() if v.sale_type == 'tax_deed'}


def get_state_quiet_title_estimate(state_code: str) -> float:
    """
    Get estimated quiet title cost for a state.

    Args:
        state_code: Two-letter state code

    Returns:
        Estimated quiet title cost in USD, 0 if not found
    """
    config = get_state_config(state_code)
    return config.quiet_title_cost_estimate if config else 0.0


def get_state_time_to_ownership(state_code: str) -> int:
    """
    Get estimated time to marketable ownership for a state.

    Args:
        state_code: Two-letter state code

    Returns:
        Days to ownership, 0 if not found
    """
    config = get_state_config(state_code)
    return config.time_to_ownership_days if config else 0


# Assessment ratios by state (for market value estimation)
# Used when no external API is available
ASSESSMENT_RATIOS: Dict[str, float] = {
    'AL': 0.10,  # Alabama assesses at 10% of market value
    'AR': 0.20,  # Arkansas assesses at 20%
    'TX': 1.00,  # Texas assesses at 100%
    'FL': 0.85,  # Florida assesses at ~85%
}


def estimate_market_value_from_assessed(assessed_value: float, state_code: str) -> Optional[float]:
    """
    Estimate market value from assessed value using state assessment ratio.

    Args:
        assessed_value: County assessed value
        state_code: Two-letter state code

    Returns:
        Estimated market value, None if ratio unknown
    """
    ratio = ASSESSMENT_RATIOS.get(state_code.upper())
    if ratio and assessed_value > 0:
        return assessed_value / ratio
    return None
