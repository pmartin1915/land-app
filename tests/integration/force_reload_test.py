#!/usr/bin/env python3
"""
Force reload the validation module to test if there's a caching issue
"""

import sys
import importlib
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# First import
from config.validation import PropertyValidator, VALIDATION_MODULE_VERSION

print(f"First import - Module version: {VALIDATION_MODULE_VERSION}")

# Test validation
result = PropertyValidator.validate_owner_name('SIMPKINS RANDY')
print(f"Owner name validation result: {result.is_valid}, Errors: {result.errors}")

# Force reload the module
import config.validation
importlib.reload(config.validation)

# Re-import after reload
from config.validation import PropertyValidator as PropertyValidatorReloaded, VALIDATION_MODULE_VERSION as VERSION_RELOADED

print(f"After reload - Module version: {VERSION_RELOADED}")

# Test validation again
result2 = PropertyValidatorReloaded.validate_owner_name('SIMPKINS RANDY')
print(f"Owner name validation result after reload: {result2.is_valid}, Errors: {result2.errors}")

# Now test the PropertyCreate model
try:
    from backend_api.models.property import PropertyCreate

    test_data = {
        'parcel_id': '560808340001020017',
        'county': 'Randolph',
        'amount': 2726.19,
        'acreage': 0.005,
        'description': 'LOT 6 CHIMNEY COVE AT LAKE WEDOWEE CABINET B SLIDE',
        'owner_name': 'SIMPKINS RANDY',
        'year_sold': '2019'
    }

    property_instance = PropertyCreate(**test_data)
    print(f"PropertyCreate success: {property_instance.owner_name}")

except Exception as e:
    print(f"PropertyCreate failed: {e}")
    import traceback
    traceback.print_exc()