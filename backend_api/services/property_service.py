"""
Property service layer using exact Python algorithms from scripts/utils.py
CRITICAL: Maintains mathematical precision with iOS Swift implementation
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc

from ..utils import utc_now

# Import exact Python algorithms (CRITICAL for compatibility)
from scripts.utils import (
    calculate_investment_score,
    calculate_water_score,
    calculate_estimated_all_in_cost
)
from scripts.enhanced_description_analysis import EnhancedDescriptionAnalyzer
from scripts.county_intelligence import CountyIntelligenceAnalyzer
from config.settings import INVESTMENT_SCORE_WEIGHTS

# Import caching system
from config.caching import cache_result, get_cache_invalidator

from ..database.models import Property
from ..models.property import (
    PropertyCreate, PropertyUpdate, PropertyFilters, PropertyCalculationRequest,
    PropertyCalculationResponse, PropertyMetrics
)

logger = logging.getLogger(__name__)

class PropertyService:
    """
    Property service using exact Python algorithms.
    Ensures mathematical consistency with iOS Swift implementation.
    """

    def __init__(self, db: Session):
        self.db = db

    def calculate_property_metrics(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate all property metrics using exact Python algorithms.
        CRITICAL: This function MUST produce identical results to iOS calculations.
        Enhanced in Phase 1 with advanced description intelligence.
        """
        try:
            # Water score calculation (original algorithm)
            description = property_data.get('description', '') or ''
            water_score = calculate_water_score(description)

            # Enhanced Description Intelligence Analysis (Phase 1)
            logger.debug(f"Starting enhanced analysis for description (length={len(description)})")
            analyzer = EnhancedDescriptionAnalyzer()
            intelligence = analyzer.analyze_description(description)
            logger.debug(f"Enhanced analysis complete. Total score: {intelligence.total_description_score}")

            # County Intelligence Analysis (Phase 1)
            county_name = property_data.get('county', '')
            county_intelligence_scores = {'county_market_score': 0.0, 'geographic_score': 0.0, 'market_timing_score': 0.0}

            if county_name:
                logger.debug(f"Starting county intelligence analysis for: {county_name}")
                county_analyzer = CountyIntelligenceAnalyzer()
                county_intelligence = county_analyzer.analyze_county(county_name)
                county_intelligence_scores = {
                    'county_market_score': county_intelligence.county_market_score,
                    'geographic_score': county_intelligence.geographic_score,
                    'market_timing_score': county_intelligence.market_timing_score
                }
                logger.debug(f"County analysis complete. Market score: {county_intelligence_scores['county_market_score']:.2f}")
            else:
                logger.warning("No county specified for property - using default county intelligence scores")

            # Price per acre calculation
            price_per_acre = 0.0
            acreage = property_data.get('acreage', 0) or 0
            amount = property_data.get('amount', 0) or 0

            if acreage and acreage > 0:
                price_per_acre = amount / acreage

            # Assessed value ratio calculation
            assessed_value_ratio = 0.0
            assessed_value = property_data.get('assessed_value', 0) or 0

            if assessed_value and assessed_value > 0:
                assessed_value_ratio = amount / assessed_value

            # Investment score calculation using exact Python weights
            # TODO: This will be enhanced in next phase to include new factors
            investment_score = calculate_investment_score(
                price_per_acre=price_per_acre,
                acreage=acreage,
                water_score=water_score,
                assessed_value_ratio=assessed_value_ratio,
                weights=INVESTMENT_SCORE_WEIGHTS
            )

            # All-in cost calculation
            estimated_all_in_cost = calculate_estimated_all_in_cost(amount)

            # Return enhanced metrics including all new intelligence fields
            result = {
                # Original metrics
                'water_score': water_score,
                'price_per_acre': price_per_acre,
                'assessed_value_ratio': assessed_value_ratio,
                'investment_score': investment_score,
                'estimated_all_in_cost': estimated_all_in_cost,

                # Enhanced Description Intelligence (Phase 1)
                'lot_dimensions_score': intelligence.lot_dimensions_score,
                'shape_efficiency_score': intelligence.shape_efficiency_score,
                'corner_lot_bonus': intelligence.corner_lot_bonus,
                'irregular_shape_penalty': intelligence.irregular_shape_penalty,
                'subdivision_quality_score': intelligence.subdivision_quality_score,
                'road_access_score': intelligence.road_access_score,
                'location_type_score': intelligence.location_type_score,
                'title_complexity_score': intelligence.title_complexity_score,
                'survey_requirement_score': intelligence.survey_requirement_score,
                'premium_water_access_score': intelligence.premium_water_access_score,
                'total_description_score': intelligence.total_description_score,

                # County Intelligence (Phase 1 Enhancement)
                'county_market_score': county_intelligence_scores['county_market_score'],
                'geographic_score': county_intelligence_scores['geographic_score'],
                'market_timing_score': county_intelligence_scores['market_timing_score']
            }

            logger.debug(f"Enhanced metrics calculated. Investment score: {result.get('investment_score', 0):.2f}")
            return result

        except Exception as e:
            logger.error(f"Algorithm calculation failed: {str(e)}")
            raise

    def create_property(
        self,
        property_data: PropertyCreate,
        device_id: Optional[str] = None,
        auto_commit: bool = True
    ) -> Property:
        """
        Create a new property with calculated metrics.

        Args:
            property_data: Property creation data
            device_id: Optional device identifier for sync tracking
            auto_commit: If True (default), commits the transaction.
                        Set to False when caller manages transaction (e.g., sync orchestrator).
        """
        property_obj = None
        try:
            # Convert Pydantic model to dict
            data_dict = property_data.dict()

            # Calculate metrics using exact Python algorithms
            calculated_metrics = self.calculate_property_metrics(data_dict)

            # Create new property instance
            property_obj = Property(
                parcel_id=data_dict['parcel_id'],
                amount=data_dict['amount'],
                acreage=data_dict.get('acreage'),
                description=data_dict.get('description'),
                county=data_dict.get('county'),
                owner_name=data_dict.get('owner_name'),
                year_sold=data_dict.get('year_sold'),
                assessed_value=data_dict.get('assessed_value'),
                device_id=device_id,

                # Calculated fields (original)
                price_per_acre=calculated_metrics['price_per_acre'],
                water_score=calculated_metrics['water_score'],
                investment_score=calculated_metrics['investment_score'],
                estimated_all_in_cost=calculated_metrics['estimated_all_in_cost'],
                assessed_value_ratio=calculated_metrics['assessed_value_ratio'],

                # Enhanced Description Intelligence Fields (Phase 1)
                lot_dimensions_score=calculated_metrics['lot_dimensions_score'],
                shape_efficiency_score=calculated_metrics['shape_efficiency_score'],
                corner_lot_bonus=calculated_metrics['corner_lot_bonus'],
                irregular_shape_penalty=calculated_metrics['irregular_shape_penalty'],
                subdivision_quality_score=calculated_metrics['subdivision_quality_score'],
                road_access_score=calculated_metrics['road_access_score'],
                location_type_score=calculated_metrics['location_type_score'],
                title_complexity_score=calculated_metrics['title_complexity_score'],
                survey_requirement_score=calculated_metrics['survey_requirement_score'],
                premium_water_access_score=calculated_metrics['premium_water_access_score'],
                total_description_score=calculated_metrics['total_description_score'],

                # County Intelligence Fields (Phase 1 - defaults for now)
                county_market_score=calculated_metrics['county_market_score'],
                geographic_score=calculated_metrics['geographic_score'],
                market_timing_score=calculated_metrics['market_timing_score']
            )

            self.db.add(property_obj)
            self.db.flush()  # Get ID without committing

            if auto_commit:
                self.db.commit()
                self.db.refresh(property_obj)

            logger.info(f"Created property {property_obj.id} with investment score {property_obj.investment_score}")
            return property_obj

        except Exception as e:
            if auto_commit:
                self.db.rollback()
            logger.error(f"Failed to create property: {str(e)}")
            raise
        finally:
            # Invalidate relevant caches after property creation
            if auto_commit:
                self._invalidate_property_caches(property_obj.county if property_obj else None)

    @cache_result("property_detail", ttl=900)  # Cache for 15 minutes
    def get_property(self, property_id: str) -> Optional[Property]:
        """Get property by ID."""
        return self.db.query(Property).filter(
            and_(Property.id == property_id, Property.is_deleted == False)
        ).first()

    def update_property(
        self,
        property_id: str,
        property_data: PropertyUpdate,
        device_id: Optional[str] = None,
        auto_commit: bool = True
    ) -> Optional[Property]:
        """
        Update property with recalculated metrics.

        Args:
            property_id: ID of property to update
            property_data: Property update data
            device_id: Optional device identifier for sync tracking
            auto_commit: If True (default), commits the transaction.
                        Set to False when caller manages transaction (e.g., sync orchestrator).
        """
        property_obj = None
        try:
            property_obj = self.get_property(property_id)
            if not property_obj:
                return None

            # Update fields from request
            update_data = property_data.dict(exclude_unset=True)

            for field, value in update_data.items():
                if field != 'device_id':  # Handle device_id separately
                    setattr(property_obj, field, value)

            # Set device_id for sync tracking
            if device_id:
                property_obj.device_id = device_id

            # Recalculate metrics using exact Python algorithms
            current_data = {
                'amount': property_obj.amount,
                'acreage': property_obj.acreage,
                'description': property_obj.description,
                'assessed_value': property_obj.assessed_value
            }

            calculated_metrics = self.calculate_property_metrics(current_data)

            # Update calculated fields (original)
            property_obj.price_per_acre = calculated_metrics['price_per_acre']
            property_obj.water_score = calculated_metrics['water_score']
            property_obj.investment_score = calculated_metrics['investment_score']
            property_obj.estimated_all_in_cost = calculated_metrics['estimated_all_in_cost']
            property_obj.assessed_value_ratio = calculated_metrics['assessed_value_ratio']

            # Update Enhanced Description Intelligence Fields (Phase 1)
            property_obj.lot_dimensions_score = calculated_metrics['lot_dimensions_score']
            property_obj.shape_efficiency_score = calculated_metrics['shape_efficiency_score']
            property_obj.corner_lot_bonus = calculated_metrics['corner_lot_bonus']
            property_obj.irregular_shape_penalty = calculated_metrics['irregular_shape_penalty']
            property_obj.subdivision_quality_score = calculated_metrics['subdivision_quality_score']
            property_obj.road_access_score = calculated_metrics['road_access_score']
            property_obj.location_type_score = calculated_metrics['location_type_score']
            property_obj.title_complexity_score = calculated_metrics['title_complexity_score']
            property_obj.survey_requirement_score = calculated_metrics['survey_requirement_score']
            property_obj.premium_water_access_score = calculated_metrics['premium_water_access_score']
            property_obj.total_description_score = calculated_metrics['total_description_score']

            # Update County Intelligence Fields (Phase 1 - defaults for now)
            property_obj.county_market_score = calculated_metrics['county_market_score']
            property_obj.geographic_score = calculated_metrics['geographic_score']
            property_obj.market_timing_score = calculated_metrics['market_timing_score']

            self.db.flush()  # Ensure changes are in transaction

            if auto_commit:
                self.db.commit()
                self.db.refresh(property_obj)

            logger.info(f"Updated property {property_obj.id} with new investment score {property_obj.investment_score}")
            return property_obj

        except Exception as e:
            if auto_commit:
                self.db.rollback()
            logger.error(f"Failed to update property {property_id}: {str(e)}")
            raise
        finally:
            # Invalidate relevant caches after property update
            if auto_commit and property_obj:
                self._invalidate_property_caches(property_obj.county, property_obj.id)

    def delete_property(
        self,
        property_id: str,
        device_id: Optional[str] = None,
        auto_commit: bool = True
    ) -> bool:
        """
        Soft delete property (for sync compatibility).

        Args:
            property_id: ID of property to delete
            device_id: Optional device identifier for sync tracking
            auto_commit: If True (default), commits the transaction.
                        Set to False when caller manages transaction (e.g., sync orchestrator).
        """
        property_obj = None
        try:
            property_obj = self.get_property(property_id)
            if not property_obj:
                return False

            # Soft delete for sync compatibility
            property_obj.is_deleted = True
            property_obj.device_id = device_id
            property_obj.updated_at = utc_now()

            self.db.flush()  # Ensure changes are in transaction

            if auto_commit:
                self.db.commit()

            logger.info(f"Soft deleted property {property_id}")
            return True

        except Exception as e:
            if auto_commit:
                self.db.rollback()
            logger.error(f"Failed to delete property {property_id}: {str(e)}")
            raise
        finally:
            # Invalidate relevant caches after property deletion
            if auto_commit and property_obj:
                self._invalidate_property_caches(property_obj.county, property_obj.id)

    @cache_result("property_list", ttl=300)  # Cache for 5 minutes
    def list_properties(self, filters: PropertyFilters) -> Tuple[List[Property], int]:
        """List properties with filtering, sorting, and pagination."""
        try:
            # Base query excluding soft-deleted properties
            query = self.db.query(Property).filter(Property.is_deleted == False)

            # Apply filters
            if filters.state:
                query = query.filter(Property.state == filters.state)

            if filters.county:
                query = query.filter(Property.county == filters.county)

            if filters.min_price is not None:
                query = query.filter(Property.amount >= filters.min_price)

            if filters.max_price is not None:
                query = query.filter(Property.amount <= filters.max_price)

            if filters.min_acreage is not None:
                query = query.filter(Property.acreage >= filters.min_acreage)

            if filters.max_acreage is not None:
                query = query.filter(Property.acreage <= filters.max_acreage)

            if filters.water_features is not None:
                if filters.water_features:
                    query = query.filter(Property.water_score > 0)
                else:
                    query = query.filter(Property.water_score == 0)

            if filters.min_investment_score is not None:
                query = query.filter(Property.investment_score >= filters.min_investment_score)

            if filters.max_investment_score is not None:
                query = query.filter(Property.investment_score <= filters.max_investment_score)

            if filters.year_sold:
                query = query.filter(Property.year_sold == filters.year_sold)

            # Minimum year sold filter (exclude pre-X delinquencies)
            # "Fail open" for NULL: properties with unknown delinquency year are included
            if filters.min_year_sold is not None:
                query = query.filter(
                    or_(
                        Property.year_sold >= str(filters.min_year_sold),
                        Property.year_sold.is_(None),
                        Property.year_sold == ''
                    )
                )

            # Exclude Delta region counties (AR high-risk)
            # "Fail open" for NULL: properties with unknown county are included
            if filters.exclude_delta_region:
                from core.scoring import DELTA_REGION_COUNTIES
                query = query.filter(
                    or_(
                        Property.county.is_(None),
                        ~func.upper(Property.county).in_(DELTA_REGION_COUNTIES)
                    )
                )

            # Created after filter (period selector)
            if filters.created_after is not None:
                query = query.filter(Property.created_at >= filters.created_after)

            if filters.search_query:
                search_term = f"%{filters.search_query}%"
                query = query.filter(
                    or_(
                        Property.description.ilike(search_term),
                        Property.owner_name.ilike(search_term),
                        Property.parcel_id.ilike(search_term)
                    )
                )

            # Advanced Intelligence Filters
            if filters.min_county_market_score is not None:
                query = query.filter(Property.county_market_score >= filters.min_county_market_score)
            if filters.min_geographic_score is not None:
                query = query.filter(Property.geographic_score >= filters.min_geographic_score)
            if filters.min_market_timing_score is not None:
                query = query.filter(Property.market_timing_score >= filters.min_market_timing_score)
            if filters.min_total_description_score is not None:
                query = query.filter(Property.total_description_score >= filters.min_total_description_score)
            if filters.min_road_access_score is not None:
                query = query.filter(Property.road_access_score >= filters.min_road_access_score)

            # Multi-state scoring filters
            if filters.max_effective_cost is not None:
                query = query.filter(Property.effective_cost <= filters.max_effective_cost)
            if filters.min_buy_hold_score is not None:
                query = query.filter(Property.buy_hold_score >= filters.min_buy_hold_score)

            # Get total count before pagination
            total_count = query.count()

            # Apply sorting
            sort_column = getattr(Property, filters.sort_by, Property.investment_score)
            if filters.sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))

            # Apply pagination
            offset = (filters.page - 1) * filters.page_size
            properties = query.offset(offset).limit(filters.page_size).all()

            logger.info(f"Retrieved {len(properties)} properties (page {filters.page}, total {total_count})")
            return properties, total_count

        except Exception as e:
            logger.error(f"Failed to list properties: {str(e)}")
            raise

    def calculate_metrics_for_request(self, request: PropertyCalculationRequest) -> PropertyCalculationResponse:
        """Calculate metrics for API request (validation endpoint)."""
        try:
            data_dict = request.dict()
            calculated_metrics = self.calculate_property_metrics(data_dict)

            return PropertyCalculationResponse(
                price_per_acre=calculated_metrics['price_per_acre'],
                water_score=calculated_metrics['water_score'],
                investment_score=calculated_metrics['investment_score'],
                estimated_all_in_cost=calculated_metrics['estimated_all_in_cost'],
                assessed_value_ratio=calculated_metrics['assessed_value_ratio'],
                algorithm_version="1.0.0",  # Match iOS version
                calculation_timestamp=utc_now()
            )

        except Exception as e:
            logger.error(f"Failed to calculate metrics: {str(e)}")
            raise

    @cache_result("analytics", ttl=1800)  # Cache for 30 minutes
    def get_property_metrics(self) -> PropertyMetrics:
        """Get overall property analytics."""
        try:
            # Basic counts and averages
            total_properties = self.db.query(Property).filter(Property.is_deleted == False).count()

            if total_properties == 0:
                return PropertyMetrics(
                    total_properties=0,
                    average_investment_score=0.0,
                    average_water_score=0.0,
                    average_price_per_acre=0.0,
                    properties_with_water=0,
                    county_distribution={},
                    year_distribution={},
                    score_ranges={}
                )

            # Calculate averages
            avg_investment = self.db.query(func.avg(Property.investment_score)).filter(
                Property.is_deleted == False
            ).scalar() or 0.0

            avg_water = self.db.query(func.avg(Property.water_score)).filter(
                Property.is_deleted == False
            ).scalar() or 0.0

            avg_price_per_acre = self.db.query(func.avg(Property.price_per_acre)).filter(
                and_(Property.is_deleted == False, Property.price_per_acre.isnot(None))
            ).scalar() or 0.0

            # Count properties with water features
            properties_with_water = self.db.query(Property).filter(
                and_(Property.is_deleted == False, Property.water_score > 0)
            ).count()

            # County distribution
            county_dist = {}
            county_results = self.db.query(
                Property.county, func.count(Property.id)
            ).filter(
                Property.is_deleted == False
            ).group_by(Property.county).all()

            for county, count in county_results:
                county_dist[county or "Unknown"] = count

            # Year distribution
            year_dist = {}
            year_results = self.db.query(
                Property.year_sold, func.count(Property.id)
            ).filter(
                Property.is_deleted == False
            ).group_by(Property.year_sold).all()

            for year, count in year_results:
                year_dist[year or "Unknown"] = count

            # Score ranges
            score_ranges = {
                "0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0
            }

            score_results = self.db.query(Property.investment_score).filter(
                and_(Property.is_deleted == False, Property.investment_score.isnot(None))
            ).all()

            for (score,) in score_results:
                if score <= 20:
                    score_ranges["0-20"] += 1
                elif score <= 40:
                    score_ranges["21-40"] += 1
                elif score <= 60:
                    score_ranges["41-60"] += 1
                elif score <= 80:
                    score_ranges["61-80"] += 1
                else:
                    score_ranges["81-100"] += 1

            return PropertyMetrics(
                total_properties=total_properties,
                average_investment_score=round(avg_investment, 2),
                average_water_score=round(avg_water, 2),
                average_price_per_acre=round(avg_price_per_acre, 2),
                properties_with_water=properties_with_water,
                county_distribution=county_dist,
                year_distribution=year_dist,
                score_ranges=score_ranges
            )

        except Exception as e:
            logger.error(f"Failed to get property metrics: {str(e)}")
            raise

    def recalculate_all_ranks(self):
        """Recalculate ranking for all properties based on investment score."""
        try:
            # Get all active properties ordered by investment score (desc)
            properties = self.db.query(Property).filter(
                and_(
                    Property.is_deleted == False,
                    Property.investment_score.isnot(None)
                )
            ).order_by(desc(Property.investment_score)).all()

            # Update ranks
            for rank, property_obj in enumerate(properties, 1):
                property_obj.rank = rank

            self.db.commit()
            logger.info(f"Recalculated ranks for {len(properties)} properties")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to recalculate ranks: {str(e)}")
            raise

    def _invalidate_property_caches(self, county: Optional[str] = None, property_id: Optional[str] = None):
        """Invalidate property-related caches after data changes."""
        try:
            cache_invalidator = get_cache_invalidator()
            cache_invalidator.invalidate_property_caches(property_id=property_id, county=county)
            logger.debug(f"Invalidated caches for property_id={property_id}, county={county}")
        except Exception as e:
            logger.warning(f"Failed to invalidate caches: {e}")

    @cache_result("dashboard_stats", ttl=300)  # Cache for 5 minutes
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """
        Get aggregated statistics for the frontend dashboard.
        Uses efficient SQL aggregations to minimize database roundtrips.
        """
        from datetime import datetime, timedelta, timezone
        from sqlalchemy import case

        try:
            now = datetime.now(timezone.utc)
            seven_days_ago = now - timedelta(days=7)
            fourteen_days_ago = now - timedelta(days=14)

            # 1. Main aggregates in a single query
            main_stats = self.db.query(
                func.count(Property.id).label("total"),
                func.avg(Property.investment_score).label("avg_inv_score"),
                func.avg(Property.price_per_acre).label("avg_price"),
                func.avg(Property.water_score).label("avg_water_score"),
                func.count(case((Property.water_score > 0, 1))).label("water_count"),
                func.count(case((Property.created_at >= seven_days_ago, 1))).label("new_7d"),
                func.count(case((and_(
                    Property.created_at >= fourteen_days_ago,
                    Property.created_at < seven_days_ago
                ), 1))).label("new_prev_7d"),
            ).filter(
                Property.is_deleted == False
            ).first()

            total_props = main_stats.total or 0
            new_7d = main_stats.new_7d or 0
            prev_7d = main_stats.new_prev_7d or 0
            water_count = main_stats.water_count or 0

            # Calculate trend
            if prev_7d > 0:
                pct_change = ((new_7d - prev_7d) / prev_7d) * 100
                trend_str = f"{pct_change:+.0f}% vs last week"
            elif new_7d > 0:
                trend_str = "New this week"
            else:
                trend_str = "No change"

            # Calculate water access percentage
            water_percentage = (water_count / total_props * 100) if total_props > 0 else 0

            # 2. Top counties by property count
            counties_query = self.db.query(
                Property.county,
                func.count(Property.id).label("count"),
                func.avg(Property.investment_score).label("avg_score")
            ).filter(
                Property.is_deleted == False,
                Property.county.isnot(None)
            ).group_by(
                Property.county
            ).order_by(
                desc("count")
            ).limit(5).all()

            top_counties = [
                {
                    "name": r.county,
                    "count": r.count,
                    "avg_investment_score": round(r.avg_score or 0, 1)
                }
                for r in counties_query
            ]

            # 3. Price distribution buckets
            price_buckets = self.db.query(
                func.count(case((Property.price_per_acre < 1000, 1))).label("r0"),
                func.count(case((and_(Property.price_per_acre >= 1000, Property.price_per_acre < 5000), 1))).label("r1"),
                func.count(case((and_(Property.price_per_acre >= 5000, Property.price_per_acre < 10000), 1))).label("r2"),
                func.count(case((and_(Property.price_per_acre >= 10000, Property.price_per_acre < 50000), 1))).label("r3"),
                func.count(case((Property.price_per_acre >= 50000, 1))).label("r4")
            ).filter(Property.is_deleted == False).first()

            price_distribution = {
                "ranges": ["<$1k", "$1k-5k", "$5k-10k", "$10k-50k", "$50k+"],
                "counts": [
                    price_buckets.r0 or 0,
                    price_buckets.r1 or 0,
                    price_buckets.r2 or 0,
                    price_buckets.r3 or 0,
                    price_buckets.r4 or 0
                ]
            }

            # 4. Activity timeline (last 14 days)
            timeline_query = self.db.query(
                func.date(Property.created_at).label("date"),
                func.count(Property.id).label("count")
            ).filter(
                Property.is_deleted == False,
                Property.created_at >= (now - timedelta(days=14))
            ).group_by(
                func.date(Property.created_at)
            ).all()

            timeline_map = {str(r.date): r.count for r in timeline_query}
            timeline_dates = []
            timeline_counts = []
            for i in range(14):
                d = (now - timedelta(days=13-i)).date()
                timeline_dates.append(d.strftime("%b %d"))
                timeline_counts.append(timeline_map.get(str(d), 0))

            # 5. Recent activity (synthesized from recent properties)
            recent_props = self.db.query(Property).filter(
                Property.is_deleted == False
            ).order_by(desc(Property.updated_at)).limit(10).all()

            recent_activity = []
            for p in recent_props:
                # Determine activity type
                if p.created_at and p.updated_at:
                    # If created and updated are within 1 minute, it's new
                    is_new = abs((p.created_at - p.updated_at).total_seconds()) < 60
                else:
                    is_new = True

                if p.status == 'reviewing':
                    act_type = "reviewed"
                elif is_new:
                    act_type = "new"
                else:
                    act_type = "updated"

                county_name = p.county or "Unknown County"
                recent_activity.append({
                    "type": act_type,
                    "description": f"{county_name} - {p.parcel_id[:20] if p.parcel_id else 'Property'}",
                    "timestamp": p.updated_at.isoformat() if p.updated_at else now.isoformat()
                })

            # 6. Score distribution averages
            scores = self.db.query(
                func.avg(Property.water_score).label("water"),
                func.avg(Property.investment_score).label("invest"),
                func.avg(Property.county_market_score).label("county"),
                func.avg(Property.geographic_score).label("geo"),
                func.avg(Property.total_description_score).label("desc")
            ).filter(Property.is_deleted == False).first()

            score_distribution = {
                "water_score": round(scores.water or 0, 1),
                "investment_score": round(scores.invest or 0, 1),
                "county_market_score": round(scores.county or 0, 1),
                "geographic_score": round(scores.geo or 0, 1),
                "description_score": round(scores.desc or 0, 1)
            }

            # 7. State distribution (multi-state support)
            state_counts = self.db.query(
                Property.state,
                func.count(Property.id).label("count"),
                func.avg(Property.investment_score).label("avg_score")
            ).filter(
                Property.is_deleted == False
            ).group_by(
                Property.state
            ).order_by(
                desc("count")
            ).all()

            state_distribution = [
                {
                    "state": r.state or "AL",
                    "count": r.count,
                    "avg_investment_score": round(r.avg_score or 0, 1)
                }
                for r in state_counts
            ]

            return {
                "total_properties": total_props,
                "upcoming_auctions": 0,  # No auction_date field in model
                "new_items_7d": new_7d,
                "new_items_trend": trend_str,
                "watchlist_count": 0,  # No is_watchlisted field in model
                "avg_investment_score": round(main_stats.avg_inv_score or 0, 1),
                "water_access_percentage": round(water_percentage, 1),
                "avg_price_per_acre": round(main_stats.avg_price or 0, 2),
                "top_counties": top_counties,
                "recent_activity": recent_activity,
                "price_distribution": price_distribution,
                "score_distribution": score_distribution,
                "activity_timeline": {
                    "dates": timeline_dates,
                    "new_properties": timeline_counts
                },
                "state_distribution": state_distribution
            }

        except Exception as e:
            logger.error(f"Failed to get dashboard stats: {str(e)}")
            raise
