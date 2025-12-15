#!/usr/bin/env python3
"""
Debug script to test individual field validation and find regex errors
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.validation import PropertyValidator

def test_individual_fields():
    """Test each field validation individually to isolate the regex error."""

    # Sample data from watchlist.csv
    test_data = {
        'parcel_id': '560808340001020017',
        'county': 'Randolph',
        'amount': 2726.19,
        'acreage': 0.005,
        'description': 'LOT 6 CHIMNEY COVE AT LAKE WEDOWEE CABINET B SLIDE',
        'owner_name': 'SIMPKINS RANDY',
        'year_sold': '2019'
    }

    print("Testing individual field validation...")
    print("=" * 50)

    # Test parcel_id
    try:
        print(f"Testing parcel_id: {test_data['parcel_id']}")
        result = PropertyValidator.validate_parcel_id(test_data['parcel_id'])
        print(f"  Result: {result.is_valid}, Errors: {result.errors}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Test county
    try:
        print(f"Testing county: {test_data['county']}")
        result = PropertyValidator.validate_county(test_data['county'])
        print(f"  Result: {result.is_valid}, Errors: {result.errors}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Test amount
    try:
        print(f"Testing amount: {test_data['amount']}")
        result = PropertyValidator.validate_amount(test_data['amount'])
        print(f"  Result: {result.is_valid}, Errors: {result.errors}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Test acreage
    try:
        print(f"Testing acreage: {test_data['acreage']}")
        result = PropertyValidator.validate_acreage(test_data['acreage'])
        print(f"  Result: {result.is_valid}, Errors: {result.errors}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Test description
    try:
        print(f"Testing description: {test_data['description']}")
        result = PropertyValidator.validate_description(test_data['description'])
        print(f"  Result: {result.is_valid}, Errors: {result.errors}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Test owner_name
    try:
        print(f"Testing owner_name: {test_data['owner_name']}")
        result = PropertyValidator.validate_owner_name(test_data['owner_name'])
        print(f"  Result: {result.is_valid}, Errors: {result.errors}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Test year_sold
    try:
        print(f"Testing year_sold: {test_data['year_sold']}")
        result = PropertyValidator.validate_year_sold(test_data['year_sold'])
        print(f"  Result: {result.is_valid}, Errors: {result.errors}")
    except Exception as e:
        print(f"  ERROR: {e}")

if __name__ == "__main__":
    test_individual_fields()