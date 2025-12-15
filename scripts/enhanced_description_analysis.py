"""
Enhanced Legal Description Intelligence Module
Alabama Auction Watcher - Phase 1 Enhancement

This module extracts detailed property intelligence from legal descriptions
to significantly improve investment scoring accuracy.

Author: Claude Code AI Assistant
Date: 2025-09-19
"""

import re
from typing import Dict
import pandas as pd
from dataclasses import dataclass

@dataclass
class PropertyIntelligence:
    """Container for extracted property intelligence."""
    # Shape & Size Intelligence
    lot_dimensions_score: float = 0.0
    shape_efficiency_score: float = 0.0
    corner_lot_bonus: float = 0.0
    irregular_shape_penalty: float = 0.0

    # Access & Location Features
    subdivision_quality_score: float = 0.0
    road_access_score: float = 0.0
    location_type_score: float = 0.0

    # Legal Complexity Risk
    title_complexity_score: float = 0.0
    survey_requirement_score: float = 0.0

    # Enhanced Water Features
    premium_water_access_score: float = 0.0

    # Overall Description Intelligence Score
    total_description_score: float = 0.0


class EnhancedDescriptionAnalyzer:
    """Advanced property description analysis for investment intelligence."""

    def __init__(self):
        """Initialize the analyzer with pattern definitions."""
        self._initialize_patterns()
        self._initialize_scoring_weights()

    def _initialize_patterns(self):
        """Define regex patterns for extracting property features."""

        # Dimension patterns for shape analysis
        self.dimension_patterns = {
            'standard_dimensions': re.compile(r'(\d+\.?\d*)\s*[\'\"]*\s*[X×x]\s*(\d+\.?\d*)', re.IGNORECASE),
            'feet_dimensions': re.compile(r'(\d+)\'?\s*[X×x]\s*(\d+)\'?', re.IGNORECASE),
            'complex_dimensions': re.compile(r'(\d+\.?\d*)\s*[\'\"]*\s*[X×x]\s*(\d+\.?\d*)\s*[\'\"]*', re.IGNORECASE)
        }

        # Property shape and location indicators
        self.shape_patterns = {
            'irregular': re.compile(r'\bIRR\b|\birregular\b', re.IGNORECASE),
            'corner': re.compile(r'\bCOR\b|\bcorner\b', re.IGNORECASE),
            'partial': re.compile(r'\bPT\b|\bpart\b|\bpartial\b', re.IGNORECASE),
            'frontage': re.compile(r'(\d+\.?\d*)\s*[\'\"]*\s*frontage', re.IGNORECASE)
        }

        # Subdivision and location quality indicators
        self.subdivision_patterns = {
            'premium': [
                r'\blakefront\b', r'\bwater\s*view\b', r'\bcreek\s*side\b',
                r'\bpark\s*view\b', r'\bhighlands?\b', r'\bestate\b', r'\bmanor\b'
            ],
            'standard': [
                r'\bsubdivision\b', r'\bsubd?\b', r'\badd\b', r'\baddition\b',
                r'\bhills?\b', r'\bmeadows?\b', r'\bgrove\b'
            ],
            'industrial': [
                r'\bfactory\b', r'\bindustrial\b', r'\bcommercial\b',
                r'\bwarehouse\b', r'\bplant\b'
            ],
            'rural': [
                r'\brural\b', r'\bfarm\b', r'\bagricultural\b', r'\bacres?\b'
            ]
        }

        # Road and access patterns
        self.access_patterns = {
            'named_road': re.compile(r'\b\w+\s+(road|rd|street|st|avenue|ave|drive|dr|lane|ln|way|blvd|boulevard)\b', re.IGNORECASE),
            'highway': re.compile(r'\bhighway\b|\bhwy\b|\bus\s*\d+\b|\bstate\s*route\b', re.IGNORECASE),
            'private': re.compile(r'\bprivate\b|\baccess\s*easement\b', re.IGNORECASE)
        }

        # Legal complexity indicators
        self.complexity_patterns = {
            'metes_bounds': re.compile(r'\bbeg\b|\bpob\b|\brun\b|\bthence\b|\bbearing\b', re.IGNORECASE),
            'survey_required': re.compile(r'\bsurvey\b|\bresur\b|\bplat\b|\bpb\s*\d+\b', re.IGNORECASE),
            'easements': re.compile(r'\beasement\b|\bright\s*of\s*way\b|\butility\b', re.IGNORECASE),
            'restrictions': re.compile(r'\brestriction\b|\bcovenant\b|\bzoning\b', re.IGNORECASE)
        }

        # Enhanced water feature patterns
        self.premium_water_patterns = {
            'waterfront': re.compile(r'\bwaterfront\b|\blakefront\b|\briver\s*front\b|\bocean\s*front\b', re.IGNORECASE),
            'water_view': re.compile(r'\bwater\s*view\b|\blake\s*view\b|\briver\s*view\b', re.IGNORECASE),
            'water_access': re.compile(r'\bwater\s*access\b|\blake\s*access\b|\bpond\s*access\b', re.IGNORECASE),
            'creek_frontage': re.compile(r'\bcreek\s*frontage\b|\bstream\s*frontage\b', re.IGNORECASE),
            'near_water': re.compile(r'\bnear\s+(spring|creek|lake|pond|stream|river)\b', re.IGNORECASE)
        }

    def _initialize_scoring_weights(self):
        """Define scoring weights for different features."""

        self.scoring_weights = {
            # Shape efficiency scoring
            'optimal_ratio_bonus': 10.0,  # For lots close to golden ratio
            'square_bonus': 8.0,          # Square lots are efficient
            'long_narrow_penalty': -5.0,  # Long narrow lots are less desirable

            # Size and corner bonuses
            'corner_lot_bonus': 15.0,     # Corner lots have premium value
            'irregular_penalty': -8.0,    # Irregular shapes reduce value
            'partial_lot_penalty': -12.0, # Partial lots have complications

            # Subdivision quality
            'premium_subdivision': 20.0,   # Lakefront, water view, estates
            'standard_subdivision': 5.0,   # Regular subdivisions
            'industrial_penalty': -10.0,  # Industrial areas less desirable
            'rural_bonus': 3.0,           # Rural properties can be desirable

            # Access quality
            'named_road_bonus': 8.0,      # Named roads better than coordinates
            'highway_access_bonus': 12.0, # Highway access valuable
            'private_access_penalty': -5.0, # Private access complications

            # Legal complexity (risk factors)
            'metes_bounds_penalty': -3.0,  # Complex legal descriptions
            'survey_penalty': -5.0,        # Survey requirements add cost
            'easement_penalty': -7.0,      # Easements reduce value
            'restriction_penalty': -4.0,   # Restrictions limit use

            # Premium water features
            'waterfront_premium': 25.0,    # Direct water frontage
            'water_view_premium': 15.0,    # Water views valuable
            'water_access_premium': 12.0,  # Water access valuable
            'creek_frontage_premium': 18.0, # Creek frontage premium
            'near_water_bonus': 8.0        # Near water still valuable
        }

    def analyze_description(self, description: str) -> PropertyIntelligence:
        """
        Analyze a property description and extract intelligence.

        Args:
            description: The legal property description

        Returns:
            PropertyIntelligence object with all extracted features
        """
        if not description or pd.isna(description):
            return PropertyIntelligence()

        intelligence = PropertyIntelligence()
        description = str(description).strip()

        # Analyze each category
        intelligence.lot_dimensions_score = self._analyze_lot_dimensions(description)
        intelligence.shape_efficiency_score = self._analyze_shape_efficiency(description)
        intelligence.corner_lot_bonus = self._analyze_corner_lot(description)
        intelligence.irregular_shape_penalty = self._analyze_irregular_shape(description)

        intelligence.subdivision_quality_score = self._analyze_subdivision_quality(description)
        intelligence.road_access_score = self._analyze_road_access(description)
        intelligence.location_type_score = self._analyze_location_type(description)

        intelligence.title_complexity_score = self._analyze_title_complexity(description)
        intelligence.survey_requirement_score = self._analyze_survey_requirements(description)

        intelligence.premium_water_access_score = self._analyze_premium_water_features(description)

        # Calculate total score
        intelligence.total_description_score = self._calculate_total_score(intelligence)

        return intelligence

    def _analyze_lot_dimensions(self, description: str) -> float:
        """Analyze lot dimensions and calculate dimension score."""
        score = 0.0

        # Extract dimensions
        for pattern_name, pattern in self.dimension_patterns.items():
            match = pattern.search(description)
            if match:
                try:
                    width = float(match.group(1))
                    length = float(match.group(2))

                    # Calculate area (assuming feet)
                    area_sq_ft = width * length

                    # Size scoring (larger lots generally better, but not too large)
                    if 2000 <= area_sq_ft <= 50000:  # 0.05 to 1.15 acres
                        score += 5.0
                    elif 500 <= area_sq_ft <= 100000:  # Still reasonable
                        score += 2.0

                    # Shape ratio scoring (closer to square is better)
                    ratio = max(width, length) / min(width, length)
                    if ratio <= 1.5:  # Nearly square
                        score += self.scoring_weights['square_bonus']
                    elif ratio <= 2.0:  # Reasonable rectangle
                        score += self.scoring_weights['optimal_ratio_bonus'] / 2
                    elif ratio >= 4.0:  # Long and narrow
                        score += self.scoring_weights['long_narrow_penalty']

                    break  # Use first match found

                except (ValueError, TypeError):
                    continue

        return score

    def _analyze_shape_efficiency(self, description: str) -> float:
        """Analyze shape efficiency indicators."""
        score = 0.0

        # Look for frontage information
        frontage_match = self.shape_patterns['frontage'].search(description)
        if frontage_match:
            try:
                frontage = float(frontage_match.group(1))
                if frontage >= 100:  # Good frontage
                    score += 8.0
                elif frontage >= 50:  # Adequate frontage
                    score += 4.0
                else:  # Limited frontage
                    score -= 2.0
            except (ValueError, TypeError):
                pass

        return score

    def _analyze_corner_lot(self, description: str) -> float:
        """Check for corner lot indicators."""
        if self.shape_patterns['corner'].search(description):
            return self.scoring_weights['corner_lot_bonus']
        return 0.0

    def _analyze_irregular_shape(self, description: str) -> float:
        """Analyze irregular shape penalties."""
        score = 0.0

        if self.shape_patterns['irregular'].search(description):
            score += self.scoring_weights['irregular_penalty']

        if self.shape_patterns['partial'].search(description):
            score += self.scoring_weights['partial_lot_penalty']

        return score

    def _analyze_subdivision_quality(self, description: str) -> float:
        """Analyze subdivision quality indicators."""
        score = 0.0

        # Check premium subdivisions
        for pattern in self.subdivision_patterns['premium']:
            if re.search(pattern, description, re.IGNORECASE):
                score += self.scoring_weights['premium_subdivision']
                break

        # Check standard subdivisions
        if score == 0.0:  # Only if not premium
            for pattern in self.subdivision_patterns['standard']:
                if re.search(pattern, description, re.IGNORECASE):
                    score += self.scoring_weights['standard_subdivision']
                    break

        # Check industrial (penalty)
        for pattern in self.subdivision_patterns['industrial']:
            if re.search(pattern, description, re.IGNORECASE):
                score += self.scoring_weights['industrial_penalty']
                break

        # Check rural (bonus)
        for pattern in self.subdivision_patterns['rural']:
            if re.search(pattern, description, re.IGNORECASE):
                score += self.scoring_weights['rural_bonus']
                break

        return score

    def _analyze_road_access(self, description: str) -> float:
        """Analyze road access quality."""
        score = 0.0

        if self.access_patterns['highway'].search(description):
            score += self.scoring_weights['highway_access_bonus']
        elif self.access_patterns['named_road'].search(description):
            score += self.scoring_weights['named_road_bonus']

        if self.access_patterns['private'].search(description):
            score += self.scoring_weights['private_access_penalty']

        return score

    def _analyze_location_type(self, description: str) -> float:
        """Analyze location type indicators."""
        # This could be expanded with more sophisticated location analysis
        # For now, incorporated into subdivision quality
        return 0.0

    def _analyze_title_complexity(self, description: str) -> float:
        """Analyze title complexity risk factors."""
        score = 0.0

        if self.complexity_patterns['metes_bounds'].search(description):
            score += self.scoring_weights['metes_bounds_penalty']

        if self.complexity_patterns['easements'].search(description):
            score += self.scoring_weights['easement_penalty']

        if self.complexity_patterns['restrictions'].search(description):
            score += self.scoring_weights['restriction_penalty']

        return score

    def _analyze_survey_requirements(self, description: str) -> float:
        """Analyze survey requirement indicators."""
        if self.complexity_patterns['survey_required'].search(description):
            return self.scoring_weights['survey_penalty']
        return 0.0

    def _analyze_premium_water_features(self, description: str) -> float:
        """Analyze premium water feature access."""
        score = 0.0

        if self.premium_water_patterns['waterfront'].search(description):
            score += self.scoring_weights['waterfront_premium']
        elif self.premium_water_patterns['creek_frontage'].search(description):
            score += self.scoring_weights['creek_frontage_premium']
        elif self.premium_water_patterns['water_view'].search(description):
            score += self.scoring_weights['water_view_premium']
        elif self.premium_water_patterns['water_access'].search(description):
            score += self.scoring_weights['water_access_premium']
        elif self.premium_water_patterns['near_water'].search(description):
            score += self.scoring_weights['near_water_bonus']

        return score

    def _calculate_total_score(self, intelligence: PropertyIntelligence) -> float:
        """Calculate the total description intelligence score."""
        total = (
            intelligence.lot_dimensions_score +
            intelligence.shape_efficiency_score +
            intelligence.corner_lot_bonus +
            intelligence.irregular_shape_penalty +
            intelligence.subdivision_quality_score +
            intelligence.road_access_score +
            intelligence.location_type_score +
            intelligence.title_complexity_score +
            intelligence.survey_requirement_score +
            intelligence.premium_water_access_score
        )

        # Normalize to 0-100 scale
        # Theoretical max: ~75 points, min: ~-40 points
        # Shift and scale to 0-100
        normalized = max(0, min(100, (total + 50) * (100 / 125)))

        return round(normalized, 1)


def analyze_property_description(description: str) -> Dict[str, float]:
    """
    Convenience function to analyze a single property description.

    Args:
        description: Property legal description

    Returns:
        Dictionary with all scoring factors
    """
    analyzer = EnhancedDescriptionAnalyzer()
    intelligence = analyzer.analyze_description(description)

    return {
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
        'total_description_score': intelligence.total_description_score
    }


if __name__ == "__main__":
    # Test with sample descriptions
    test_descriptions = [
        "25X125 FACTORY ADDN BLK 24 LOT 24",
        "70X110 IRR NE COR SEC 31 RUN W740'S S200' TO POB",
        "LOT 2 BLK 5 CREEK SUBDIVISION 75' X 150' NEAR SPRING",
        "Beautiful creek frontage test property",
        "LOT 12 WATER VIEW 2.1 AC WITH STREAM"
    ]

    analyzer = EnhancedDescriptionAnalyzer()

    print("=== ENHANCED DESCRIPTION ANALYSIS TEST ===")
    for i, desc in enumerate(test_descriptions, 1):
        intelligence = analyzer.analyze_description(desc)
        print(f"\n{i}. {desc}")
        print(f"   Total Score: {intelligence.total_description_score}")
        print(f"   Corner Bonus: {intelligence.corner_lot_bonus}")
        print(f"   Water Premium: {intelligence.premium_water_access_score}")
        print(f"   Subdivision: {intelligence.subdivision_quality_score}")
        print(f"   Complexity: {intelligence.title_complexity_score}")