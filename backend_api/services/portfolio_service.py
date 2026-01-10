"""
Portfolio Analytics Service.
Provides aggregate analysis of user's watched properties.
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case, desc

from core.scoring import DELTA_REGION_COUNTIES, STALE_DELINQUENCY_THRESHOLD
from config.states import STATE_CONFIGS, get_state_time_to_ownership

from ..database.models import Property, PropertyInteraction
from ..models.portfolio import (
    PortfolioSummaryResponse, GeographicBreakdownResponse, StateBreakdown,
    CountyBreakdown, ScoreDistributionResponse, ScoreBucket,
    RiskAnalysisResponse, ConcentrationRisk, PerformanceTrackingResponse,
    StarRatingBreakdown, RecentAddition, PortfolioAnalyticsExport
)

logger = logging.getLogger(__name__)


class PortfolioService:
    """
    Portfolio analytics service for watched properties.
    All queries are scoped to device_id for multi-tenancy.
    """

    def __init__(self, db: Session, device_id: str):
        self.db = db
        self.device_id = device_id

    def _get_watched_properties_query(self):
        """Base query for watched properties joined with Property data."""
        return self.db.query(Property, PropertyInteraction).join(
            PropertyInteraction,
            Property.id == PropertyInteraction.property_id
        ).filter(
            PropertyInteraction.device_id == self.device_id,
            PropertyInteraction.is_watched == True,
            PropertyInteraction.dismissed == False,
            Property.is_deleted == False
        )

    # ========================================================================
    # Portfolio Summary
    # ========================================================================

    def get_summary(self) -> PortfolioSummaryResponse:
        """Get portfolio summary with aggregate metrics."""
        try:
            # Main aggregates query
            aggregates = self.db.query(
                func.count(Property.id).label("total_count"),
                func.coalesce(func.sum(Property.amount), 0).label("total_value"),
                func.coalesce(func.sum(Property.acreage), 0).label("total_acreage"),
                func.coalesce(
                    func.sum(Property.effective_cost),
                    func.sum(Property.amount)
                ).label("total_effective_cost"),
                func.avg(Property.investment_score).label("avg_investment_score"),
                func.avg(Property.buy_hold_score).label("avg_buy_hold_score"),
                func.avg(Property.wholesale_score).label("avg_wholesale_score"),
                func.avg(Property.price_per_acre).label("avg_price_per_acre"),
                func.count(case((Property.water_score > 0, 1))).label("water_count")
            ).select_from(Property).join(
                PropertyInteraction,
                Property.id == PropertyInteraction.property_id
            ).filter(
                PropertyInteraction.device_id == self.device_id,
                PropertyInteraction.is_watched == True,
                PropertyInteraction.dismissed == False,
                Property.is_deleted == False
            ).first()

            total_count = aggregates.total_count or 0
            total_value = float(aggregates.total_value or 0)
            total_effective_cost = float(aggregates.total_effective_cost or total_value)
            water_count = aggregates.water_count or 0

            # Capital utilization - using default budget of $10k if not set
            # Could be enhanced to read from user preferences
            budget = 10000.0
            capital_utilization_pct = (total_effective_cost / budget) * 100 if budget > 0 else None
            capital_remaining = max(0, budget - total_effective_cost) if budget else None

            water_pct = (water_count / total_count * 100) if total_count > 0 else 0

            return PortfolioSummaryResponse(
                total_count=total_count,
                total_value=round(total_value, 2),
                total_acreage=round(float(aggregates.total_acreage or 0), 2),
                total_effective_cost=round(total_effective_cost, 2),
                avg_investment_score=round(float(aggregates.avg_investment_score or 0), 1),
                avg_buy_hold_score=round(float(aggregates.avg_buy_hold_score), 1) if aggregates.avg_buy_hold_score else None,
                avg_wholesale_score=round(float(aggregates.avg_wholesale_score), 1) if aggregates.avg_wholesale_score else None,
                avg_price_per_acre=round(float(aggregates.avg_price_per_acre or 0), 2),
                capital_budget=budget,
                capital_utilized=round(total_effective_cost, 2),
                capital_utilization_pct=round(capital_utilization_pct, 1) if capital_utilization_pct else None,
                capital_remaining=round(capital_remaining, 2) if capital_remaining is not None else None,
                properties_with_water=water_count,
                water_access_percentage=round(water_pct, 1),
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Failed to get portfolio summary: {str(e)}")
            raise

    # ========================================================================
    # Geographic Breakdown
    # ========================================================================

    def get_geographic_breakdown(self) -> GeographicBreakdownResponse:
        """Get state and county distribution."""
        try:
            # Get total count for percentage calculations
            total_query = self._get_watched_properties_query()
            total_count = total_query.count()

            if total_count == 0:
                return GeographicBreakdownResponse(
                    total_states=0,
                    total_counties=0,
                    states=[],
                    top_state=None,
                    top_county=None,
                    timestamp=datetime.utcnow()
                )

            # State-level aggregation
            state_query = self.db.query(
                Property.state,
                func.count(Property.id).label("count"),
                func.sum(Property.amount).label("total_value"),
                func.sum(Property.acreage).label("total_acreage"),
                func.avg(Property.investment_score).label("avg_investment_score"),
                func.avg(Property.buy_hold_score).label("avg_buy_hold_score")
            ).join(
                PropertyInteraction,
                Property.id == PropertyInteraction.property_id
            ).filter(
                PropertyInteraction.device_id == self.device_id,
                PropertyInteraction.is_watched == True,
                PropertyInteraction.dismissed == False,
                Property.is_deleted == False
            ).group_by(Property.state).order_by(desc("count")).all()

            states = []
            top_state = None
            top_county_info = None
            total_counties = 0

            for state_row in state_query:
                state_code = state_row.state or "AL"
                state_config = STATE_CONFIGS.get(state_code)
                state_name = state_config.state_name if state_config else state_code

                # County breakdown for this state
                county_query = self.db.query(
                    Property.county,
                    func.count(Property.id).label("count"),
                    func.sum(Property.amount).label("total_value"),
                    func.avg(Property.investment_score).label("avg_score")
                ).join(
                    PropertyInteraction,
                    Property.id == PropertyInteraction.property_id
                ).filter(
                    PropertyInteraction.device_id == self.device_id,
                    PropertyInteraction.is_watched == True,
                    PropertyInteraction.dismissed == False,
                    Property.is_deleted == False,
                    Property.state == state_code
                ).group_by(Property.county).order_by(desc("count")).all()

                counties = []
                for county_row in county_query:
                    county_pct = (county_row.count / total_count * 100) if total_count > 0 else 0
                    county_breakdown = CountyBreakdown(
                        county=county_row.county or "Unknown",
                        state=state_code,
                        count=county_row.count,
                        total_value=round(float(county_row.total_value or 0), 2),
                        avg_investment_score=round(float(county_row.avg_score or 0), 1),
                        percentage_of_portfolio=round(county_pct, 1)
                    )
                    counties.append(county_breakdown)
                    total_counties += 1

                    # Track top county
                    if top_county_info is None or county_row.count > top_county_info[1]:
                        top_county_info = (f"{county_row.county or 'Unknown'}, {state_code}", county_row.count)

                state_pct = (state_row.count / total_count * 100) if total_count > 0 else 0
                states.append(StateBreakdown(
                    state=state_code,
                    state_name=state_name,
                    count=state_row.count,
                    total_value=round(float(state_row.total_value or 0), 2),
                    total_acreage=round(float(state_row.total_acreage or 0), 2),
                    avg_investment_score=round(float(state_row.avg_investment_score or 0), 1),
                    avg_buy_hold_score=round(float(state_row.avg_buy_hold_score), 1) if state_row.avg_buy_hold_score else None,
                    percentage_of_portfolio=round(state_pct, 1),
                    counties=counties
                ))

            # Track top state
            if states:
                top_state = states[0].state

            return GeographicBreakdownResponse(
                total_states=len(states),
                total_counties=total_counties,
                states=states,
                top_state=top_state,
                top_county=top_county_info[0] if top_county_info else None,
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Failed to get geographic breakdown: {str(e)}")
            raise

    # ========================================================================
    # Score Distribution
    # ========================================================================

    def get_score_distribution(self) -> ScoreDistributionResponse:
        """Get investment quality breakdown."""
        try:
            # Get all watched properties with scores
            query = self._get_watched_properties_query()
            results = query.all()

            total_count = len(results)
            if total_count == 0:
                empty_buckets = [
                    ScoreBucket(
                        range_label=f"{i}-{i+19}",
                        min_score=i,
                        max_score=i+19,
                        count=0,
                        percentage=0,
                        property_ids=[]
                    )
                    for i in range(0, 100, 20)
                ]
                return ScoreDistributionResponse(
                    investment_score_buckets=empty_buckets,
                    buy_hold_score_buckets=empty_buckets,
                    top_performers_count=0,
                    top_performers=[],
                    underperformers_count=0,
                    underperformers=[],
                    median_investment_score=None,
                    score_std_deviation=None,
                    timestamp=datetime.utcnow()
                )

            # Build buckets
            bucket_labels = ["0-19", "20-39", "40-59", "60-79", "80-99"]
            inv_buckets = {label: [] for label in bucket_labels}
            bh_buckets = {label: [] for label in bucket_labels}
            top_performers = []
            underperformers = []
            all_inv_scores = []

            for prop, interaction in results:
                inv_score = prop.investment_score or 0
                bh_score = prop.buy_hold_score or 0
                all_inv_scores.append(inv_score)

                # Categorize by investment score
                if inv_score < 20:
                    inv_buckets["0-19"].append(prop.id)
                elif inv_score < 40:
                    inv_buckets["20-39"].append(prop.id)
                elif inv_score < 60:
                    inv_buckets["40-59"].append(prop.id)
                elif inv_score < 80:
                    inv_buckets["60-79"].append(prop.id)
                else:
                    inv_buckets["80-99"].append(prop.id)

                # Categorize by buy-hold score
                if bh_score < 20:
                    bh_buckets["0-19"].append(prop.id)
                elif bh_score < 40:
                    bh_buckets["20-39"].append(prop.id)
                elif bh_score < 60:
                    bh_buckets["40-59"].append(prop.id)
                elif bh_score < 80:
                    bh_buckets["60-79"].append(prop.id)
                else:
                    bh_buckets["80-99"].append(prop.id)

                # Top performers (score >= 80)
                if inv_score >= 80:
                    top_performers.append(prop.id)

                # Underperformers (score < 40)
                if inv_score < 40:
                    underperformers.append(prop.id)

            # Build response buckets
            bucket_ranges = [(0, 19), (20, 39), (40, 59), (60, 79), (80, 99)]
            inv_score_buckets = []
            bh_score_buckets = []

            for (min_s, max_s), label in zip(bucket_ranges, bucket_labels):
                inv_score_buckets.append(ScoreBucket(
                    range_label=label,
                    min_score=min_s,
                    max_score=max_s,
                    count=len(inv_buckets[label]),
                    percentage=round(len(inv_buckets[label]) / total_count * 100, 1),
                    property_ids=inv_buckets[label][:10]  # Limit to 10 IDs per bucket
                ))
                bh_score_buckets.append(ScoreBucket(
                    range_label=label,
                    min_score=min_s,
                    max_score=max_s,
                    count=len(bh_buckets[label]),
                    percentage=round(len(bh_buckets[label]) / total_count * 100, 1),
                    property_ids=bh_buckets[label][:10]
                ))

            median = statistics.median(all_inv_scores) if all_inv_scores else None
            std_dev = statistics.stdev(all_inv_scores) if len(all_inv_scores) > 1 else None

            return ScoreDistributionResponse(
                investment_score_buckets=inv_score_buckets,
                buy_hold_score_buckets=bh_score_buckets,
                top_performers_count=len(top_performers),
                top_performers=top_performers[:20],  # Limit to 20
                underperformers_count=len(underperformers),
                underperformers=underperformers[:20],
                median_investment_score=round(median, 1) if median else None,
                score_std_deviation=round(std_dev, 2) if std_dev else None,
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Failed to get score distribution: {str(e)}")
            raise

    # ========================================================================
    # Risk Analysis
    # ========================================================================

    def get_risk_analysis(self) -> RiskAnalysisResponse:
        """Get risk metrics for portfolio."""
        try:
            query = self._get_watched_properties_query()
            results = query.all()

            total_count = len(results)
            if total_count == 0:
                return RiskAnalysisResponse(
                    concentration=ConcentrationRisk(
                        highest_state_concentration=0,
                        highest_state=None,
                        highest_county_concentration=0,
                        highest_county=None,
                        diversification_score=100
                    ),
                    avg_time_to_ownership_days=None,
                    properties_over_1_year=0,
                    properties_over_3_years=0,
                    delta_region_count=0,
                    delta_region_percentage=0,
                    delta_region_counties=[],
                    market_reject_count=0,
                    market_reject_percentage=0,
                    largest_single_property_pct=0,
                    top_3_properties_pct=0,
                    overall_risk_level="low",
                    risk_flags=[],
                    timestamp=datetime.utcnow()
                )

            # Concentration analysis
            state_counts: Dict[str, int] = {}
            county_counts: Dict[str, int] = {}
            property_values: List[float] = []
            delta_counties: set = set()
            delta_count = 0
            market_reject_count = 0
            time_to_ownership_list: List[int] = []
            over_1_year = 0
            over_3_years = 0

            for prop, interaction in results:
                state = prop.state or "AL"
                county = prop.county or "Unknown"
                full_county = f"{county}, {state}"

                state_counts[state] = state_counts.get(state, 0) + 1
                county_counts[full_county] = county_counts.get(full_county, 0) + 1
                property_values.append(prop.amount or 0)

                # Delta region check
                if prop.is_delta_region:
                    delta_count += 1
                    delta_counties.add(county)
                elif county and county.upper() in DELTA_REGION_COUNTIES:
                    delta_count += 1
                    delta_counties.add(county)

                # Market reject check
                if prop.is_market_reject:
                    market_reject_count += 1
                elif prop.year_sold:
                    try:
                        year = int(prop.year_sold)
                        if year < STALE_DELINQUENCY_THRESHOLD:
                            market_reject_count += 1
                    except ValueError:
                        pass

                # Time to ownership
                tto = prop.time_to_ownership_days
                if not tto:
                    tto = get_state_time_to_ownership(state)
                if tto:
                    time_to_ownership_list.append(tto)
                    if tto > 365:
                        over_1_year += 1
                    if tto > 1095:  # 3 years
                        over_3_years += 1

            # Calculate concentration metrics
            highest_state_count = max(state_counts.values()) if state_counts else 0
            highest_state = max(state_counts, key=state_counts.get) if state_counts else None
            highest_state_pct = (highest_state_count / total_count * 100) if total_count > 0 else 0

            highest_county_count = max(county_counts.values()) if county_counts else 0
            highest_county = max(county_counts, key=county_counts.get) if county_counts else None
            highest_county_pct = (highest_county_count / total_count * 100) if total_count > 0 else 0

            # Diversification score (100 = perfectly diversified, 0 = all in one)
            # Based on inverse of HHI (Herfindahl-Hirschman Index)
            hhi = sum((count / total_count) ** 2 for count in county_counts.values())
            diversification = round((1 - hhi) * 100, 1)

            # Capital concentration
            total_value = sum(property_values)
            sorted_values = sorted(property_values, reverse=True)
            largest_pct = (sorted_values[0] / total_value * 100) if total_value > 0 else 0
            top_3_pct = (sum(sorted_values[:3]) / total_value * 100) if total_value > 0 else 0

            # Risk flags
            risk_flags = []
            if highest_state_pct > 80:
                risk_flags.append(f"High state concentration: {highest_state_pct:.0f}% in {highest_state}")
            if highest_county_pct > 50:
                risk_flags.append(f"High county concentration: {highest_county_pct:.0f}% in {highest_county}")
            if delta_count > 0:
                risk_flags.append(f"{delta_count} properties in Delta region (economic distress)")
            if market_reject_count > 0:
                risk_flags.append(f"{market_reject_count} market rejects (stale delinquency)")
            if over_3_years > total_count * 0.5:
                risk_flags.append("Over 50% of portfolio has 3+ year time to ownership")
            if largest_pct > 50:
                risk_flags.append(f"Single property represents {largest_pct:.0f}% of portfolio value")

            # Overall risk level
            risk_score = len(risk_flags)
            if risk_score == 0:
                overall_risk = "low"
            elif risk_score <= 2:
                overall_risk = "medium"
            elif risk_score <= 4:
                overall_risk = "high"
            else:
                overall_risk = "critical"

            avg_tto = statistics.mean(time_to_ownership_list) if time_to_ownership_list else None

            return RiskAnalysisResponse(
                concentration=ConcentrationRisk(
                    highest_state_concentration=round(highest_state_pct, 1),
                    highest_state=highest_state,
                    highest_county_concentration=round(highest_county_pct, 1),
                    highest_county=highest_county,
                    diversification_score=diversification
                ),
                avg_time_to_ownership_days=round(avg_tto, 0) if avg_tto else None,
                properties_over_1_year=over_1_year,
                properties_over_3_years=over_3_years,
                delta_region_count=delta_count,
                delta_region_percentage=round(delta_count / total_count * 100, 1) if total_count > 0 else 0,
                delta_region_counties=list(delta_counties),
                market_reject_count=market_reject_count,
                market_reject_percentage=round(market_reject_count / total_count * 100, 1) if total_count > 0 else 0,
                largest_single_property_pct=round(largest_pct, 1),
                top_3_properties_pct=round(top_3_pct, 1),
                overall_risk_level=overall_risk,
                risk_flags=risk_flags,
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Failed to get risk analysis: {str(e)}")
            raise

    # ========================================================================
    # Performance Tracking
    # ========================================================================

    def get_performance_tracking(self) -> PerformanceTrackingResponse:
        """Get performance and activity tracking."""
        try:
            now = datetime.utcnow()
            seven_days_ago = now - timedelta(days=7)
            thirty_days_ago = now - timedelta(days=30)

            query = self._get_watched_properties_query()
            results = query.all()

            # Recent additions (based on interaction created_at)
            additions_7d = 0
            additions_30d = 0
            recent_additions_data: List[Tuple] = []
            star_ratings: Dict[int, List[float]] = {1: [], 2: [], 3: [], 4: [], 5: []}
            rated_count = 0
            all_ratings: List[int] = []

            # First deal tracking
            first_deal = None

            for prop, interaction in results:
                # Check when added
                added_at = interaction.created_at
                if added_at:
                    if added_at >= seven_days_ago:
                        additions_7d += 1
                    if added_at >= thirty_days_ago:
                        additions_30d += 1
                        recent_additions_data.append((prop, interaction, added_at))

                # Star ratings
                if interaction.star_rating:
                    star_ratings[interaction.star_rating].append(prop.investment_score or 0)
                    rated_count += 1
                    all_ratings.append(interaction.star_rating)

                # First deal
                if interaction.is_first_deal:
                    first_deal = interaction

            # Sort recent additions by date
            recent_additions_data.sort(key=lambda x: x[2], reverse=True)
            recent_list = [
                RecentAddition(
                    property_id=prop.id,
                    parcel_id=prop.parcel_id,
                    county=prop.county,
                    state=prop.state or "AL",
                    amount=prop.amount or 0,
                    investment_score=prop.investment_score,
                    added_at=added_at
                )
                for prop, interaction, added_at in recent_additions_data[:10]
            ]

            # Star rating breakdown
            rating_breakdown = []
            for rating in range(1, 6):
                scores = star_ratings[rating]
                avg_score = statistics.mean(scores) if scores else 0
                rating_breakdown.append(StarRatingBreakdown(
                    rating=rating,
                    count=len(scores),
                    avg_investment_score=round(avg_score, 1)
                ))

            avg_star = statistics.mean(all_ratings) if all_ratings else None

            # Activity by week (last 8 weeks)
            activity_by_week: Dict[str, int] = {}
            for prop, interaction, added_at in recent_additions_data:
                week_start = added_at - timedelta(days=added_at.weekday())
                week_key = week_start.strftime("%Y-%m-%d")
                activity_by_week[week_key] = activity_by_week.get(week_key, 0) + 1

            return PerformanceTrackingResponse(
                additions_last_7_days=additions_7d,
                additions_last_30_days=additions_30d,
                recent_additions=recent_list,
                star_rating_breakdown=rating_breakdown,
                rated_count=rated_count,
                unrated_count=len(results) - rated_count,
                avg_star_rating=round(avg_star, 1) if avg_star else None,
                has_first_deal=first_deal is not None,
                first_deal_stage=first_deal.first_deal_stage if first_deal else None,
                first_deal_property_id=first_deal.property_id if first_deal else None,
                activity_by_week=activity_by_week,
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Failed to get performance tracking: {str(e)}")
            raise

    # ========================================================================
    # Full Export
    # ========================================================================

    def get_full_export(self) -> PortfolioAnalyticsExport:
        """Get complete portfolio analytics export."""
        return PortfolioAnalyticsExport(
            summary=self.get_summary(),
            geographic=self.get_geographic_breakdown(),
            scores=self.get_score_distribution(),
            risk=self.get_risk_analysis(),
            performance=self.get_performance_tracking(),
            exported_at=datetime.utcnow()
        )
