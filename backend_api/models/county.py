"""
Pydantic models for Alabama County API operations
CRITICAL: County codes and names must exactly match iOS CountyValidator.swift
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime

class CountyResponse(BaseModel):
    """Model for county API responses."""
    code: str = Field(..., description="ADOR alphabetical county code (01-67)")
    name: str = Field(..., description="Alabama county name")
    created_at: Optional[datetime] = Field(None, description="Record creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        from_attributes = True  # Enable ORM mode for SQLAlchemy compatibility

class CountyListResponse(BaseModel):
    """Model for county list API responses."""
    counties: List[CountyResponse] = Field(..., description="List of all 67 Alabama counties")
    total_count: int = Field(67, description="Total number of Alabama counties")

class CountyValidationRequest(BaseModel):
    """Model for validating county codes or names."""
    code: Optional[str] = Field(None, description="County code to validate (01-67)")
    name: Optional[str] = Field(None, description="County name to validate")

    @field_validator('code')
    @classmethod
    def validate_county_code(cls, v: Optional[str]) -> Optional[str]:
        """Validate ADOR county code format and range."""
        if v is None:
            return v

        # Must be 2-digit string
        if not isinstance(v, str) or len(v) != 2:
            raise ValueError("County code must be a 2-digit string")

        try:
            code_int = int(v)
            if code_int < 1 or code_int > 67:
                raise ValueError("County code must be between 01 and 67")
        except ValueError:
            raise ValueError("County code must be numeric")

        return v

    @field_validator('name')
    @classmethod
    def validate_county_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate Alabama county name against official list."""
        if v is None:
            return v

        # Valid Alabama counties (must match iOS CountyValidator.swift exactly)
        valid_counties = {
            "Autauga", "Mobile", "Baldwin", "Barbour", "Bibb", "Blount", "Bullock", "Butler",
            "Calhoun", "Chambers", "Cherokee", "Chilton", "Choctaw", "Clarke", "Clay",
            "Cleburne", "Coffee", "Colbert", "Conecuh", "Coosa", "Covington", "Crenshaw",
            "Cullman", "Dale", "Dallas", "DeKalb", "Elmore", "Escambia", "Etowah",
            "Fayette", "Franklin", "Geneva", "Greene", "Hale", "Henry", "Houston",
            "Jackson", "Jefferson", "Lamar", "Lauderdale", "Lawrence", "Lee", "Limestone",
            "Lowndes", "Macon", "Madison", "Marengo", "Marion", "Marshall", "Monroe",
            "Montgomery", "Morgan", "Perry", "Pickens", "Pike", "Randolph", "Russell",
            "St. Clair", "Shelby", "Sumter", "Talladega", "Tallapoosa", "Tuscaloosa",
            "Walker", "Washington", "Wilcox", "Winston"
        }

        if v not in valid_counties:
            raise ValueError(f"Invalid Alabama county name: {v}")

        return v

class CountyValidationResponse(BaseModel):
    """Model for county validation responses."""
    is_valid: bool = Field(..., description="Whether the county code/name is valid")
    code: Optional[str] = Field(None, description="Valid county code")
    name: Optional[str] = Field(None, description="Valid county name")
    error_message: Optional[str] = Field(None, description="Error message if validation failed")

class CountyLookupRequest(BaseModel):
    """Model for county lookup operations."""
    code: Optional[str] = Field(None, description="Look up county by code")
    name: Optional[str] = Field(None, description="Look up county by name")
    partial_name: Optional[str] = Field(None, description="Partial county name for search")

class CountyLookupResponse(BaseModel):
    """Model for county lookup responses."""
    matches: List[CountyResponse] = Field(..., description="Matching counties")
    exact_match: bool = Field(..., description="Whether an exact match was found")
    suggestions: List[str] = Field(default=[], description="Suggested county names for partial matches")

class CountyStatistics(BaseModel):
    """Model for county-related statistics."""
    county_code: str = Field(..., description="ADOR county code")
    county_name: str = Field(..., description="County name")
    property_count: int = Field(..., description="Number of properties in this county")
    average_investment_score: Optional[float] = Field(None, description="Average investment score for county")
    average_price_per_acre: Optional[float] = Field(None, description="Average price per acre for county")
    average_water_score: Optional[float] = Field(None, description="Average water score for county")
    total_sales_volume: Optional[float] = Field(None, description="Total sales volume in USD")
    properties_with_water: int = Field(default=0, description="Number of properties with water features")

class CountyStatisticsResponse(BaseModel):
    """Model for county statistics API responses."""
    statistics: List[CountyStatistics] = Field(..., description="Statistics for all counties")
    generated_at: datetime = Field(..., description="When statistics were generated")
    total_properties_analyzed: int = Field(..., description="Total number of properties included in analysis")

# ADOR County Code Mapping (CRITICAL: Must match iOS exactly)
ADOR_COUNTY_MAPPING = {
    "01": "Autauga", "02": "Mobile", "03": "Baldwin", "04": "Barbour", "05": "Bibb",
    "06": "Blount", "07": "Bullock", "08": "Butler", "09": "Calhoun", "10": "Chambers",
    "11": "Cherokee", "12": "Chilton", "13": "Choctaw", "14": "Clarke", "15": "Clay",
    "16": "Cleburne", "17": "Coffee", "18": "Colbert", "19": "Conecuh", "20": "Coosa",
    "21": "Covington", "22": "Crenshaw", "23": "Cullman", "24": "Dale", "25": "Dallas",
    "26": "DeKalb", "27": "Elmore", "28": "Escambia", "29": "Etowah", "30": "Fayette",
    "31": "Franklin", "32": "Geneva", "33": "Greene", "34": "Hale", "35": "Henry",
    "36": "Houston", "37": "Jackson", "38": "Jefferson", "39": "Lamar", "40": "Lauderdale",
    "41": "Lawrence", "42": "Lee", "43": "Limestone", "44": "Lowndes", "45": "Macon",
    "46": "Madison", "47": "Marengo", "48": "Marion", "49": "Marshall", "50": "Monroe",
    "51": "Montgomery", "52": "Morgan", "53": "Perry", "54": "Pickens", "55": "Pike",
    "56": "Randolph", "57": "Russell", "58": "St. Clair", "59": "Shelby", "60": "Sumter",
    "61": "Talladega", "62": "Tallapoosa", "63": "Tuscaloosa", "64": "Walker", "65": "Washington",
    "66": "Wilcox", "67": "Winston"
}

# Reverse mapping for name-to-code lookups
COUNTY_NAME_TO_CODE = {name: code for code, name in ADOR_COUNTY_MAPPING.items()}

def validate_county_code(code: str) -> bool:
    """Validate ADOR county code."""
    return code in ADOR_COUNTY_MAPPING

def validate_county_name(name: str) -> bool:
    """Validate Alabama county name."""
    return name in COUNTY_NAME_TO_CODE

def get_county_by_code(code: str) -> Optional[str]:
    """Get county name by ADOR code."""
    return ADOR_COUNTY_MAPPING.get(code)

def get_county_by_name(name: str) -> Optional[str]:
    """Get county code by name."""
    return COUNTY_NAME_TO_CODE.get(name)

def get_all_counties() -> List[dict]:
    """Get all Alabama counties as list of dictionaries."""
    return [{"code": code, "name": name} for code, name in ADOR_COUNTY_MAPPING.items()]

def search_counties(partial_name: str) -> List[dict]:
    """Search counties by partial name (case-insensitive)."""
    partial_lower = partial_name.lower()
    matches = []

    for code, name in ADOR_COUNTY_MAPPING.items():
        if partial_lower in name.lower():
            matches.append({"code": code, "name": name})

    return matches