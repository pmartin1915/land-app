#!/usr/bin/env python3
"""
Quick API test script for Alabama Auction Watcher Backend
Tests core endpoints to ensure API functionality
"""

import requests
import json
import time
import sys
from datetime import datetime

# API Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def print_status(message, success=True):
    """Print colored status message."""
    color = "✅" if success else "❌"
    print(f"{color} {message}")

def test_health_check():
    """Test basic health endpoints."""
    print("\n🔍 Testing Health Checks...")

    try:
        # Basic health check
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        health_data = response.json()
        assert health_data["status"] == "healthy", f"Health status not healthy: {health_data}"
        print_status("Basic health check passed")

        # Detailed health check
        response = requests.get(f"{BASE_URL}/health/detailed", timeout=10)
        assert response.status_code == 200, f"Detailed health check failed: {response.status_code}"
        detailed_health = response.json()
        print_status(f"Detailed health check passed - Algorithm status: {detailed_health['components']['algorithms']}")

        return True
    except Exception as e:
        print_status(f"Health check failed: {str(e)}", False)
        return False

def test_authentication():
    """Test authentication endpoints."""
    print("\n🔐 Testing Authentication...")

    try:
        # Test device API key creation
        device_request = {
            "device_id": "test-device-12345",
            "app_version": "1.0.0",
            "device_name": "Test iPhone"
        }

        response = requests.post(f"{API_BASE}/auth/device/api-key", json=device_request, timeout=5)
        assert response.status_code == 200, f"API key creation failed: {response.status_code}"

        api_key_data = response.json()
        api_key = api_key_data["api_key"]
        assert api_key, "No API key returned"
        print_status("Device API key created successfully")

        # Test API key validation
        headers = {"X-API-Key": api_key}
        response = requests.get(f"{API_BASE}/auth/validate", headers=headers, timeout=5)
        assert response.status_code == 200, f"API key validation failed: {response.status_code}"

        validation_data = response.json()
        assert validation_data["valid"] == True, "API key validation failed"
        print_status("API key validation passed")

        return api_key
    except Exception as e:
        print_status(f"Authentication test failed: {str(e)}", False)
        return None

def test_county_endpoints(api_key):
    """Test county endpoints."""
    print("\n🏛️ Testing County Endpoints...")

    try:
        headers = {"X-API-Key": api_key}

        # Test counties list
        response = requests.get(f"{API_BASE}/counties", headers=headers, timeout=5)
        assert response.status_code == 200, f"Counties list failed: {response.status_code}"

        counties = response.json()
        assert len(counties) >= 60, f"Expected 67 Alabama counties, got {len(counties)}"
        print_status(f"Counties endpoint passed - {len(counties)} counties loaded")

        return True
    except Exception as e:
        print_status(f"County endpoints test failed: {str(e)}", False)
        return False

def test_property_endpoints(api_key):
    """Test property CRUD endpoints."""
    print("\n🏠 Testing Property Endpoints...")

    try:
        headers = {"X-API-Key": api_key}

        # Test property creation
        property_data = {
            "parcel_id": "TEST-001",
            "amount": 5000.0,
            "acreage": 3.0,
            "description": "Beautiful creek frontage with mature trees",
            "county": "Baldwin",
            "owner_name": "Test Owner",
            "year_sold": "2023",
            "assessed_value": 4000.0
        }

        response = requests.post(f"{API_BASE}/properties/", json=property_data, headers=headers, timeout=10)
        assert response.status_code == 201, f"Property creation failed: {response.status_code} - {response.text}"

        created_property = response.json()
        property_id = created_property["id"]

        # Verify calculated metrics
        assert created_property["water_score"] >= 3.0, f"Water score calculation failed: {created_property['water_score']}"
        assert created_property["investment_score"] > 0, f"Investment score calculation failed: {created_property['investment_score']}"
        assert abs(created_property["price_per_acre"] - 1666.67) < 1, f"Price per acre calculation failed: {created_property['price_per_acre']}"

        print_status(f"Property created - Investment Score: {created_property['investment_score']:.1f}, Water Score: {created_property['water_score']}")

        # Test property retrieval
        response = requests.get(f"{API_BASE}/properties/{property_id}", headers=headers, timeout=5)
        assert response.status_code == 200, f"Property retrieval failed: {response.status_code}"

        retrieved_property = response.json()
        assert retrieved_property["id"] == property_id, "Property ID mismatch"
        print_status("Property retrieval passed")

        # Test property list with filters
        response = requests.get(f"{API_BASE}/properties/?county=Baldwin&min_investment_score=40", headers=headers, timeout=5)
        assert response.status_code == 200, f"Property list failed: {response.status_code}"

        property_list = response.json()
        assert property_list["total_count"] >= 1, "Property not found in filtered list"
        print_status(f"Property filtering passed - {property_list['total_count']} properties found")

        # Test algorithm calculation endpoint
        calc_request = {
            "amount": 10000.0,
            "acreage": 5.0,
            "description": "Property with pond and stream access",
            "assessed_value": 8000.0
        }

        response = requests.post(f"{API_BASE}/properties/calculate", json=calc_request, headers=headers, timeout=5)
        assert response.status_code == 200, f"Algorithm calculation failed: {response.status_code}"

        calc_result = response.json()
        assert calc_result["investment_score"] > 0, "Investment score calculation failed"
        assert calc_result["water_score"] >= 6.0, f"Water score should be >=6 for pond+stream, got {calc_result['water_score']}"

        print_status(f"Algorithm calculation passed - Water: {calc_result['water_score']}, Investment: {calc_result['investment_score']:.1f}")

        return property_id
    except Exception as e:
        print_status(f"Property endpoints test failed: {str(e)}", False)
        return None

def test_sync_endpoints(api_key, property_id):
    """Test synchronization endpoints."""
    print("\n🔄 Testing Sync Endpoints...")

    try:
        headers = {"X-API-Key": api_key}

        # Test sync status
        response = requests.get(f"{API_BASE}/sync/status?device_id=test-device-12345", headers=headers, timeout=5)
        assert response.status_code == 200, f"Sync status failed: {response.status_code}"

        sync_status = response.json()
        print_status(f"Sync status retrieved - Pending changes: {sync_status['pending_changes']}")

        # Test full sync
        full_sync_request = {
            "device_id": "test-device-12345",
            "algorithm_version": "1.0.0",
            "app_version": "1.0.0",
            "include_deleted": False
        }

        response = requests.post(f"{API_BASE}/sync/full", json=full_sync_request, headers=headers, timeout=10)
        assert response.status_code == 200, f"Full sync failed: {response.status_code}"

        full_sync_result = response.json()
        assert full_sync_result["total_properties"] >= 1, "Full sync returned no properties"
        assert full_sync_result["algorithm_compatibility"] == True, "Algorithm compatibility check failed"

        print_status(f"Full sync passed - {full_sync_result['total_properties']} properties synced")

        return True
    except Exception as e:
        print_status(f"Sync endpoints test failed: {str(e)}", False)
        return False

def main():
    """Run all API tests."""
    print("🚀 Starting Alabama Auction Watcher API Tests")
    print(f"📍 Testing API at: {BASE_URL}")

    # Wait for server to be ready
    print("\n⏳ Waiting for server to start...")
    for i in range(30):  # Wait up to 30 seconds
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                print_status("Server is ready!")
                break
        except:
            pass
        time.sleep(1)
        if i % 5 == 4:
            print(f"   Still waiting... ({i+1}/30)")
    else:
        print_status("Server failed to start within 30 seconds", False)
        return False

    # Run tests
    tests_passed = 0
    total_tests = 5

    # Test 1: Health checks
    if test_health_check():
        tests_passed += 1

    # Test 2: Authentication
    api_key = test_authentication()
    if api_key:
        tests_passed += 1

        # Test 3: County endpoints
        if test_county_endpoints(api_key):
            tests_passed += 1

        # Test 4: Property endpoints
        property_id = test_property_endpoints(api_key)
        if property_id:
            tests_passed += 1

            # Test 5: Sync endpoints
            if test_sync_endpoints(api_key, property_id):
                tests_passed += 1

    # Results
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")

    if tests_passed == total_tests:
        print_status("🎉 ALL TESTS PASSED! Backend API is working correctly.")
        return True
    else:
        print_status(f"❌ {total_tests - tests_passed} tests failed. Check the errors above.", False)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)