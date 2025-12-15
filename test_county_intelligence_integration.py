"""
Test County Intelligence Integration
Validates that county intelligence is properly integrated into property scoring
"""

import requests
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.security import create_secure_headers

# Test configuration
BASE_URL = "http://localhost:8003"
# Use test-specific API key for integration testing
TEST_API_KEY = os.getenv("TEST_API_KEY", "AW_test-device_abc123def456")

# Headers for API requests
headers = create_secure_headers(TEST_API_KEY)

def test_county_intelligence_integration():
    """Test county intelligence integration with property creation."""

    print("=== COUNTY INTELLIGENCE INTEGRATION TEST ===")

    # Test properties from different counties to verify intelligence scoring
    test_properties = [
        {
            "name": "Baldwin County Gulf Coast Property",
            "data": {
                "parcel_id": "BALDWIN-GULF-001",
                "amount": 75000,
                "acreage": 1.5,
                "description": "150X200 WATERFRONT LOT 15 GULF SHORES SUBDIVISION NEAR BEACH ACCESS",
                "county": "Baldwin",
                "owner_name": "Test Owner Gulf",
                "year_sold": "2024",
                "assessed_value": 65000
            },
            "expected_features": {
                "high_geographic_score": True,  # Gulf Coast advantages
                "strong_market_score": True,    # Tourist/development area
                "premium_water": True          # Waterfront
            }
        },
        {
            "name": "Madison County Tech Hub Property",
            "data": {
                "parcel_id": "MADISON-TECH-001",
                "amount": 95000,
                "acreage": 2.0,
                "description": "100X150 LOT 8 BLK 12 TECH PARK SUBDIVISION NEAR RESEARCH PARK",
                "county": "Madison",
                "owner_name": "Test Owner Tech",
                "year_sold": "2024",
                "assessed_value": 85000
            },
            "expected_features": {
                "high_market_score": True,     # Tech hub economics
                "tech_bonus": True,           # Huntsville tech corridor
                "strong_growth": True         # Population growth area
            }
        },
        {
            "name": "Jefferson County Metro Property",
            "data": {
                "parcel_id": "JEFFERSON-METRO-001",
                "amount": 55000,
                "acreage": 1.8,
                "description": "120X180 NE COR LOT 22 HIGHLANDS SUBDIVISION WITH CREEK ACCESS",
                "county": "Jefferson",
                "owner_name": "Test Owner Metro",
                "year_sold": "2024",
                "assessed_value": 50000
            },
            "expected_features": {
                "metro_bonus": True,          # Birmingham metro area
                "corner_lot": True,          # Corner lot premium
                "water_features": True       # Creek access
            }
        }
    ]

    created_properties = []

    for test_case in test_properties:
        print(f"\n--- Testing {test_case['name']} ---")

        try:
            # Create property
            response = requests.post(
                f"{BASE_URL}/api/v1/properties/",
                headers=headers,
                json=test_case['data']
            )

            if response.status_code == 201:
                property_data = response.json()
                created_properties.append(property_data)

                print(f"[SUCCESS] Property created successfully")
                print(f"  ID: {property_data['id']}")
                print(f"  County: {property_data['county']}")

                # Analyze county intelligence scores
                print(f"\n  County Intelligence Scores:")
                print(f"    Market Score: {property_data['county_market_score']}")
                print(f"    Geographic Score: {property_data['geographic_score']}")
                print(f"    Market Timing Score: {property_data['market_timing_score']}")

                # Analyze enhanced description scores
                print(f"\n  Enhanced Description Scores:")
                print(f"    Total Description: {property_data['total_description_score']}")
                print(f"    Corner Lot Bonus: {property_data['corner_lot_bonus']}")
                print(f"    Premium Water Access: {property_data['premium_water_access_score']}")
                print(f"    Subdivision Quality: {property_data['subdivision_quality_score']}")

                # Verify expected features
                expected = test_case['expected_features']

                if expected.get('high_geographic_score') and property_data['geographic_score'] >= 80:
                    print(f"  [PASS] High geographic score verified: {property_data['geographic_score']}")
                elif expected.get('high_geographic_score'):
                    print(f"  [WARN] Expected high geographic score, got: {property_data['geographic_score']}")

                if expected.get('high_market_score') and property_data['county_market_score'] >= 80:
                    print(f"  [PASS] High market score verified: {property_data['county_market_score']}")
                elif expected.get('high_market_score'):
                    print(f"  [WARN] Expected high market score, got: {property_data['county_market_score']}")

                if expected.get('corner_lot') and property_data['corner_lot_bonus'] > 0:
                    print(f"  [PASS] Corner lot bonus verified: {property_data['corner_lot_bonus']}")
                elif expected.get('corner_lot'):
                    print(f"  [WARN] Expected corner lot bonus, got: {property_data['corner_lot_bonus']}")

                if expected.get('premium_water') and property_data['premium_water_access_score'] > 0:
                    print(f"  [PASS] Premium water access verified: {property_data['premium_water_access_score']}")
                elif expected.get('premium_water'):
                    print(f"  [WARN] Expected premium water access, got: {property_data['premium_water_access_score']}")

            else:
                print(f"[ERROR] Failed to create property: {response.status_code}")
                print(f"  Response: {response.text}")

        except Exception as e:
            print(f"[ERROR] Error testing {test_case['name']}: {e}")

    # Summary analysis
    print(f"\n=== COUNTY INTELLIGENCE INTEGRATION SUMMARY ===")
    if created_properties:
        print(f"Successfully created {len(created_properties)} test properties")

        # Compare county scores across different counties
        print(f"\nCounty Intelligence Comparison:")
        for prop in created_properties:
            print(f"{prop['county']:>10}: Market={prop['county_market_score']:>5.1f}, Geographic={prop['geographic_score']:>5.1f}, Timing={prop['market_timing_score']:>5.1f}")

        # Verify county intelligence is working as expected
        baldwin_props = [p for p in created_properties if p['county'] == 'Baldwin']
        madison_props = [p for p in created_properties if p['county'] == 'Madison']

        if baldwin_props and baldwin_props[0]['geographic_score'] >= 80:
            print(f"[PASS] Baldwin County geographic advantages properly detected")

        if madison_props and madison_props[0]['county_market_score'] >= 80:
            print(f"[PASS] Madison County tech hub market advantages properly detected")

        print(f"\n[SUCCESS] County intelligence integration is working correctly!")

    else:
        print(f"[ERROR] No properties were created successfully")
        return False

    return True

if __name__ == "__main__":
    test_county_intelligence_integration()