# Alabama Auction Watcher - API Reference

Complete API reference for all modules, functions, and classes in the Alabama Auction Watcher system.

## Quick Reference

### Core Modules
- **[scripts.parser](#scriptsparser)**: Main orchestrator and CLI interface
- **[scripts.scraper](#scriptsscraper)**: Web scraping engine for ADOR data
- **[scripts.utils](#scriptsutils)**: Data processing and utility functions
- **[scripts.exceptions](#scriptsexceptions)**: Custom exception classes
- **[config.settings](#configsettings)**: Configuration parameters
- **[config.logging_config](#configlogging_config)**: Structured logging setup

### Key Functions
- `scrape_county_data()`: Scrape property data from ADOR website
- `process_scraped_data()`: Complete data processing pipeline
- `calculate_investment_score()`: Property investment analysis
- `parse_acreage_from_description()`: Extract acreage from legal descriptions
- `calculate_water_score()`: Detect and score water features

---

## scripts.parser

Main orchestrator module that provides the CLI interface and coordinates all data processing operations.

### Classes

#### `class AuctionParser`
Main parser class for processing ADOR CSV files.

```python
class AuctionParser:
    def __init__(
        self,
        min_acres: float = MIN_ACRES,
        max_acres: float = MAX_ACRES,
        max_price: float = MAX_PRICE,
        infer_acres: bool = False
    )
```

**Parameters:**
- `min_acres` (float): Minimum acreage filter (default: 1.0)
- `max_acres` (float): Maximum acreage filter (default: 5.0)
- `max_price` (float): Maximum price filter (default: 20000.0)
- `infer_acres` (bool): Whether to infer acreage from descriptions (default: False)

**Methods:**

##### `load_csv_file(file_path: str) -> pd.DataFrame`
Load CSV file with flexible delimiter and encoding detection.

**Parameters:**
- `file_path` (str): Path to the CSV file

**Returns:**
- `pd.DataFrame`: Loaded data

**Raises:**
- `FileNotFoundError`: If file doesn't exist
- `DataProcessingError`: If file cannot be read

**Example:**
```python
parser = AuctionParser()
df = parser.load_csv_file("data/raw/county_data.csv")
```

##### `process_file(input_path: str, output_path: str) -> Dict[str, Any]`
Process a CSV file and generate filtered watchlist.

**Parameters:**
- `input_path` (str): Path to input CSV file
- `output_path` (str): Path for output watchlist

**Returns:**
- `Dict[str, Any]`: Processing summary with metrics

**Example:**
```python
parser = AuctionParser(min_acres=2.0, max_price=15000.0)
summary = parser.process_file("input.csv", "output.csv")
print(f"Processed {summary['original_records']} records")
```

##### `process_scraped_data(county_input: str, output_path: str, max_pages: int = 10) -> Dict[str, Any]`
Scrape county data and process into watchlist.

**Parameters:**
- `county_input` (str): County code ('05') or name ('Baldwin')
- `output_path` (str): Path for output watchlist
- `max_pages` (int): Maximum pages to scrape (default: 10)

**Returns:**
- `Dict[str, Any]`: Processing summary with metrics

**Raises:**
- `CountyValidationError`: If county is invalid
- `ScrapingError`: If web scraping fails

**Example:**
```python
parser = AuctionParser(infer_acres=True)
summary = parser.process_scraped_data("Baldwin", "watchlist.csv", max_pages=5)
```

### Functions

#### `main() -> None`
Main CLI entry point that handles command-line arguments and orchestrates processing.

**Command Line Usage:**
```bash
# Web scraping (primary method)
python scripts/parser.py --scrape-county Baldwin --infer-acres
python scripts/parser.py --scrape-county 05 --max-pages 10

# CSV file processing
python scripts/parser.py --input data.csv --output watchlist.csv

# List available counties
python scripts/parser.py --list-counties
```

**Command Line Arguments:**
- `--scrape-county`: County to scrape (name or code)
- `--input`: Input CSV file path
- `--output`: Output CSV file path (default: data/processed/watchlist.csv)
- `--max-pages`: Maximum pages to scrape (default: 10)
- `--min-acres`: Minimum acreage filter
- `--max-acres`: Maximum acreage filter
- `--max-price`: Maximum price filter
- `--infer-acres`: Enable acreage inference from descriptions
- `--list-counties`: List all available Alabama counties

---

## scripts.scraper

Web scraping engine that handles automated data collection from the Alabama Department of Revenue website.

### Constants

#### `ALABAMA_COUNTY_CODES: Dict[str, str]`
Complete mapping of Alabama county codes to names (alphabetical ADOR ordering).

**Example:**
```python
{
    '01': 'Autauga',
    '02': 'Mobile',
    '03': 'Barbour',
    '05': 'Baldwin',
    # ... all 67 counties
}
```

#### `COUNTY_NAME_TO_CODE: Dict[str, str]`
Reverse mapping from county names to codes (uppercase keys).

#### Configuration Constants
- `ADOR_BASE_URL`: Base URL for ADOR delinquent property search
- `DEFAULT_TIMEOUT`: HTTP request timeout (30 seconds)
- `RATE_LIMIT_DELAY`: Delay between requests (2.0 seconds)
- `MAX_RETRIES`: Maximum retry attempts (3)

### Functions

#### `validate_county_code(county_input: str) -> str`
Validate and normalize county code input.

**Parameters:**
- `county_input` (str): County code (e.g., '05') or name (e.g., 'Baldwin')

**Returns:**
- `str`: Validated 2-digit county code

**Raises:**
- `CountyValidationError`: If county is not found

**Example:**
```python
code = validate_county_code('Baldwin')  # Returns '05'
code = validate_county_code('5')        # Returns '05' (zero-padded)
code = validate_county_code('05')       # Returns '05'
```

#### `get_county_name(county_code: str) -> str`
Get county name from code.

**Parameters:**
- `county_code` (str): 2-digit county code

**Returns:**
- `str`: County name or fallback string

**Example:**
```python
name = get_county_name('05')  # Returns 'Baldwin'
```

#### `scrape_county_data(county_input: str, max_pages: int = 10, save_raw: bool = True) -> pd.DataFrame`
Scrape all delinquent property data for a county.

**Parameters:**
- `county_input` (str): County code ('05') or name ('Baldwin')
- `max_pages` (int): Maximum number of pages to scrape (default: 10)
- `save_raw` (bool): Whether to save raw scraped data to CSV (default: True)

**Returns:**
- `pd.DataFrame`: All scraped property data with county information

**Raises:**
- `CountyValidationError`: Invalid county
- `NetworkError`: HTTP request failures
- `ParseError`: HTML parsing failures
- `ScrapingError`: General scraping failures

**Features:**
- Automatic pagination handling
- Rate limiting (2-3 seconds between requests)
- Duplicate record removal
- Raw data saving with timestamps
- Comprehensive error handling and logging

**Example:**
```python
# Scrape Baldwin County
df = scrape_county_data('Baldwin', max_pages=5)
print(f"Scraped {len(df)} records")

# Scrape with county code
df = scrape_county_data('05', max_pages=1, save_raw=False)
```

#### `list_available_counties() -> Dict[str, str]`
Return dictionary of available counties.

**Returns:**
- `Dict[str, str]`: County codes mapped to names

#### `search_counties(query: str) -> Dict[str, str]`
Search for counties by partial name.

**Parameters:**
- `query` (str): Search query (partial county name)

**Returns:**
- `Dict[str, str]`: Matching counties (code -> name)

**Example:**
```python
matches = search_counties('Mobile')  # Returns {'02': 'Mobile'}
matches = search_counties('B')       # Returns counties starting with 'B'
```

### Internal Functions

#### `create_session() -> requests.Session`
Create a requests session with appropriate headers for web scraping.

#### `extract_pagination_info(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str], int]`
Extract pagination information from ADOR page HTML.

#### `parse_property_table(soup: BeautifulSoup) -> pd.DataFrame`
Extract property data from HTML table using pandas and BeautifulSoup fallback.

#### `scrape_single_page(session: requests.Session, url: str, params: Dict) -> Tuple[pd.DataFrame, Dict]`
Scrape a single page of ADOR data with pagination info.

---

## scripts.utils

Data processing and utility functions for property analysis and filtering.

### Functions

#### `detect_csv_delimiter(file_path: str, sample_size: int = 1024) -> str`
Detect the delimiter used in a CSV file.

**Parameters:**
- `file_path` (str): Path to the CSV file
- `sample_size` (int): Number of bytes to analyze (default: 1024)

**Returns:**
- `str`: Detected delimiter character

#### `find_column_mapping(df_columns: List[str], target_field: str) -> Optional[str]`
Find the best matching column name for a target field using fuzzy matching.

**Parameters:**
- `df_columns` (List[str]): List of column names from DataFrame
- `target_field` (str): Target field to find (e.g., 'parcel_id', 'amount')

**Returns:**
- `Optional[str]`: Matching column name or None

**Supported Fields:**
- `parcel_id`: Parcel ID, CS Number, PIN, Tax ID
- `amount`: Amount Bid at Tax Sale, Sale Price, Bid Amount
- `assessed_value`: Assessed Value, Appraised Value, Market Value
- `description`: Property Description, Legal Description
- `acreage`: Acreage, Acres, Size, Area
- `year_sold`: Year Sold, Sale Year
- `owner_name`: Name, Owner Name, Property Owner
- `county`: County, County Name

#### `normalize_price(price_str: Any) -> Optional[float]`
Normalize price strings to float values.

**Parameters:**
- `price_str` (Any): Price string (e.g., "$1,234.56", "1234")

**Returns:**
- `Optional[float]`: Normalized price or None if invalid

**Example:**
```python
price = normalize_price("$1,234.56")    # Returns 1234.56
price = normalize_price("1234")         # Returns 1234.0
price = normalize_price("invalid")      # Returns None
```

#### `parse_acreage_from_description(description: str) -> Optional[float]`
Extract acreage information from legal property descriptions.

**Parameters:**
- `description` (str): Property legal description

**Returns:**
- `Optional[float]`: Extracted acreage or None if not found

**Supported Patterns:**
- Direct acreage: "2.5 AC", "1.25 ACRES"
- Square footage: "43560 SF" (converted to acres)
- Rectangular lots: "100' X 200'" (converted to acres)
- Fractional acres: "1/2 ACRE", "3/4 AC"

**Example:**
```python
acres = parse_acreage_from_description("LOT 1 BLK 2 2.5 AC")  # Returns 2.5
acres = parse_acreage_from_description("100' X 200' LOT")     # Returns ~0.46
acres = parse_acreage_from_description("43560 SF")            # Returns 1.0
```

#### `calculate_water_score(description: str) -> float`
Calculate water feature score based on keywords in description.

**Parameters:**
- `description` (str): Property description text

**Returns:**
- `float`: Water score (0.0 to 10.0+)

**Scoring System:**
- Primary keywords (creek, stream, river, lake, pond, spring): 3.0 points each
- Secondary keywords (branch, run, brook, tributary, wetland, marsh): 2.0 points each
- Tertiary keywords (water, aquatic, riparian, shore, bank, waterfront): 1.0 points each

**Example:**
```python
score = calculate_water_score("Property near creek and stream")  # Returns 6.0
score = calculate_water_score("Lakefront property with pond")    # Returns 6.0
score = calculate_water_score("Dry land property")              # Returns 0.0
```

#### `calculate_estimated_all_in_cost(price: float) -> float`
Calculate estimated total acquisition cost including fees.

**Parameters:**
- `price` (float): Base purchase price

**Returns:**
- `float`: Total estimated cost

**Cost Components:**
- Purchase price
- Recording fee ($35)
- County fee (5% of purchase price)
- Miscellaneous fees ($100)

**Example:**
```python
total_cost = calculate_estimated_all_in_cost(5000.0)  # Returns ~5385.0
```

#### `calculate_investment_score(price: float, acreage: float, water_score: float, assessed_value: Optional[float] = None) -> float`
Calculate composite investment score for property ranking.

**Parameters:**
- `price` (float): Property purchase price
- `acreage` (float): Property size in acres
- `water_score` (float): Water feature score
- `assessed_value` (Optional[float]): County assessed value

**Returns:**
- `float`: Investment score (0.0 to 100.0)

**Scoring Factors:**
- Price per acre competitiveness (40% weight)
- Acreage preference curve (30% weight)
- Water features bonus (20% weight)
- Assessed value ratio (10% weight, if available)

**Example:**
```python
score = calculate_investment_score(5000.0, 2.5, 3.0, 8000.0)  # Returns ~75.3
```

#### `validate_data_quality(df: pd.DataFrame) -> Dict[str, Any]`
Validate data quality and return quality metrics.

**Parameters:**
- `df` (pd.DataFrame): Input DataFrame

**Returns:**
- `Dict[str, Any]`: Quality metrics including missing values, outliers, duplicates

#### `clean_dataframe(df: pd.DataFrame) -> pd.DataFrame`
Clean DataFrame by removing empty rows, normalizing strings, and handling nulls.

**Parameters:**
- `df` (pd.DataFrame): Input DataFrame

**Returns:**
- `pd.DataFrame`: Cleaned DataFrame

### Formatting Functions

#### `format_currency(amount: float) -> str`
Format number as currency string.

#### `format_acreage(acres: float) -> str`
Format acreage with appropriate precision.

#### `format_score(score: float) -> str`
Format score with one decimal place.

---

## scripts.exceptions

Custom exception classes for better error handling and user feedback.

### Base Exception

#### `class AuctionWatcherError(Exception)`
Base exception class for all auction watcher errors.

### Validation Exceptions

#### `class DataValidationError(AuctionWatcherError)`
Raised when data validation fails.

**Attributes:**
- `field` (str): Field that failed validation
- `value` (str): Invalid value

#### `class CountyValidationError(AuctionWatcherError)`
Raised when county code or name validation fails.

**Attributes:**
- `county_input` (str): Invalid county input

#### `class FilterValidationError(DataValidationError)`
Raised when filter parameters are invalid.

### Scraping Exceptions

#### `class ScrapingError(AuctionWatcherError)`
Base class for web scraping related errors.

#### `class NetworkError(ScrapingError)`
Raised when network-related errors occur during scraping.

**Attributes:**
- `url` (str): URL that failed
- `status_code` (int): HTTP status code

#### `class ParseError(ScrapingError)`
Raised when HTML parsing fails during scraping.

**Attributes:**
- `page_content_length` (int): Length of content that failed to parse

#### `class RateLimitError(ScrapingError)`
Raised when rate limiting is triggered.

**Attributes:**
- `retry_after` (int): Seconds to wait before retry

### Processing Exceptions

#### `class DataProcessingError(AuctionWatcherError)`
Raised when data processing operations fail.

**Attributes:**
- `operation` (str): Operation that failed
- `records_affected` (int): Number of records affected

#### `class InvestmentCalculationError(DataProcessingError)`
Raised when investment metric calculations fail.

**Attributes:**
- `property_id` (str): Property identifier
- `metric` (str): Metric that failed calculation

### System Exceptions

#### `class ConfigurationError(AuctionWatcherError)`
Raised when configuration is invalid or missing.

**Attributes:**
- `config_key` (str): Configuration key that's invalid

#### `class FileOperationError(AuctionWatcherError)`
Raised when file operations fail.

**Attributes:**
- `file_path` (str): File path that failed
- `operation` (str): Operation type (read, write, delete)

### Utility Functions

#### `safe_float_conversion(value, field_name: str = None) -> float`
Safely convert value to float with meaningful error messages.

#### `safe_int_conversion(value, field_name: str = None) -> int`
Safely convert value to int with meaningful error messages.

#### `validate_positive_number(value, field_name: str = None) -> float`
Validate that a value is a positive number.

#### `validate_range(value, min_val: float = None, max_val: float = None, field_name: str = None) -> float`
Validate that a value is within a specified range.

---

## config.settings

Configuration parameters for filtering, scoring, and system behavior.

### Filtering Settings

```python
# Property filtering criteria
MIN_ACRES = 1.0                # Minimum acreage
MAX_ACRES = 5.0                # Maximum acreage
MAX_PRICE = 20000.0            # Maximum price

# Fee calculation
RECORDING_FEE = 35.0           # Fixed recording fee
COUNTY_FEE_PERCENT = 0.05      # 5% county fee
MISC_FEES = 100.0              # Miscellaneous fees
```

### Water Feature Keywords

```python
# Primary keywords (3.0 points each)
PRIMARY_WATER_KEYWORDS = [
    'creek', 'stream', 'river', 'lake', 'pond', 'spring'
]

# Secondary keywords (2.0 points each)
SECONDARY_WATER_KEYWORDS = [
    'branch', 'run', 'brook', 'tributary', 'wetland', 'marsh'
]

# Tertiary keywords (1.0 points each)
TERTIARY_WATER_KEYWORDS = [
    'water', 'aquatic', 'riparian', 'shore', 'bank', 'waterfront'
]
```

### Investment Scoring

```python
# Scoring weights (must sum to 1.0)
INVESTMENT_SCORE_WEIGHTS = {
    'price_per_acre': 0.4,        # Price competitiveness
    'acreage_preference': 0.3,    # Size preference
    'water_features': 0.2,        # Water feature bonus
    'assessed_value_ratio': 0.1   # Value ratio
}

# Preferred acreage range for scoring
PREFERRED_MIN_ACRES = 2.0
PREFERRED_MAX_ACRES = 4.0
```

### Data Processing

```python
# CSV parsing settings
CSV_DELIMITERS = [',', '\t', '|', ';']
FILE_ENCODINGS = ['utf-8', 'latin-1', 'cp1252']

# Validation thresholds
MIN_REASONABLE_PRICE = 1.0
MAX_REASONABLE_PRICE = 1000000.0
MIN_REASONABLE_ACRES = 0.01
MAX_REASONABLE_ACRES = 1000.0
MAX_REASONABLE_PRICE_PER_ACRE = 50000.0
```

### Output Configuration

```python
# Column order for output files
OUTPUT_COLUMNS = [
    'parcel_id', 'county', 'amount', 'acreage', 'price_per_acre',
    'estimated_all_in_cost', 'water_score', 'investment_score',
    'assessed_value', 'description', 'owner_name', 'year_sold'
]

# Display formatting
CURRENCY_FORMAT = "${:,.2f}"
ACREAGE_FORMAT = "{:.2f}"
SCORE_FORMAT = "{:.1f}"
```

---

## config.logging_config

Structured logging configuration with performance tracking and different log levels.

### Functions

#### `setup_logging(log_level: str = 'INFO', log_file: Optional[str] = None, console_output: bool = True, detailed_format: bool = False) -> logging.Logger`
Set up structured logging for the application.

**Parameters:**
- `log_level` (str): Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
- `log_file` (Optional[str]): Optional log file path
- `console_output` (bool): Whether to output logs to console
- `detailed_format` (bool): Whether to use detailed format with function names

**Returns:**
- `logging.Logger`: Configured logger instance

#### `get_logger(name: str) -> logging.Logger`
Get a logger instance for a specific module.

**Parameters:**
- `name` (str): Logger name (typically `__name__`)

**Returns:**
- `logging.Logger`: Logger instance

#### `log_performance(logger: logging.Logger, operation: str, duration: float, records_processed: int = 0)`
Log performance metrics in a structured way.

**Parameters:**
- `logger` (logging.Logger): Logger instance
- `operation` (str): Description of the operation
- `duration` (float): Duration in seconds
- `records_processed` (int): Number of records processed

#### `log_scraping_metrics(logger: logging.Logger, county: str, pages: int, records: int, duration: float, errors: int = 0)`
Log web scraping metrics in a structured way.

**Parameters:**
- `logger` (logging.Logger): Logger instance
- `county` (str): County name
- `pages` (int): Number of pages scraped
- `records` (int): Number of records extracted
- `duration` (float): Total duration in seconds
- `errors` (int): Number of errors encountered

#### `log_processing_metrics(logger: logging.Logger, operation: str, input_records: int, output_records: int, duration: float)`
Log data processing metrics in a structured way.

#### `log_error_with_context(logger: logging.Logger, error: Exception, context: str, **kwargs)`
Log errors with additional context information.

### Environment Setup

#### `setup_environment_logging()`
Set up logging based on environment variables.

**Environment Variables:**
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_FILE`: Log file path (optional)
- `LOG_DETAILED`: Use detailed format (true/false)

---

## streamlit_app.app

Interactive Streamlit dashboard for property data visualization and analysis.

### Main Functions

#### `main() -> None`
Main Streamlit application entry point.

#### `load_available_data() -> pd.DataFrame`
Load all available processed data from CSV files.

#### `apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame`
Apply user-selected filters to the dataset.

#### `create_summary_metrics(df: pd.DataFrame) -> Dict[str, Any]`
Calculate summary statistics for the dashboard.

#### `create_visualizations(df: pd.DataFrame) -> Dict[str, Any]`
Generate Plotly visualizations for the dashboard.

### Dashboard Features

- **Legal Disclaimer**: Prominent 3-year redemption period warning
- **Interactive Filters**: Price range, acreage, water features, county selection
- **Summary Metrics**: Total properties, average price, price ranges
- **Data Visualizations**:
  - Price vs. acreage scatter plot
  - County distribution
  - Water feature analysis
  - Investment score distribution
- **Data Table**: Sortable table with all property details
- **Export Functionality**: Download filtered data as CSV

---

## Environment Variables

### Logging Configuration
```bash
LOG_LEVEL=INFO                    # Logging level
LOG_FILE=logs/auction_watcher.log # Log file path
LOG_DETAILED=false                # Detailed logging format
```

### Performance Tuning
```bash
SCRAPING_DELAY=2.0               # Seconds between requests
MAX_CONCURRENT_REQUESTS=1        # Keep at 1 for ADOR respect
REQUEST_TIMEOUT=30               # HTTP timeout in seconds
```

### Data Management
```bash
DATA_RETENTION_DAYS=30           # Days to keep raw data
CACHE_ENABLED=true               # Enable data caching
```

---

## Error Codes

### Exit Codes
- `0`: Success
- `1`: General error
- `2`: Invalid arguments
- `3`: Network error
- `4`: Data processing error
- `5`: File operation error

### HTTP Status Codes
- `200`: Successful scraping
- `404`: County page not found
- `429`: Rate limited
- `500`: Server error
- `503`: Service unavailable

---

## Performance Benchmarks

### Target Performance Metrics
- **Scraping Speed**: 200+ records/second
- **Memory Usage**: <1GB for 10,000 records
- **Dashboard Load**: <3 seconds
- **Error Rate**: <1% for web scraping

### Typical Usage Patterns
- **Small counties**: 1-50 records, <10 seconds
- **Medium counties**: 50-500 records, <60 seconds
- **Large counties**: 500+ records, <300 seconds
- **Dashboard**: Real-time filtering for datasets up to 1000 records

---

## Version History

### v1.0.0 (Current)
- Complete web scraping for all 67 Alabama counties
- Investment analysis with water feature detection
- Interactive Streamlit dashboard
- Comprehensive error handling and logging
- Production-ready deployment capabilities

### Planned Features (See ROADMAP.md)
- v1.1.0: Batch processing and performance improvements
- v1.2.0: Database integration and automation
- v2.0.0: Mapping interface and advanced analytics

---

**API Reference Maintainer**: Development Team
**Last Updated**: September 2025
**Questions?**: See CONTRIBUTING.md for guidance