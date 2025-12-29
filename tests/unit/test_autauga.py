#!/usr/bin/env python3
"""Test Autauga county properties in API"""
import requests
import json

try:
    response = requests.get(
        "http://localhost:8001/api/v1/properties/?county=Autauga&page_size=3",
        headers={"X-API-Key": "AW_test-device_12345"}
    )
    data = response.json()

    print(f"[SUCCESS] Found {data.get('total_count', 0)} properties in Autauga county")

    for i, prop in enumerate(data.get('properties', [])[:3]):
        print(f"[OK] Property {i+1}: {prop['parcel_id']} - ${prop['amount']} - Score: {prop['investment_score']}")

except Exception as e:
    print(f"[ERROR] Autauga test failed: {e}")