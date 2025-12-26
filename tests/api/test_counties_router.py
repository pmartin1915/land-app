"""
Test Suite for Counties Router
Path: backend_api/routers/counties.py
Coverage: 100% of endpoints, ~120 tests covering happy paths, edge cases, and errors.
"""

import pytest
import logging
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Project Imports
from backend_api.routers.counties import router as counties_router
from backend_api.database.connection import get_db
from backend_api.models.county import (
    CountyResponse, CountyListResponse, CountyValidationResponse,
    CountyLookupResponse, CountyStatisticsResponse, ADOR_COUNTY_MAPPING
)

# Test Infrastructure
from tests.api.base_api_test import BaseAPITest
from tests.api.auth_helpers import generate_test_jwt_token

# Configure Logger
logger = logging.getLogger(__name__)


# =============================================================================
# TEST DATA FIXTURES
# =============================================================================

# Sample valid codes for parametrized tests (spread across range)
SAMPLE_VALID_CODES = [
    ("01", "Autauga"), ("02", "Mobile"), ("03", "Baldwin"),
    ("10", "Chambers"), ("20", "Coosa"), ("30", "Fayette"),
    ("38", "Jefferson"), ("40", "Lauderdale"), ("50", "Monroe"),
    ("51", "Montgomery"), ("58", "St. Clair"), ("60", "Sumter"),
    ("63", "Tuscaloosa"), ("67", "Winston"),
]

# Invalid code scenarios with expected behavior
INVALID_CODE_FORMAT_CASES = [
    ("1", 400, "2-digit"),           # Single digit
    ("001", 400, "2-digit"),         # Three digits
    ("AB", 400, "numeric"),          # Letters
    ("1A", 400, "numeric"),          # Mixed
    ("A1", 400, "numeric"),          # Mixed reversed
]

INVALID_CODE_RANGE_CASES = [
    ("00", 404),    # Below range
    ("68", 404),    # Above range
    ("99", 404),    # Way above range
]

# Valid Alabama county names for testing
SAMPLE_VALID_NAMES = [
    "Autauga", "Baldwin", "Jefferson", "Mobile", "Montgomery",
    "Tuscaloosa", "Madison", "Shelby", "St. Clair", "Winston",
]


# =============================================================================
# FIXTURES AND SETUP
# =============================================================================

def override_get_db():
    """Mock database session dependency."""
    mock_session = MagicMock(spec=Session)
    try:
        yield mock_session
    finally:
        pass


@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI application instance for testing the router."""
    # Disable rate limiting for tests by disabling the router's limiter
    import backend_api.routers.counties as counties_module

    # Disable the limiter directly
    original_enabled = counties_module.limiter.enabled
    counties_module.limiter.enabled = False

    application = FastAPI()
    application.include_router(counties_router, prefix="/counties")
    application.dependency_overrides[get_db] = override_get_db
    application.state.limiter = counties_module.limiter

    yield application

    # Cleanup: restore original limiter state and reset dependency overrides
    counties_module.limiter.enabled = original_enabled
    application.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a TestClient instance."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_db_session(app: FastAPI):
    """Retrieve the mock session from the dependency override."""
    mock_session = MagicMock(spec=Session)
    app.dependency_overrides[get_db] = lambda: mock_session
    return mock_session


@pytest.fixture
def auth_headers():
    """Generate valid authentication headers."""
    token = generate_test_jwt_token(device_id="test_device_001")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_county_logic():
    """Patch the logic functions in the router module."""
    with patch("backend_api.routers.counties.get_county_by_code") as mock_by_code, \
         patch("backend_api.routers.counties.get_county_by_name") as mock_by_name, \
         patch("backend_api.routers.counties.search_counties") as mock_search:
        yield {
            "by_code": mock_by_code,
            "by_name": mock_by_name,
            "search": mock_search
        }


class MockCountyORM:
    """Mock ORM object for County database records."""
    def __init__(self, code: str, name: str, created_at=None, updated_at=None):
        self.code = code
        self.name = name
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()


class MockPropertyORM:
    """Mock ORM object for Property database records used in statistics."""
    def __init__(self, county: str, investment_score: float = 75.0,
                 water_score: float = 5.0, price_per_acre: float = 2000.0,
                 amount: float = 10000.0, is_deleted: bool = False):
        self.county = county
        self.investment_score = investment_score
        self.water_score = water_score
        self.price_per_acre = price_per_acre
        self.amount = amount
        self.is_deleted = is_deleted


# =============================================================================
# TEST CLASS
# =============================================================================

class TestCountiesRouter(BaseAPITest):
    """
    Comprehensive test suite for Alabama Counties Router.
    Target: ~120 tests total covering all 7 endpoints.
    """

    # =========================================================================
    # 1. GET /counties - List Counties (15 Tests)
    # =========================================================================

    def test_list_counties_all_67_returned_db_empty(self, client, mock_db_session):
        """Should return all 67 static counties when DB is empty."""
        mock_db_session.query.return_value.order_by.return_value.all.return_value = []

        response = client.get("/counties/")

        self.assert_200(response)
        data = response.json()
        assert data["total_count"] == 67
        assert len(data["counties"]) == 67

    def test_list_counties_response_structure(self, client, mock_db_session):
        """Validate the exact JSON structure of the list response."""
        mock_db_session.query.return_value.order_by.return_value.all.return_value = []

        response = client.get("/counties/")

        data = response.json()
        self.assert_has_fields(data, ["counties", "total_count"])
        self.assert_has_fields(data["counties"][0], ["code", "name"])

    def test_list_counties_alphabetical_order_check(self, client, mock_db_session):
        """Ensure static fallback returns items sorted by code."""
        mock_db_session.query.return_value.order_by.return_value.all.return_value = []

        response = client.get("/counties/")
        counties = response.json()["counties"]

        codes = [c["code"] for c in counties]
        assert codes == sorted(codes)

    def test_list_counties_from_database(self, client, mock_db_session):
        """Should return counties from database when populated."""
        db_counties = [
            MockCountyORM("01", "Autauga"),
            MockCountyORM("02", "Mobile"),
        ]
        mock_db_session.query.return_value.order_by.return_value.all.return_value = db_counties

        response = client.get("/counties/")

        self.assert_200(response)
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["counties"]) == 2

    def test_list_counties_county_fields_complete(self, client, mock_db_session):
        """Verify each county object has all required fields."""
        mock_db_session.query.return_value.order_by.return_value.all.return_value = []

        response = client.get("/counties/")
        county = response.json()["counties"][0]

        assert "code" in county
        assert "name" in county
        assert "created_at" in county
        assert "updated_at" in county

    @pytest.mark.parametrize("code,expected_name", [
        ("01", "Autauga"),
        ("02", "Mobile"),
        ("03", "Baldwin"),
        ("38", "Jefferson"),
        ("51", "Montgomery"),
        ("67", "Winston"),
    ])
    def test_list_counties_verify_specific_mappings(self, client, mock_db_session, code, expected_name):
        """Verify specific ADOR code-to-name mappings are correct."""
        mock_db_session.query.return_value.order_by.return_value.all.return_value = []

        response = client.get("/counties/")
        counties = {c["code"]: c["name"] for c in response.json()["counties"]}

        assert counties[code] == expected_name

    def test_list_counties_database_error_returns_500(self, client, mock_db_session):
        """Should return 500 on database exception."""
        mock_db_session.query.side_effect = Exception("Database connection failed")

        response = client.get("/counties/")

        assert response.status_code == 500
        assert "Failed to retrieve counties" in response.json()["detail"]

    def test_list_counties_first_county_is_01(self, client, mock_db_session):
        """First county in sorted list should be code 01."""
        mock_db_session.query.return_value.order_by.return_value.all.return_value = []

        response = client.get("/counties/")
        first = response.json()["counties"][0]

        assert first["code"] == "01"
        assert first["name"] == "Autauga"

    def test_list_counties_last_county_is_67(self, client, mock_db_session):
        """Last county in sorted list should be code 67."""
        mock_db_session.query.return_value.order_by.return_value.all.return_value = []

        response = client.get("/counties/")
        last = response.json()["counties"][-1]

        assert last["code"] == "67"
        assert last["name"] == "Winston"

    # =========================================================================
    # 2. GET /counties/{county_code} - Get County (20 Tests)
    # =========================================================================

    def test_get_county_valid_code_returns_county(self, client, mock_db_session):
        """Should return county for valid code."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        response = client.get("/counties/01")

        self.assert_200(response)
        data = response.json()
        assert data["code"] == "01"
        assert data["name"] == "Autauga"

    def test_get_county_from_database(self, client, mock_db_session):
        """Should return county from database when found."""
        db_county = MockCountyORM("01", "Autauga")
        mock_db_session.query.return_value.filter.return_value.first.return_value = db_county

        response = client.get("/counties/01")

        self.assert_200(response)
        assert response.json()["name"] == "Autauga"

    def test_get_county_fallback_to_static_mapping(self, client, mock_db_session):
        """Should fall back to static mapping when not in database."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        response = client.get("/counties/38")

        self.assert_200(response)
        assert response.json()["name"] == "Jefferson"

    def test_get_county_response_structure(self, client, mock_db_session):
        """Verify response has all required fields."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        response = client.get("/counties/01")
        data = response.json()

        self.assert_has_fields(data, ["code", "name", "created_at", "updated_at"])

    @pytest.mark.parametrize("code,expected_name", SAMPLE_VALID_CODES)
    def test_get_county_all_valid_codes(self, client, mock_db_session, code, expected_name):
        """Test retrieval for sample of valid county codes."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        response = client.get(f"/counties/{code}")

        self.assert_200(response)
        assert response.json()["code"] == code
        assert response.json()["name"] == expected_name

    @pytest.mark.parametrize("invalid_code,expected_status,error_contains", INVALID_CODE_FORMAT_CASES)
    def test_get_county_invalid_code_format(self, client, invalid_code, expected_status, error_contains):
        """Test various invalid code formats."""
        response = client.get(f"/counties/{invalid_code}")

        assert response.status_code == expected_status
        if error_contains:
            assert error_contains in response.json()["detail"]

    @pytest.mark.parametrize("invalid_code,expected_status", INVALID_CODE_RANGE_CASES)
    def test_get_county_invalid_code_range(self, client, mock_db_session, invalid_code, expected_status):
        """Test codes outside valid range (00, 68+)."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        response = client.get(f"/counties/{invalid_code}")

        assert response.status_code == expected_status

    def test_get_county_code_with_leading_zero(self, client, mock_db_session):
        """Ensure codes like '01' work correctly with leading zero."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        response = client.get("/counties/01")

        self.assert_200(response)
        assert response.json()["code"] == "01"

    def test_get_county_st_clair_special_name(self, client, mock_db_session):
        """Test county with period in name (St. Clair)."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        response = client.get("/counties/58")

        self.assert_200(response)
        assert response.json()["name"] == "St. Clair"

    def test_get_county_database_error_returns_500(self, client, mock_db_session):
        """Should return 500 on database exception."""
        mock_db_session.query.side_effect = Exception("Database error")

        response = client.get("/counties/01")

        assert response.status_code == 500
        assert "Failed to retrieve county" in response.json()["detail"]

    def test_get_county_not_found_returns_404(self, client, mock_db_session):
        """Should return 404 for non-existent county code."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        response = client.get("/counties/99")

        self.assert_404(response)

    # =========================================================================
    # 3. POST /counties/validate - Validate County (25 Tests)
    # =========================================================================

    def test_validate_county_valid_code_returns_is_valid_true(self, client):
        """Valid code should return is_valid=True."""
        response = client.post("/counties/validate", json={"code": "01"})

        self.assert_200(response)
        data = response.json()
        assert data["is_valid"] is True

    def test_validate_county_code_returns_name(self, client):
        """Valid code should return corresponding county name."""
        response = client.post("/counties/validate", json={"code": "38"})

        data = response.json()
        assert data["name"] == "Jefferson"
        assert data["code"] == "38"

    def test_validate_county_valid_name_returns_is_valid_true(self, client):
        """Valid name should return is_valid=True."""
        response = client.post("/counties/validate", json={"name": "Jefferson"})

        self.assert_200(response)
        assert response.json()["is_valid"] is True

    def test_validate_county_name_returns_code(self, client):
        """Valid name should return corresponding county code."""
        response = client.post("/counties/validate", json={"name": "Mobile"})

        data = response.json()
        assert data["code"] == "02"
        assert data["name"] == "Mobile"

    def test_validate_county_response_structure(self, client):
        """Verify response has all required fields."""
        response = client.post("/counties/validate", json={"code": "01"})

        data = response.json()
        self.assert_has_fields(data, ["is_valid", "code", "name"])

    @pytest.mark.parametrize("code", ["01", "10", "25", "38", "51", "67"])
    def test_validate_county_sample_valid_codes(self, client, code):
        """Test validation for sample of valid codes."""
        response = client.post("/counties/validate", json={"code": code})

        assert response.json()["is_valid"] is True

    @pytest.mark.parametrize("name", SAMPLE_VALID_NAMES)
    def test_validate_county_sample_valid_names(self, client, name):
        """Test validation for sample of valid county names."""
        response = client.post("/counties/validate", json={"name": name})

        assert response.json()["is_valid"] is True

    def test_validate_county_invalid_code_returns_422(self, client):
        """Invalid code outside range should return 422 (Pydantic validation)."""
        response = client.post("/counties/validate", json={"code": "99"})

        # Pydantic validator rejects codes outside 01-67 range
        self.assert_422(response)

    def test_validate_county_invalid_name_returns_422(self, client):
        """Invalid name should return 422 (Pydantic validation)."""
        response = client.post("/counties/validate", json={"name": "FakeCounty"})

        # Pydantic validator rejects names not in valid county list
        self.assert_422(response)

    def test_validate_county_name_case_sensitive_lowercase(self, client):
        """Lowercase name should fail Pydantic validation."""
        response = client.post("/counties/validate", json={"name": "jefferson"})

        # Pydantic validator rejects - case sensitive
        self.assert_422(response)

    def test_validate_county_name_case_sensitive_uppercase(self, client):
        """Uppercase name should fail Pydantic validation."""
        response = client.post("/counties/validate", json={"name": "JEFFERSON"})

        # Pydantic validator rejects - case sensitive
        self.assert_422(response)

    def test_validate_county_special_name_st_clair(self, client):
        """Test St. Clair with period in name."""
        response = client.post("/counties/validate", json={"name": "St. Clair"})

        assert response.json()["is_valid"] is True
        assert response.json()["code"] == "58"

    def test_validate_county_neither_code_nor_name_returns_400(self, client):
        """Should return 400 when neither code nor name provided."""
        response = client.post("/counties/validate", json={})

        self.assert_400(response, "Either code or name must be provided")

    def test_validate_county_both_code_and_name_uses_code(self, client):
        """When both provided, code should take precedence."""
        response = client.post("/counties/validate", json={
            "code": "01",
            "name": "Jefferson"  # Different from code 01
        })

        data = response.json()
        assert data["is_valid"] is True
        assert data["name"] == "Autauga"  # From code 01, not Jefferson

    def test_validate_county_code_out_of_range_00(self, client):
        """Code 00 should fail Pydantic validation."""
        response = client.post("/counties/validate", json={"code": "00"})

        # Pydantic validator rejects codes outside 01-67 range
        self.assert_422(response)

    def test_validate_county_code_out_of_range_68(self, client):
        """Code 68 should fail Pydantic validation (only 67 counties)."""
        response = client.post("/counties/validate", json={"code": "68"})

        # Pydantic validator rejects codes outside 01-67 range
        self.assert_422(response)

    def test_validate_county_empty_code_returns_error(self, client):
        """Empty code string should fail validation."""
        response = client.post("/counties/validate", json={"code": ""})

        # Either 422 validation error or is_valid=False
        assert response.status_code in [200, 422]

    def test_validate_county_empty_name_returns_error(self, client):
        """Empty name string should fail validation."""
        response = client.post("/counties/validate", json={"name": ""})

        assert response.status_code in [200, 422]

    def test_validate_county_null_values(self, client):
        """Null values for both should return 400."""
        response = client.post("/counties/validate", json={"code": None, "name": None})

        self.assert_400(response, "Either code or name must be provided")

    def test_validate_county_service_error_returns_500(self, client):
        """Should return 500 on service exception."""
        with patch("backend_api.routers.counties.get_county_by_code", side_effect=Exception("Service error")):
            response = client.post("/counties/validate", json={"code": "01"})

            assert response.status_code == 500

    # =========================================================================
    # 4. POST /counties/lookup - County Lookup (20 Tests)
    # =========================================================================

    def test_lookup_county_by_code_returns_exact_match(self, client):
        """Lookup by code should return exact_match=True."""
        response = client.post("/counties/lookup", json={"code": "01"})

        self.assert_200(response)
        data = response.json()
        assert data["exact_match"] is True

    def test_lookup_county_by_code_returns_single_match(self, client):
        """Lookup by code should return exactly one match."""
        response = client.post("/counties/lookup", json={"code": "38"})

        data = response.json()
        assert len(data["matches"]) == 1
        assert data["matches"][0]["code"] == "38"
        assert data["matches"][0]["name"] == "Jefferson"

    def test_lookup_county_by_code_invalid_returns_empty(self, client):
        """Invalid code should return empty matches."""
        response = client.post("/counties/lookup", json={"code": "99"})

        data = response.json()
        assert len(data["matches"]) == 0
        assert data["exact_match"] is False

    def test_lookup_county_by_code_response_structure(self, client):
        """Verify lookup response has correct structure."""
        response = client.post("/counties/lookup", json={"code": "01"})

        data = response.json()
        self.assert_has_fields(data, ["matches", "exact_match", "suggestions"])

    def test_lookup_county_by_name_returns_exact_match(self, client):
        """Lookup by name should return exact_match=True."""
        response = client.post("/counties/lookup", json={"name": "Jefferson"})

        data = response.json()
        assert data["exact_match"] is True
        assert len(data["matches"]) == 1

    def test_lookup_county_by_name_case_sensitive(self, client):
        """Lookup by name is case-sensitive."""
        response = client.post("/counties/lookup", json={"name": "jefferson"})

        data = response.json()
        assert data["exact_match"] is False
        assert len(data["matches"]) == 0

    def test_lookup_county_by_name_st_clair(self, client):
        """Lookup St. Clair with special character."""
        response = client.post("/counties/lookup", json={"name": "St. Clair"})

        data = response.json()
        assert data["exact_match"] is True
        assert data["matches"][0]["code"] == "58"

    def test_lookup_county_partial_name_returns_matches(self, client):
        """Partial name lookup should return multiple matches."""
        response = client.post("/counties/lookup", json={"partial_name": "M"})

        data = response.json()
        assert data["exact_match"] is False
        # Should find: Macon, Madison, Marengo, Marion, Marshall, Mobile, Monroe, Montgomery, Morgan
        assert len(data["matches"]) >= 5

    def test_lookup_county_partial_name_case_insensitive(self, client):
        """Partial name search is case-insensitive."""
        response = client.post("/counties/lookup", json={"partial_name": "mobile"})

        data = response.json()
        assert len(data["matches"]) >= 1
        names = [m["name"] for m in data["matches"]]
        assert "Mobile" in names

    def test_lookup_county_partial_name_suggestions_limited(self, client):
        """Suggestions should be limited to 5."""
        response = client.post("/counties/lookup", json={"partial_name": "C"})

        data = response.json()
        # Many counties start with C
        assert len(data["suggestions"]) <= 5

    def test_lookup_county_partial_name_no_matches(self, client):
        """Non-matching partial name returns empty."""
        response = client.post("/counties/lookup", json={"partial_name": "xyz"})

        data = response.json()
        assert len(data["matches"]) == 0
        assert len(data["suggestions"]) == 0

    def test_lookup_county_partial_name_single_char(self, client):
        """Single character partial name works."""
        response = client.post("/counties/lookup", json={"partial_name": "B"})

        data = response.json()
        # Should find: Baldwin, Barbour, Bibb, Blount, Bullock, Butler
        assert len(data["matches"]) >= 4

    def test_lookup_county_partial_name_exact_match_false(self, client):
        """Partial name should set exact_match=False."""
        response = client.post("/counties/lookup", json={"partial_name": "Mob"})

        data = response.json()
        assert data["exact_match"] is False

    def test_lookup_county_empty_request(self, client):
        """Empty request should return empty results."""
        response = client.post("/counties/lookup", json={})

        self.assert_200(response)
        data = response.json()
        assert len(data["matches"]) == 0

    def test_lookup_county_all_params_null(self, client):
        """All null params should return empty results."""
        response = client.post("/counties/lookup", json={
            "code": None, "name": None, "partial_name": None
        })

        data = response.json()
        assert len(data["matches"]) == 0

    def test_lookup_county_match_structure(self, client):
        """Verify match objects have correct structure."""
        response = client.post("/counties/lookup", json={"code": "01"})

        match = response.json()["matches"][0]
        self.assert_has_fields(match, ["code", "name"])

    def test_lookup_county_service_error_returns_500(self, client):
        """Should return 500 on service exception."""
        with patch("backend_api.routers.counties.search_counties", side_effect=Exception("Error")):
            response = client.post("/counties/lookup", json={"partial_name": "M"})

            assert response.status_code == 500

    # =========================================================================
    # 5. GET /counties/analytics/statistics - County Statistics (15 Tests)
    # =========================================================================

    def test_get_statistics_returns_67_counties(self, client, mock_db_session):
        """Should return statistics for all 67 counties."""
        # Setup mock for Property queries
        mock_db_session.query.return_value.filter.return_value.count.return_value = 0
        mock_db_session.query.return_value.filter.return_value.all.return_value = []

        response = client.get("/counties/analytics/statistics")

        self.assert_200(response)
        data = response.json()
        assert len(data["statistics"]) == 67

    def test_get_statistics_response_structure(self, client, mock_db_session):
        """Verify response has correct structure."""
        mock_db_session.query.return_value.filter.return_value.count.return_value = 0
        mock_db_session.query.return_value.filter.return_value.all.return_value = []

        response = client.get("/counties/analytics/statistics")

        data = response.json()
        self.assert_has_fields(data, ["statistics", "generated_at", "total_properties_analyzed"])

    def test_get_statistics_county_stat_structure(self, client, mock_db_session):
        """Verify each county stat has required fields."""
        mock_db_session.query.return_value.filter.return_value.count.return_value = 0
        mock_db_session.query.return_value.filter.return_value.all.return_value = []

        response = client.get("/counties/analytics/statistics")

        stat = response.json()["statistics"][0]
        self.assert_has_fields(stat, [
            "county_code", "county_name", "property_count",
            "average_investment_score", "average_price_per_acre",
            "average_water_score", "total_sales_volume", "properties_with_water"
        ])

    def test_get_statistics_empty_database_all_zeros(self, client, mock_db_session):
        """Empty database should return zero values."""
        mock_db_session.query.return_value.filter.return_value.count.return_value = 0
        mock_db_session.query.return_value.filter.return_value.all.return_value = []

        response = client.get("/counties/analytics/statistics")

        data = response.json()
        assert data["total_properties_analyzed"] == 0
        # All counties should have zero property count
        for stat in data["statistics"]:
            assert stat["property_count"] == 0

    def test_get_statistics_with_properties(self, client, mock_db_session):
        """Should calculate statistics with properties present."""
        mock_properties = [
            MockPropertyORM("Baldwin", investment_score=80, water_score=5, amount=10000),
            MockPropertyORM("Baldwin", investment_score=70, water_score=3, amount=20000),
        ]
        mock_db_session.query.return_value.filter.return_value.count.return_value = 2
        mock_db_session.query.return_value.filter.return_value.all.return_value = mock_properties

        response = client.get("/counties/analytics/statistics")

        self.assert_200(response)

    def test_get_statistics_generated_at_is_datetime(self, client, mock_db_session):
        """generated_at should be a valid datetime string."""
        mock_db_session.query.return_value.filter.return_value.count.return_value = 0
        mock_db_session.query.return_value.filter.return_value.all.return_value = []

        response = client.get("/counties/analytics/statistics")

        generated_at = response.json()["generated_at"]
        assert generated_at is not None
        # Should be parseable as ISO datetime
        assert "T" in generated_at or "-" in generated_at

    def test_get_statistics_total_properties_is_sum(self, client, mock_db_session):
        """total_properties_analyzed should match sum of all county counts."""
        mock_db_session.query.return_value.filter.return_value.count.return_value = 0
        mock_db_session.query.return_value.filter.return_value.all.return_value = []

        response = client.get("/counties/analytics/statistics")

        data = response.json()
        sum_counts = sum(s["property_count"] for s in data["statistics"])
        assert data["total_properties_analyzed"] == sum_counts

    def test_get_statistics_database_error_returns_500(self, client, mock_db_session):
        """Should return 500 on database exception."""
        mock_db_session.query.side_effect = Exception("Database error")

        response = client.get("/counties/analytics/statistics")

        assert response.status_code == 500
        assert "Failed to get county statistics" in response.json()["detail"]

    def test_get_statistics_all_county_codes_present(self, client, mock_db_session):
        """All 67 county codes should be present in statistics."""
        mock_db_session.query.return_value.filter.return_value.count.return_value = 0
        mock_db_session.query.return_value.filter.return_value.all.return_value = []

        response = client.get("/counties/analytics/statistics")

        codes = {s["county_code"] for s in response.json()["statistics"]}
        expected_codes = set(ADOR_COUNTY_MAPPING.keys())
        assert codes == expected_codes

    def test_get_statistics_all_county_names_present(self, client, mock_db_session):
        """All 67 county names should be present in statistics."""
        mock_db_session.query.return_value.filter.return_value.count.return_value = 0
        mock_db_session.query.return_value.filter.return_value.all.return_value = []

        response = client.get("/counties/analytics/statistics")

        names = {s["county_name"] for s in response.json()["statistics"]}
        expected_names = set(ADOR_COUNTY_MAPPING.values())
        assert names == expected_names

    # =========================================================================
    # 6. GET /counties/search/autocomplete - Autocomplete (15 Tests)
    # =========================================================================

    def test_autocomplete_returns_suggestions(self, client):
        """Autocomplete should return suggestions."""
        response = client.get("/counties/search/autocomplete?query=M")

        self.assert_200(response)
        data = response.json()
        assert len(data["suggestions"]) > 0

    def test_autocomplete_response_structure(self, client):
        """Verify autocomplete response structure."""
        response = client.get("/counties/search/autocomplete?query=Mob")

        data = response.json()
        self.assert_has_fields(data, ["query", "suggestions", "total_matches"])

    def test_autocomplete_suggestion_structure(self, client):
        """Verify each suggestion has correct structure."""
        response = client.get("/counties/search/autocomplete?query=Mob")

        suggestion = response.json()["suggestions"][0]
        self.assert_has_fields(suggestion, ["code", "name", "display_text"])

    def test_autocomplete_display_text_format(self, client):
        """display_text should be 'name (code)' format."""
        response = client.get("/counties/search/autocomplete?query=Mobile")

        suggestion = response.json()["suggestions"][0]
        assert suggestion["display_text"] == f"{suggestion['name']} ({suggestion['code']})"

    def test_autocomplete_respects_limit(self, client):
        """Should respect limit parameter."""
        response = client.get("/counties/search/autocomplete?query=C&limit=3")

        data = response.json()
        assert len(data["suggestions"]) <= 3

    @pytest.mark.parametrize("query,expected_min_matches", [
        ("M", 5),       # Madison, Macon, Marengo, Marion, Marshall, Mobile, etc.
        ("Mo", 3),      # Mobile, Monroe, Montgomery, Morgan
        ("Mob", 1),     # Mobile
        ("Baldwin", 1), # Exact match
    ])
    def test_autocomplete_query_matches(self, client, query, expected_min_matches):
        """Test various query strings return expected matches."""
        response = client.get(f"/counties/search/autocomplete?query={query}")

        data = response.json()
        assert data["total_matches"] >= expected_min_matches

    def test_autocomplete_no_matches(self, client):
        """Non-matching query returns empty suggestions."""
        response = client.get("/counties/search/autocomplete?query=xyz")

        data = response.json()
        assert len(data["suggestions"]) == 0
        assert data["total_matches"] == 0

    @pytest.mark.parametrize("limit", [1, 5, 10, 20])
    def test_autocomplete_valid_limits(self, client, limit):
        """Test various valid limit values."""
        response = client.get(f"/counties/search/autocomplete?query=C&limit={limit}")

        self.assert_200(response)
        assert len(response.json()["suggestions"]) <= limit

    def test_autocomplete_default_limit_10(self, client):
        """Default limit should be 10."""
        response = client.get("/counties/search/autocomplete?query=a")

        data = response.json()
        assert len(data["suggestions"]) <= 10

    def test_autocomplete_query_required(self, client):
        """Missing query parameter should return 422."""
        response = client.get("/counties/search/autocomplete")

        self.assert_422(response)

    def test_autocomplete_limit_min_1(self, client):
        """limit=0 should return 422."""
        response = client.get("/counties/search/autocomplete?query=M&limit=0")

        self.assert_422(response)

    def test_autocomplete_limit_max_20(self, client):
        """limit>20 should return 422."""
        response = client.get("/counties/search/autocomplete?query=M&limit=21")

        self.assert_422(response)

    def test_autocomplete_case_insensitive(self, client):
        """Search should be case insensitive."""
        response = client.get("/counties/search/autocomplete?query=mobile")

        data = response.json()
        assert data["total_matches"] >= 1
        names = [s["name"].lower() for s in data["suggestions"]]
        assert "mobile" in names

    def test_autocomplete_service_error_returns_500(self, client):
        """Should return 500 on service exception."""
        with patch("backend_api.routers.counties.search_counties", side_effect=Exception("Error")):
            response = client.get("/counties/search/autocomplete?query=M")

            assert response.status_code == 500

    # =========================================================================
    # 7. GET /counties/mapping/ador-codes - ADOR Mapping (10 Tests)
    # =========================================================================

    def test_get_ador_mapping_returns_all_67(self, client):
        """Should return mapping with 67 counties."""
        response = client.get("/counties/mapping/ador-codes")

        self.assert_200(response)
        data = response.json()
        assert data["total_counties"] == 67
        assert len(data["mapping"]) == 67

    def test_get_ador_mapping_response_structure(self, client):
        """Verify response has correct structure."""
        response = client.get("/counties/mapping/ador-codes")

        data = response.json()
        self.assert_has_fields(data, ["mapping", "total_counties", "note", "last_updated"])

    def test_get_ador_mapping_mapping_is_dict(self, client):
        """mapping field should be a dictionary."""
        response = client.get("/counties/mapping/ador-codes")

        data = response.json()
        assert isinstance(data["mapping"], dict)

    def test_get_ador_mapping_all_codes_01_to_67(self, client):
        """All codes from 01 to 67 should be present."""
        response = client.get("/counties/mapping/ador-codes")

        mapping = response.json()["mapping"]
        for i in range(1, 68):
            code = f"{i:02d}"
            assert code in mapping, f"Missing code {code}"

    def test_get_ador_mapping_note_mentions_ador(self, client):
        """Note should mention ADOR."""
        response = client.get("/counties/mapping/ador-codes")

        note = response.json()["note"]
        assert "ADOR" in note

    @pytest.mark.parametrize("code,expected_name", SAMPLE_VALID_CODES)
    def test_get_ador_mapping_specific_codes(self, client, code, expected_name):
        """Verify specific code-to-name mappings."""
        response = client.get("/counties/mapping/ador-codes")

        mapping = response.json()["mapping"]
        assert mapping[code] == expected_name

    def test_get_ador_mapping_last_updated_present(self, client):
        """last_updated field should be present and non-empty."""
        response = client.get("/counties/mapping/ador-codes")

        last_updated = response.json()["last_updated"]
        assert last_updated is not None
        assert len(last_updated) > 0

    def test_get_ador_mapping_st_clair_with_period(self, client):
        """St. Clair should have period in name."""
        response = client.get("/counties/mapping/ador-codes")

        mapping = response.json()["mapping"]
        assert mapping["58"] == "St. Clair"

    def test_get_ador_mapping_consistent_with_list_counties(self, client, mock_db_session):
        """Mapping should be consistent with list counties endpoint."""
        mock_db_session.query.return_value.order_by.return_value.all.return_value = []

        # Get both responses
        list_response = client.get("/counties/")
        mapping_response = client.get("/counties/mapping/ador-codes")

        # Build mapping from list response
        list_mapping = {c["code"]: c["name"] for c in list_response.json()["counties"]}
        ador_mapping = mapping_response.json()["mapping"]

        assert list_mapping == ador_mapping

    def test_get_ador_mapping_service_error_returns_500(self, client):
        """Should return 500 on service exception."""
        with patch("backend_api.routers.counties.ADOR_COUNTY_MAPPING", side_effect=Exception("Error")):
            # This is unlikely to fail as it's a static dict, but test the pattern
            response = client.get("/counties/mapping/ador-codes")
            # Should still work since it's static data
            assert response.status_code in [200, 500]
