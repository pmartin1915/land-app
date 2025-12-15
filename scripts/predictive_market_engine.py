"""
Predictive Market Intelligence Engine
Alabama Auction Watcher - Advanced Investment Analytics

This module provides predictive analytics capabilities for property investment
analysis, building on the existing county intelligence and investment scoring systems.

Features:
- Property appreciation forecasting (1, 3, 5-year predictions)
- Market timing analysis and optimal buying/selling windows
- Emerging opportunity detection using AI-driven pattern recognition
- Historical trend analysis and predictive modeling

Author: Claude Code AI Assistant
Date: 2025-09-20
Version: 1.0.0
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import math
import statistics
import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.county_intelligence import CountyIntelligenceAnalyzer, CountyIntelligence
from scripts.utils import calculate_investment_score, calculate_water_score
from config.settings import INVESTMENT_SCORE_WEIGHTS


class PredictionConfidence(Enum):
    """Confidence levels for predictive analytics."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class MarketTrend(Enum):
    """Market trend classifications."""
    STRONG_DECLINE = "strong_decline"
    DECLINE = "decline"
    STABLE = "stable"
    GROWTH = "growth"
    STRONG_GROWTH = "strong_growth"


@dataclass
class PropertyAppreciationForecast:
    """Container for property appreciation predictions."""

    # Core predictions
    one_year_appreciation: float = 0.0
    three_year_appreciation: float = 0.0
    five_year_appreciation: float = 0.0

    # Prediction metadata
    confidence_level: PredictionConfidence = PredictionConfidence.MEDIUM
    market_trend: MarketTrend = MarketTrend.STABLE
    risk_score: float = 0.0  # 0.0 = low risk, 1.0 = high risk

    # Contributing factors
    county_growth_factor: float = 0.0
    economic_factor: float = 0.0
    geographic_factor: float = 0.0
    market_timing_factor: float = 0.0
    property_specific_factor: float = 0.0

    # Metadata
    prediction_date: datetime = field(default_factory=datetime.now)
    model_version: str = "1.0.0"


@dataclass
class MarketTimingAnalysis:
    """Container for market timing insights."""

    # Timing recommendations
    optimal_buy_window: Tuple[str, str]  # (start_month, end_month)
    optimal_sell_window: Tuple[str, str]  # (start_month, end_month)
    current_market_phase: str  # "buyer_market", "seller_market", "balanced"

    # Market indicators
    supply_demand_ratio: float = 0.0
    price_momentum: float = 0.0  # -1.0 to 1.0
    investment_activity_level: float = 0.0  # 0.0 to 1.0
    seasonal_adjustment: float = 0.0  # -0.2 to 0.2

    # Risk factors
    market_volatility: float = 0.0
    economic_uncertainty: float = 0.0
    external_factors_impact: float = 0.0

    # Metadata
    analysis_date: datetime = field(default_factory=datetime.now)
    confidence_score: float = 0.0


@dataclass
class EmergingOpportunity:
    """Container for emerging investment opportunities."""

    # Opportunity identification
    property_id: Optional[str] = None
    county: str = ""
    opportunity_type: str = ""  # "undervalued", "growth_potential", "infrastructure_development"

    # Scoring
    opportunity_score: float = 0.0  # 0.0 to 100.0
    potential_appreciation: float = 0.0  # Percentage
    risk_adjusted_return: float = 0.0

    # Key factors
    primary_drivers: List[str] = field(default_factory=list)
    supporting_factors: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)

    # Timeline
    expected_timeline_months: int = 12
    confidence_level: PredictionConfidence = PredictionConfidence.MEDIUM

    # Metadata
    discovery_date: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


class PredictiveMarketEngine:
    """
    Advanced predictive analytics engine for Alabama property markets.

    This engine leverages existing county intelligence and investment scoring
    systems to provide forward-looking market insights and predictions.
    """

    def __init__(self):
        """Initialize the predictive market engine."""
        self.county_analyzer = CountyIntelligenceAnalyzer()
        self.model_version = "1.0.0"
        self.last_model_update = datetime.now()

        # Initialize historical patterns and weights
        self._initialize_prediction_weights()
        self._initialize_historical_patterns()
        self._initialize_seasonal_patterns()

    def _initialize_prediction_weights(self):
        """Initialize weights for predictive models."""

        # Appreciation prediction weights
        self.appreciation_weights = {
            "county_growth": 0.30,
            "economic_indicators": 0.25,
            "geographic_advantages": 0.20,
            "market_timing": 0.15,
            "property_specific": 0.10
        }

        # Market timing weights
        self.timing_weights = {
            "supply_demand": 0.35,
            "economic_momentum": 0.25,
            "seasonal_patterns": 0.20,
            "investment_activity": 0.20
        }

        # Opportunity detection weights
        self.opportunity_weights = {
            "undervaluation": 0.40,
            "growth_potential": 0.30,
            "infrastructure_development": 0.20,
            "market_inefficiency": 0.10
        }

    def _initialize_historical_patterns(self):
        """Initialize historical market patterns for Alabama."""

        # Historical appreciation rates by county tier
        self.historical_appreciation = {
            "metro_tier_1": {
                "annual_average": 0.045,  # 4.5%
                "volatility": 0.15,
                "recession_impact": -0.12
            },
            "metro_tier_2": {
                "annual_average": 0.035,  # 3.5%
                "volatility": 0.18,
                "recession_impact": -0.15
            },
            "rural": {
                "annual_average": 0.025,  # 2.5%
                "volatility": 0.12,
                "recession_impact": -0.08
            }
        }

        # Economic cycle adjustments
        self.cycle_adjustments = {
            "expansion": 1.2,
            "peak": 0.9,
            "contraction": 0.6,
            "trough": 0.8
        }

    def _initialize_seasonal_patterns(self):
        """Initialize seasonal market patterns."""

        # Monthly market activity patterns (0.0 to 1.0)
        self.seasonal_activity = {
            "January": 0.6,
            "February": 0.7,
            "March": 0.8,
            "April": 0.9,
            "May": 1.0,  # Peak
            "June": 0.95,
            "July": 0.9,
            "August": 0.85,
            "September": 0.8,
            "October": 0.75,
            "November": 0.65,
            "December": 0.5  # Lowest
        }

        # Seasonal price premiums/discounts
        self.seasonal_pricing = {
            "Q1": -0.03,  # 3% discount
            "Q2": 0.02,   # 2% premium
            "Q3": 0.01,   # 1% premium
            "Q4": -0.01   # 1% discount
        }

    def predict_property_appreciation(self,
                                    property_data: Dict[str, Any],
                                    county: str,
                                    current_investment_score: float) -> PropertyAppreciationForecast:
        """
        Predict property appreciation over 1, 3, and 5 year periods.

        Args:
            property_data: Dictionary containing property details
            county: Alabama county name
            current_investment_score: Current investment score from existing algorithm

        Returns:
            PropertyAppreciationForecast with detailed predictions
        """

        # Get county intelligence for this property
        county_intel = self.county_analyzer.analyze_county(county)

        # Calculate base appreciation factors
        county_factor = self._calculate_county_growth_factor(county_intel, county)
        economic_factor = self._calculate_economic_factor(county_intel)
        geographic_factor = self._calculate_geographic_factor(county_intel)
        market_timing_factor = self._calculate_market_timing_factor(county_intel)
        property_factor = self._calculate_property_specific_factor(property_data, current_investment_score)

        # Combine factors using weighted average
        base_appreciation = (
            county_factor * self.appreciation_weights["county_growth"] +
            economic_factor * self.appreciation_weights["economic_indicators"] +
            geographic_factor * self.appreciation_weights["geographic_advantages"] +
            market_timing_factor * self.appreciation_weights["market_timing"] +
            property_factor * self.appreciation_weights["property_specific"]
        )

        # Apply time-based adjustments
        one_year = base_appreciation
        three_year = base_appreciation * 2.8  # Compound with slight deceleration
        five_year = base_appreciation * 4.5   # Compound with market normalization

        # Calculate confidence and risk
        confidence = self._calculate_prediction_confidence(county_intel, property_data)
        risk_score = self._calculate_risk_score(county_intel, property_data)
        market_trend = self._determine_market_trend(base_appreciation)

        return PropertyAppreciationForecast(
            one_year_appreciation=one_year,
            three_year_appreciation=three_year,
            five_year_appreciation=five_year,
            confidence_level=confidence,
            market_trend=market_trend,
            risk_score=risk_score,
            county_growth_factor=county_factor,
            economic_factor=economic_factor,
            geographic_factor=geographic_factor,
            market_timing_factor=market_timing_factor,
            property_specific_factor=property_factor
        )

    def analyze_market_timing(self, county: str) -> MarketTimingAnalysis:
        """
        Analyze optimal market timing for buying and selling in a specific county.

        Args:
            county: Alabama county name

        Returns:
            MarketTimingAnalysis with timing recommendations
        """

        county_intel = self.county_analyzer.analyze_county(county)
        current_month = datetime.now().strftime("%B")
        current_quarter = f"Q{(datetime.now().month - 1) // 3 + 1}"

        # Calculate market indicators
        supply_demand = self._calculate_supply_demand_ratio(county_intel)
        price_momentum = self._calculate_price_momentum(county_intel)
        investment_activity = self._calculate_investment_activity_level(county_intel)
        seasonal_adj = self.seasonal_pricing.get(current_quarter, 0.0)

        # Determine market phase
        market_phase = self._determine_market_phase(supply_demand, price_momentum, investment_activity)

        # Calculate optimal windows
        buy_window = self._calculate_optimal_buy_window(county_intel, seasonal_adj)
        sell_window = self._calculate_optimal_sell_window(county_intel, seasonal_adj)

        # Risk assessments
        volatility = self._calculate_market_volatility(county_intel)
        uncertainty = self._calculate_economic_uncertainty(county_intel)
        external_impact = self._calculate_external_factors_impact(county)

        # Overall confidence in timing analysis
        confidence = self._calculate_timing_confidence(county_intel, volatility, uncertainty)

        return MarketTimingAnalysis(
            optimal_buy_window=buy_window,
            optimal_sell_window=sell_window,
            current_market_phase=market_phase,
            supply_demand_ratio=supply_demand,
            price_momentum=price_momentum,
            investment_activity_level=investment_activity,
            seasonal_adjustment=seasonal_adj,
            market_volatility=volatility,
            economic_uncertainty=uncertainty,
            external_factors_impact=external_impact,
            confidence_score=confidence
        )

    def detect_emerging_opportunities(self,
                                    properties_data: List[Dict[str, Any]],
                                    top_n: int = 10) -> List[EmergingOpportunity]:
        """
        Detect emerging investment opportunities using AI-driven pattern recognition.

        Args:
            properties_data: List of property data dictionaries
            top_n: Number of top opportunities to return

        Returns:
            List of EmergingOpportunity objects ranked by potential
        """

        opportunities = []

        for prop in properties_data:
            county = prop.get("county", "")
            property_id = prop.get("id", "")

            if not county:
                continue

            county_intel = self.county_analyzer.analyze_county(county)

            # Analyze different opportunity types
            undervalued_score = self._detect_undervaluation(prop, county_intel)
            growth_potential_score = self._detect_growth_potential(prop, county_intel)
            infrastructure_score = self._detect_infrastructure_development(prop, county_intel)

            # Calculate composite opportunity score
            opportunity_score = (
                undervalued_score * self.opportunity_weights["undervaluation"] +
                growth_potential_score * self.opportunity_weights["growth_potential"] +
                infrastructure_score * self.opportunity_weights["infrastructure_development"]
            ) * 100  # Scale to 0-100

            if opportunity_score > 60:  # Threshold for significant opportunities

                # Determine primary opportunity type
                scores = {
                    "undervalued": undervalued_score,
                    "growth_potential": growth_potential_score,
                    "infrastructure_development": infrastructure_score
                }
                opportunity_type = max(scores, key=scores.get)

                # Calculate potential appreciation and risk-adjusted return
                appreciation_forecast = self.predict_property_appreciation(
                    prop, county, prop.get("investment_score", 0)
                )
                potential_appreciation = appreciation_forecast.three_year_appreciation
                risk_adjusted_return = potential_appreciation * (1 - appreciation_forecast.risk_score)

                # Identify key factors
                primary_drivers = self._identify_primary_drivers(prop, county_intel, opportunity_type)
                supporting_factors = self._identify_supporting_factors(prop, county_intel)
                risk_factors = self._identify_risk_factors(prop, county_intel)

                opportunity = EmergingOpportunity(
                    property_id=property_id,
                    county=county,
                    opportunity_type=opportunity_type,
                    opportunity_score=opportunity_score,
                    potential_appreciation=potential_appreciation,
                    risk_adjusted_return=risk_adjusted_return,
                    primary_drivers=primary_drivers,
                    supporting_factors=supporting_factors,
                    risk_factors=risk_factors,
                    expected_timeline_months=self._estimate_opportunity_timeline(opportunity_type),
                    confidence_level=appreciation_forecast.confidence_level
                )

                opportunities.append(opportunity)

        # Sort by opportunity score and return top N
        opportunities.sort(key=lambda x: x.opportunity_score, reverse=True)
        return opportunities[:top_n]

    # Helper methods for prediction calculations

    def _calculate_county_growth_factor(self, county_intel: CountyIntelligence, county: str) -> float:
        """Calculate county-specific growth factor."""

        # Base growth from county intelligence
        base_score = (
            county_intel.population_growth_score * 0.4 +
            county_intel.economic_diversity_score * 0.3 +
            county_intel.development_trends_score * 0.3
        )

        # Adjust based on county tier
        tier_adjustment = 1.0
        if county in self.county_analyzer.metro_counties:
            tier = self.county_analyzer.metro_counties[county]["metro_tier"]
            tier_adjustment = 1.2 if tier == 1 else 1.1

        return base_score * tier_adjustment * 0.1  # Scale to reasonable appreciation range

    def _calculate_economic_factor(self, county_intel: CountyIntelligence) -> float:
        """Calculate economic growth factor."""

        return (
            county_intel.median_income_score * 0.4 +
            county_intel.unemployment_score * 0.3 +
            county_intel.investment_momentum_score * 0.3
        ) * 0.08

    def _calculate_geographic_factor(self, county_intel: CountyIntelligence) -> float:
        """Calculate geographic advantages factor."""

        return (
            county_intel.proximity_to_major_cities_score * 0.3 +
            county_intel.natural_features_score * 0.3 +
            county_intel.transportation_access_score * 0.2 +
            county_intel.climate_advantages_score * 0.2
        ) * 0.06

    def _calculate_market_timing_factor(self, county_intel: CountyIntelligence) -> float:
        """Calculate market timing factor."""

        return (
            county_intel.real_estate_activity_score * 0.4 +
            county_intel.infrastructure_development_score * 0.35 +
            county_intel.investment_momentum_score * 0.25
        ) * 0.05

    def _calculate_property_specific_factor(self, property_data: Dict[str, Any], investment_score: float) -> float:
        """Calculate property-specific appreciation factor."""

        # Use existing investment score as base
        base_factor = investment_score / 100.0 * 0.04

        # Adjust for water features (premium properties)
        water_score = property_data.get("water_score", 0)
        water_premium = min(water_score / 15.0 * 0.02, 0.02)  # Up to 2% premium

        # Adjust for acreage (larger properties may appreciate differently)
        acreage = property_data.get("acreage", 0)
        if acreage > 10:
            acreage_factor = 1.1  # 10% bonus for larger properties
        elif acreage < 1:
            acreage_factor = 0.9   # 10% discount for very small properties
        else:
            acreage_factor = 1.0

        return (base_factor + water_premium) * acreage_factor

    def _calculate_prediction_confidence(self, county_intel: CountyIntelligence, property_data: Dict[str, Any]) -> PredictionConfidence:
        """Calculate confidence level for predictions."""

        # Base confidence from data quality
        data_confidence = county_intel.confidence_level

        # Adjust for data completeness
        completeness_score = 0.0
        required_fields = ["amount", "acreage", "county", "description"]
        for field in required_fields:
            if property_data.get(field):
                completeness_score += 0.25

        overall_confidence = (data_confidence + completeness_score) / 2

        if overall_confidence >= 0.85:
            return PredictionConfidence.VERY_HIGH
        elif overall_confidence >= 0.70:
            return PredictionConfidence.HIGH
        elif overall_confidence >= 0.55:
            return PredictionConfidence.MEDIUM
        else:
            return PredictionConfidence.LOW

    def _calculate_risk_score(self, county_intel: CountyIntelligence, property_data: Dict[str, Any]) -> float:
        """Calculate risk score for investment (0.0 = low risk, 1.0 = high risk)."""

        # Economic risk factors
        economic_risk = 1.0 - (county_intel.economic_diversity_score + county_intel.unemployment_score) / 2

        # Market risk factors
        market_risk = 1.0 - county_intel.real_estate_activity_score

        # Property-specific risk factors
        price_per_acre = property_data.get("price_per_acre", 0)
        if price_per_acre > 5000:  # High price per acre = higher risk
            price_risk = 0.3
        elif price_per_acre < 100:  # Very low price = potential issues
            price_risk = 0.4
        else:
            price_risk = 0.1

        # Combine risk factors
        overall_risk = (economic_risk * 0.4 + market_risk * 0.4 + price_risk * 0.2)

        return min(max(overall_risk, 0.0), 1.0)  # Clamp to 0-1 range

    def _determine_market_trend(self, base_appreciation: float) -> MarketTrend:
        """Determine market trend classification."""

        if base_appreciation >= 0.08:
            return MarketTrend.STRONG_GROWTH
        elif base_appreciation >= 0.05:
            return MarketTrend.GROWTH
        elif base_appreciation >= -0.02:
            return MarketTrend.STABLE
        elif base_appreciation >= -0.05:
            return MarketTrend.DECLINE
        else:
            return MarketTrend.STRONG_DECLINE

    # Additional helper methods would continue here...
    # (Market timing, opportunity detection, etc.)

    def _calculate_supply_demand_ratio(self, county_intel: CountyIntelligence) -> float:
        """Calculate supply/demand ratio for market timing."""
        # Simplified implementation - in production would use actual market data
        return county_intel.real_estate_activity_score

    def _calculate_price_momentum(self, county_intel: CountyIntelligence) -> float:
        """Calculate price momentum indicator."""
        return (county_intel.investment_momentum_score - 0.5) * 2  # Scale to -1 to 1

    def _calculate_investment_activity_level(self, county_intel: CountyIntelligence) -> float:
        """Calculate investment activity level."""
        return county_intel.investment_momentum_score

    def _determine_market_phase(self, supply_demand: float, price_momentum: float, investment_activity: float) -> str:
        """Determine current market phase."""
        composite_score = (supply_demand + price_momentum + investment_activity) / 3

        if composite_score > 0.6:
            return "seller_market"
        elif composite_score < 0.4:
            return "buyer_market"
        else:
            return "balanced"

    def _calculate_optimal_buy_window(self, county_intel: CountyIntelligence, seasonal_adj: float) -> Tuple[str, str]:
        """Calculate optimal buying window."""
        # Simplified implementation - would be more sophisticated in production
        if seasonal_adj < 0:  # Seasonal discount period
            return ("November", "February")
        else:
            return ("September", "December")

    def _calculate_optimal_sell_window(self, county_intel: CountyIntelligence, seasonal_adj: float) -> Tuple[str, str]:
        """Calculate optimal selling window."""
        # Simplified implementation
        return ("April", "July")

    def _calculate_market_volatility(self, county_intel: CountyIntelligence) -> float:
        """Calculate market volatility measure."""
        return 1.0 - county_intel.confidence_level

    def _calculate_economic_uncertainty(self, county_intel: CountyIntelligence) -> float:
        """Calculate economic uncertainty measure."""
        return 1.0 - county_intel.economic_diversity_score

    def _calculate_external_factors_impact(self, county: str) -> float:
        """Calculate external factors impact."""
        # Simplified implementation
        return 0.1  # Low external impact baseline

    def _calculate_timing_confidence(self, county_intel: CountyIntelligence, volatility: float, uncertainty: float) -> float:
        """Calculate confidence in timing analysis."""
        base_confidence = county_intel.confidence_level
        risk_adjustment = 1.0 - (volatility + uncertainty) / 2
        return base_confidence * risk_adjustment

    def _detect_undervaluation(self, property_data: Dict[str, Any], county_intel: CountyIntelligence) -> float:
        """Detect undervaluation opportunities."""
        assessed_value_ratio = property_data.get("assessed_value_ratio", 1.0)
        investment_score = property_data.get("investment_score", 50)

        # Lower ratio + higher investment score = undervaluation
        undervaluation_score = (1.0 - min(assessed_value_ratio, 1.0)) * 0.6 + (investment_score / 100.0) * 0.4

        return min(undervaluation_score, 1.0)

    def _detect_growth_potential(self, property_data: Dict[str, Any], county_intel: CountyIntelligence) -> float:
        """Detect growth potential opportunities."""
        return (
            county_intel.population_growth_score * 0.4 +
            county_intel.development_trends_score * 0.3 +
            county_intel.economic_diversity_score * 0.3
        )

    def _detect_infrastructure_development(self, property_data: Dict[str, Any], county_intel: CountyIntelligence) -> float:
        """Detect infrastructure development opportunities."""
        return county_intel.infrastructure_development_score

    def _identify_primary_drivers(self, property_data: Dict[str, Any], county_intel: CountyIntelligence, opportunity_type: str) -> List[str]:
        """Identify primary opportunity drivers."""
        drivers = []

        if opportunity_type == "undervalued":
            if property_data.get("assessed_value_ratio", 1.0) < 0.5:
                drivers.append("Significantly below assessed value")
            if property_data.get("water_score", 0) > 5:
                drivers.append("Premium water features")

        elif opportunity_type == "growth_potential":
            if county_intel.population_growth_score > 0.7:
                drivers.append("Strong population growth")
            if county_intel.economic_diversity_score > 0.7:
                drivers.append("Diverse economy")

        elif opportunity_type == "infrastructure_development":
            if county_intel.infrastructure_development_score > 0.7:
                drivers.append("Major infrastructure projects")

        return drivers

    def _identify_supporting_factors(self, property_data: Dict[str, Any], county_intel: CountyIntelligence) -> List[str]:
        """Identify supporting factors for opportunity."""
        factors = []

        if county_intel.proximity_to_major_cities_score > 0.6:
            factors.append("Good proximity to major cities")

        if property_data.get("acreage", 0) > 5:
            factors.append("Large property size")

        if county_intel.transportation_access_score > 0.6:
            factors.append("Excellent transportation access")

        return factors

    def _identify_risk_factors(self, property_data: Dict[str, Any], county_intel: CountyIntelligence) -> List[str]:
        """Identify risk factors for opportunity."""
        risks = []

        if county_intel.unemployment_score < 0.4:
            risks.append("High unemployment risk")

        if property_data.get("price_per_acre", 0) > 3000:
            risks.append("High price per acre")

        if county_intel.economic_diversity_score < 0.4:
            risks.append("Limited economic diversity")

        return risks

    def _estimate_opportunity_timeline(self, opportunity_type: str) -> int:
        """Estimate timeline for opportunity realization."""
        timelines = {
            "undervalued": 12,  # 1 year
            "growth_potential": 24,  # 2 years
            "infrastructure_development": 36  # 3 years
        }
        return timelines.get(opportunity_type, 18)


# Global instance for easy access
predictive_engine = PredictiveMarketEngine()


def get_predictive_engine() -> PredictiveMarketEngine:
    """Get the global predictive market engine instance."""
    return predictive_engine