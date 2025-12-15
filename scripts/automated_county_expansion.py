#!/usr/bin/env python3
"""
Automated County Expansion Script for Alabama Auction Watcher
Systematically expands the property database by processing multiple counties

This script:
1. Prioritizes counties by market potential and data availability
2. Automatically scrapes and imports data for each county
3. Tracks progress toward the 3,000+ property goal
4. Provides detailed reporting and analytics
5. Handles errors gracefully and continues processing

Usage:
    python scripts/automated_county_expansion.py --target-counties 10 --max-pages 100
    python scripts/automated_county_expansion.py --all-counties --conservative
"""

import argparse
import logging
import time
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import json
from datetime import datetime
import sqlite3

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend_api.database.models import ALABAMA_COUNTIES

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/county_expansion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CountyExpansionManager:
    """Manages automated county expansion process."""

    def __init__(self):
        self.db_path = project_root / "alabama_auction_watcher.db"
        self.counties_processed = []
        self.counties_failed = []
        self.total_properties_added = 0
        self.start_time = datetime.now()

        # County priority ranking based on market intelligence
        # Higher scores = higher priority for expansion
        self.county_priorities = {
            'Lee': 95,           # Auburn area - high growth, university
            'Houston': 90,       # Dothan area - strong market
            'Montgomery': 85,    # State capital - good opportunities
            'Tuscaloosa': 80,    # University of Alabama area
            'Shelby': 75,        # Birmingham suburbs - growth area
            'Cullman': 70,       # North Alabama - rural/suburban mix
            'Morgan': 68,        # Decatur area - industrial
            'St. Clair': 65,     # Birmingham metro - growth
            'DeKalb': 62,        # Mountain region - scenic
            'Marshall': 60,      # Lake Guntersville area
            'Etowah': 58,        # Gadsden area
            'Cherokee': 55,      # Mountain region
            'Limestone': 52,     # Huntsville area overflow
            'Walker': 50,        # Coal region - mixed market
            'Talladega': 48,     # Central Alabama
            'Randolph': 45,      # Rural - lower cost
            'Clay': 42,          # Rural opportunities
            'Cleburne': 40,      # Mountain region
            'Tallapoosa': 38,    # Lake Martin area
            'Calhoun': 35,       # Anniston area
            'Coosa': 32,         # Rural/lake access
            'Chambers': 30,      # Auburn overflow
            'Russell': 28,       # Columbus GA border
            'Pike': 25,          # Troy area
            'Coffee': 22,        # Enterprise area
            'Geneva': 20,        # Lower Alabama
            'Covington': 18,     # Southern Alabama
            'Dale': 15,          # Ozark area
            'Henry': 12,         # Rural southern
            'Barbour': 10,       # Rural opportunities
        }

    def get_current_database_stats(self) -> Dict[str, Any]:
        """Get current database statistics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Total properties
            cursor.execute("SELECT COUNT(*) FROM properties WHERE is_deleted = 0")
            total_properties = cursor.fetchone()[0]

            # Properties by county
            cursor.execute("""
                SELECT county, COUNT(*) as count
                FROM properties
                WHERE is_deleted = 0 AND county IS NOT NULL
                GROUP BY county
                ORDER BY count DESC
            """)
            counties_data = cursor.fetchall()

            # Investment score statistics
            cursor.execute("""
                SELECT AVG(investment_score), MIN(investment_score), MAX(investment_score)
                FROM properties
                WHERE is_deleted = 0 AND investment_score IS NOT NULL
            """)
            score_stats = cursor.fetchone()

            conn.close()

            return {
                'total_properties': total_properties,
                'counties_with_data': len(counties_data),
                'counties_data': dict(counties_data),
                'avg_score': score_stats[0] if score_stats[0] else 0,
                'min_score': score_stats[1] if score_stats[1] else 0,
                'max_score': score_stats[2] if score_stats[2] else 0,
            }

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {'total_properties': 0, 'counties_with_data': 0, 'counties_data': {}}

    def get_prioritized_county_list(self, exclude_existing: bool = True) -> List[Tuple[str, int]]:
        """Get prioritized list of counties to process."""
        current_stats = self.get_current_database_stats()
        existing_counties = set(current_stats['counties_data'].keys())

        # Create prioritized list
        prioritized = []
        for county_name in ALABAMA_COUNTIES.values():
            if exclude_existing and county_name in existing_counties:
                continue

            priority = self.county_priorities.get(county_name, 5)  # Default low priority
            prioritized.append((county_name, priority))

        # Sort by priority (highest first)
        prioritized.sort(key=lambda x: x[1], reverse=True)

        return prioritized

    def scrape_county(self, county_name: str, max_pages: int = 100) -> Dict[str, Any]:
        """Scrape a single county and return results."""
        logger.info(f"Starting scrape for {county_name} County...")

        try:
            # Run the scraper
            cmd = [
                sys.executable,
                "scripts/parser.py",
                "--scrape-county", county_name,
                "--max-pages", str(max_pages)
            ]

            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )

            if result.returncode == 0:
                # Parse output for metrics
                output = result.stdout
                if "Successfully scraped" in output and "records" in output:
                    # Extract number of records
                    lines = output.split('\n')
                    for line in lines:
                        if "Successfully scraped" in line and "records" in line:
                            try:
                                records = int(line.split()[2])
                                return {
                                    'success': True,
                                    'records_scraped': records,
                                    'message': f"Successfully scraped {records} records"
                                }
                            except (IndexError, ValueError):
                                pass

                    return {
                        'success': True,
                        'records_scraped': 0,
                        'message': "Scraping completed but no records found"
                    }
                else:
                    return {
                        'success': False,
                        'records_scraped': 0,
                        'message': "No data found for county"
                    }
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                return {
                    'success': False,
                    'records_scraped': 0,
                    'message': f"Scraping failed: {error_msg}"
                }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'records_scraped': 0,
                'message': "Scraping timed out (30 minutes)"
            }
        except Exception as e:
            return {
                'success': False,
                'records_scraped': 0,
                'message': f"Error: {str(e)}"
            }

    def import_data(self) -> Dict[str, Any]:
        """Import processed data into database."""
        logger.info("Importing data into database...")

        try:
            cmd = [sys.executable, "direct_import.py"]

            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                output = result.stdout
                # Parse import results
                imported = 0
                if "Records imported:" in output:
                    lines = output.split('\n')
                    for line in lines:
                        if "Records imported:" in line:
                            try:
                                imported = int(line.split(':')[1].strip())
                                break
                            except (IndexError, ValueError):
                                pass

                return {
                    'success': True,
                    'records_imported': imported,
                    'message': f"Successfully imported {imported} records"
                }
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                return {
                    'success': False,
                    'records_imported': 0,
                    'message': f"Import failed: {error_msg}"
                }

        except Exception as e:
            return {
                'success': False,
                'records_imported': 0,
                'message': f"Import error: {str(e)}"
            }

    def process_county(self, county_name: str, max_pages: int = 100) -> Dict[str, Any]:
        """Process a single county (scrape + import)."""
        logger.info(f"Processing {county_name} County...")

        # Scrape
        scrape_result = self.scrape_county(county_name, max_pages)

        if not scrape_result['success']:
            return {
                'county': county_name,
                'success': False,
                'records_added': 0,
                'message': f"Scraping failed: {scrape_result['message']}"
            }

        if scrape_result['records_scraped'] == 0:
            return {
                'county': county_name,
                'success': True,
                'records_added': 0,
                'message': "No data available for this county"
            }

        # Import
        import_result = self.import_data()

        return {
            'county': county_name,
            'success': import_result['success'],
            'records_scraped': scrape_result['records_scraped'],
            'records_added': import_result['records_imported'],
            'message': f"Scraped: {scrape_result['records_scraped']}, Imported: {import_result['records_imported']}"
        }

    def run_expansion(self, target_counties: int = 10, max_pages: int = 100,
                     specific_counties: List[str] = None, conservative_mode: bool = False) -> Dict[str, Any]:
        """Run the county expansion process."""
        logger.info(f"Starting county expansion - Target: {target_counties} counties")

        initial_stats = self.get_current_database_stats()
        logger.info(f"Initial database: {initial_stats['total_properties']} properties from {initial_stats['counties_with_data']} counties")

        # Get counties to process
        if specific_counties:
            counties_to_process = [(name, 100) for name in specific_counties]
        else:
            prioritized_counties = self.get_prioritized_county_list()
            counties_to_process = prioritized_counties[:target_counties]

        if conservative_mode:
            max_pages = min(max_pages, 20)  # Limit pages in conservative mode

        logger.info(f"Counties to process: {[county[0] for county in counties_to_process]}")

        # Process each county
        for i, (county_name, priority) in enumerate(counties_to_process, 1):
            logger.info(f"Processing county {i}/{len(counties_to_process)}: {county_name} (Priority: {priority})")

            result = self.process_county(county_name, max_pages)

            if result['success']:
                self.counties_processed.append(result)
                self.total_properties_added += result.get('records_added', 0)
                logger.info(f"✅ {county_name}: {result['message']}")
            else:
                self.counties_failed.append(result)
                logger.warning(f"❌ {county_name}: {result['message']}")

            # Rate limiting between counties
            if i < len(counties_to_process):
                logger.info("Rate limiting: waiting 30 seconds before next county...")
                time.sleep(30)

        # Final statistics
        final_stats = self.get_current_database_stats()
        duration = datetime.now() - self.start_time

        return {
            'success': True,
            'duration_minutes': duration.total_seconds() / 60,
            'counties_processed': len(self.counties_processed),
            'counties_failed': len(self.counties_failed),
            'total_properties_added': self.total_properties_added,
            'initial_properties': initial_stats['total_properties'],
            'final_properties': final_stats['total_properties'],
            'processed_counties': self.counties_processed,
            'failed_counties': self.counties_failed
        }

    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate detailed expansion report."""
        report = f"""
=============================================================
ALABAMA AUCTION WATCHER - COUNTY EXPANSION REPORT
=============================================================
Execution Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Duration: {results['duration_minutes']:.1f} minutes

DATABASE GROWTH:
  Initial Properties: {results['initial_properties']:,}
  Final Properties: {results['final_properties']:,}
  Net Properties Added: {results['total_properties_added']:,}
  Growth Rate: {((results['final_properties'] - results['initial_properties']) / results['initial_properties'] * 100):.1f}%

PROCESSING SUMMARY:
  Counties Processed: {results['counties_processed']}
  Counties Failed: {results['counties_failed']}
  Success Rate: {(results['counties_processed'] / (results['counties_processed'] + results['counties_failed']) * 100):.1f}%

SUCCESSFULLY PROCESSED COUNTIES:
"""

        for county_result in results['processed_counties']:
            report += f"  ✅ {county_result['county']}: {county_result.get('records_added', 0)} properties added\n"

        if results['failed_counties']:
            report += "\nFAILED COUNTIES:\n"
            for county_result in results['failed_counties']:
                report += f"  ❌ {county_result['county']}: {county_result['message']}\n"

        # Progress toward 3,000+ goal
        goal_progress = (results['final_properties'] / 3000) * 100
        remaining = max(0, 3000 - results['final_properties'])

        report += f"""
GOAL PROGRESS:
  Target: 3,000+ properties
  Current: {results['final_properties']:,} properties
  Progress: {goal_progress:.1f}%
  Remaining: {remaining:,} properties needed

RECOMMENDATIONS:
"""

        if results['final_properties'] < 3000:
            counties_needed = max(1, remaining // 30)  # Estimate 30 properties per county
            report += f"  • Continue expansion with approximately {counties_needed} more counties\n"
            report += f"  • Focus on high-priority counties for better property yields\n"
        else:
            report += f"  • 🎉 Congratulations! You've exceeded the 3,000 property goal!\n"
            report += f"  • Consider focusing on data quality and optimization\n"

        report += f"""
  • Consider re-processing failed counties during different auction cycles
  • Monitor property turnover and refresh existing county data periodically

=============================================================
"""

        return report


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Automated County Expansion for Alabama Auction Watcher')

    parser.add_argument('--target-counties', type=int, default=10,
                        help='Number of counties to process (default: 10)')
    parser.add_argument('--max-pages', type=int, default=100,
                        help='Maximum pages per county (default: 100)')
    parser.add_argument('--counties', nargs='+',
                        help='Specific counties to process (overrides target-counties)')
    parser.add_argument('--all-counties', action='store_true',
                        help='Process all remaining counties')
    parser.add_argument('--conservative', action='store_true',
                        help='Conservative mode (limits pages and processing)')
    parser.add_argument('--report-only', action='store_true',
                        help='Generate status report without processing')

    args = parser.parse_args()

    # Create logs directory if it doesn't exist
    Path('logs').mkdir(exist_ok=True)

    # Initialize manager
    manager = CountyExpansionManager()

    if args.report_only:
        # Generate status report only
        stats = manager.get_current_database_stats()
        prioritized = manager.get_prioritized_county_list()

        print(f"""
Alabama Auction Watcher - Database Status Report
================================================
Total Properties: {stats['total_properties']:,}
Counties with Data: {stats['counties_with_data']}
Average Investment Score: {stats['avg_score']:.1f}

Progress toward 3,000+ goal: {(stats['total_properties'] / 3000 * 100):.1f}%

Next Recommended Counties:
""")
        for i, (county, priority) in enumerate(prioritized[:10], 1):
            print(f"  {i}. {county} (Priority: {priority})")

        return

    # Determine counties to process
    if args.all_counties:
        prioritized_counties = manager.get_prioritized_county_list()
        target_counties = len(prioritized_counties)
        specific_counties = None
    elif args.counties:
        target_counties = len(args.counties)
        specific_counties = args.counties
    else:
        target_counties = args.target_counties
        specific_counties = None

    # Run expansion
    try:
        results = manager.run_expansion(
            target_counties=target_counties,
            max_pages=args.max_pages,
            specific_counties=specific_counties,
            conservative_mode=args.conservative
        )

        # Generate and save report
        report = manager.generate_report(results)
        print(report)

        # Save report to file
        report_file = f"logs/expansion_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)

        logger.info(f"Detailed report saved to: {report_file}")

    except KeyboardInterrupt:
        logger.info("Expansion interrupted by user")
        print("\n⚠️ County expansion interrupted. Partial results may be available.")
    except Exception as e:
        logger.error(f"Expansion failed: {e}")
        print(f"\n❌ County expansion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()