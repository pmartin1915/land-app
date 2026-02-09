"""
CSV Import API endpoints.
Provides bulk property import from CSV files with validation and preview.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import logging
import csv
import io
from datetime import datetime

from ..database.connection import get_db
from ..database.models import Property
from ..auth import get_current_user_or_api_key
from ..config import limiter
from ..services.property_service import PropertyService
from ..models.property import PropertyCreate

logger = logging.getLogger(__name__)

router = APIRouter()


# Column mapping for common CSV header variations
COLUMN_ALIASES = {
    'parcel_id': ['parcel_id', 'parcel', 'parcel_number', 'parcel_num', 'pid', 'parcel id'],
    'amount': ['amount', 'price', 'bid', 'bid_amount', 'sale_price', 'asking_price'],
    'acreage': ['acreage', 'acres', 'area', 'lot_size', 'size'],
    'county': ['county', 'county_name'],
    'state': ['state', 'state_code', 'st'],
    'description': ['description', 'legal_description', 'legal', 'property_description', 'desc'],
    'owner_name': ['owner_name', 'owner', 'property_owner', 'name'],
    'year_sold': ['year_sold', 'year', 'sale_year', 'tax_year'],
    'assessed_value': ['assessed_value', 'assessed', 'value', 'tax_value'],
    'sale_type': ['sale_type', 'type', 'auction_type'],
    'redemption_period_days': ['redemption_period_days', 'redemption_days', 'redemption'],
    'auction_date': ['auction_date', 'auction', 'sale_date', 'date'],
    'auction_platform': ['auction_platform', 'platform', 'source'],
    'data_source': ['data_source', 'source', 'origin'],
    'estimated_market_value': ['estimated_market_value', 'market_value', 'fmv'],
}

# Required fields for import
REQUIRED_FIELDS = ['parcel_id', 'amount']

# All importable fields
IMPORTABLE_FIELDS = list(COLUMN_ALIASES.keys())


class CSVColumnMapping(BaseModel):
    """Mapping from CSV column names to property fields."""
    parcel_id: Optional[str] = None
    amount: Optional[str] = None
    acreage: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    description: Optional[str] = None
    owner_name: Optional[str] = None
    year_sold: Optional[str] = None
    assessed_value: Optional[str] = None
    sale_type: Optional[str] = None
    redemption_period_days: Optional[str] = None
    auction_date: Optional[str] = None
    auction_platform: Optional[str] = None
    data_source: Optional[str] = None
    estimated_market_value: Optional[str] = None


class CSVPreviewResponse(BaseModel):
    """Response model for CSV preview."""
    headers: List[str]
    rows: List[List[str]]
    total_rows: int
    suggested_mapping: Dict[str, Optional[str]]
    unmapped_headers: List[str]
    potential_duplicates: int


class CSVImportRequest(BaseModel):
    """Request model for CSV import with column mapping."""
    mapping: CSVColumnMapping
    skip_duplicates: bool = Field(True, description="Skip rows with duplicate parcel_ids")
    default_state: str = Field('AL', description="Default state if not in CSV")


class CSVImportRowError(BaseModel):
    """Error details for a failed row."""
    row: int
    field: Optional[str] = None
    error: str


class CSVImportResponse(BaseModel):
    """Response model for CSV import results."""
    imported: int
    skipped_duplicates: int
    errors: int
    failed_rows: List[CSVImportRowError]


def detect_column_mapping(headers: List[str]) -> Dict[str, Optional[str]]:
    """
    Auto-detect column mapping based on CSV headers.
    Returns a dict mapping property fields to CSV column names.
    """
    mapping = {}
    headers_lower = {h.lower().strip(): h for h in headers}

    for field, aliases in COLUMN_ALIASES.items():
        mapping[field] = None
        for alias in aliases:
            if alias.lower() in headers_lower:
                mapping[field] = headers_lower[alias.lower()]
                break

    return mapping


def get_unmapped_headers(headers: List[str], mapping: Dict[str, Optional[str]]) -> List[str]:
    """Get list of headers that weren't auto-mapped."""
    mapped_headers = set(v for v in mapping.values() if v is not None)
    return [h for h in headers if h not in mapped_headers]


def parse_csv_value(value: str, field: str) -> Any:
    """Parse a CSV value to the appropriate type for a field."""
    if not value or value.strip() == '':
        return None

    value = value.strip()

    # Numeric fields
    if field in ['amount', 'acreage', 'assessed_value', 'estimated_market_value']:
        try:
            # Remove currency symbols and commas
            cleaned = value.replace('$', '').replace(',', '').strip()
            return float(cleaned)
        except ValueError:
            return None

    # Integer fields
    if field in ['redemption_period_days']:
        try:
            return int(value)
        except ValueError:
            return None

    # Date fields
    if field in ['auction_date']:
        # Try common date formats
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None

    # String fields - return as-is
    return value


def get_property_service(db: Session = Depends(get_db)) -> PropertyService:
    """Dependency to get PropertyService instance."""
    return PropertyService(db)


@router.post("/csv/preview", response_model=CSVPreviewResponse)
@limiter.limit("30/minute")
async def preview_csv(
    request: Request,
    file: UploadFile = File(...),
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Preview a CSV file and suggest column mappings.
    Returns headers, sample rows, and auto-detected field mapping.
    """
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV file")

        # Read file content (limit to 5MB)
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 5MB)")

        # Decode and parse CSV
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            # Try latin-1 as fallback
            text = content.decode('latin-1')

        reader = csv.reader(io.StringIO(text))
        rows = list(reader)

        if len(rows) < 2:
            raise HTTPException(status_code=400, detail="CSV must have headers and at least one data row")

        headers = rows[0]
        data_rows = rows[1:]

        # Auto-detect column mapping
        suggested_mapping = detect_column_mapping(headers)
        unmapped_headers = get_unmapped_headers(headers, suggested_mapping)

        # Count potential duplicates
        parcel_col = suggested_mapping.get('parcel_id')
        potential_duplicates = 0
        if parcel_col:
            col_idx = headers.index(parcel_col)
            parcel_ids = [row[col_idx] for row in data_rows if len(row) > col_idx and row[col_idx]]
            # Check for duplicates within CSV
            seen = set()
            for pid in parcel_ids:
                if pid in seen:
                    potential_duplicates += 1
                seen.add(pid)
            # Check for duplicates in database
            existing = db.query(Property.parcel_id).filter(
                Property.parcel_id.in_(list(seen)),
                Property.is_deleted == False
            ).all()
            potential_duplicates += len(existing)

        # Return preview (first 10 rows max)
        preview_rows = [row for row in data_rows[:10]]

        return CSVPreviewResponse(
            headers=headers,
            rows=preview_rows,
            total_rows=len(data_rows),
            suggested_mapping=suggested_mapping,
            unmapped_headers=unmapped_headers,
            potential_duplicates=potential_duplicates
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to preview CSV: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to parse CSV: {str(e)}")


@router.post("/csv", response_model=CSVImportResponse)
@limiter.limit("5/minute")
async def import_csv(
    request: Request,
    file: UploadFile = File(...),
    skip_duplicates: bool = True,
    default_state: str = 'AL',
    parcel_id_col: Optional[str] = None,
    amount_col: Optional[str] = None,
    acreage_col: Optional[str] = None,
    county_col: Optional[str] = None,
    state_col: Optional[str] = None,
    description_col: Optional[str] = None,
    owner_name_col: Optional[str] = None,
    year_sold_col: Optional[str] = None,
    assessed_value_col: Optional[str] = None,
    auth_data: dict = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db)
):
    """
    Import properties from a CSV file.
    Column mapping can be specified via query parameters or auto-detected.
    """
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV file")

        # Read file content (limit to 10MB for import)
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")

        # Decode and parse CSV
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            text = content.decode('latin-1')

        reader = csv.reader(io.StringIO(text))
        rows = list(reader)

        if len(rows) < 2:
            raise HTTPException(status_code=400, detail="CSV must have headers and at least one data row")

        headers = rows[0]
        data_rows = rows[1:]

        # Build column mapping from query params or auto-detect
        mapping = {}
        if parcel_id_col:
            mapping['parcel_id'] = parcel_id_col
        if amount_col:
            mapping['amount'] = amount_col
        if acreage_col:
            mapping['acreage'] = acreage_col
        if county_col:
            mapping['county'] = county_col
        if state_col:
            mapping['state'] = state_col
        if description_col:
            mapping['description'] = description_col
        if owner_name_col:
            mapping['owner_name'] = owner_name_col
        if year_sold_col:
            mapping['year_sold'] = year_sold_col
        if assessed_value_col:
            mapping['assessed_value'] = assessed_value_col

        # Auto-detect any missing mappings
        auto_mapping = detect_column_mapping(headers)
        for field, col in auto_mapping.items():
            if field not in mapping and col:
                mapping[field] = col

        # Validate required fields are mapped
        for required in REQUIRED_FIELDS:
            if required not in mapping or not mapping[required]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Required field '{required}' could not be mapped. Please specify column name."
                )

        # Build column index lookup
        col_indices = {field: headers.index(col) for field, col in mapping.items() if col and col in headers}

        # Get existing parcel IDs for duplicate check
        existing_parcel_ids = set()
        if skip_duplicates:
            existing = db.query(Property.parcel_id).filter(Property.is_deleted == False).all()
            existing_parcel_ids = {p.parcel_id for p in existing}

        # Process rows
        property_service = PropertyService(db)
        device_id = auth_data.get('user_id', 'csv-import')

        imported = 0
        skipped_duplicates = 0
        errors = 0
        failed_rows: List[CSVImportRowError] = []

        for row_num, row in enumerate(data_rows, start=2):  # Start at 2 (1 is header)
            try:
                # Extract values based on mapping
                property_data = {}
                for field, col_idx in col_indices.items():
                    if col_idx < len(row):
                        value = parse_csv_value(row[col_idx], field)
                        if value is not None:
                            property_data[field] = value

                # Apply default state if not in data
                if 'state' not in property_data or not property_data['state']:
                    property_data['state'] = default_state

                # Validate required fields
                if 'parcel_id' not in property_data or not property_data['parcel_id']:
                    failed_rows.append(CSVImportRowError(
                        row=row_num,
                        field='parcel_id',
                        error='Missing required parcel_id'
                    ))
                    errors += 1
                    continue

                if 'amount' not in property_data or not property_data['amount']:
                    failed_rows.append(CSVImportRowError(
                        row=row_num,
                        field='amount',
                        error='Missing required amount'
                    ))
                    errors += 1
                    continue

                # Check for duplicates
                parcel_id = property_data['parcel_id']
                if skip_duplicates and parcel_id in existing_parcel_ids:
                    skipped_duplicates += 1
                    continue

                # Create property using service (handles validation and calculations)
                try:
                    # Create PropertyCreate model for validation
                    property_create = PropertyCreate(**property_data)

                    # Create property in database
                    new_property = Property(
                        **property_create.model_dump(exclude_unset=True),
                        device_id=device_id,
                        data_source=property_data.get('data_source', 'csv-import')
                    )

                    # Calculate metrics
                    metrics = property_service.calculate_property_metrics(property_create.model_dump())
                    for key, value in metrics.items():
                        if hasattr(new_property, key):
                            setattr(new_property, key, value)

                    db.add(new_property)
                    existing_parcel_ids.add(parcel_id)  # Track for duplicates within batch
                    imported += 1

                except ValueError as ve:
                    failed_rows.append(CSVImportRowError(
                        row=row_num,
                        error=str(ve)
                    ))
                    errors += 1
                    continue

            except Exception as e:
                failed_rows.append(CSVImportRowError(
                    row=row_num,
                    error=str(e)
                ))
                errors += 1

        # Commit all successful imports
        if imported > 0:
            db.commit()

        logger.info(f"CSV import complete: {imported} imported, {skipped_duplicates} duplicates skipped, {errors} errors")

        return CSVImportResponse(
            imported=imported,
            skipped_duplicates=skipped_duplicates,
            errors=errors,
            failed_rows=failed_rows[:50]  # Limit error details to first 50
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to import CSV: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/columns")
@limiter.limit("60/minute")
async def get_importable_columns(request: Request):
    """
    Get list of importable columns and their aliases.
    Useful for building column mapping UI.
    """
    return {
        "required_fields": REQUIRED_FIELDS,
        "importable_fields": IMPORTABLE_FIELDS,
        "column_aliases": COLUMN_ALIASES
    }
