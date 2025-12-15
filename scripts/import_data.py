import pandas as pd
import requests
import json
import sys
import os
import argparse
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.security import get_security_config, create_secure_headers

# Configuration
DEFAULT_CSV_PATH = "data/processed/watchlist.csv"
DEVICE_ID = "data_importer_v1"

def import_data(csv_path):
    """
    Reads property data from a CSV and uses the bulk API endpoint to import it.
    """
    print("--- Starting Data Import Script ---")

    # Check if CSV file exists
    if not os.path.exists(csv_path):
        print(f"[ERROR] CSV file not found at: {csv_path}")
        print("Please run the parser script first: python scripts/parser.py --input data/raw/your_file.csv")
        sys.exit(1)

    try:
        # Read the CSV file, ensuring year_sold and parcel_id are treated as strings
        df = pd.read_csv(csv_path, dtype={'year_sold': str, 'parcel_id': str})
        print(f"Loaded {len(df)} records from {csv_path}")

        # --- Data Cleaning ---
        # Replace NaN values in 'acreage' with a default of 0.0
        if 'acreage' in df.columns:
            df['acreage'] = df['acreage'].fillna(0.0)
            print("Cleaned NaN values from 'acreage' column.")

        # Convert DataFrame to a list of dictionaries
        properties_to_create = df.to_dict(orient='records')

        # Prepare the bulk request payload
        payload = {
            "operation": "create",
            "properties": properties_to_create
        }

        # Use secure configuration for API access
        security_config = get_security_config()
        API_URL = f"{security_config.api_base_url}/properties/bulk"
        headers = create_secure_headers()

        # Send the request to the bulk endpoint
        print(f"Sending {len(properties_to_create)} properties to the API at {API_URL}...")
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload), params={"device_id": DEVICE_ID}, timeout=security_config.api_timeout)

        # Check the response
        response.raise_for_status()  # Raise an exception for bad status codes

        response_data = response.json()
        print("\n--- API Response ---")
        print(f"Operation: {response_data.get('operation')}")
        print(f"Total Requested: {response_data.get('total_requested')}")
        print(f"Successful: {response_data.get('successful')}")
        print(f"Failed: {response_data.get('failed')}")
        print(f"Processing Time: {response_data.get('processing_time_seconds'):.2f} seconds")

        if response_data.get('failed') > 0:
            print("\n[WARNING] Some records failed to import. Errors:")
            for error in response_data.get('errors', []):
                print(f"  - Index {error.get('index')}: {error.get('error')}")
        else:
            print("\n[SUCCESS] All records imported successfully!")

    except FileNotFoundError:
        print(f"[ERROR] Input file not found: {csv_path}")
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] API request failed: {e}")
        if e.response:
            print(f"Response Status: {e.response.status_code}")
            print(f"Response Body: {e.response.text}")
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import property data from a CSV to the API.")
    parser.add_argument(
        '--input',
        default=DEFAULT_CSV_PATH,
        help=f'Input CSV file path (default: {DEFAULT_CSV_PATH})'
    )
    args = parser.parse_args()
    import_data(args.input)
