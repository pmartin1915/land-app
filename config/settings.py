"""
Configuration settings for Alabama Auction Watcher

This module contains all configurable parameters including filtering criteria,
water feature keywords, fee calculations, and column mappings for flexible CSV parsing.
"""

# =============================================================================
# FILTERING DEFAULTS
# =============================================================================

# Property filtering criteria
MIN_ACRES = 0.001
MAX_ACRES = 500.0
MAX_PRICE = 20000.0

# =============================================================================
# FEE CALCULATION SETTINGS
# =============================================================================

# Standard fees associated with tax sale purchases
RECORDING_FEE = 35.0  # Fixed recording fee
COUNTY_FEE_PERCENT = 0.05  # 5% county fee on purchase price
MISC_FEES = 100.0  # Estimated miscellaneous fees (title search, etc.)

# =============================================================================
# WATER FEATURE KEYWORDS
# =============================================================================

# Primary water feature keywords (highest weight)
PRIMARY_WATER_KEYWORDS = [
    'creek', 'stream', 'river', 'lake', 'pond', 'spring'
]

# Secondary water feature keywords (medium weight)
SECONDARY_WATER_KEYWORDS = [
    'branch', 'run', 'brook', 'tributary', 'wetland', 'marsh'
]

# Tertiary water feature keywords (lowest weight)
TERTIARY_WATER_KEYWORDS = [
    'water', 'aquatic', 'riparian', 'shore', 'bank', 'waterfront'
]

# Water keyword scoring weights
WATER_SCORE_WEIGHTS = {
    'primary': 3.0,
    'secondary': 2.0,
    'tertiary': 1.0
}

# =============================================================================
# COLUMN MAPPINGS FOR FLEXIBLE CSV PARSING
# =============================================================================

# Possible column names for key fields (case-insensitive matching)
COLUMN_MAPPINGS = {
    'parcel_id': [
        'parcel id', 'parcel_id', 'parcel number', 'parcel_number',
        'cs number', 'cs_number', 'parcel', 'pin', 'tax id'
    ],
    'amount': [
        'amount bid at tax sale', 'amount_bid_at_tax_sale', 'bid amount',
        'bid_amount', 'sale price', 'sale_price', 'amount', 'price',
        'tax sale amount', 'minimum bid'
    ],
    'assessed_value': [
        'assessed value', 'assessed_value', 'appraised value',
        'appraised_value', 'market value', 'market_value', 'value'
    ],
    'description': [
        'description', 'property description', 'property_description',
        'legal description', 'legal_description', 'location'
    ],
    'acreage': [
        'acreage', 'acres', 'acre', 'size', 'area', 'lot size', 'lot_size'
    ],
    'year_sold': [
        'year sold', 'year_sold', 'sale year', 'sale_year', 'year'
    ],
    'owner_name': [
        'name', 'owner name', 'owner_name', 'owner', 'property owner'
    ],
    'county': [
        'county', 'county name', 'county_name'
    ]
}

# =============================================================================
# INVESTMENT SCORING PARAMETERS
# =============================================================================

# Weights for composite investment score calculation
INVESTMENT_SCORE_WEIGHTS = {
    'price_per_acre': 0.4,  # Lower price per acre is better
    'acreage_preference': 0.3,  # Prefer certain acreage ranges
    'water_features': 0.2,  # Water features add value
    'assessed_value_ratio': 0.1  # Ratio of bid to assessed value
}

# Preferred acreage range for scoring (peak score at these values)
PREFERRED_MIN_ACRES = 2.0
PREFERRED_MAX_ACRES = 4.0

# =============================================================================
# DATA PARSING SETTINGS
# =============================================================================

# Common delimiters to try when parsing CSV files
CSV_DELIMITERS = [',', '\t', '|', ';']

# Encoding options to try when reading files
FILE_ENCODINGS = ['utf-8', 'latin-1', 'cp1252']

# Maximum price per acre to consider reasonable (outlier detection)
MAX_REASONABLE_PRICE_PER_ACRE = 50000.0

# =============================================================================
# ACREAGE PARSING PATTERNS
# =============================================================================

# Regex patterns for extracting acreage from legal descriptions
ACREAGE_PATTERNS = {
    # Direct acreage mentions: "2.5 AC", "1.25 ACRES", etc.
    'direct_acres': r'(\d+\.?\d*)\s*(?:AC|ACRE|ACRES)\b',

    # Square footage: "43560 SF", "87120 SQ FT", etc. (43560 SF = 1 acre)
    'square_feet': r'(\d+\.?\d*)\s*(?:SF|SQ\.?\s*FT|SQUARE\s*FEET)\b',

    # Rectangular lots: "100' X 200'", "75 x 150", etc.
    'rectangular': r'(\d+\.?\d*)\s*[\'\"X×x]\s*(\d+\.?\d*)',

    # Fractional acres: "1/2 ACRE", "3/4 AC", etc.
    'fractional': r'(\d+)/(\d+)\s*(?:AC|ACRE|ACRES)\b'
}

# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

# Column order for output CSV files
OUTPUT_COLUMNS = [
    'parcel_id', 'county', 'amount', 'acreage', 'price_per_acre',
    'estimated_all_in_cost', 'water_score', 'investment_score',
    'should_bid', 'max_bid_amount', 'bid_reason',
    'assessed_value', 'description', 'owner_name', 'year_sold'
]

# Display formatting for currency and numbers
CURRENCY_FORMAT = "${:,.2f}"
ACREAGE_FORMAT = "{:.2f}"
SCORE_FORMAT = "{:.1f}"

# =============================================================================
# VALIDATION RULES
# =============================================================================

# Data quality validation thresholds
MIN_REASONABLE_PRICE = 1.0  # Minimum reasonable price
MAX_REASONABLE_PRICE = 1000000.0  # Maximum reasonable price
MIN_REASONABLE_ACRES = 0.01  # Minimum reasonable acreage
MAX_REASONABLE_ACRES = 1000.0  # Maximum reasonable acreage

# =============================================================================
# STREAMLIT UI SETTINGS
# =============================================================================

# Default filter ranges for Streamlit UI
DEFAULT_PRICE_RANGE = (0.0, MAX_PRICE)
DEFAULT_ACREAGE_RANGE = (MIN_ACRES, MAX_ACRES)

# Chart colors
CHART_COLORS = {
    'water_features': '#1f77b4',  # Blue
    'no_water': '#ff7f0e',  # Orange
    'primary': '#2ca02c',  # Green
    'secondary': '#d62728'  # Red
}
