#!/usr/bin/env python3
"""
Test the API directly with detailed error logging
"""

import requests
import json
import traceback

def test_api_direct():
    """Test the API directly to see the exact error."""

    # Sample data from watchlist.csv
    test_data = {
        "operation": "create",
        "properties": [{
            'parcel_id': '560808340001020017',
            'county': 'Randolph',
            'amount': 2726.19,
            'acreage': 0.005,
            'description': 'LOT 6 CHIMNEY COVE AT LAKE WEDOWEE CABINET B SLIDE',
            'owner_name': 'SIMPKINS RANDY',
            'year_sold': '2019'
        }]
    }

    print("Testing API directly...")
    print("=" * 50)
    print(f"Sending data: {json.dumps(test_data, indent=2)}")

    try:
        # Use the same authentication as the import script
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent
        sys.path.insert(0, str(project_root))
        from config.security import create_secure_headers

        headers = create_secure_headers()
        headers["Device-ID"] = "test_device"

        response = requests.post(
            "http://localhost:8001/api/v1/properties/bulk",
            headers=headers,
            data=json.dumps(test_data),
            params={"device_id": "test_device"},
            timeout=30
        )

        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")

        if response.status_code == 200:
            result = response.json()
            print(f"Success response: {json.dumps(result, indent=2)}")
        else:
            print(f"Error response: {response.text}")

    except Exception as e:
        print(f"Request failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_api_direct()