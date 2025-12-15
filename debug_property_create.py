#!/usr/bin/env python3
"""
Debug script to test PropertyCreate model directly
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Test PropertyCreate model directly
try:
    from backend_api.models.property import PropertyCreate

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

    print("Testing PropertyCreate model instantiation...")
    print("=" * 50)
    print(f"Test data: {test_data}")

    # Try to create PropertyCreate instance
    try:
        property_instance = PropertyCreate(**test_data)
        print("SUCCESS: PropertyCreate instance created successfully!")
        print(f"Created: {property_instance}")
    except Exception as e:
        print(f"ERROR: Failed to create PropertyCreate instance: {e}")
        import traceback
        traceback.print_exc()

except ImportError as e:
    print(f"ERROR: Failed to import PropertyCreate: {e}")
    import traceback
    traceback.print_exc()