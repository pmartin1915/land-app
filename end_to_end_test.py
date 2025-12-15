#!/usr/bin/env python3
"""
End-to-end system test with expanded dataset
"""
import requests
import json

def test_api_health():
    """Test API health and basic functionality"""
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8001/health")
        health = response.json()
        print(f"[OK] API Health: {health['status']}")

        # Test detailed health
        response = requests.get("http://localhost:8001/health/detailed")
        detailed = response.json()
        print(f"[OK] Database: {detailed['components']['database']}")
        print(f"[OK] Algorithms: {detailed['components']['algorithms']}")

        return True
    except Exception as e:
        print(f"[ERROR] API health test failed: {e}")
        return False

def test_property_endpoints():
    """Test property endpoints with expanded dataset"""
    headers = {"X-API-Key": "AW_test-device_12345"}

    try:
        # Test total count
        response = requests.get("http://localhost:8001/api/v1/properties/?page_size=1", headers=headers)
        data = response.json()
        total_count = data.get('total_count', 0)
        print(f"[OK] Total properties: {total_count}")

        # Test filtering by Autauga
        response = requests.get("http://localhost:8001/api/v1/properties/?county=Autauga&page_size=5", headers=headers)
        autauga_data = response.json()
        autauga_count = autauga_data.get('total_count', 0)
        print(f"[OK] Autauga properties: {autauga_count}")

        # Test high investment scores
        response = requests.get("http://localhost:8001/api/v1/properties/?min_investment_score=75&page_size=5", headers=headers)
        high_score_data = response.json()
        high_score_count = high_score_data.get('total_count', 0)
        print(f"[OK] High score properties (75+): {high_score_count}")

        return total_count >= 1500  # Should have 1,510
    except Exception as e:
        print(f"[ERROR] Property endpoints test failed: {e}")
        return False

def test_application_assistant():
    """Test Property Application Assistant endpoints"""
    headers = {"X-API-Key": "AW_test-device_12345"}

    try:
        # Test user profiles endpoint
        response = requests.get("http://localhost:8001/api/v1/applications/profiles", headers=headers)
        profiles = response.json()
        print(f"[OK] User profiles endpoint: {len(profiles)} profiles")

        # Test ROI calculator with a property
        response = requests.get("http://localhost:8001/api/v1/properties/?page_size=1", headers=headers)
        property_data = response.json()
        if property_data.get('properties'):
            property_id = property_data['properties'][0]['id']

            response = requests.get(f"http://localhost:8001/api/v1/applications/properties/{property_id}/roi", headers=headers)
            roi_data = response.json()
            print(f"[OK] ROI calculator: {roi_data.get('roi_percentage', 'N/A')}% ROI")

        return True
    except Exception as e:
        print(f"[ERROR] Application Assistant test failed: {e}")
        return False

def test_streamlit_access():
    """Test Streamlit dashboard accessibility"""
    try:
        response = requests.get("http://localhost:8501", timeout=10)
        if response.status_code == 200:
            print("[OK] Streamlit dashboard accessible")
            return True
        else:
            print(f"[WARNING] Streamlit returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"[WARNING] Streamlit access test: {e}")
        return False

def main():
    """Run complete end-to-end test suite"""
    print("=== Alabama Auction Watcher End-to-End Test ===")
    print()

    tests = [
        ("API Health", test_api_health),
        ("Property Endpoints", test_property_endpoints),
        ("Application Assistant", test_application_assistant),
        ("Streamlit Dashboard", test_streamlit_access),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"Running {test_name} test...")
        result = test_func()
        results.append(result)
        print(f"Result: {'PASS' if result else 'FAIL'}")
        print()

    passed = sum(results)
    total = len(results)

    print(f"=== Test Summary: {passed}/{total} tests passed ===")

    if passed == total:
        print("[SUCCESS] All systems operational with expanded dataset!")
    else:
        print("[WARNING] Some tests failed - check system status")

    return passed == total

if __name__ == "__main__":
    main()