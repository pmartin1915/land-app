#!/usr/bin/env python3
"""
Enhanced Data Quality Validation Pipeline for Alabama Auction Watcher

This script provides comprehensive data quality validation for newly scraped
county data, including security validation, data integrity checks, and
quality scoring.
"""

import pandas as pd
import numpy as np
import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import sys

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.validation import validate_property_data, get_validation_summary

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataQualityValidator:
    """Comprehensive data quality validation for scraped property data."""

    def __init__(self):
        self.validation_results = {}
        self.quality_scores = {}
        self.recommendations = []

    def validate_csv_file(self, file_path: str) -> Dict[str, Any]:
        """
        Validate a CSV file containing scraped property data.

        Args:
            file_path: Path to CSV file to validate

        Returns:
            Dictionary with validation results and quality metrics
        """
        logger.info(f"Starting validation for: {file_path}")

        try:
            # Load data
            df = pd.read_csv(file_path, dtype={'year_sold': str, 'parcel_id': str})
            logger.info(f"Loaded {len(df)} records from {file_path}")

            # Perform comprehensive validation
            results = {
                'file_info': self._analyze_file_info(file_path, df),
                'schema_validation': self._validate_schema(df),
                'data_quality': self._validate_data_quality(df),
                'security_validation': self._validate_security(df),
                'business_rules': self._validate_business_rules(df),
                'statistical_analysis': self._analyze_statistics(df),
                'recommendations': self._generate_recommendations(df)
            }

            # Calculate overall quality score
            results['overall_quality_score'] = self._calculate_quality_score(results)

            logger.info(f"Validation complete. Quality score: {results['overall_quality_score']:.1f}/100")

            return results

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {'error': str(e)}

    def _analyze_file_info(self, file_path: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze basic file information."""
        file_stats = Path(file_path).stat()

        return {
            'file_path': file_path,
            'file_size_mb': file_stats.st_size / (1024 * 1024),
            'record_count': len(df),
            'column_count': len(df.columns),
            'file_modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
            'columns': list(df.columns)
        }

    def _validate_schema(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate data schema and structure."""
        # Expected columns for Alabama property data
        required_columns = [
            'parcel_id', 'county', 'amount', 'description'
        ]

        optional_columns = [
            'acreage', 'investment_score', 'water_score', 'price_per_acre',
            'assessed_value', 'owner_name', 'year_sold', 'cs_number'
        ]

        all_expected = required_columns + optional_columns

        missing_required = [col for col in required_columns if col not in df.columns]
        missing_optional = [col for col in optional_columns if col not in df.columns]
        unexpected_columns = [col for col in df.columns if col not in all_expected]

        return {
            'required_columns_present': len(missing_required) == 0,
            'missing_required_columns': missing_required,
            'missing_optional_columns': missing_optional,
            'unexpected_columns': unexpected_columns,
            'total_columns': len(df.columns),
            'schema_score': max(0, 100 - len(missing_required) * 25 - len(unexpected_columns) * 5)
        }

    def _validate_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate data quality and completeness."""
        quality_metrics = {
            'total_records': len(df),
            'column_completeness': {},
            'data_types': {},
            'duplicates': {},
            'anomalies': {}
        }

        # Analyze completeness for each column
        for col in df.columns:
            if col in df.columns:
                non_null_count = df[col].notna().sum()
                completeness = (non_null_count / len(df)) * 100
                quality_metrics['column_completeness'][col] = {
                    'non_null_count': int(non_null_count),
                    'null_count': int(len(df) - non_null_count),
                    'completeness_percentage': round(completeness, 2)
                }

                # Data type analysis
                quality_metrics['data_types'][col] = str(df[col].dtype)

        # Check for duplicates
        if 'parcel_id' in df.columns:
            duplicate_parcels = df['parcel_id'].duplicated().sum()
            quality_metrics['duplicates']['duplicate_parcel_ids'] = int(duplicate_parcels)
            quality_metrics['duplicates']['duplicate_percentage'] = round((duplicate_parcels / len(df)) * 100, 2)

        # Check for anomalies in numeric columns
        numeric_columns = ['amount', 'acreage', 'investment_score', 'water_score', 'assessed_value']
        for col in numeric_columns:
            if col in df.columns:
                col_data = pd.to_numeric(df[col], errors='coerce')
                anomalies = {
                    'negative_values': int((col_data < 0).sum()),
                    'zero_values': int((col_data == 0).sum()),
                    'extremely_high_values': int((col_data > col_data.quantile(0.99) * 3).sum()) if len(col_data) > 0 else 0
                }
                quality_metrics['anomalies'][col] = anomalies

        # Calculate overall data quality score
        avg_completeness = np.mean([m['completeness_percentage'] for m in quality_metrics['column_completeness'].values()])
        duplicate_penalty = min(quality_metrics['duplicates'].get('duplicate_percentage', 0) * 2, 20)

        quality_metrics['data_quality_score'] = max(0, avg_completeness - duplicate_penalty)

        return quality_metrics

    def _validate_security(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate data for security issues using the validation module."""
        security_results = {
            'security_violations': {},
            'sanitization_applied': {},
            'security_score': 100
        }

        # Check text columns for security issues
        text_columns = ['description', 'owner_name', 'parcel_id']

        for col in text_columns:
            if col in df.columns:
                violations = []
                sample_size = min(100, len(df))  # Check sample for performance
                sample_data = df[col].dropna().head(sample_size)

                for idx, value in sample_data.items():
                    if pd.isna(value):
                        continue

                    # Create property data dict for validation
                    property_data = {col: str(value)}
                    validation_results = validate_property_data(property_data)

                    if col in validation_results:
                        result = validation_results[col]
                        if not result.is_valid:
                            violations.append({
                                'row_index': idx,
                                'original_value': str(value)[:100],  # Truncate for logging
                                'errors': result.errors
                            })

                security_results['security_violations'][col] = violations

                # Reduce security score for violations
                violation_penalty = min(len(violations) * 5, 30)
                security_results['security_score'] -= violation_penalty

        security_results['security_score'] = max(0, security_results['security_score'])

        return security_results

    def _validate_business_rules(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate business-specific rules for Alabama property data."""
        business_violations = []

        # Alabama-specific county validation
        valid_alabama_counties = {
            'Autauga', 'Mobile', 'Baldwin', 'Barbour', 'Bibb', 'Blount', 'Bullock', 'Butler',
            'Calhoun', 'Chambers', 'Cherokee', 'Chilton', 'Choctaw', 'Clarke', 'Clay',
            'Cleburne', 'Coffee', 'Colbert', 'Conecuh', 'Coosa', 'Covington', 'Crenshaw',
            'Cullman', 'Dale', 'Dallas', 'DeKalb', 'Elmore', 'Escambia', 'Etowah',
            'Fayette', 'Franklin', 'Geneva', 'Greene', 'Hale', 'Henry', 'Houston',
            'Jackson', 'Jefferson', 'Lamar', 'Lauderdale', 'Lawrence', 'Lee', 'Limestone',
            'Lowndes', 'Macon', 'Madison', 'Marengo', 'Marion', 'Marshall', 'Monroe',
            'Montgomery', 'Morgan', 'Perry', 'Pickens', 'Pike', 'Randolph', 'Russell',
            'St. Clair', 'Shelby', 'Sumter', 'Talladega', 'Tallapoosa', 'Tuscaloosa',
            'Walker', 'Washington', 'Wilcox', 'Winston'
        }

        if 'county' in df.columns:
            invalid_counties = df[~df['county'].isin(valid_alabama_counties)]['county'].unique()
            if len(invalid_counties) > 0:
                business_violations.append({
                    'rule': 'Alabama County Validation',
                    'violation': f'Invalid counties found: {list(invalid_counties)}'
                })

        # Amount validation (reasonable property values)
        if 'amount' in df.columns:
            amount_col = pd.to_numeric(df['amount'], errors='coerce')
            extremely_low = (amount_col < 100).sum()
            extremely_high = (amount_col > 1_000_000).sum()

            if extremely_low > 0:
                business_violations.append({
                    'rule': 'Minimum Property Value',
                    'violation': f'{extremely_low} properties with amount < $100'
                })

            if extremely_high > 0:
                business_violations.append({
                    'rule': 'Maximum Property Value',
                    'violation': f'{extremely_high} properties with amount > $1M'
                })

        # Acreage validation
        if 'acreage' in df.columns:
            acreage_col = pd.to_numeric(df['acreage'], errors='coerce')
            zero_acreage = (acreage_col <= 0).sum()
            huge_acreage = (acreage_col > 1000).sum()

            if zero_acreage > len(df) * 0.5:  # More than 50% zero acreage
                business_violations.append({
                    'rule': 'Acreage Completeness',
                    'violation': f'{zero_acreage} properties with zero/missing acreage ({zero_acreage/len(df)*100:.1f}%)'
                })

            if huge_acreage > 0:
                business_violations.append({
                    'rule': 'Maximum Acreage',
                    'violation': f'{huge_acreage} properties with acreage > 1000 acres'
                })

        # Investment score validation
        if 'investment_score' in df.columns:
            score_col = pd.to_numeric(df['investment_score'], errors='coerce')
            invalid_scores = ((score_col < 0) | (score_col > 10)).sum()

            if invalid_scores > 0:
                business_violations.append({
                    'rule': 'Investment Score Range',
                    'violation': f'{invalid_scores} properties with investment score outside 0-10 range'
                })

        business_score = max(0, 100 - len(business_violations) * 15)

        return {
            'business_violations': business_violations,
            'business_rules_score': business_score
        }

    def _analyze_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze statistical properties of the data."""
        stats = {
            'summary_statistics': {},
            'data_distribution': {},
            'correlations': {}
        }

        # Summary statistics for numeric columns
        numeric_columns = ['amount', 'acreage', 'investment_score', 'water_score', 'assessed_value']

        for col in numeric_columns:
            if col in df.columns:
                col_data = pd.to_numeric(df[col], errors='coerce').dropna()
                if len(col_data) > 0:
                    stats['summary_statistics'][col] = {
                        'count': int(len(col_data)),
                        'mean': float(col_data.mean()),
                        'median': float(col_data.median()),
                        'std': float(col_data.std()),
                        'min': float(col_data.min()),
                        'max': float(col_data.max()),
                        'q25': float(col_data.quantile(0.25)),
                        'q75': float(col_data.quantile(0.75))
                    }

        # Data distribution analysis
        if 'county' in df.columns:
            county_counts = df['county'].value_counts()
            stats['data_distribution']['county_distribution'] = {
                'total_counties': len(county_counts),
                'top_counties': county_counts.head(5).to_dict(),
                'properties_per_county_avg': float(county_counts.mean()),
                'properties_per_county_std': float(county_counts.std())
            }

        return stats

    def _generate_recommendations(self, df: pd.DataFrame) -> List[Dict[str, str]]:
        """Generate data quality improvement recommendations."""
        recommendations = []

        # Check completeness
        for col in ['acreage', 'investment_score', 'water_score']:
            if col in df.columns:
                completeness = (df[col].notna().sum() / len(df)) * 100
                if completeness < 80:
                    recommendations.append({
                        'type': 'Data Completeness',
                        'priority': 'High' if completeness < 50 else 'Medium',
                        'recommendation': f'Improve {col} data completeness (currently {completeness:.1f}%)',
                        'action': f'Review scraping logic for {col} extraction'
                    })

        # Check duplicates
        if 'parcel_id' in df.columns:
            duplicate_rate = (df['parcel_id'].duplicated().sum() / len(df)) * 100
            if duplicate_rate > 5:
                recommendations.append({
                    'type': 'Data Quality',
                    'priority': 'High',
                    'recommendation': f'High duplicate rate detected ({duplicate_rate:.1f}%)',
                    'action': 'Implement deduplication process before import'
                })

        # Check county coverage
        if 'county' in df.columns:
            county_count = df['county'].nunique()
            if county_count < 10:
                recommendations.append({
                    'type': 'Coverage',
                    'priority': 'Medium',
                    'recommendation': f'Limited county coverage ({county_count} counties)',
                    'action': 'Expand scraping to additional Alabama counties'
                })

        return recommendations

    def _calculate_quality_score(self, results: Dict[str, Any]) -> float:
        """Calculate overall data quality score."""
        scores = []

        # Schema score
        schema_score = results['schema_validation'].get('schema_score', 0)
        scores.append(('Schema', schema_score, 0.2))

        # Data quality score
        data_quality_score = results['data_quality'].get('data_quality_score', 0)
        scores.append(('Data Quality', data_quality_score, 0.3))

        # Security score
        security_score = results['security_validation'].get('security_score', 0)
        scores.append(('Security', security_score, 0.2))

        # Business rules score
        business_score = results['business_rules'].get('business_rules_score', 0)
        scores.append(('Business Rules', business_score, 0.3))

        # Calculate weighted average
        weighted_score = sum(score * weight for name, score, weight in scores)

        logger.info("Quality Score Breakdown:")
        for name, score, weight in scores:
            logger.info(f"  {name}: {score:.1f} (weight: {weight})")

        return round(weighted_score, 1)

def validate_all_new_files() -> Dict[str, Any]:
    """Validate all new CSV files in the raw data directory."""
    validator = DataQualityValidator()

    raw_data_dir = Path("data/raw")
    csv_files = list(raw_data_dir.glob("scraped_*_county_*.csv"))

    logger.info(f"Found {len(csv_files)} CSV files to validate")

    all_results = {
        'validation_timestamp': datetime.now().isoformat(),
        'total_files': len(csv_files),
        'file_results': {},
        'overall_summary': {}
    }

    valid_files = 0
    total_records = 0

    for csv_file in csv_files:
        logger.info(f"Validating: {csv_file.name}")

        result = validator.validate_csv_file(str(csv_file))
        all_results['file_results'][csv_file.name] = result

        if 'error' not in result:
            if result.get('overall_quality_score', 0) >= 70:
                valid_files += 1

            total_records += result.get('file_info', {}).get('record_count', 0)

    # Overall summary
    all_results['overall_summary'] = {
        'valid_files': valid_files,
        'invalid_files': len(csv_files) - valid_files,
        'validation_success_rate': round((valid_files / len(csv_files)) * 100, 1) if csv_files else 0,
        'total_records_validated': total_records,
        'ready_for_import': valid_files > 0
    }

    return all_results

def main():
    """Main validation routine."""
    print("Alabama Auction Watcher - Enhanced Data Quality Validation")
    print("=" * 60)
    print("Validating all newly scraped county data files...")
    print()

    # Run validation
    results = validate_all_new_files()

    # Save detailed results
    results_file = f"data_quality_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"Detailed results saved to: {results_file}")

    # Print summary
    summary = results['overall_summary']
    print(f"Validation Summary:")
    print(f"  Total files processed: {results['total_files']}")
    print(f"  Valid files: {summary['valid_files']}")
    print(f"  Invalid files: {summary['invalid_files']}")
    print(f"  Success rate: {summary['validation_success_rate']:.1f}%")
    print(f"  Total records: {summary['total_records_validated']:,}")
    print(f"  Ready for import: {'Yes' if summary['ready_for_import'] else 'No'}")

    if summary['ready_for_import']:
        print("\nNext steps:")
        print("1. Run: python scripts/import_data.py")
        print("2. Test application performance")
        print("3. Validate all tabs work with expanded dataset")
    else:
        print("\nAction required:")
        print("1. Review validation errors in detailed results file")
        print("2. Fix data quality issues")
        print("3. Re-run validation")

    return summary['ready_for_import']

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)