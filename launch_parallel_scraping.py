#!/usr/bin/env python3
"""
Simple launcher for parallel county scraping

This script provides an easy way to start scraping all 67 Alabama counties
with intelligent defaults and progress monitoring.
"""

import sys
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scripts.parallel_county_scraper import ParallelCountyScraper

def main():
    """Launch parallel scraping with user-friendly interface."""
    print("Alabama Auction Watcher - Parallel County Scraper")
    print("="*60)
    print("This will scrape all 67 Alabama counties for property data.")
    print("Estimated time: 2-4 hours depending on data availability.")
    print("Progress will be automatically saved and can be resumed if interrupted.")
    print()

    # Get user preferences
    try:
        workers = input("Number of parallel workers (default: 4): ").strip()
        workers = int(workers) if workers else 4
        workers = max(1, min(workers, 8))  # Limit between 1-8
    except ValueError:
        workers = 4

    try:
        pages = input("Max pages per county (default: 100): ").strip()
        pages = int(pages) if pages else 100
        pages = max(10, min(pages, 500))  # Limit between 10-500
    except ValueError:
        pages = 100

    print(f"\nConfiguration:")
    print(f"- Workers: {workers}")
    print(f"- Max pages per county: {pages}")
    print(f"- Rate limiting: Intelligent adaptive")
    print(f"- Error handling: Enhanced with retry logic")
    print(f"- Checkpoints: Every 5 counties")

    confirm = input("\nStart scraping? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("Scraping cancelled.")
        return

    print("\nStarting parallel scraping...")
    print("Press Ctrl+C at any time to safely stop and save progress.")
    print("-" * 60)

    # Create and run scraper
    scraper = ParallelCountyScraper(
        max_workers=workers,
        max_pages_per_county=pages,
        rate_limit_delay=2.5  # Conservative rate limiting
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

        print(f"📊 Results Summary:")
        print(f"   • Total Counties: {stats['total_counties_processed']}")
        print(f"   • Successful: {stats['successful_counties']} ({stats['success_rate_percentage']:.1f}%)")
        print(f"   • Total Properties: {stats['total_records_scraped']:,}")
        print(f"   • Average per County: {stats['average_records_per_county']:.0f}")
        print(f"   • Data Quality Score: {stats['average_data_quality_score']:.1f}/100")

        print(f"\n⏱️ Performance:")
        print(f"   • Total Duration: {summary['session_info']['total_duration_formatted']}")
        print(f"   • Records/Second: {perf['records_per_second']:.1f}")
        print(f"   • Counties/Hour: {perf['counties_per_hour']:.1f}")

        if summary['top_performing_counties']:
            print(f"\n🏆 Top Performing Counties:")
            for i, county in enumerate(summary['top_performing_counties'][:3], 1):
                print(f"   {i}. {county['county_name']}: {county['records_scraped']:,} properties")

        if summary['failed_counties']:
            print(f"\n⚠️ Failed Counties ({len(summary['failed_counties'])}):")
            for county in summary['failed_counties'][:3]:
                print(f"   • {county['county_name']}: {county['error_message']}")

        print(f"\n💾 Data Files:")
        print(f"   • Raw data saved to: data/raw/")
        print(f"   • Results exported to: data/scraping_results/")
        print(f"   • Checkpoints saved to: data/checkpoints/")

        # Suggest next steps
        print(f"\n🚀 Next Steps:")
        print(f"   1. Run 'python scripts/import_data.py' to load data into database")
        print(f"   2. Start the application: 'streamlit run streamlit_app/app.py'")
        print(f"   3. Explore your expanded property database!")

    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user.")
        print("Progress has been saved automatically.")
        print("Run this script again to resume from where you left off.")
    except Exception as e:
        print(f"\nScraping failed: {e}")
        print("Check logs for details. Progress has been saved.")

if __name__ == "__main__":
    main()