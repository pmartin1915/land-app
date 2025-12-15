#!/usr/bin/env python3
"""
Comprehensive System Validation for Alabama Auction Watcher

This script performs end-to-end validation of the entire system including
database performance, application functionality, data quality, and readiness
for production use.
"""

import sqlite3
import time
import json
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
import sys

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import column mapping utilities
from scripts.utils import find_column_mapping

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemValidator:
    """Comprehensive system validation for Alabama Auction Watcher."""

    def __init__(self, db_path: str = "alabama_auction_watcher.db"):
        self.db_path = db_path
        self.validation_results = {}
        self.performance_metrics = {}

    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """
        Run complete system validation including all components.

        Returns:
            Dictionary with validation results, performance metrics, and recommendations
        """
        logger.info("Starting comprehensive system validation...")

        validation_results = {
            'timestamp': datetime.now().isoformat(),
            'validation_modules': {},
            'performance_benchmarks': {},
            'system_health': {},
            'recommendations': [],
            'overall_score': 0
        }

        # Run validation modules
        validation_modules = [
            ('database_validation', self._validate_database),
            ('data_quality_validation', self._validate_data_quality),
            ('performance_validation', self._validate_performance),
            ('security_validation', self._validate_security),
            ('configuration_validation', self._validate_configuration),
            ('file_system_validation', self._validate_file_system)
        ]

        scores = []

        for module_name, module_func in validation_modules:
            try:
                logger.info(f"Running {module_name}...")
                result = module_func()
                validation_results['validation_modules'][module_name] = result

                # Extract score if available
                if 'score' in result:
                    scores.append(result['score'])

                logger.info(f"{module_name} completed: {result.get('status', 'unknown')}")

            except Exception as e:
                logger.error(f"{module_name} failed: {e}")
                validation_results['validation_modules'][module_name] = {
                    'status': 'failed',
                    'error': str(e),
                    'score': 0
                }
                scores.append(0)

        # Calculate overall score
        validation_results['overall_score'] = round(sum(scores) / len(scores), 1) if scores else 0

        # Generate system recommendations
        validation_results['recommendations'] = self._generate_system_recommendations(validation_results)

        logger.info(f"Comprehensive validation complete. Overall score: {validation_results['overall_score']}/100")

        return validation_results

    def _validate_database(self) -> Dict[str, Any]:
        """Validate database structure, integrity, and performance."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            validation = {
                'status': 'passed',
                'checks': {},
                'metrics': {},
                'score': 100
            }

            # Check table existence
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            required_tables = ['properties', 'counties']
            missing_tables = [t for t in required_tables if t not in tables]

            validation['checks']['required_tables'] = {
                'passed': len(missing_tables) == 0,
                'missing_tables': missing_tables,
                'total_tables': len(tables)
            }

            if missing_tables:
                validation['score'] -= 30

            # Check data integrity
            try:
                cursor.execute("SELECT COUNT(*) FROM properties")
                property_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(DISTINCT county) FROM properties")
                county_count = cursor.fetchone()[0]

                validation['metrics']['property_count'] = property_count
                validation['metrics']['county_count'] = county_count

                if property_count == 0:
                    validation['score'] -= 40
                elif property_count < 1000:
                    validation['score'] -= 20

            except Exception as e:
                validation['checks']['data_integrity'] = {'passed': False, 'error': str(e)}
                validation['score'] -= 30

            # Check indexes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]

            validation['checks']['indexes'] = {
                'total_indexes': len(indexes),
                'has_indexes': len(indexes) > 0
            }

            if len(indexes) < 5:
                validation['score'] -= 10

            # Performance test
            start_time = time.time()
            cursor.execute("SELECT * FROM properties LIMIT 100")
            results = cursor.fetchall()
            query_time = time.time() - start_time

            validation['metrics']['sample_query_time'] = round(query_time, 4)

            if query_time > 1.0:
                validation['score'] -= 20

            conn.close()

            validation['score'] = max(0, validation['score'])

            return validation

        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e),
                'score': 0
            }

    def _validate_data_quality(self) -> Dict[str, Any]:
        """Validate data quality across all data sources."""
        try:
            validation = {
                'status': 'passed',
                'checks': {},
                'metrics': {},
                'score': 100
            }

            # Check raw data files
            raw_dir = Path("data/raw")
            if raw_dir.exists():
                csv_files = list(raw_dir.glob("scraped_*_county_*.csv"))
                validation['metrics']['raw_files_count'] = len(csv_files)

                if len(csv_files) < 10:
                    validation['score'] -= 20

                # Sample file quality check
                if csv_files:
                    sample_file = csv_files[0]
                    try:
                        df = pd.read_csv(sample_file)
                        validation['metrics']['sample_file_columns'] = len(df.columns)
                        validation['metrics']['sample_file_rows'] = len(df)

                        # Use column mapping to check if required fields can be found
                        required_fields = ['parcel_id', 'county', 'amount', 'description']
                        missing_fields = []
                        found_mappings = {}

                        for field in required_fields:
                            mapped_column = find_column_mapping(df.columns.tolist(), field)
                            if mapped_column:
                                found_mappings[field] = mapped_column
                            else:
                                missing_fields.append(field)

                        validation['checks']['sample_file_schema'] = {
                            'passed': len(missing_fields) == 0,
                            'missing_columns': missing_fields,
                            'found_mappings': found_mappings
                        }

                        if missing_fields:
                            validation['score'] -= 15

                    except Exception as e:
                        validation['checks']['sample_file_read'] = {'passed': False, 'error': str(e)}
                        validation['score'] -= 25
            else:
                validation['score'] -= 30

            # Check processed data
            processed_dir = Path("data/processed")
            if processed_dir.exists():
                processed_files = list(processed_dir.glob("*.csv"))
                validation['metrics']['processed_files_count'] = len(processed_files)
            else:
                validation['score'] -= 10

            validation['score'] = max(0, validation['score'])

            return validation

        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e),
                'score': 0
            }

    def _validate_performance(self) -> Dict[str, Any]:
        """Validate system performance characteristics."""
        try:
            validation = {
                'status': 'passed',
                'benchmarks': {},
                'score': 100
            }

            # Database performance benchmarks
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Test 1: Large query performance
            start_time = time.time()
            cursor.execute("SELECT COUNT(*) FROM properties")
            count_time = time.time() - start_time
            validation['benchmarks']['count_query_time'] = round(count_time, 4)

            if count_time > 1.0:
                validation['score'] -= 15

            # Test 2: Complex query performance
            start_time = time.time()
            cursor.execute("""
                SELECT county, COUNT(*), AVG(amount), MAX(amount)
                FROM properties
                GROUP BY county
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """)
            results = cursor.fetchall()
            complex_query_time = time.time() - start_time
            validation['benchmarks']['complex_query_time'] = round(complex_query_time, 4)

            if complex_query_time > 2.0:
                validation['score'] -= 20

            # Test 3: Memory efficiency
            start_time = time.time()
            cursor.execute("SELECT * FROM properties LIMIT 1000")
            large_result = cursor.fetchall()
            fetch_time = time.time() - start_time
            validation['benchmarks']['large_fetch_time'] = round(fetch_time, 4)

            if fetch_time > 0.5:
                validation['score'] -= 10

            conn.close()

            # File I/O performance
            raw_dir = Path("data/raw")
            if raw_dir.exists():
                csv_files = list(raw_dir.glob("*.csv"))
                if csv_files:
                    test_file = csv_files[0]
                    start_time = time.time()
                    df = pd.read_csv(test_file)
                    file_read_time = time.time() - start_time
                    validation['benchmarks']['csv_read_time'] = round(file_read_time, 4)

                    if file_read_time > 2.0:
                        validation['score'] -= 10

            validation['score'] = max(0, validation['score'])

            return validation

        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e),
                'score': 0
            }

    def _validate_security(self) -> Dict[str, Any]:
        """Validate security configurations and practices."""
        try:
            validation = {
                'status': 'passed',
                'checks': {},
                'score': 100
            }

            # Check for sensitive files
            sensitive_patterns = ['*.key', '*.pem', '*.env', 'config.json']
            found_sensitive = []

            for pattern in sensitive_patterns:
                matches = list(Path('.').glob(pattern))
                if matches:
                    found_sensitive.extend([str(m) for m in matches])

            validation['checks']['sensitive_files'] = {
                'found_files': found_sensitive,
                'file_count': len(found_sensitive)
            }

            # Check database file permissions (basic check)
            db_file = Path(self.db_path)
            if db_file.exists():
                validation['checks']['database_file'] = {
                    'exists': True,
                    'size_mb': round(db_file.stat().st_size / (1024 * 1024), 2)
                }
            else:
                validation['score'] -= 20

            # Check configuration files
            config_files = ['config/settings.py', 'config/validation.py']
            missing_config = []

            for config_file in config_files:
                if not Path(config_file).exists():
                    missing_config.append(config_file)

            validation['checks']['configuration_files'] = {
                'missing_files': missing_config,
                'all_present': len(missing_config) == 0
            }

            if missing_config:
                validation['score'] -= 15

            validation['score'] = max(0, validation['score'])

            return validation

        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e),
                'score': 0
            }

    def _validate_configuration(self) -> Dict[str, Any]:
        """Validate system configuration and setup."""
        try:
            validation = {
                'status': 'passed',
                'checks': {},
                'score': 100
            }

            # Check critical directories
            required_dirs = ['data', 'data/raw', 'data/processed', 'config', 'scripts', 'streamlit_app']
            missing_dirs = []

            for dir_path in required_dirs:
                if not Path(dir_path).exists():
                    missing_dirs.append(dir_path)

            validation['checks']['directory_structure'] = {
                'missing_directories': missing_dirs,
                'all_present': len(missing_dirs) == 0
            }

            if missing_dirs:
                validation['score'] -= len(missing_dirs) * 5

            # Check critical files
            critical_files = [
                'streamlit_app/app.py',
                'scripts/scraper.py',
                'config/settings.py',
                'requirements.txt'
            ]

            missing_files = []
            for file_path in critical_files:
                if not Path(file_path).exists():
                    missing_files.append(file_path)

            validation['checks']['critical_files'] = {
                'missing_files': missing_files,
                'all_present': len(missing_files) == 0
            }

            if missing_files:
                validation['score'] -= len(missing_files) * 10

            # Check Python dependencies (basic check)
            try:
                import streamlit, pandas, plotly, requests, sqlite3
                validation['checks']['dependencies'] = {'basic_imports': True}
            except ImportError as e:
                validation['checks']['dependencies'] = {'basic_imports': False, 'error': str(e)}
                validation['score'] -= 25

            validation['score'] = max(0, validation['score'])

            return validation

        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e),
                'score': 0
            }

    def _validate_file_system(self) -> Dict[str, Any]:
        """Validate file system organization and health."""
        try:
            validation = {
                'status': 'passed',
                'metrics': {},
                'checks': {},
                'score': 100
            }

            # Calculate total disk usage
            total_size = 0
            file_counts = {}

            for pattern in ['**/*.py', '**/*.csv', '**/*.json', '**/*.db']:
                files = list(Path('.').glob(pattern))
                file_counts[pattern] = len(files)

                for file in files:
                    try:
                        total_size += file.stat().st_size
                    except:
                        pass

            validation['metrics']['total_size_mb'] = round(total_size / (1024 * 1024), 2)
            validation['metrics']['file_counts'] = file_counts

            # Check for large files that might indicate issues
            large_files = []
            for file in Path('.').rglob('*'):
                if file.is_file():
                    try:
                        size_mb = file.stat().st_size / (1024 * 1024)
                        if size_mb > 100:  # Files larger than 100MB
                            large_files.append({
                                'file': str(file),
                                'size_mb': round(size_mb, 2)
                            })
                    except:
                        pass

            validation['checks']['large_files'] = {
                'files': large_files,
                'count': len(large_files)
            }

            # Check log files
            log_files = list(Path('.').glob('**/*.log'))
            validation['metrics']['log_files_count'] = len(log_files)

            validation['score'] = max(0, validation['score'])

            return validation

        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e),
                'score': 0
            }

    def _generate_system_recommendations(self, validation_results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on validation results."""
        recommendations = []

        overall_score = validation_results.get('overall_score', 0)

        if overall_score < 60:
            recommendations.append("CRITICAL: System score is below 60 - immediate attention required")
        elif overall_score < 80:
            recommendations.append("System score is below optimal - address identified issues")

        # Analyze specific modules
        modules = validation_results.get('validation_modules', {})

        for module_name, module_result in modules.items():
            score = module_result.get('score', 0)

            if score < 50:
                recommendations.append(f"Critical issues in {module_name} - requires immediate action")
            elif score < 80:
                recommendations.append(f"Improvements needed in {module_name}")

        # General recommendations
        if overall_score >= 80:
            recommendations.extend([
                "System is performing well - continue monitoring",
                "Consider implementing automated testing",
                "Plan for production deployment preparation"
            ])
        else:
            recommendations.extend([
                "Address performance bottlenecks before production",
                "Review and fix data quality issues",
                "Enhance error handling and monitoring"
            ])

        return recommendations

def main():
    """Main validation routine."""
    print("Alabama Auction Watcher - Comprehensive System Validation")
    print("=" * 60)
    print("Running complete system validation...")
    print()

    # Run validation
    validator = SystemValidator()
    results = validator.run_comprehensive_validation()

    # Save detailed results
    results_file = f"system_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Print summary
    print(f"System Validation Report:")
    print(f"  Overall Score: {results['overall_score']:.1f}/100")
    print()

    # Module scores
    modules = results.get('validation_modules', {})
    print("Module Scores:")
    for module_name, module_result in modules.items():
        score = module_result.get('score', 0)
        status = module_result.get('status', 'unknown')
        print(f"  {module_name}: {score:.1f}/100 ({status})")

    print()

    # Recommendations
    recommendations = results.get('recommendations', [])
    if recommendations:
        print("Recommendations:")
        for i, rec in enumerate(recommendations[:5], 1):
            print(f"  {i}. {rec}")

    print(f"\nDetailed report saved to: {results_file}")

    # Determine if system is ready
    overall_score = results['overall_score']
    if overall_score >= 75:
        print("\nSystem Status: READY FOR PRODUCTION")
        return True
    elif overall_score >= 60:
        print("\nSystem Status: NEEDS IMPROVEMENT")
        return False
    else:
        print("\nSystem Status: CRITICAL ISSUES - NOT READY")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)