"""
Property service layer using exact Python algorithms from scripts/utils.py
CRITICAL: Maintains mathematical precision with iOS Swift implementation
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from datetime import datetime

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
            logger.info(f"Starting enhanced analysis for description: {description[:50]}...")
            analyzer = EnhancedDescriptionAnalyzer()
            intelligence = analyzer.analyze_description(description)
            logger.info(f"Enhanced analysis complete. Total score: {intelligence.total_description_score}")

            # County Intelligence Analysis (Phase 1)
            county_name = property_data.get('county', '')
            county_intelligence_scores = {'county_market_score': 0.0, 'geographic_score': 0.0, 'market_timing_score': 0.0}

            if county_name:
                logger.info(f"Starting county intelligence analysis for: {county_name}")
                county_analyzer = CountyIntelligenceAnalyzer()
                county_intelligence = county_analyzer.analyze_county(county_name)
                county_intelligence_scores = {
                    'county_market_score': county_intelligence.county_market_score,
                    'geographic_score': county_intelligence.geographic_score,
                    'market_timing_score': county_intelligence.market_timing_score
                }
                logger.info(f"County analysis complete. Market: {county_intelligence_scores['county_market_score']}, Geographic: {county_intelligence_scores['geographic_score']}, Timing: {county_intelligence_scores['market_timing_score']}")
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

            logger.info(f"Returning enhanced metrics. Corner bonus: {result['corner_lot_bonus']}, Total description score: {result['total_description_score']}, County market: {result['county_market_score']}, Geographic: {result['geographic_score']}, Timing: {result['market_timing_score']}")
            return result

        except Exception as e:
            logger.error(f"Algorithm calculation failed: {str(e)}")
            raise

    def create_property(self, property_data: PropertyCreate, device_id: Optional[str] = None) -> Property:
        """Create a new property with calculated metrics."""
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
            self.db.commit()
            self.db.refresh(property_obj)

            logger.info(f"Created property {property_obj.id} with investment score {property_obj.investment_score}")
            return property_obj

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create property: {str(e)}")
            raise
        finally:
            # Invalidate relevant caches after property creation
            self._invalidate_property_caches(property_obj.county if property_obj else None)

    @cache_result("property_detail", ttl=900)  # Cache for 15 minutes
    def get_property(self, property_id: str) -> Optional[Property]:
        """Get property by ID."""
        return self.db.query(Property).filter(
            and_(Property.id == property_id, Property.is_deleted == False)
        ).first()

    def update_property(self, property_id: str, property_data: PropertyUpdate, device_id: Optional[str] = None) -> Optional[Property]:
        """Update property with recalculated metrics."""
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

            self.db.commit()
            self.db.refresh(property_obj)

            logger.info(f"Updated property {property_obj.id} with new investment score {property_obj.investment_score}")
            return property_obj

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update property {property_id}: {str(e)}")
            raise
        finally:
            # Invalidate relevant caches after property update
            if property_obj:
                self._invalidate_property_caches(property_obj.county, property_obj.id)

    def delete_property(self, property_id: str, device_id: Optional[str] = None) -> bool:
        """Soft delete property (for sync compatibility)."""
        try:
            property_obj = self.get_property(property_id)
            if not property_obj:
                return False

            # Soft delete for sync compatibility
            property_obj.is_deleted = True
            property_obj.device_id = device_id
            property_obj.updated_at = datetime.utcnow()

            self.db.commit()
            logger.info(f"Soft deleted property {property_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete property {property_id}: {str(e)}")
            raise
        finally:
            # Invalidate relevant caches after property deletion
            if property_obj:
                self._invalidate_property_caches(property_obj.county, property_obj.id)

    @cache_result("property_list", ttl=300)  # Cache for 5 minutes
    def list_properties(self, filters: PropertyFilters) -> Tuple[List[Property], int]:
        """List properties with filtering, sorting, and pagination."""
        try:
            # Base query excluding soft-deleted properties
            query = self.db.query(Property).filter(Property.is_deleted == False)

            # Apply filters
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
                calculation_timestamp=datetime.utcnow()
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
