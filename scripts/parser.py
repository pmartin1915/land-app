"""
Alabama Auction Watcher - CSV Parser

This script parses Alabama ADOR delinquent property CSV files, applies filters,
calculates investment metrics, and produces ranked watchlists.

Usage:
    python scripts/parser.py --input data/raw/county.csv --output data/processed/watchlist.csv
    python scripts/parser.py -i data/raw/baldwin.csv -o data/processed/watchlist.csv --infer-acres
"""

import argparse
import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import (
    MIN_ACRES, MAX_ACRES, MAX_PRICE, RECORDING_FEE, COUNTY_FEE_PERCENT,
    MISC_FEES, INVESTMENT_SCORE_WEIGHTS, CSV_DELIMITERS, FILE_ENCODINGS,
    OUTPUT_COLUMNS
)

from scripts.utils import (
    detect_csv_delimiter, find_column_mapping, normalize_price,
    parse_acreage_from_description, calculate_water_score,
    calculate_estimated_all_in_cost, calculate_investment_score,
    validate_data_quality, clean_dataframe
)

from scripts.scraper import (
    scrape_county_data, validate_county_code, get_county_name,
    list_available_counties
)

from config.logging_config import get_logger, log_processing_metrics, log_error_with_context
from scripts.exceptions import (
    CountyValidationError, ScrapingError, DataValidationError,
    FileOperationError, DataProcessingError
)

# Set up logger
logger = get_logger(__name__)


class AuctionParser:
    """Main parser class for processing ADOR CSV files."""

    def __init__(self, min_acres: float = MIN_ACRES, max_acres: float = MAX_ACRES,
                 max_price: float = MAX_PRICE, infer_acres: bool = False):
        """
        Initialize the parser with filtering criteria.

        Args:
            min_acres: Minimum acreage filter
            max_acres: Maximum acreage filter
            max_price: Maximum price filter
            infer_acres: Whether to infer acreage from descriptions
        """
        self.min_acres = min_acres
        self.max_acres = max_acres
        self.max_price = max_price
        self.infer_acres = infer_acres
        self.column_mapping = {}
        self.original_records = 0
        self.filtered_records = 0

    def load_csv_file(self, file_path: str) -> pd.DataFrame:
        """
        Load CSV file with flexible delimiter and encoding detection.

        Args:
            file_path: Path to the CSV file

        Returns:
            DataFrame with loaded data

        Raises:
            FileNotFoundError: If file doesn't exist
            Exception: If file cannot be read
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        print(f"Loading CSV file: {file_path}")

        # Try to detect delimiter
        try:
            delimiter = detect_csv_delimiter(file_path)
            print(f"Detected delimiter: '{delimiter}'")
        except Exception as e:
            print(f"Delimiter detection failed: {e}, using comma")
            delimiter = ','

        # Try different encodings
        df = None
        for encoding in FILE_ENCODINGS:
            try:
                df = pd.read_csv(file_path, delimiter=delimiter, encoding=encoding,
                               dtype=str, na_values=['', 'N/A', 'NA', 'null', 'NULL'])
                print(f"Successfully loaded with encoding: {encoding}")
                break
            except Exception as e:
                print(f"Failed with encoding {encoding}: {e}")
                continue

        if df is None:
            raise Exception(f"Could not read file with any encoding: {FILE_ENCODINGS}")

        self.original_records = len(df)
        print(f"Loaded {self.original_records} records")

        return df

    def map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Map DataFrame columns to standardized field names.

        Args:
            df: Raw DataFrame

        Returns:
            DataFrame with mapped column names
        """
        print("Mapping columns to standard field names...")

        # Create mapping dictionary
        mapped_df = df.copy()
        self.column_mapping = {}

        # Map each field type
        fields_to_map = ['parcel_id', 'amount', 'assessed_value', 'description',
                        'acreage', 'year_sold', 'owner_name', 'county']

        for field in fields_to_map:
            mapped_col = find_column_mapping(df.columns.tolist(), field)
            if mapped_col:
                self.column_mapping[field] = mapped_col
                print(f"  {field}: '{mapped_col}'")
            else:
                print(f"  {field}: NOT FOUND")

        # Rename columns in DataFrame
        rename_dict = {v: k for k, v in self.column_mapping.items()}
        mapped_df = mapped_df.rename(columns=rename_dict)

        return mapped_df

    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize price and acreage data.

        Args:
            df: DataFrame with mapped columns

        Returns:
            DataFrame with normalized data
        """
        print("Normalizing data...")
        df_norm = df.copy()

        # Normalize prices
        if 'amount' in df_norm.columns:
            print("  Normalizing prices...")
            df_norm['amount'] = df_norm['amount'].apply(normalize_price)
            valid_prices = df_norm['amount'].notna().sum()
            print(f"    {valid_prices} valid prices found")

        # Normalize assessed values
        if 'assessed_value' in df_norm.columns:
            print("  Normalizing assessed values...")
            df_norm['assessed_value'] = df_norm['assessed_value'].apply(normalize_price)

        # Handle acreage
        if 'acreage' in df_norm.columns:
            print("  Normalizing acreage from direct column...")
            df_norm['acreage'] = df_norm['acreage'].apply(normalize_price)  # Reuse price normalization for numbers

        # Infer acreage from descriptions if requested and no direct acreage column
        if self.infer_acres and ('acreage' not in df_norm.columns or df_norm['acreage'].isna().all()):
            if 'description' in df_norm.columns:
                print("  Inferring acreage from descriptions...")
                inferred_acreage = df_norm['description'].apply(parse_acreage_from_description)

                if 'acreage' in df_norm.columns:
                    # Fill missing values with inferred ones
                    df_norm['acreage'] = df_norm['acreage'].fillna(inferred_acreage)
                else:
                    # Create new acreage column
                    df_norm['acreage'] = inferred_acreage

                valid_acreage = df_norm['acreage'].notna().sum()
                print(f"    {valid_acreage} properties with inferred acreage")

        # Clean the dataframe
        df_norm = clean_dataframe(df_norm)

        return df_norm

    def apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply filtering criteria to the data.

        Args:
            df: Normalized DataFrame

        Returns:
            Filtered DataFrame
        """
        print(f"Applying filters...")
        df_filtered = df.copy()

        initial_count = len(df_filtered)

        # Filter by price
        if 'amount' in df_filtered.columns:
            price_mask = (df_filtered['amount'].notna()) & (df_filtered['amount'] <= self.max_price)
            df_filtered = df_filtered[price_mask]
            print(f"  After price filter (<=${self.max_price:,.0f}): {len(df_filtered)} records")

        # Filter by acreage
        if 'acreage' in df_filtered.columns:
            acreage_mask = (
                (df_filtered['acreage'].notna()) &
                (df_filtered['acreage'] >= self.min_acres) &
                (df_filtered['acreage'] <= self.max_acres)
            )
            df_filtered = df_filtered[acreage_mask]
            print(f"  After acreage filter ({self.min_acres}-{self.max_acres} acres): {len(df_filtered)} records")

        # Remove records without essential data
        essential_cols = ['amount', 'description']
        for col in essential_cols:
            if col in df_filtered.columns:
                before_count = len(df_filtered)
                df_filtered = df_filtered[df_filtered[col].notna()]
                after_count = len(df_filtered)
                if before_count != after_count:
                    print(f"  Removed {before_count - after_count} records missing {col}")

        self.filtered_records = len(df_filtered)
        print(f"Final filtered dataset: {self.filtered_records} records ({self.filtered_records/initial_count*100:.1f}% of original)")

        return df_filtered

    def calculate_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate investment metrics for each property.

        Args:
            df: Filtered DataFrame

        Returns:
            DataFrame with calculated metrics
        """
        print("Calculating investment metrics...")
        df_metrics = df.copy()

        # Calculate price per acre
        if 'amount' in df_metrics.columns and 'acreage' in df_metrics.columns:
            df_metrics['price_per_acre'] = df_metrics['amount'] / df_metrics['acreage']
            print(f"  Calculated price per acre for {df_metrics['price_per_acre'].notna().sum()} properties")

        # Calculate estimated all-in cost
        if 'amount' in df_metrics.columns:
            df_metrics['estimated_all_in_cost'] = df_metrics['amount'].apply(
                lambda x: calculate_estimated_all_in_cost(x, RECORDING_FEE, COUNTY_FEE_PERCENT, MISC_FEES)
            )

        # Calculate water scores
        if 'description' in df_metrics.columns:
            df_metrics['water_score'] = df_metrics['description'].apply(calculate_water_score)
            water_properties = (df_metrics['water_score'] > 0).sum()
            print(f"  Found {water_properties} properties with water features")

        # Calculate assessed value ratio
        if 'amount' in df_metrics.columns and 'assessed_value' in df_metrics.columns:
            df_metrics['assessed_value_ratio'] = np.where(
                df_metrics['assessed_value'] > 0,
                df_metrics['amount'] / df_metrics['assessed_value'],
                np.nan
            )

        # Calculate composite investment score
        required_cols = ['price_per_acre', 'acreage', 'water_score']
        if all(col in df_metrics.columns for col in required_cols):
            def calc_score(row):
                return calculate_investment_score(
                    price_per_acre=row.get('price_per_acre', 0),
                    acreage=row.get('acreage', 0),
                    water_score=row.get('water_score', 0),
                    assessed_value_ratio=row.get('assessed_value_ratio', 1.0),
                    weights=INVESTMENT_SCORE_WEIGHTS
                )

            df_metrics['investment_score'] = df_metrics.apply(calc_score, axis=1)
            print(f"  Calculated investment scores")

        return df_metrics

    def rank_properties(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rank properties by investment score and other criteria.

        Args:
            df: DataFrame with calculated metrics

        Returns:
            Ranked DataFrame
        """
        print("Ranking properties...")

        # Sort by investment score (descending), then by price per acre (ascending)
        sort_columns = []
        sort_ascending = []

        if 'investment_score' in df.columns:
            sort_columns.append('investment_score')
            sort_ascending.append(False)  # Higher score is better

        if 'price_per_acre' in df.columns:
            sort_columns.append('price_per_acre')
            sort_ascending.append(True)  # Lower price per acre is better

        if 'water_score' in df.columns:
            sort_columns.append('water_score')
            sort_ascending.append(False)  # Higher water score is better

        if sort_columns:
            df_ranked = df.sort_values(sort_columns, ascending=sort_ascending).reset_index(drop=True)
        else:
            df_ranked = df.reset_index(drop=True)

        # Add rank column
        df_ranked['rank'] = range(1, len(df_ranked) + 1)

        return df_ranked

    def export_results(self, df: pd.DataFrame, output_path: str) -> None:
        """
        Export results to CSV file.

        Args:
            df: Ranked DataFrame
            output_path: Output file path
        """
        print(f"Exporting results to: {output_path}")

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Select and order columns for output
        available_columns = [col for col in OUTPUT_COLUMNS if col in df.columns]
        if 'rank' in df.columns and 'rank' not in available_columns:
            available_columns.insert(0, 'rank')

        export_df = df[available_columns].copy()

        # Round numeric columns for cleaner output
        numeric_columns = export_df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if col in ['price_per_acre', 'amount', 'estimated_all_in_cost', 'assessed_value']:
                export_df[col] = export_df[col].round(2)
            elif col in ['acreage']:
                export_df[col] = export_df[col].round(3)
            elif col in ['water_score', 'investment_score']:
                export_df[col] = export_df[col].round(1)

        # Export to CSV
        export_df.to_csv(output_path, index=False)
        print(f"Successfully exported {len(export_df)} properties")

    def generate_summary_report(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate summary statistics for the processed data.

        Args:
            df: Final processed DataFrame

        Returns:
            Dictionary with summary statistics
        """
        summary = {
            'original_records': self.original_records,
            'filtered_records': self.filtered_records,
            'filter_retention_rate': f"{self.filtered_records/self.original_records*100:.1f}%" if self.original_records > 0 else "N/A"
        }

        if len(df) > 0:
            # Price statistics
            if 'amount' in df.columns:
                summary['avg_price'] = f"${df['amount'].mean():.2f}"
                summary['median_price'] = f"${df['amount'].median():.2f}"
                summary['price_range'] = f"${df['amount'].min():.2f} - ${df['amount'].max():.2f}"

            # Acreage statistics
            if 'acreage' in df.columns:
                summary['avg_acreage'] = f"{df['acreage'].mean():.2f}"
                summary['median_acreage'] = f"{df['acreage'].median():.2f}"

            # Price per acre statistics
            if 'price_per_acre' in df.columns:
                summary['avg_price_per_acre'] = f"${df['price_per_acre'].mean():.2f}"
                summary['median_price_per_acre'] = f"${df['price_per_acre'].median():.2f}"

            # Water features
            if 'water_score' in df.columns:
                water_count = (df['water_score'] > 0).sum()
                summary['properties_with_water'] = f"{water_count} ({water_count/len(df)*100:.1f}%)"

            # Investment potential
            if 'investment_score' in df.columns:
                summary['avg_investment_score'] = f"{df['investment_score'].mean():.1f}"
                top_10_pct = max(1, len(df) // 10)
                summary['top_10_percent_avg_score'] = f"{df.head(top_10_pct)['investment_score'].mean():.1f}"

        return summary

    def process_scraped_data(self, county_input: str, output_path: str, max_pages: int = 10) -> Dict[str, Any]:
        """
        Process scraped data from ADOR website for a county.

        Args:
            county_input: County code ('05') or name ('Baldwin')
            output_path: Path to output CSV file
            max_pages: Maximum number of pages to scrape

        Returns:
            Dictionary with processing summary
        """
        try:
            # Validate county and get info
            county_code = validate_county_code(county_input)
            county_name = get_county_name(county_code)

            print(f"Scraping data for {county_name} County (code: {county_code})...")

            # Scrape data from ADOR website
            df = scrape_county_data(county_input, max_pages=max_pages, save_raw=True)

            if df.empty:
                raise Exception(f"No data found for {county_name} County")

            print(f"Successfully scraped {len(df)} records")
            self.original_records = len(df)

            # Process the scraped data through the same pipeline as CSV files
            df = self.map_columns(df)
            df = self.normalize_data(df)
            df = self.apply_filters(df)
            df = self.calculate_metrics(df)
            df = self.rank_properties(df)

            # Validate data quality
            validation_results = validate_data_quality(df)
            if validation_results['issues']:
                print("Data quality issues found:")
                for issue in validation_results['issues']:
                    print(f"  - {issue}")

            if validation_results['warnings']:
                print("Data quality warnings:")
                for warning in validation_results['warnings']:
                    print(f"  - {warning}")

            # Export results
            self.export_results(df, output_path)

            # Generate summary
            summary = self.generate_summary_report(df)
            summary['data_source'] = f"Scraped from ADOR website ({county_name} County)"

            print("\n" + "="*50)
            print("PROCESSING SUMMARY")
            print("="*50)
            for key, value in summary.items():
                print(f"{key.replace('_', ' ').title()}: {value}")
            print("="*50)

            return summary

        except ScrapingError as e:
            print(f"Scraping failed: {e}")
            raise
        except Exception as e:
            print(f"Error processing scraped data: {e}")
            raise

    def process_file(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """
        Main processing method that orchestrates the entire pipeline.

        Args:
            input_path: Path to input CSV file
            output_path: Path to output CSV file

        Returns:
            Dictionary with processing summary
        """
        try:
            # Load and process the data
            df = self.load_csv_file(input_path)
            df = self.map_columns(df)
            df = self.normalize_data(df)
            df = self.apply_filters(df)
            df = self.calculate_metrics(df)
            df = self.rank_properties(df)

            # Validate data quality
            validation_results = validate_data_quality(df)
            if validation_results['issues']:
                print("Data quality issues found:")
                for issue in validation_results['issues']:
                    print(f"  - {issue}")

            if validation_results['warnings']:
                print("Data quality warnings:")
                for warning in validation_results['warnings']:
                    print(f"  - {warning}")

            # Export results
            self.export_results(df, output_path)

            # Generate summary
            summary = self.generate_summary_report(df)

            print("\n" + "="*50)
            print("PROCESSING SUMMARY")
            print("="*50)
            for key, value in summary.items():
                print(f"{key.replace('_', ' ').title()}: {value}")
            print("="*50)

            return summary

        except Exception as e:
            print(f"Error processing file: {e}")
            raise


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Alabama Auction Watcher - CSV Parser",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process CSV file
  python scripts/parser.py --input data/raw/baldwin.csv --output data/processed/watchlist.csv
  python scripts/parser.py -i data/raw/jefferson.csv -o data/processed/jefferson_watchlist.csv --infer-acres

  # Scrape data directly from ADOR website
  python scripts/parser.py --scrape-county 05 --output data/processed/baldwin_watchlist.csv
  python scripts/parser.py --scrape-county Baldwin --infer-acres --max-pages 20
  python scripts/parser.py --scrape-county "Mobile" --min-acres 2 --max-acres 10 --max-price 15000

  # List available counties
  python scripts/parser.py --list-counties
        """
    )

    parser.add_argument(
        '-i', '--input',
        help='Input CSV file path (required if not scraping)'
    )

    parser.add_argument(
        '--scrape-county',
        help='Scrape data directly from ADOR website. Use county code (e.g., "05") or name (e.g., "Baldwin")'
    )

    parser.add_argument(
        '--max-pages',
        type=int,
        default=10,
        help='Maximum pages to scrape from ADOR website (default: 10)'
    )

    parser.add_argument(
        '--list-counties',
        action='store_true',
        help='List all available Alabama county codes and names'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output CSV file path (default: data/processed/watchlist.csv)'
    )

    parser.add_argument(
        '--min-acres',
        type=float,
        default=MIN_ACRES,
        help=f'Minimum acreage filter (default: {MIN_ACRES})'
    )

    parser.add_argument(
        '--max-acres',
        type=float,
        default=MAX_ACRES,
        help=f'Maximum acreage filter (default: {MAX_ACRES})'
    )

    parser.add_argument(
        '--max-price',
        type=float,
        default=MAX_PRICE,
        help=f'Maximum price filter (default: ${MAX_PRICE:,.0f})'
    )

    parser.add_argument(
        '--infer-acres',
        action='store_true',
        help='Attempt to infer acreage from property descriptions'
    )

    args = parser.parse_args()

    # Handle list counties command
    if args.list_counties:
        counties = list_available_counties()
        print("Available Alabama Counties:")
        print("=" * 40)
        for code, name in sorted(counties.items()):
            print(f"{code}: {name}")
        print(f"\nTotal: {len(counties)} counties")
        return

    # Validate that either input or scrape-county is provided
    if not args.input and not args.scrape_county:
        print("Error: Must specify either --input (CSV file) or --scrape-county")
        print("Use --help for usage examples")
        sys.exit(1)

    if args.input and args.scrape_county:
        print("Error: Cannot specify both --input and --scrape-county. Choose one.")
        sys.exit(1)

    # Set default output path if not provided
    if not args.output:
        args.output = 'data/processed/watchlist.csv'

    # Create parser instance
    auction_parser = AuctionParser(
        min_acres=args.min_acres,
        max_acres=args.max_acres,
        max_price=args.max_price,
        infer_acres=args.infer_acres
    )

    try:
        if args.scrape_county:
            # Scrape data from ADOR website
            summary = auction_parser.process_scraped_data(
                county_input=args.scrape_county,
                output_path=args.output,
                max_pages=args.max_pages
            )
            print(f"\nScraping and processing completed successfully!")
            print(f"Watchlist saved to: {args.output}")

        else:
            # Process CSV file
            if not os.path.exists(args.input):
                print(f"Error: Input file does not exist: {args.input}")
                sys.exit(1)

            summary = auction_parser.process_file(args.input, args.output)
            print(f"\nProcessing completed successfully!")
            print(f"Watchlist saved to: {args.output}")

    except CountyValidationError as e:
        print(f"Invalid county: {e}")
        print("\nTo see available counties, run:")
        print("  python scripts/parser.py --list-counties")
    except ScrapingError as e:
        print(f"Scraping failed: {e}")
        print("\nTroubleshooting tips:")
        print("- Check your internet connection")
        print("- Verify the county code is correct (use --list-counties)")
        print("- Try again later if ADOR website is temporarily unavailable")
        print("- Use a CSV file with --input as fallback")
        sys.exit(1)
    except Exception as e:
        print(f"Processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()