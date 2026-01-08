#!/usr/bin/env python3
"""
Run All Scrapers - Comprehensive scraping for all states and counties

Usage:
    python scripts/run_all_scrapers.py --all          # Run all states
    python scripts/run_all_scrapers.py --state AR     # Just Arkansas
    python scripts/run_all_scrapers.py --state AL     # Just Alabama (missing counties only)
    python scripts/run_all_scrapers.py --state TX     # Just Texas
    python scripts/run_all_scrapers.py --state AL --all-counties  # All Alabama counties
"""

import asyncio
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import get_logger
from config.states import ALABAMA_COUNTIES, ALABAMA_MISSING_COUNTIES, TEXAS_COUNTIES
from core.scrapers.factory import ScraperFactory

logger = get_logger(__name__)


async def _scrape_counties(state: str, counties: List[str], results: Dict[str, Any]) -> None:
    """Scrape multiple counties for a state and update results dict."""
    results['counties_attempted'] = len(counties)

    for county in counties:
        logger.info(f"Scraping {state} - {county} County...")
        try:
            result = await ScraperFactory.scrape(state=state, county=county)

            county_result = {
                'county': county,
                'properties': result.items_found,
                'success': result.error_message is None
            }

            if result.error_message:
                county_result['error'] = result.error_message
                results['errors'].append({'county': county, 'error': result.error_message})
                results['counties_failed'] += 1
            else:
                results['counties_succeeded'] += 1
                results['total_properties'] += result.items_found

            results['county_results'].append(county_result)
            logger.info(f"  {county}: {result.items_found} properties" +
                       (f" (ERROR: {result.error_message})" if result.error_message else ""))

            # Brief delay between counties to avoid rate limiting
            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Exception scraping {county}: {e}")
            results['errors'].append({'county': county, 'error': str(e)})
            results['counties_failed'] += 1


async def scrape_state(state: str, counties: Optional[List[str]] = None) -> Dict[str, Any]:
    """Scrape a single state (with optional county filter for county-based states)."""
    results = {
        'state': state,
        'started_at': datetime.now().isoformat(),
        'counties_attempted': 0,
        'counties_succeeded': 0,
        'counties_failed': 0,
        'total_properties': 0,
        'errors': [],
        'county_results': []
    }

    if state == 'AR':
        # Arkansas - centralized system, no counties needed
        logger.info("Scraping Arkansas (centralized COSL system)...")
        result = await ScraperFactory.scrape(state='AR')

        if result.error_message:
            results['errors'].append({'state': 'AR', 'error': result.error_message})
            results['counties_failed'] = 1
        else:
            results['counties_succeeded'] = 1
            results['total_properties'] = result.items_found
            logger.info(f"Arkansas: Found {result.items_found} properties")

        results['counties_attempted'] = 1

    elif state == 'AL':
        # Alabama - county-based system
        counties_to_scrape = counties or ALABAMA_MISSING_COUNTIES
        await _scrape_counties('AL', counties_to_scrape, results)

    elif state == 'TX':
        # Texas - county-based system
        counties_to_scrape = counties or TEXAS_COUNTIES
        await _scrape_counties('TX', counties_to_scrape, results)

    else:
        results['errors'].append({'error': f'Unknown state: {state}'})

    results['completed_at'] = datetime.now().isoformat()
    return results


async def run_all_scrapers(states: List[str], all_counties: bool = False) -> Dict[str, Any]:
    """Run scrapers for multiple states."""
    summary = {
        'started_at': datetime.now().isoformat(),
        'states_processed': [],
        'total_properties': 0,
        'state_results': {}
    }

    for state in states:
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting {state} scraping...")
        logger.info(f"{'='*60}")

        # For Alabama, optionally scrape all counties
        counties = None
        if state == 'AL' and all_counties:
            counties = ALABAMA_COUNTIES

        result = await scrape_state(state, counties)
        summary['state_results'][state] = result
        summary['states_processed'].append(state)
        summary['total_properties'] += result['total_properties']

        logger.info(f"\n{state} Summary:")
        logger.info(f"  Counties attempted: {result['counties_attempted']}")
        logger.info(f"  Counties succeeded: {result['counties_succeeded']}")
        logger.info(f"  Counties failed: {result['counties_failed']}")
        logger.info(f"  Total properties: {result['total_properties']}")

    summary['completed_at'] = datetime.now().isoformat()

    return summary


def main():
    parser = argparse.ArgumentParser(description='Run all scrapers')
    parser.add_argument('--all', action='store_true', help='Run all states')
    parser.add_argument('--state', type=str, help='Run specific state (AR, AL, TX)')
    parser.add_argument('--all-counties', action='store_true',
                        help='For AL: scrape all counties instead of just missing ones')
    parser.add_argument('--output', type=str, default='scrape_results.json',
                        help='Output file for results')

    args = parser.parse_args()

    if args.all:
        states = ['AR', 'AL', 'TX']
    elif args.state:
        states = [args.state.upper()]
    else:
        print("Usage: python run_all_scrapers.py --all OR --state AR|AL|TX")
        print("\nCurrent data in database:")
        print("  Arkansas: 2,159 properties (40 counties)")
        print("  Alabama: 3,946 properties (39 counties, 28 missing)")
        print("  Texas: 1 property (8 counties supported)")
        return 1

    logger.info(f"Starting scrape for states: {states}")

    # Run async scraper
    summary = asyncio.run(run_all_scrapers(states, args.all_counties))

    # Save results
    output_path = project_root / args.output
    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2)

    logger.info(f"\nResults saved to {output_path}")

    # Print summary
    print("\n" + "="*60)
    print("SCRAPING COMPLETE")
    print("="*60)
    print(f"States processed: {', '.join(summary['states_processed'])}")
    print(f"Total properties scraped: {summary['total_properties']}")
    print(f"Duration: {summary['started_at']} to {summary['completed_at']}")

    for state, result in summary['state_results'].items():
        print(f"\n{state}:")
        print(f"  Attempted: {result['counties_attempted']} counties")
        print(f"  Succeeded: {result['counties_succeeded']} counties")
        print(f"  Failed: {result['counties_failed']} counties")
        print(f"  Properties: {result['total_properties']}")
        if result['errors']:
            print(f"  Errors: {len(result['errors'])}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
