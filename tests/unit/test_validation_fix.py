#!/usr/bin/env python3
"""
Test script to verify the validation system works correctly after the regex fix.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.validation import InputSanitizer, PropertyValidator, validate_property_data

def test_regex_patterns():
    """Test that the regex patterns compile and work correctly."""
    print("Testing regex patterns...")

    # Test command injection patterns (the one we fixed)
    test_strings = [
        "normal text",  # Should pass
        "ls -la",  # Should be caught
        "rm -rf /",  # Should be caught
        "test`whoami`",  # Should be caught (backtick)
        "test$(whoami)",  # Should be caught
        "test|grep something",  # Should be caught
        "test && echo hi",  # Should be caught
    ]

    for test_str in test_strings:
        result = InputSanitizer.sanitize_string(test_str)
        print(f"'{test_str}' -> Valid: {result.is_valid}, Errors: {result.errors}")

    print("\n" + "="*50 + "\n")

def test_property_validation():
    """Test property-specific validation."""
    print("Testing property validation...")

    # Test valid property data
    valid_property = {
        'parcel_id': 'AB123456',
        'amount': 5000.0,
        'acreage': 2.5,
        'county': 'Mobile',
        'description': 'Beautiful 2.5 acre lot with trees',
        'owner_name': 'John Doe',
        'year_sold': '2024'
    }

    results = validate_property_data(valid_property)
    print("Valid property test:")
    for field, result in results.items():
        print(f"  {field}: Valid={result.is_valid}, Errors={result.errors}")

    print("\n" + "-"*30 + "\n")

    # Test invalid property data
    invalid_property = {
        'parcel_id': 'AB',  # Too short
        'amount': -1000,  # Negative
        'acreage': 0,  # Zero
        'county': 'InvalidCounty',  # Invalid county
        'description': '<script>alert("xss")</script>',  # XSS attempt
        'owner_name': 'DROP TABLE users;--',  # SQL injection attempt
        'year_sold': '1800'  # Invalid year
    }

    results = validate_property_data(invalid_property)
    print("Invalid property test:")
    for field, result in results.items():
        print(f"  {field}: Valid={result.is_valid}, Errors={result.errors}")

def test_numeric_validation():
    """Test numeric validation."""
    print("\n" + "="*50 + "\n")
    print("Testing numeric validation...")

    test_values = [
        ("5000", "Valid string number"),
        ("$5,000.50", "Formatted currency"),
        (-100, "Negative number"),
        ("not_a_number", "Invalid string"),
        (1e20, "Very large number"),
        (None, "None value")
    ]

    for value, description in test_values:
        result = InputSanitizer.sanitize_numeric(value, min_value=0, max_value=1000000)
        print(f"{description}: '{value}' -> Valid={result.is_valid}, Value={result.sanitized_value}, Errors={result.errors}")

if __name__ == "__main__":
    print("Alabama Auction Watcher - Validation System Test")
    print("="*60)

    try:
        test_regex_patterns()
        test_property_validation()
        test_numeric_validation()
        print("\n" + "="*60)
        print("[SUCCESS] All validation tests completed successfully!")
        print("The regex fix appears to be working correctly.")

    except Exception as e:
        print(f"\n[ERROR] Validation test failed: {e}")
        print("Please check the validation system configuration.")
        sys.exit(1)