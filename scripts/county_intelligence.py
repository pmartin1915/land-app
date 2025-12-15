"""
County Intelligence Module
Alabama Auction Watcher - Phase 1 Enhancement

This module provides advanced county-level intelligence for property investment
analysis, including economic indicators, geographic advantages, and market timing.

Author: Claude Code AI Assistant
Date: 2025-09-19
"""

from typing import Dict, Tuple
from dataclasses import dataclass
import math

@dataclass
class CountyIntelligence:
    """Container for county-level investment intelligence."""

    # Economic Intelligence
    median_income_score: float = 0.0
    unemployment_score: float = 0.0
    population_growth_score: float = 0.0
    economic_diversity_score: float = 0.0

    # Geographic Intelligence
    proximity_to_major_cities_score: float = 0.0
    natural_features_score: float = 0.0
    transportation_access_score: float = 0.0
    climate_advantages_score: float = 0.0

    # Market Timing Intelligence
    development_trends_score: float = 0.0
    real_estate_activity_score: float = 0.0
    investment_momentum_score: float = 0.0
    infrastructure_development_score: float = 0.0

    # Overall County Scores
    county_market_score: float = 0.0
    geographic_score: float = 0.0
    market_timing_score: float = 0.0

    # Metadata
    data_freshness_days: int = 0
    confidence_level: float = 0.0


class CountyIntelligenceAnalyzer:
    """Advanced county intelligence analysis for Alabama counties."""

    def __init__(self):
        """Initialize the analyzer with county data and scoring weights."""
        self._initialize_county_profiles()
        self._initialize_scoring_weights()
        self._initialize_geographic_data()

    def _initialize_county_profiles(self):
        """Initialize baseline county profiles with known characteristics."""

        # Alabama major metropolitan areas and their characteristics
        self.metro_counties = {
            # Birmingham Metro
            'Jefferson': {'metro_tier': 1, 'population_tier': 'large', 'economic_diversity': 'high'},
            'Shelby': {'metro_tier': 1, 'population_tier': 'medium', 'economic_diversity': 'high'},
            'St. Clair': {'metro_tier': 2, 'population_tier': 'small', 'economic_diversity': 'medium'},
            'Blount': {'metro_tier': 2, 'population_tier': 'small', 'economic_diversity': 'medium'},

            # Huntsville Metro (Tech Hub)
            'Madison': {'metro_tier': 1, 'population_tier': 'large', 'economic_diversity': 'very_high'},
            'Limestone': {'metro_tier': 2, 'population_tier': 'medium', 'economic_diversity': 'high'},
            'Morgan': {'metro_tier': 2, 'population_tier': 'medium', 'economic_diversity': 'medium'},

            # Mobile Metro (Port City)
            'Mobile': {'metro_tier': 1, 'population_tier': 'large', 'economic_diversity': 'high'},
            'Baldwin': {'metro_tier': 1, 'population_tier': 'large', 'economic_diversity': 'high'},

            # Montgomery Metro (Capital)
            'Montgomery': {'metro_tier': 1, 'population_tier': 'large', 'economic_diversity': 'high'},
            'Elmore': {'metro_tier': 2, 'population_tier': 'medium', 'economic_diversity': 'medium'},
            'Autauga': {'metro_tier': 2, 'population_tier': 'small', 'economic_diversity': 'medium'},

            # Tuscaloosa Metro (University)
            'Tuscaloosa': {'metro_tier': 1, 'population_tier': 'large', 'economic_diversity': 'high'},

            # Auburn-Opelika Metro
            'Lee': {'metro_tier': 2, 'population_tier': 'medium', 'economic_diversity': 'high'},

            # Florence-Muscle Shoals Metro
            'Lauderdale': {'metro_tier': 2, 'population_tier': 'medium', 'economic_diversity': 'medium'},
            'Colbert': {'metro_tier': 2, 'population_tier': 'small', 'economic_diversity': 'medium'},

            # Gadsden Metro
            'Etowah': {'metro_tier': 2, 'population_tier': 'medium', 'economic_diversity': 'medium'},

            # Anniston-Oxford Metro
            'Calhoun': {'metro_tier': 2, 'population_tier': 'medium', 'economic_diversity': 'medium'},
        }

        # Counties with significant natural features
        self.natural_feature_counties = {
            # Gulf Coast
            'Baldwin': {'water_features': 'exceptional', 'recreation': 'very_high', 'tourism': 'high'},
            'Mobile': {'water_features': 'high', 'recreation': 'high', 'tourism': 'medium'},

            # Tennessee River Valley
            'Madison': {'water_features': 'high', 'recreation': 'high', 'tourism': 'medium'},
            'Limestone': {'water_features': 'high', 'recreation': 'high', 'tourism': 'medium'},
            'Lauderdale': {'water_features': 'high', 'recreation': 'high', 'tourism': 'medium'},
            'Morgan': {'water_features': 'high', 'recreation': 'high', 'tourism': 'medium'},
            'Marshall': {'water_features': 'high', 'recreation': 'high', 'tourism': 'medium'},
            'Jackson': {'water_features': 'high', 'recreation': 'high', 'tourism': 'low'},

            # Appalachian Foothills
            'DeKalb': {'water_features': 'medium', 'recreation': 'high', 'tourism': 'medium'},
            'Cherokee': {'water_features': 'medium', 'recreation': 'high', 'tourism': 'medium'},
            'Etowah': {'water_features': 'medium', 'recreation': 'medium', 'tourism': 'low'},

            # Black Belt Region (Rich Soil)
            'Dallas': {'water_features': 'low', 'recreation': 'low', 'tourism': 'historical'},
            'Marengo': {'water_features': 'low', 'recreation': 'low', 'tourism': 'historical'},
            'Perry': {'water_features': 'low', 'recreation': 'low', 'tourism': 'historical'},

            # Central Alabama Lakes
            'Coosa': {'water_features': 'high', 'recreation': 'high', 'tourism': 'medium'},
            'Tallapoosa': {'water_features': 'high', 'recreation': 'high', 'tourism': 'medium'},
            'Elmore': {'water_features': 'high', 'recreation': 'high', 'tourism': 'medium'},
        }

        # Transportation corridors and infrastructure
        self.transportation_corridors = {
            # Interstate 65 Corridor (North-South)
            'I65': ['Mobile', 'Baldwin', 'Monroe', 'Butler', 'Crenshaw', 'Montgomery',
                   'Autauga', 'Chilton', 'Shelby', 'Jefferson', 'Blount', 'Cullman', 'Morgan', 'Limestone'],

            # Interstate 20/59 Corridor (East-West)
            'I20': ['Tuscaloosa', 'Jefferson', 'St. Clair', 'Calhoun', 'Cleburne'],

            # Interstate 85 Corridor (Northeast)
            'I85': ['Montgomery', 'Macon', 'Lee', 'Chambers'],

            # US Highway 231 Corridor
            'US231': ['Houston', 'Dale', 'Coffee', 'Pike', 'Montgomery'],

            # Tennessee River Ports
            'River_Access': ['Lauderdale', 'Colbert', 'Morgan', 'Marshall', 'Jackson', 'Madison', 'Limestone'],

            # Port of Mobile Access
            'Port_Access': ['Mobile', 'Baldwin', 'Monroe', 'Clarke', 'Washington']
        }

    def _initialize_scoring_weights(self):
        """Define scoring weights for county intelligence factors."""

        self.economic_weights = {
            'metro_tier_1_bonus': 25.0,       # Major metro areas
            'metro_tier_2_bonus': 15.0,       # Secondary metro areas
            'high_diversity_bonus': 20.0,     # Economic diversity
            'university_presence_bonus': 15.0, # University towns
            'government_presence_bonus': 12.0, # State/federal facilities
            'port_access_bonus': 18.0,        # Port access
            'tech_hub_bonus': 30.0,           # Technology centers
            'tourism_economy_bonus': 12.0,    # Tourism-based economy
        }

        self.geographic_weights = {
            'exceptional_water_bonus': 35.0,   # Gulf Coast, exceptional lakes
            'high_water_bonus': 25.0,          # Tennessee River, major lakes
            'medium_water_bonus': 15.0,        # Smaller lakes, streams
            'recreation_bonus': 20.0,          # Recreation opportunities
            'climate_advantage_bonus': 10.0,   # Favorable climate
            'mountain_proximity_bonus': 8.0,   # Near mountains/hills
            'agricultural_quality_bonus': 12.0, # Prime agricultural land
        }

        self.market_timing_weights = {
            'interstate_access_bonus': 20.0,   # Interstate highway access
            'major_city_proximity_bonus': 25.0, # Within 50 miles of major city
            'development_pressure_bonus': 18.0, # Growth pressure areas
            'infrastructure_investment_bonus': 15.0, # New infrastructure
            'population_growth_bonus': 22.0,   # Growing population
            'job_growth_bonus': 20.0,          # Employment growth
        }

    def _initialize_geographic_data(self):
        """Initialize geographic reference data for distance calculations."""

        # Major Alabama cities with approximate coordinates
        self.major_cities = {
            'Birmingham': (33.5186, -86.8104),
            'Montgomery': (32.3792, -86.3077),
            'Mobile': (30.6954, -88.0399),
            'Huntsville': (34.7304, -86.5861),
            'Tuscaloosa': (33.2098, -87.5692),
            'Auburn': (32.6099, -85.4808),
            'Dothan': (31.2232, -85.3905),
            'Florence': (34.7998, -87.6773),
            'Gadsden': (34.0143, -86.0066),
            'Anniston': (33.6598, -85.8316)
        }

        # County seat coordinates (approximate)
        self.county_coordinates = {
            'Autauga': (32.5246, -86.6441), 'Baldwin': (30.7266, -87.7286),
            'Barbour': (31.8593, -85.3873), 'Bibb': (33.0232, -87.1253),
            'Blount': (33.9809, -86.5669), 'Bullock': (32.1079, -85.7164),
            'Butler': (31.7540, -86.6836), 'Calhoun': (33.7709, -85.8269),
            'Chambers': (32.9079, -85.4269), 'Cherokee': (34.2609, -85.6408),
            'Chilton': (32.8409, -86.7408), 'Choctaw': (32.0409, -88.2408),
            'Clarke': (31.5409, -87.8408), 'Clay': (33.2709, -85.8908),
            'Cleburne': (33.6709, -85.5408), 'Coffee': (31.4609, -85.9908),
            'Colbert': (34.6309, -87.7908), 'Conecuh': (31.4309, -86.8908),
            'Coosa': (32.9009, -86.3408), 'Covington': (31.3009, -86.4408),
            'Crenshaw': (31.7409, -86.3008), 'Cullman': (34.1809, -86.8408),
            'Dale': (31.5009, -85.6408), 'Dallas': (32.4409, -87.0408),
            'DeKalb': (34.4709, -85.7908), 'Elmore': (32.5909, -86.0908),
            'Escambia': (31.0909, -87.0908), 'Etowah': (34.0109, -86.0408),
            'Fayette': (33.7009, -87.8408), 'Franklin': (34.3109, -87.6908),
            'Geneva': (31.0409, -85.8908), 'Greene': (32.8609, -87.8908),
            'Hale': (32.7909, -87.6408), 'Henry': (31.3509, -85.1908),
            'Houston': (31.2209, -85.3908), 'Jackson': (34.8709, -85.8408),
            'Jefferson': (33.5209, -86.8108), 'Lamar': (33.6709, -88.0908),
            'Lauderdale': (34.8209, -87.6908), 'Lawrence': (34.5309, -87.3408),
            'Lee': (32.6109, -85.4808), 'Limestone': (34.8009, -86.9908),
            'Lowndes': (32.1509, -86.6408), 'Macon': (32.4409, -85.7008),
            'Madison': (34.7309, -86.5908), 'Marengo': (32.3109, -87.7908),
            'Marion': (34.1309, -87.9908), 'Marshall': (34.3509, -86.3608),
            'Mobile': (30.6909, -88.0408), 'Monroe': (31.5309, -87.3408),
            'Montgomery': (32.3809, -86.3108), 'Morgan': (34.4909, -86.9008),
            'Perry': (32.6509, -87.2908), 'Pickens': (33.2309, -88.2708),
            'Pike': (31.8409, -85.9908), 'Randolph': (33.3109, -85.5408),
            'Russell': (32.3509, -85.1008), 'St. Clair': (33.8109, -86.3008),
            'Shelby': (33.1509, -86.5808), 'Sumter': (32.5609, -88.1408),
            'Talladega': (33.4309, -86.1008), 'Tallapoosa': (32.9609, -85.8908),
            'Tuscaloosa': (33.2109, -87.5708), 'Walker': (33.7909, -87.2908),
            'Washington': (31.4509, -88.1908), 'Wilcox': (31.9909, -87.2408),
            'Winston': (34.1109, -87.1908)
        }

    def analyze_county(self, county_name: str) -> CountyIntelligence:
        """
        Analyze a specific Alabama county and generate intelligence scores.

        Args:
            county_name: Name of the Alabama county (e.g., "Baldwin", "Jefferson")

        Returns:
            CountyIntelligence object with all scoring factors
        """
        if county_name not in self.county_coordinates:
            return CountyIntelligence()

        intelligence = CountyIntelligence()

        # Analyze economic factors
        intelligence.median_income_score = self._analyze_economic_indicators(county_name)
        intelligence.unemployment_score = self._analyze_employment_factors(county_name)
        intelligence.population_growth_score = self._analyze_population_trends(county_name)
        intelligence.economic_diversity_score = self._analyze_economic_diversity(county_name)

        # Analyze geographic advantages
        intelligence.proximity_to_major_cities_score = self._analyze_city_proximity(county_name)
        intelligence.natural_features_score = self._analyze_natural_features(county_name)
        intelligence.transportation_access_score = self._analyze_transportation_access(county_name)
        intelligence.climate_advantages_score = self._analyze_climate_advantages(county_name)

        # Analyze market timing factors
        intelligence.development_trends_score = self._analyze_development_trends(county_name)
        intelligence.real_estate_activity_score = self._analyze_real_estate_activity(county_name)
        intelligence.investment_momentum_score = self._analyze_investment_momentum(county_name)
        intelligence.infrastructure_development_score = self._analyze_infrastructure_development(county_name)

        # Calculate overall scores
        intelligence.county_market_score = self._calculate_market_score(intelligence)
        intelligence.geographic_score = self._calculate_geographic_score(intelligence)
        intelligence.market_timing_score = self._calculate_timing_score(intelligence)

        # Set metadata
        intelligence.data_freshness_days = 1  # Baseline data
        intelligence.confidence_level = self._calculate_confidence_level(county_name)

        return intelligence

    def _analyze_economic_indicators(self, county_name: str) -> float:
        """Analyze economic indicators for the county."""
        score = 0.0

        # Metro area presence
        if county_name in self.metro_counties:
            metro_info = self.metro_counties[county_name]
            if metro_info['metro_tier'] == 1:
                score += self.economic_weights['metro_tier_1_bonus']
            elif metro_info['metro_tier'] == 2:
                score += self.economic_weights['metro_tier_2_bonus']

        # Economic diversity bonus
        if county_name in self.metro_counties:
            diversity = self.metro_counties[county_name]['economic_diversity']
            if diversity == 'very_high':
                score += self.economic_weights['tech_hub_bonus']
            elif diversity == 'high':
                score += self.economic_weights['high_diversity_bonus']

        # Special economic features
        if county_name in ['Madison', 'Limestone']:  # Huntsville tech corridor
            score += self.economic_weights['tech_hub_bonus']

        if county_name in ['Mobile', 'Baldwin']:  # Port access
            score += self.economic_weights['port_access_bonus']

        if county_name in ['Tuscaloosa', 'Lee', 'Jefferson']:  # University presence
            score += self.economic_weights['university_presence_bonus']

        if county_name in ['Montgomery', 'Madison']:  # Government presence
            score += self.economic_weights['government_presence_bonus']

        return score

    def _analyze_employment_factors(self, county_name: str) -> float:
        """Analyze employment and job market factors."""
        score = 0.0

        # Metro areas generally have better employment
        if county_name in self.metro_counties:
            score += 15.0

        # Technology centers have exceptional job markets
        if county_name in ['Madison', 'Jefferson', 'Shelby']:
            score += 25.0

        return score

    def _analyze_population_trends(self, county_name: str) -> float:
        """Analyze population growth trends."""
        score = 0.0

        # Fast-growing counties (based on known growth patterns)
        high_growth_counties = ['Baldwin', 'Madison', 'Shelby', 'Lee', 'Limestone', 'Elmore', 'Autauga']
        medium_growth_counties = ['Mobile', 'Tuscaloosa', 'St. Clair', 'Morgan']

        if county_name in high_growth_counties:
            score += self.market_timing_weights['population_growth_bonus']
        elif county_name in medium_growth_counties:
            score += self.market_timing_weights['population_growth_bonus'] * 0.6

        return score

    def _analyze_economic_diversity(self, county_name: str) -> float:
        """Analyze economic diversity factors."""
        score = 0.0

        if county_name in self.metro_counties:
            diversity = self.metro_counties[county_name]['economic_diversity']
            if diversity == 'very_high':
                score += 30.0
            elif diversity == 'high':
                score += 20.0
            elif diversity == 'medium':
                score += 10.0

        return score

    def _analyze_city_proximity(self, county_name: str) -> float:
        """Analyze proximity to major cities."""
        score = 0.0

        if county_name not in self.county_coordinates:
            return 0.0

        county_coords = self.county_coordinates[county_name]

        for city_name, city_coords in self.major_cities.items():
            distance = self._calculate_distance(county_coords, city_coords)

            if distance <= 25:  # Within 25 miles
                score += self.market_timing_weights['major_city_proximity_bonus']
                break
            elif distance <= 50:  # Within 50 miles
                score += self.market_timing_weights['major_city_proximity_bonus'] * 0.6
                break

        return score

    def _analyze_natural_features(self, county_name: str) -> float:
        """Analyze natural features and recreational opportunities."""
        score = 0.0

        if county_name in self.natural_feature_counties:
            features = self.natural_feature_counties[county_name]

            # Water features scoring
            water_quality = features.get('water_features', 'none')
            if water_quality == 'exceptional':
                score += self.geographic_weights['exceptional_water_bonus']
            elif water_quality == 'high':
                score += self.geographic_weights['high_water_bonus']
            elif water_quality == 'medium':
                score += self.geographic_weights['medium_water_bonus']

            # Recreation opportunities
            recreation = features.get('recreation', 'none')
            if recreation in ['very_high', 'high']:
                score += self.geographic_weights['recreation_bonus']

        return score

    def _analyze_transportation_access(self, county_name: str) -> float:
        """Analyze transportation infrastructure and access."""
        score = 0.0

        # Interstate access
        for corridor, counties in self.transportation_corridors.items():
            if county_name in counties:
                if corridor.startswith('I'):  # Interstate highways
                    score += self.market_timing_weights['interstate_access_bonus']
                    break

        # River access for shipping
        if county_name in self.transportation_corridors.get('River_Access', []):
            score += 15.0

        # Port access
        if county_name in self.transportation_corridors.get('Port_Access', []):
            score += 12.0

        return score

    def _analyze_climate_advantages(self, county_name: str) -> float:
        """Analyze climate and weather advantages."""
        score = 0.0

        # Gulf Coast counties have climate advantages
        if county_name in ['Baldwin', 'Mobile']:
            score += self.geographic_weights['climate_advantage_bonus']

        # Moderate climate counties
        if county_name in ['Madison', 'Jefferson', 'Tuscaloosa']:
            score += self.geographic_weights['climate_advantage_bonus'] * 0.6

        return score

    def _analyze_development_trends(self, county_name: str) -> float:
        """Analyze development and growth trends."""
        score = 0.0

        # High development pressure areas
        high_development_counties = ['Baldwin', 'Shelby', 'Madison', 'Lee', 'Elmore']
        medium_development_counties = ['Limestone', 'St. Clair', 'Autauga', 'Morgan']

        if county_name in high_development_counties:
            score += self.market_timing_weights['development_pressure_bonus']
        elif county_name in medium_development_counties:
            score += self.market_timing_weights['development_pressure_bonus'] * 0.6

        return score

    def _analyze_real_estate_activity(self, county_name: str) -> float:
        """Analyze real estate market activity."""
        score = 0.0

        # Metro areas have higher real estate activity
        if county_name in self.metro_counties:
            metro_tier = self.metro_counties[county_name]['metro_tier']
            if metro_tier == 1:
                score += 25.0
            else:
                score += 15.0

        return score

    def _analyze_investment_momentum(self, county_name: str) -> float:
        """Analyze investment momentum and business growth."""
        score = 0.0

        # Technology and growth centers
        if county_name in ['Madison', 'Baldwin', 'Shelby', 'Lee']:
            score += 30.0
        elif county_name in ['Jefferson', 'Mobile', 'Tuscaloosa']:
            score += 20.0

        return score

    def _analyze_infrastructure_development(self, county_name: str) -> float:
        """Analyze infrastructure development and investment."""
        score = 0.0

        # Counties with major infrastructure investments
        if county_name in ['Baldwin', 'Madison', 'Mobile']:  # Port expansion, aerospace
            score += self.market_timing_weights['infrastructure_investment_bonus']

        return score

    def _calculate_market_score(self, intelligence: CountyIntelligence) -> float:
        """Calculate overall county market score."""
        total = (
            intelligence.median_income_score +
            intelligence.unemployment_score +
            intelligence.population_growth_score +
            intelligence.economic_diversity_score
        )

        # Normalize to 0-100 scale
        normalized = max(0, min(100, total * (100 / 150)))
        return round(normalized, 1)

    def _calculate_geographic_score(self, intelligence: CountyIntelligence) -> float:
        """Calculate overall geographic advantages score."""
        total = (
            intelligence.proximity_to_major_cities_score +
            intelligence.natural_features_score +
            intelligence.transportation_access_score +
            intelligence.climate_advantages_score
        )

        # Normalize to 0-100 scale
        normalized = max(0, min(100, total * (100 / 120)))
        return round(normalized, 1)

    def _calculate_timing_score(self, intelligence: CountyIntelligence) -> float:
        """Calculate overall market timing score."""
        total = (
            intelligence.development_trends_score +
            intelligence.real_estate_activity_score +
            intelligence.investment_momentum_score +
            intelligence.infrastructure_development_score
        )

        # Normalize to 0-100 scale
        normalized = max(0, min(100, total * (100 / 140)))
        return round(normalized, 1)

    def _calculate_distance(self, coords1: Tuple[float, float], coords2: Tuple[float, float]) -> float:
        """Calculate distance between two coordinate points in miles."""
        lat1, lon1 = coords1
        lat2, lon2 = coords2

        # Haversine formula for distance calculation
        R = 3959  # Earth's radius in miles

        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat/2) * math.sin(dlat/2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon/2) * math.sin(dlon/2))

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c

        return distance

    def _calculate_confidence_level(self, county_name: str) -> float:
        """Calculate confidence level for the analysis."""
        confidence = 0.7  # Base confidence

        # Higher confidence for well-known metro areas
        if county_name in self.metro_counties:
            confidence += 0.2

        # Higher confidence for counties with detailed data
        if county_name in self.natural_feature_counties:
            confidence += 0.1

        return min(1.0, confidence)


def analyze_county_intelligence(county_name: str) -> Dict[str, float]:
    """
    Convenience function to analyze a single county.

    Args:
        county_name: Alabama county name

    Returns:
        Dictionary with all county intelligence scores
    """
    analyzer = CountyIntelligenceAnalyzer()
    intelligence = analyzer.analyze_county(county_name)

    return {
        'median_income_score': intelligence.median_income_score,
        'unemployment_score': intelligence.unemployment_score,
        'population_growth_score': intelligence.population_growth_score,
        'economic_diversity_score': intelligence.economic_diversity_score,
        'proximity_to_major_cities_score': intelligence.proximity_to_major_cities_score,
        'natural_features_score': intelligence.natural_features_score,
        'transportation_access_score': intelligence.transportation_access_score,
        'climate_advantages_score': intelligence.climate_advantages_score,
        'development_trends_score': intelligence.development_trends_score,
        'real_estate_activity_score': intelligence.real_estate_activity_score,
        'investment_momentum_score': intelligence.investment_momentum_score,
        'infrastructure_development_score': intelligence.infrastructure_development_score,
        'county_market_score': intelligence.county_market_score,
        'geographic_score': intelligence.geographic_score,
        'market_timing_score': intelligence.market_timing_score,
        'confidence_level': intelligence.confidence_level
    }


if __name__ == "__main__":
    # Test county intelligence analysis
    test_counties = ['Baldwin', 'Jefferson', 'Madison', 'Mobile', 'Tuscaloosa', 'Shelby', 'Lee']

    analyzer = CountyIntelligenceAnalyzer()

    print("=== COUNTY INTELLIGENCE ANALYSIS TEST ===")
    for county in test_counties:
        intelligence = analyzer.analyze_county(county)
        print(f"\n{county} County:")
        print(f"  Market Score: {intelligence.county_market_score}")
        print(f"  Geographic Score: {intelligence.geographic_score}")
        print(f"  Timing Score: {intelligence.market_timing_score}")
        print(f"  Economic Diversity: {intelligence.economic_diversity_score}")
        print(f"  Natural Features: {intelligence.natural_features_score}")
        print(f"  Investment Momentum: {intelligence.investment_momentum_score}")
        print(f"  Confidence: {intelligence.confidence_level:.1%}")