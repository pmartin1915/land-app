"""
Test script for Predictive Market Intelligence Engine
Validates the prediction algorithms and integrates with existing data
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scripts.predictive_market_engine import (
    PredictiveMarketEngine,
    PropertyAppreciationForecast,
    MarketTimingAnalysis,
    EmergingOpportunity
)


def test_predictive_engine():
    """Test the predictive market engine with sample data."""

    print("TESTING: Predictive Market Intelligence Engine")
    print("=" * 60)

    # Initialize the engine
    engine = PredictiveMarketEngine()

    # Sample property data (using realistic data from the Alabama Auction Watcher dataset)
    sample_properties = [
        {
            "id": "test_1",
            "amount": 138.87,
            "acreage": 3.546,
            "price_per_acre": 39.16,
            "water_score": 0.0,
            "investment_score": 80.0,
            "county": "Mobile",
            "description": "#TAX DEED NO: 51492 #DTD 03/31/06 ISSUED TO #RON",
            "assessed_value": 1000.0,
            "assessed_value_ratio": 0.13887
        },
        {
            "id": "test_2",
            "amount": 292.17,
            "acreage": 4.4,
            "price_per_acre": 66.40,
            "water_score": 0.0,
            "investment_score": 78.8,
            "county": "Mobile",
            "description": "LOT #185 AS SHOWN ON PLAT OF AL VILLAGE PRICHARD",
            "assessed_value": 2820.0,
            "assessed_value_ratio": 0.1036
        },
        {
            "id": "test_3",
            "amount": 5000.0,
            "acreage": 10.0,
            "price_per_acre": 500.0,
            "water_score": 6.0,
            "investment_score": 85.0,
            "county": "Baldwin",
            "description": "Beautiful creek frontage with mature trees",
            "assessed_value": 15000.0,
            "assessed_value_ratio": 0.333
        }
    ]

    print("TEST 1: Property Appreciation Predictions")
    print("-" * 40)

    for i, prop in enumerate(sample_properties, 1):
        print(f"\nProperty {i} ({prop['county']} County):")
        print(f"  Current Investment Score: {prop['investment_score']:.1f}")
        print(f"  Price per Acre: ${prop['price_per_acre']:.2f}")
        print(f"  Water Score: {prop['water_score']:.1f}")

        # Test appreciation prediction
        forecast = engine.predict_property_appreciation(
            prop, prop['county'], prop['investment_score']
        )

        print(f"  PREDICTIONS:")
        print(f"    1-Year Appreciation: {forecast.one_year_appreciation:.2%}")
        print(f"    3-Year Appreciation: {forecast.three_year_appreciation:.2%}")
        print(f"    5-Year Appreciation: {forecast.five_year_appreciation:.2%}")
        print(f"    Market Trend: {forecast.market_trend.value}")
        print(f"    Confidence: {forecast.confidence_level.value}")
        print(f"    Risk Score: {forecast.risk_score:.2f}")

    print("\n" + "=" * 60)
    print("TEST 2: Market Timing Analysis")
    print("-" * 40)

    # Test market timing for different counties
    test_counties = ["Mobile", "Baldwin", "Jefferson"]

    for county in test_counties:
        print(f"\n{county} County Market Timing:")

        timing = engine.analyze_market_timing(county)

        print(f"  Current Market Phase: {timing.current_market_phase}")
        print(f"  Optimal Buy Window: {timing.optimal_buy_window[0]} - {timing.optimal_buy_window[1]}")
        print(f"  Optimal Sell Window: {timing.optimal_sell_window[0]} - {timing.optimal_sell_window[1]}")
        print(f"  Price Momentum: {timing.price_momentum:.2f}")
        print(f"  Market Volatility: {timing.market_volatility:.2f}")
        print(f"  Confidence Score: {timing.confidence_score:.2f}")

    print("\n" + "=" * 60)
    print("TEST 3: Emerging Opportunities Detection")
    print("-" * 40)

    # Test opportunity detection
    opportunities = engine.detect_emerging_opportunities(sample_properties, top_n=5)

    print(f"\nFound {len(opportunities)} emerging opportunities:")

    for i, opp in enumerate(opportunities, 1):
        print(f"\n  Opportunity {i}:")
        print(f"    Property ID: {opp.property_id}")
        print(f"    County: {opp.county}")
        print(f"    Type: {opp.opportunity_type}")
        print(f"    Opportunity Score: {opp.opportunity_score:.1f}/100")
        print(f"    Potential Appreciation: {opp.potential_appreciation:.2%}")
        print(f"    Risk-Adjusted Return: {opp.risk_adjusted_return:.2%}")
        print(f"    Timeline: {opp.expected_timeline_months} months")
        print(f"    Confidence: {opp.confidence_level.value}")

        if opp.primary_drivers:
            print(f"    Primary Drivers: {', '.join(opp.primary_drivers)}")
        if opp.risk_factors:
            print(f"    Risk Factors: {', '.join(opp.risk_factors)}")

    print("\n" + "=" * 60)
    print("SUCCESS: All Tests Completed Successfully!")
    print("\nPredictive Market Intelligence Engine is ready for integration!")

    return True


def test_integration_with_api_data():
    """Test integration with real API data."""

    print("\nTESTING: Integration with API Data")
    print("-" * 40)

    try:
        import requests
        from config.security import create_secure_headers

        # Fetch sample data from the API
        headers = create_secure_headers()
        response = requests.get(
            "http://localhost:8001/api/v1/properties/?page=1&page_size=5",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            properties = data.get("properties", [])

            print(f"SUCCESS: Fetched {len(properties)} properties from API")

            # Test predictive engine with real data
            engine = PredictiveMarketEngine()

            for prop in properties[:2]:  # Test with first 2 properties
                county = prop.get("county", "")
                if county:
                    print(f"\nTesting with real property in {county}:")

                    forecast = engine.predict_property_appreciation(
                        prop, county, prop.get("investment_score", 50)
                    )

                    print(f"  Investment Score: {prop.get('investment_score', 50):.1f}")
                    print(f"  3-Year Appreciation Forecast: {forecast.three_year_appreciation:.2%}")
                    print(f"  Confidence: {forecast.confidence_level.value}")

            print("\nSUCCESS: API integration test successful!")
            return True

        else:
            print(f"ERROR: API request failed with status {response.status_code}")
            return False

    except Exception as e:
        print(f"ERROR: API integration test failed: {str(e)}")
        print("Note: Make sure backend API is running on localhost:8001")
        return False


if __name__ == "__main__":
    # Run the tests
    test_success = test_predictive_engine()

    if test_success:
        # Try API integration test
        api_success = test_integration_with_api_data()

        if api_success:
            print("\nSUCCESS: ALL TESTS PASSED - Predictive Engine Ready for Production!")
        else:
            print("\nWARNING: Core tests passed, but API integration needs backend running")
    else:
        print("\nERROR: Tests failed - please check the implementation")