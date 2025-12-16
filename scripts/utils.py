"""
Utility functions for Alabama Auction Watcher

This module provides helper functions for data parsing, normalization,
and validation used throughout the application.
"""

import re
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

from config.settings import (
    PRIMARY_WATER_KEYWORDS, SECONDARY_WATER_KEYWORDS, TERTIARY_WATER_KEYWORDS,
    WATER_SCORE_WEIGHTS, ACREAGE_PATTERNS, COLUMN_MAPPINGS,
    MIN_REASONABLE_PRICE, MAX_REASONABLE_PRICE,
    MIN_REASONABLE_ACRES, MAX_REASONABLE_ACRES,
    MAX_REASONABLE_PRICE_PER_ACRE
)


def detect_csv_delimiter(file_path: str, sample_size: int = 1024) -> str:
    """
    Detect the delimiter used in a CSV file by analyzing a sample.

    Args:
        file_path: Path to the CSV file
        sample_size: Number of bytes to read for analysis

    Returns:
        The detected delimiter character
    """
    import csv

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        sample = f.read(sample_size)

    try:
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(sample).delimiter
        return delimiter
    except:
        # Fallback to comma if detection fails
        return ','


def find_column_mapping(df_columns: List[str], target_field: str) -> Optional[str]:
    """
    Find the best matching column name for a target field using fuzzy matching.

    Args:
        df_columns: List of column names from the DataFrame
        target_field: The target field to find (e.g., 'parcel_id', 'amount')

    Returns:
        The matching column name or None if no match found
    """
    if target_field not in COLUMN_MAPPINGS:
        return None

    possible_names = COLUMN_MAPPINGS[target_field]
    df_columns_lower = [col.lower().strip() for col in df_columns]

    # Exact match first
    for possible_name in possible_names:
        if possible_name.lower() in df_columns_lower:
            idx = df_columns_lower.index(possible_name.lower())
            return df_columns[idx]

    # Partial match
    for possible_name in possible_names:
        for i, col in enumerate(df_columns_lower):
            if possible_name.lower() in col or col in possible_name.lower():
                return df_columns[i]

    return None


def normalize_price(price_str: Any) -> Optional[float]:
    """
    Normalize price strings to float values.

    Args:
        price_str: Price string (e.g., "$1,234.56", "1234", etc.)

    Returns:
        Normalized price as float or None if invalid
    """
    if pd.isna(price_str) or price_str is None:
        return None

    # Convert to string if not already
    price_str = str(price_str).strip()

    # Handle empty strings
    if not price_str or price_str.lower() in ['', 'n/a', 'na', 'null', 'none']:
        return None

    # Remove currency symbols, commas, and whitespace
    cleaned = re.sub(r'[$,\s]', '', price_str)

    try:
        price = float(cleaned)

        # Validate reasonable range
        if MIN_REASONABLE_PRICE <= price <= MAX_REASONABLE_PRICE:
            return price
        else:
            return None
    except ValueError:
        return None


def parse_acreage_from_description(description: str) -> Optional[float]:
    """
    Extract acreage information from legal descriptions using regex patterns.

    Args:
        description: Property legal description text

    Returns:
        Parsed acreage as float or None if not found
    """
    if pd.isna(description) or not isinstance(description, str):
        return None

    description = description.upper().strip()

    # Try direct acreage patterns first
    direct_match = re.search(ACREAGE_PATTERNS['direct_acres'], description, re.IGNORECASE)
    if direct_match:
        try:
            acres = float(direct_match.group(1))
            if MIN_REASONABLE_ACRES <= acres <= MAX_REASONABLE_ACRES:
                return acres
        except ValueError:
            pass

    # Try fractional acres
    fractional_match = re.search(ACREAGE_PATTERNS['fractional'], description, re.IGNORECASE)
    if fractional_match:
        try:
            numerator = float(fractional_match.group(1))
            denominator = float(fractional_match.group(2))
            if denominator != 0:
                acres = numerator / denominator
                if MIN_REASONABLE_ACRES <= acres <= MAX_REASONABLE_ACRES:
                    return acres
        except ValueError:
            pass

    # Try square footage conversion
    sf_match = re.search(ACREAGE_PATTERNS['square_feet'], description, re.IGNORECASE)
    if sf_match:
        try:
            sq_ft = float(sf_match.group(1))
            acres = sq_ft / 43560  # Convert square feet to acres
            if MIN_REASONABLE_ACRES <= acres <= MAX_REASONABLE_ACRES:
                return acres
        except ValueError:
            pass

    # Try rectangular dimensions with improved patterns
    # Pattern 1: Handles "75' X 150'", "75'X150'", "75X150", "75 X 150", "75 BY 150"
    dimension_patterns = [
        r'(\d+\.?\d*)\s*[\'\"]?\s*[Xx×BY]+\s*[\'\"]?\s*(\d+\.?\d*)',  # Flexible pattern
        r'(\d+\.?\d*)\s*[\'\"\-]\s*[Xx×]\s*[\'\"\-]\s*(\d+\.?\d*)',   # With dashes
        ACREAGE_PATTERNS['rectangular']  # Original pattern as fallback
    ]
    
    for pattern in dimension_patterns:
        rect_match = re.search(pattern, description, re.IGNORECASE)
        if rect_match:
            try:
                dim1 = float(rect_match.group(1))
                dim2 = float(rect_match.group(2))
                
                # Validate dimensions are reasonable for a lot (10-2000 feet)
                if (10 <= dim1 <= 2000) and (10 <= dim2 <= 2000):
                    sq_ft = dim1 * dim2
                    acres = sq_ft / 43560  # Convert square feet to acres
                    
                    # Validate calculated acreage is reasonable
                    if MIN_REASONABLE_ACRES <= acres <= MAX_REASONABLE_ACRES:
                        return acres
            except (ValueError, IndexError):
                continue

    # Fallback: Look for two consecutive numbers that could be dimensions
    # This catches cases like "LOT 100 200" or "PARCEL 75 150"
    number_pattern = r'\b(\d{2,4})\s+(\d{2,4})\b'
    number_matches = re.findall(number_pattern, description)
    
    for match in number_matches:
        try:
            dim1 = float(match[0])
            dim2 = float(match[1])
            
            # Only use if they look like lot dimensions (not parcel IDs, etc.)
            if (10 <= dim1 <= 2000) and (10 <= dim2 <= 2000):
                sq_ft = dim1 * dim2
                acres = sq_ft / 43560
                
                # Be more strict with fallback - must be in very reasonable range
                if 0.05 <= acres <= 10.0:  # 0.05 to 10 acres for fallback
                    return acres
        except (ValueError, IndexError):
            continue

    return None



def calculate_water_score(description: str) -> float:
    """
    Calculate water feature score based on keyword matching in description.

    Args:
        description: Property description text

    Returns:
        Water score (0.0 to max possible score)
    """
    if pd.isna(description) or not isinstance(description, str):
        return 0.0

    description_lower = description.lower()
    score = 0.0

    # Check primary keywords
    for keyword in PRIMARY_WATER_KEYWORDS:
        if keyword.lower() in description_lower:
            score += WATER_SCORE_WEIGHTS['primary']

    # Check secondary keywords
    for keyword in SECONDARY_WATER_KEYWORDS:
        if keyword.lower() in description_lower:
            score += WATER_SCORE_WEIGHTS['secondary']

    # Check tertiary keywords
    for keyword in TERTIARY_WATER_KEYWORDS:
        if keyword.lower() in description_lower:
            score += WATER_SCORE_WEIGHTS['tertiary']

    return score


def calculate_estimated_all_in_cost(bid_amount: float,
                                   recording_fee: float = 35.0,
                                   county_fee_percent: float = 0.05,
                                   misc_fees: float = 100.0) -> float:
    """
    Calculate estimated total cost including fees.

    Args:
        bid_amount: Original bid amount
        recording_fee: Fixed recording fee
        county_fee_percent: County fee as percentage of bid
        misc_fees: Miscellaneous fees estimate

    Returns:
        Estimated total all-in cost
    """
    if pd.isna(bid_amount) or bid_amount <= 0:
        return 0.0

    county_fee = bid_amount * county_fee_percent
    total_cost = bid_amount + recording_fee + county_fee + misc_fees

    return total_cost


def calculate_investment_score(price_per_acre: float,
                             acreage: float,
                             water_score: float,
                             assessed_value_ratio: float,
                             weights: Dict[str, float]) -> float:
    """
    Calculate composite investment score based on multiple factors.

    Args:
        price_per_acre: Price per acre
        acreage: Property acreage
        water_score: Water feature score
        assessed_value_ratio: Ratio of bid to assessed value
        weights: Dictionary of weights for each factor

    Returns:
        Composite investment score (higher is better)
    """
    # Validate inputs - return 0 for invalid properties
    if not isinstance(price_per_acre, (int, float)) or not np.isfinite(price_per_acre):
        price_per_acre = 0
    if not isinstance(acreage, (int, float)) or not np.isfinite(acreage) or acreage <= 0:
        return 0.0  # Invalid property - no acreage data
    if not isinstance(water_score, (int, float)) or not np.isfinite(water_score):
        water_score = 0
    if not isinstance(assessed_value_ratio, (int, float)) or not np.isfinite(assessed_value_ratio):
        assessed_value_ratio = 1.0
    
    score = 0.0

    # Price per acre score (lower is better, so invert)
    if price_per_acre > 0:
        # Normalize to 0-100 scale, with lower prices getting higher scores
        # Cap at minimum to prevent extremely low prices from dominating score
        price_per_acre = max(price_per_acre, 1.0)
        max_price_score = min(100, 10000 / price_per_acre)
        score += max_price_score * weights.get('price_per_acre', 0.0)

    # Acreage preference score (peak around 2-4 acres)
    if acreage > 0:
        from config.settings import PREFERRED_MIN_ACRES, PREFERRED_MAX_ACRES
        if PREFERRED_MIN_ACRES <= acreage <= PREFERRED_MAX_ACRES:
            acreage_score = 100  # Perfect score
        else:
            # Decrease score as we move away from preferred range
            if acreage < PREFERRED_MIN_ACRES:
                acreage_score = max(0, 100 * acreage / PREFERRED_MIN_ACRES)
            else:
                excess = acreage - PREFERRED_MAX_ACRES
                acreage_score = max(0, 100 - (excess * 10))  # Penalty for being too large
        score += acreage_score * weights.get('acreage_preference', 0.0)

    # Water features score
    water_normalized = min(100, water_score * 10)  # Normalize to 0-100
    score += water_normalized * weights.get('water_features', 0.0)

    # Assessed value ratio score (lower ratio is better - getting a bargain)
    if assessed_value_ratio > 0:
        ratio_score = min(100, 100 / assessed_value_ratio)  # Higher score for lower ratio
        score += ratio_score * weights.get('assessed_value_ratio', 0.0)

    return round(score, 1)


def validate_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate data quality and return summary statistics.

    Args:
        df: DataFrame to validate

    Returns:
        Dictionary with validation results and statistics
    """
    results = {
        'total_records': len(df),
        'issues': [],
        'warnings': []
    }

    # Check for required columns
    required_fields = ['parcel_id', 'amount', 'description']
    missing_required = [field for field in required_fields if field not in df.columns]
    if missing_required:
        results['issues'].append(f"Missing required columns: {missing_required}")

    # Check for empty critical fields
    if 'amount' in df.columns:
        null_amounts = df['amount'].isna().sum()
        if null_amounts > 0:
            results['warnings'].append(f"{null_amounts} records missing amount data")

    if 'parcel_id' in df.columns:
        null_parcels = df['parcel_id'].isna().sum()
        if null_parcels > 0:
            results['warnings'].append(f"{null_parcels} records missing parcel ID")

    # Check for acreage issues
    if 'acreage' in df.columns:
        zero_acreage = (df['acreage'] == 0).sum()
        null_acreage = df['acreage'].isna().sum()
        tiny_acreage = ((df['acreage'] > 0) & (df['acreage'] < 0.01)).sum()
        
        if zero_acreage > 0:
            pct = (zero_acreage / len(df)) * 100
            results['warnings'].append(f"{zero_acreage} records ({pct:.1f}%) have zero acreage")
        
        if null_acreage > 0:
            pct = (null_acreage / len(df)) * 100
            results['warnings'].append(f"{null_acreage} records ({pct:.1f}%) missing acreage")
            
        if tiny_acreage > 0:
            pct = (tiny_acreage / len(df)) * 100
            results['warnings'].append(f"{tiny_acreage} records ({pct:.1f}%) have very small acreage (<0.01 acres)")

    # Check for unrealistic price per acre values
    if 'price_per_acre' in df.columns:
        # Check for infinite values
        inf_ppa = np.isinf(df['price_per_acre']).sum()
        if inf_ppa > 0:
            results['issues'].append(f"{inf_ppa} records have infinite price per acre")
        
        # Check for extremely high values
        high_price_per_acre = (df['price_per_acre'] > MAX_REASONABLE_PRICE_PER_ACRE).sum()
        if high_price_per_acre > 0:
            pct = (high_price_per_acre / len(df)) * 100
            results['warnings'].append(
                f"{high_price_per_acre} records ({pct:.1f}%) have unusually high price per acre (>${MAX_REASONABLE_PRICE_PER_ACRE:,.0f})"
            )

    return results


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize a DataFrame with property data.

    Args:
        df: Raw DataFrame from CSV

    Returns:
        Cleaned DataFrame
    """
    df_clean = df.copy()

    # Strip whitespace from string columns
    string_columns = df_clean.select_dtypes(include=['object']).columns
    for col in string_columns:
        df_clean[col] = df_clean[col].astype(str).str.strip()
        # Replace common null representations
        df_clean[col] = df_clean[col].replace(['nan', 'NaN', 'null', 'NULL', 'None', 'NONE', ''], np.nan).infer_objects(copy=False)

    # Remove completely empty rows
    df_clean = df_clean.dropna(how='all')

    # Remove duplicate rows based on parcel_id if it exists
    if 'parcel_id' in df_clean.columns:
        df_clean = df_clean.drop_duplicates(subset=['parcel_id'], keep='first')

    return df_clean


def format_currency(amount: float) -> str:
    """Format amount as currency string."""
    if pd.isna(amount):
        return "N/A"
    return f"${amount:,.2f}"


def format_acreage(acres: float) -> str:
    """Format acreage with appropriate decimal places."""
    if pd.isna(acres):
        return "N/A"
    return f"{acres:.2f}"


def format_score(score: float) -> str:
    """Format score with one decimal place."""
    if pd.isna(score):
        return "N/A"
    return f"{score:.1f}"