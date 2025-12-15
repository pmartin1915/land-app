#!/usr/bin/env python3
"""
Non-interactive launcher for parallel county scraping

This script automatically starts scraping all remaining Alabama counties
with intelligent defaults for automated execution.
"""

import sys
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scripts.parallel_county_scraper import ParallelCountyScraper

def main():
    """Launch parallel scraping with intelligent defaults."""
    print("Alabama Auction Watcher - Automated Parallel County Scraper")
    print("="*60)
    print("This will scrape all remaining Alabama counties for property data.")
    print("Estimated time: 2-4 hours depending on data availability.")
    print("Progress will be automatically saved and can be resumed if interrupted.")
    print()

    # Use intelligent defaults for automated execution
    workers = 4  # Conservative number of workers
    pages = 100  # Max pages per county
    rate_limit = 2.5  # Conservative rate limiting

    print(f"Configuration:")
    print(f"- Workers: {workers}")
    print(f"- Max pages per county: {pages}")
    print(f"- Rate limiting: {rate_limit}s")
    print(f"- Error handling: Enhanced with retry logic")
    print(f"- Checkpoints: Every 5 counties")
    print()

    print("Starting automated parallel scraping...")
    print("Progress will be displayed in real-time.")
    print("-" * 60)

    # Create and run scraper
    scraper = ParallelCountyScraper(
        max_workers=workers,
        max_pages_per_county=pages,
        rate_limit_delay=rate_limit
    )

    try:
        start_time = time.time()
        summary = scraper.run_parallel_scraping()

        # Display final results
        print("\n" + "="*60)
        print("SCRAPING COMPLETED!")
        print("="*60)

        stats = summary['overall_statistics']
        perf = summary['performance_metrics']

        print(f"Results Summary:")
        print(f"   • Total Counties: {stats['total_counties_processed']}")
        print(f"   • Successful: {stats['successful_counties']} ({stats['success_rate_percentage']:.1f}%)")
        print(f"   • Total Properties: {stats['total_records_scraped']:,}")
        print(f"   • Average per County: {stats['average_records_per_county']:.0f}")
        print(f"   • Data Quality Score: {stats['average_data_quality_score']:.1f}/100")

        print(f"\nPerformance:")
        print(f"   • Total Duration: {summary['session_info']['total_duration_formatted']}")
        print(f"   • Records/Second: {perf['records_per_second']:.1f}")
        print(f"   • Counties/Hour: {perf['counties_per_hour']:.1f}")

        if summary['top_performing_counties']:
            print(f"\nTop Performing Counties:")
            for i, county in enumerate(summary['top_performing_counties'][:3], 1):
                print(f"   {i}. {county['county_name']}: {county['records_scraped']:,} properties")

        if summary['failed_counties']:
            print(f"\nFailed Counties ({len(summary['failed_counties'])}):")
            for county in summary['failed_counties'][:3]:
                print(f"   • {county['county_name']}: {county['error_message']}")

        print(f"\nData Files:")
        print(f"   • Raw data saved to: data/raw/")
        print(f"   • Results exported to: data/scraping_results/")
        print(f"   • Checkpoints saved to: data/checkpoints/")

        # Suggest next steps
        print(f"\nNext Steps:")
        print(f"   1. Run 'python scripts/import_data.py' to load data into database")
        print(f"   2. Start the application: 'streamlit run streamlit_app/app.py'")
        print(f"   3. Explore your expanded property database!")

        return summary

    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user.")
        print("Progress has been saved automatically.")
        print("Run this script again to resume from where you left off.")
        return None
    except Exception as e:
        print(f"\nScraping failed: {e}")
        print("Check logs for details. Progress has been saved.")
        return None

if __name__ == "__main__":
    main()