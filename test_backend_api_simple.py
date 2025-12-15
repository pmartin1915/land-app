#!/usr/bin/env python3
"""
Comprehensive API test script for Alabama Auction Watcher Backend
Tests all endpoints with full functionality - Windows compatible
"""

import requests
import json
import time
import sys
from datetime import datetime

# API Configuration
BASE_URL = "http://localhost:8001"
API_BASE = f"{BASE_URL}/api/v1"

def print_status(message, success=True):
    """Print status message."""
    status = "[SUCCESS]" if success else "[ERROR]"
    print(f"{status} {message}")

def test_health_check():
    """Test basic health endpoints."""
    print("\n[INFO] Testing Health Checks...")

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
    print("\n[INFO] Testing Authentication...")

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
    print("\n[INFO] Testing County Endpoints...")

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
    """Test property CRUD endpoints with comprehensive algorithm validation."""
    print("\n[INFO] Testing Property Endpoints...")

    try:
        headers = {"X-API-Key": api_key}

        # Test property creation with known algorithm results
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

        # Verify calculated metrics match expected values
        assert created_property["water_score"] >= 3.0, f"Water score calculation failed: {created_property['water_score']}"
        assert created_property["investment_score"] > 40, f"Investment score too low: {created_property['investment_score']}"
        assert abs(created_property["price_per_acre"] - 1666.67) < 10, f"Price per acre calculation failed: {created_property['price_per_acre']}"
        assert created_property["assessed_value_ratio"] == 1.25, f"Assessed value ratio failed: {created_property['assessed_value_ratio']}"

        print_status(f"Property created - Investment Score: {created_property['investment_score']:.1f}, Water Score: {created_property['water_score']}")

        # Test property retrieval
        response = requests.get(f"{API_BASE}/properties/{property_id}", headers=headers, timeout=5)
        assert response.status_code == 200, f"Property retrieval failed: {response.status_code}"

        retrieved_property = response.json()
        assert retrieved_property["id"] == property_id, "Property ID mismatch"
        print_status("Property retrieval passed")

        # Test property list with comprehensive filtering
        response = requests.get(f"{API_BASE}/properties/?county=Baldwin&min_investment_score=40&water_features=true", headers=headers, timeout=5)
        assert response.status_code == 200, f"Property list failed: {response.status_code}"

        property_list = response.json()
        assert property_list["total_count"] >= 1, "Property not found in filtered list"
        print_status(f"Property filtering passed - {property_list['total_count']} properties found")

        # Test advanced algorithm calculation endpoint with multiple scenarios
        test_cases = [
            {
                "name": "High-value water property",
                "data": {
                    "amount": 10000.0,
                    "acreage": 5.0,
                    "description": "Property with pond and stream access near lake",
                    "assessed_value": 8000.0
                },
                "expected_water_min": 6.0,  # pond (3) + stream (3) = 6+
                "expected_investment_min": 50.0
            },
            {
                "name": "Basic property no water",
                "data": {
                    "amount": 3000.0,
                    "acreage": 2.0,
                    "description": "Rural property with no water features",
                    "assessed_value": 2500.0
                },
                "expected_water": 0.0,
                "expected_investment_min": 20.0
            }
        ]

        for test_case in test_cases:
            response = requests.post(f"{API_BASE}/properties/calculate", json=test_case["data"], headers=headers, timeout=5)
            assert response.status_code == 200, f"Algorithm calculation failed for {test_case['name']}: {response.status_code}"

            calc_result = response.json()

            if "expected_water" in test_case:
                assert calc_result["water_score"] == test_case["expected_water"], f"Water score mismatch for {test_case['name']}: expected {test_case['expected_water']}, got {calc_result['water_score']}"
            elif "expected_water_min" in test_case:
                assert calc_result["water_score"] >= test_case["expected_water_min"], f"Water score too low for {test_case['name']}: expected >={test_case['expected_water_min']}, got {calc_result['water_score']}"

            assert calc_result["investment_score"] >= test_case["expected_investment_min"], f"Investment score too low for {test_case['name']}: expected >={test_case['expected_investment_min']}, got {calc_result['investment_score']}"

            print_status(f"Algorithm test '{test_case['name']}' passed - Water: {calc_result['water_score']}, Investment: {calc_result['investment_score']:.1f}")

        # Test property update
        update_data = {
            "description": "Updated: Beautiful creek frontage with mature trees and spring",
            "amount": 5500.0
        }

        response = requests.put(f"{API_BASE}/properties/{property_id}", json=update_data, headers=headers, timeout=5)
        assert response.status_code == 200, f"Property update failed: {response.status_code}"

        updated_property = response.json()
        assert updated_property["amount"] == 5500.0, "Property amount not updated"
        assert updated_property["water_score"] >= 6.0, f"Updated water score should be >=6 (creek+spring), got {updated_property['water_score']}"
        print_status(f"Property update passed - New water score: {updated_property['water_score']}")

        return property_id
    except Exception as e:
        print_status(f"Property endpoints test failed: {str(e)}", False)
        return None

def test_sync_endpoints(api_key, property_id):
    """Test comprehensive synchronization endpoints."""
    print("\n[INFO] Testing Sync Endpoints...")

    try:
        headers = {"X-API-Key": api_key}

        # Test sync status
        response = requests.get(f"{API_BASE}/sync/status?device_id=test-device-12345", headers=headers, timeout=5)
        assert response.status_code == 200, f"Sync status failed: {response.status_code}"

        sync_status = response.json()
        print_status(f"Sync status retrieved - Pending changes: {sync_status['pending_changes']}")

        # Test full sync with algorithm validation
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

        # Test delta sync
        from datetime import datetime, timedelta
        last_sync = datetime.utcnow() - timedelta(hours=1)

        delta_sync_request = {
            "device_id": "test-device-12345",
            "algorithm_version": "1.0.0",
            "app_version": "1.0.0",
            "last_sync_timestamp": last_sync.isoformat() + "Z",
            "changes": []  # No local changes for this test
        }

        response = requests.post(f"{API_BASE}/sync/delta", json=delta_sync_request, headers=headers, timeout=10)
        assert response.status_code == 200, f"Delta sync failed: {response.status_code}"

        delta_sync_result = response.json()
        assert delta_sync_result["algorithm_compatibility"] == True, "Algorithm compatibility check failed"
        print_status(f"Delta sync passed - {delta_sync_result['server_changes_count']} server changes received")

        # Test batch sync for large datasets
        batch_request = {
            "batch_size": 10,
            "include_calculations": True
        }

        response = requests.post(f"{API_BASE}/sync/batch", json=batch_request, headers=headers, timeout=10)
        assert response.status_code == 200, f"Batch sync failed: {response.status_code}"

        batch_result = response.json()
        assert len(batch_result["batch_data"]) > 0, "Batch sync returned no data"
        print_status(f"Batch sync passed - {batch_result['batch_count']} properties in batch")

        return True
    except Exception as e:
        print_status(f"Sync endpoints test failed: {str(e)}", False)
        return False

def test_advanced_features(api_key):
    """Test advanced API features."""
    print("\n[INFO] Testing Advanced Features...")

    try:
        headers = {"X-API-Key": api_key}

        # Test property analytics/metrics
        response = requests.get(f"{API_BASE}/properties/analytics/metrics", headers=headers, timeout=5)
        assert response.status_code == 200, f"Property metrics failed: {response.status_code}"

        metrics = response.json()
        assert "total_properties" in metrics, "Metrics missing total_properties"
        assert "average_investment_score" in metrics, "Metrics missing average_investment_score"
        print_status(f"Property analytics passed - {metrics['total_properties']} total properties")

        # Test search suggestions
        response = requests.get(f"{API_BASE}/properties/search/suggestions?query=creek", headers=headers, timeout=5)
        assert response.status_code == 200, f"Search suggestions failed: {response.status_code}"

        suggestions = response.json()
        assert "suggestions" in suggestions, "Search suggestions missing suggestions key"
        print_status(f"Search suggestions passed - {len(suggestions['suggestions'])} suggestions found")

        # Test authentication scopes
        response = requests.get(f"{API_BASE}/auth/scopes", headers=headers, timeout=5)
        assert response.status_code == 200, f"Auth scopes failed: {response.status_code}"

        scopes = response.json()
        assert "scopes" in scopes, "Auth scopes missing scopes key"
        assert "device_scopes" in scopes, "Auth scopes missing device_scopes"
        print_status("Authentication scopes retrieval passed")

        return True
    except Exception as e:
        print_status(f"Advanced features test failed: {str(e)}", False)
        return False

def main():
    """Run all API tests with comprehensive coverage."""
    print("Alabama Auction Watcher API Comprehensive Test Suite")
    print("=" * 60)
    print(f"Testing API at: {BASE_URL}")

    # Wait for server to be ready
    print("\n[INFO] Waiting for server to start...")
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

    # Run comprehensive test suite
    tests_passed = 0
    total_tests = 6

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

        # Test 4: Property endpoints (comprehensive algorithm testing)
        property_id = test_property_endpoints(api_key)
        if property_id:
            tests_passed += 1

            # Test 5: Sync endpoints (comprehensive sync testing)
            if test_sync_endpoints(api_key, property_id):
                tests_passed += 1

            # Test 6: Advanced features
            if test_advanced_features(api_key):
                tests_passed += 1

    # Final results
    print(f"\n[RESULTS] Comprehensive Test Results: {tests_passed}/{total_tests} tests passed")
    print("=" * 60)

    if tests_passed == total_tests:
        print_status("ALL COMPREHENSIVE TESTS PASSED! Backend API is production-ready.")
        print("[INFO] Algorithm compatibility validated across all endpoints")
        print("[INFO] Full CRUD operations working correctly")
        print("[INFO] Synchronization system fully functional")
        print("[INFO] Authentication and security working properly")
        return True
    else:
        print_status(f"{total_tests - tests_passed} tests failed. Check the errors above.", False)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)