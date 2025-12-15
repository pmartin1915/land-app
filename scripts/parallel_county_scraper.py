#!/usr/bin/env python3
"""
Parallel County Scraper for Alabama Auction Watcher

This module implements sophisticated parallel scraping across all 67 Alabama counties
with intelligent rate limiting, error recovery, and progress monitoring.

Features:
- Concurrent scraping with configurable worker pools
- Intelligent rate limiting per county
- Real-time progress monitoring and reporting
- Comprehensive error handling and recovery
- Resume capability for interrupted scraping sessions
- Data quality validation and statistics
"""

import asyncio
import concurrent.futures
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import pandas as pd
import sys
import threading
from queue import Queue
import signal

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.scraper import scrape_county_data, ALABAMA_COUNTY_CODES, get_county_name
from config.enhanced_error_handling import enhanced_error_handler, smart_retry, get_user_friendly_error_message
from config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class CountyScrapeResult:
    """Result of a county scraping operation."""
    county_code: str
    county_name: str
    success: bool
    records_scraped: int
    pages_processed: int
    duration_seconds: float
    start_time: datetime
    end_time: datetime
    error_message: Optional[str] = None
    data_file_path: Optional[str] = None
    data_quality_score: float = 0.0


@dataclass
class ScrapingSession:
    """Configuration and state for a scraping session."""
    session_id: str
    start_time: datetime
    max_workers: int
    counties_to_scrape: List[str]
    max_pages_per_county: int
    rate_limit_delay: float
    resume_from_checkpoint: bool = False
    checkpoint_file: Optional[str] = None


class ParallelCountyScraper:
    """Advanced parallel scraper for Alabama counties."""

    def __init__(self,
                 max_workers: int = 4,
                 max_pages_per_county: int = 100,
                 rate_limit_delay: float = 3.0,
                 checkpoint_interval: int = 5):
        """
        Initialize the parallel scraper.

        Args:
            max_workers: Maximum number of concurrent scraping operations
            max_pages_per_county: Maximum pages to scrape per county
            rate_limit_delay: Base delay between requests (seconds)
            checkpoint_interval: How often to save progress (counties)
        """
        self.max_workers = max_workers
        self.max_pages_per_county = max_pages_per_county
        self.rate_limit_delay = rate_limit_delay
        self.checkpoint_interval = checkpoint_interval

        # State management
        self.session: Optional[ScrapingSession] = None
        self.results: List[CountyScrapeResult] = []
        self.progress_queue = Queue()
        self.shutdown_event = threading.Event()

        # Statistics
        self.total_records = 0
        self.successful_counties = 0
        self.failed_counties = 0

        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
        self.shutdown_event.set()

    def create_session(self,
                      counties: Optional[List[str]] = None,
                      session_id: Optional[str] = None) -> ScrapingSession:
        """Create a new scraping session."""
        if counties is None:
            counties = list(ALABAMA_COUNTY_CODES.keys())

        if session_id is None:
            session_id = f"scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.session = ScrapingSession(
            session_id=session_id,
            start_time=datetime.now(),
            max_workers=self.max_workers,
            counties_to_scrape=counties,
            max_pages_per_county=self.max_pages_per_county,
            rate_limit_delay=self.rate_limit_delay
        )

        logger.info(f"Created scraping session {session_id} for {len(counties)} counties")
        return self.session

    def save_checkpoint(self, checkpoint_file: Optional[str] = None):
        """Save current progress to checkpoint file."""
        if not self.session:
            return

        if checkpoint_file is None:
            checkpoint_dir = Path("data/checkpoints")
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
            checkpoint_file = checkpoint_dir / f"{self.session.session_id}_checkpoint.json"

        checkpoint_data = {
            "session": asdict(self.session),
            "results": [asdict(result) for result in self.results],
            "statistics": {
                "total_records": self.total_records,
                "successful_counties": self.successful_counties,
                "failed_counties": self.failed_counties,
                "completion_percentage": (len(self.results) / len(self.session.counties_to_scrape)) * 100
            },
            "checkpoint_time": datetime.now().isoformat()
        }

        try:
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2, default=str)
            logger.info(f"Checkpoint saved to {checkpoint_file}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def load_checkpoint(self, checkpoint_file: str) -> bool:
        """Load progress from checkpoint file."""
        try:
            with open(checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)

            # Restore session
            session_data = checkpoint_data["session"]
            self.session = ScrapingSession(**session_data)

            # Restore results
            self.results = [CountyScrapeResult(**result) for result in checkpoint_data["results"]]

            # Restore statistics
            stats = checkpoint_data["statistics"]
            self.total_records = stats["total_records"]
            self.successful_counties = stats["successful_counties"]
            self.failed_counties = stats["failed_counties"]

            # Update counties to scrape (remove already completed)
            completed_counties = {result.county_code for result in self.results if result.success}
            self.session.counties_to_scrape = [
                code for code in self.session.counties_to_scrape
                if code not in completed_counties
            ]

            logger.info(f"Checkpoint loaded. Resuming with {len(self.session.counties_to_scrape)} remaining counties")
            return True

        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return False

    @smart_retry(max_retries=2, base_delay=5.0)
    def scrape_single_county(self, county_code: str) -> CountyScrapeResult:
        """Scrape a single county with comprehensive error handling."""
        county_name = get_county_name(county_code)
        start_time = datetime.now()

        logger.info(f"Starting scrape for {county_name} County (code: {county_code})")

        try:
            # Add dynamic rate limiting based on worker load
            worker_delay = self.rate_limit_delay * (1 + (self.max_workers - 1) * 0.3)
            time.sleep(worker_delay)

            # Perform the scraping
            df = scrape_county_data(
                county_input=county_code,
                max_pages=self.max_pages_per_county,
                save_raw=True
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Calculate data quality score
            quality_score = self._calculate_data_quality_score(df)

            # Determine data file path
            data_file_path = None
            if not df.empty:
                timestamp = start_time.strftime("%Y%m%d_%H%M%S")
                data_file_path = f"data/raw/scraped_{county_name.lower().replace(' ', '_')}_county_{timestamp}.csv"

            result = CountyScrapeResult(
                county_code=county_code,
                county_name=county_name,
                success=not df.empty,
                records_scraped=len(df),
                pages_processed=0,  # This would need to be passed from scraper
                duration_seconds=duration,
                start_time=start_time,
                end_time=end_time,
                data_file_path=data_file_path,
                data_quality_score=quality_score
            )

            if result.success:
                self.successful_counties += 1
                self.total_records += result.records_scraped
                logger.info(f"✅ {county_name}: {result.records_scraped} records in {duration:.1f}s")
            else:
                self.failed_counties += 1
                logger.warning(f"⚠️ {county_name}: No data found")

            return result

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            user_msg, suggestions = get_user_friendly_error_message(e)

            self.failed_counties += 1
            logger.error(f"❌ {county_name}: {user_msg}")

            return CountyScrapeResult(
                county_code=county_code,
                county_name=county_name,
                success=False,
                records_scraped=0,
                pages_processed=0,
                duration_seconds=duration,
                start_time=start_time,
                end_time=end_time,
                error_message=user_msg
            )

    def _calculate_data_quality_score(self, df: pd.DataFrame) -> float:
        """Calculate data quality score for scraped data."""
        if df.empty:
            return 0.0

        score = 0.0
        max_score = 100.0

        # Basic data availability (30 points)
        required_columns = ['parcel_id', 'amount', 'county']
        available_required = sum(1 for col in required_columns if col in df.columns)
        score += (available_required / len(required_columns)) * 30

        # Data completeness (25 points)
        if not df.empty:
            non_null_ratio = (df.count().sum() / (len(df) * len(df.columns)))
            score += non_null_ratio * 25

        # Price data quality (20 points)
        if 'amount' in df.columns:
            valid_prices = df['amount'].notna() & (df['amount'] > 0)
            if len(df) > 0:
                score += (valid_prices.sum() / len(df)) * 20

        # Acreage data quality (15 points)
        if 'acreage' in df.columns:
            valid_acreage = df['acreage'].notna() & (df['acreage'] > 0)
            if len(df) > 0:
                score += (valid_acreage.sum() / len(df)) * 15

        # Record volume bonus (10 points)
        if len(df) >= 100:
            score += 10
        elif len(df) >= 50:
            score += 7
        elif len(df) >= 10:
            score += 4

        return min(score, max_score)

    def run_parallel_scraping(self,
                            counties: Optional[List[str]] = None,
                            resume_from_checkpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Run parallel scraping across multiple counties.

        Args:
            counties: List of county codes to scrape (None = all counties)
            resume_from_checkpoint: Path to checkpoint file to resume from

        Returns:
            Dictionary with scraping results and statistics
        """
        # Setup session
        if resume_from_checkpoint and Path(resume_from_checkpoint).exists():
            if not self.load_checkpoint(resume_from_checkpoint):
                logger.error("Failed to load checkpoint. Starting fresh.")
                self.create_session(counties)
        else:
            self.create_session(counties)

        if not self.session:
            raise ValueError("Failed to create or load scraping session")

        logger.info(f"Starting parallel scraping with {self.max_workers} workers for {len(self.session.counties_to_scrape)} counties")

        start_time = time.time()
        completed_counties = 0

        # Start progress monitoring thread
        progress_thread = threading.Thread(target=self._monitor_progress, daemon=True)
        progress_thread.start()

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all county scraping tasks
                future_to_county = {
                    executor.submit(self.scrape_single_county, county_code): county_code
                    for county_code in self.session.counties_to_scrape
                }

                # Process completed tasks
                for future in concurrent.futures.as_completed(future_to_county):
                    if self.shutdown_event.is_set():
                        logger.info("Shutdown requested. Cancelling remaining tasks...")
                        break

                    county_code = future_to_county[future]

                    try:
                        result = future.result()
                        self.results.append(result)
                        completed_counties += 1

                        # Report progress
                        progress_pct = (completed_counties / len(self.session.counties_to_scrape)) * 100
                        logger.info(f"Progress: {completed_counties}/{len(self.session.counties_to_scrape)} counties ({progress_pct:.1f}%)")

                        # Save checkpoint periodically
                        if completed_counties % self.checkpoint_interval == 0:
                            self.save_checkpoint()

                    except Exception as e:
                        logger.error(f"Failed to get result for county {county_code}: {e}")

                        # Create failed result
                        failed_result = CountyScrapeResult(
                            county_code=county_code,
                            county_name=get_county_name(county_code),
                            success=False,
                            records_scraped=0,
                            pages_processed=0,
                            duration_seconds=0,
                            start_time=datetime.now(),
                            end_time=datetime.now(),
                            error_message=str(e)
                        )
                        self.results.append(failed_result)
                        self.failed_counties += 1

        except KeyboardInterrupt:
            logger.info("Scraping interrupted by user")
        except Exception as e:
            logger.error(f"Unexpected error during parallel scraping: {e}")

        finally:
            # Save final checkpoint
            self.save_checkpoint()

            # Calculate final statistics
            total_duration = time.time() - start_time

            summary = self._generate_summary_report(total_duration)
            logger.info("Parallel scraping completed")

            return summary

    def _monitor_progress(self):
        """Monitor and report scraping progress."""
        while not self.shutdown_event.is_set():
            time.sleep(30)  # Update every 30 seconds

            if self.session and self.results:
                completed = len(self.results)
                total = len(self.session.counties_to_scrape)
                success_rate = (self.successful_counties / completed) * 100 if completed > 0 else 0

                logger.info(f"📊 Progress Update: {completed}/{total} counties, "
                          f"{self.total_records:,} records, {success_rate:.1f}% success rate")

    def _generate_summary_report(self, total_duration: float) -> Dict[str, Any]:
        """Generate comprehensive summary report."""
        total_counties = len(self.results)
        avg_quality_score = sum(r.data_quality_score for r in self.results) / total_counties if total_counties > 0 else 0

        # County performance analysis
        top_performers = sorted([r for r in self.results if r.success],
                              key=lambda x: x.records_scraped, reverse=True)[:5]

        failed_counties = [r for r in self.results if not r.success]

        summary = {
            "session_info": {
                "session_id": self.session.session_id if self.session else "unknown",
                "start_time": self.session.start_time.isoformat() if self.session else None,
                "total_duration_seconds": total_duration,
                "total_duration_formatted": str(timedelta(seconds=int(total_duration)))
            },
            "overall_statistics": {
                "total_counties_processed": total_counties,
                "successful_counties": self.successful_counties,
                "failed_counties": self.failed_counties,
                "success_rate_percentage": (self.successful_counties / total_counties * 100) if total_counties > 0 else 0,
                "total_records_scraped": self.total_records,
                "average_records_per_county": self.total_records / self.successful_counties if self.successful_counties > 0 else 0,
                "average_data_quality_score": avg_quality_score
            },
            "performance_metrics": {
                "records_per_second": self.total_records / total_duration if total_duration > 0 else 0,
                "counties_per_hour": total_counties / (total_duration / 3600) if total_duration > 0 else 0,
                "average_time_per_county": total_duration / total_counties if total_counties > 0 else 0
            },
            "top_performing_counties": [
                {
                    "county_name": r.county_name,
                    "records_scraped": r.records_scraped,
                    "data_quality_score": r.data_quality_score,
                    "duration_seconds": r.duration_seconds
                }
                for r in top_performers
            ],
            "failed_counties": [
                {
                    "county_name": r.county_name,
                    "error_message": r.error_message,
                    "duration_seconds": r.duration_seconds
                }
                for r in failed_counties
            ],
            "data_files": [r.data_file_path for r in self.results if r.data_file_path]
        }

        return summary

    def export_results(self, output_dir: str = "data/scraping_results"):
        """Export scraping results to files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if not self.session:
            logger.error("No session data to export")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Export detailed results to CSV
        results_data = []
        for result in self.results:
            results_data.append({
                "county_code": result.county_code,
                "county_name": result.county_name,
                "success": result.success,
                "records_scraped": result.records_scraped,
                "pages_processed": result.pages_processed,
                "duration_seconds": result.duration_seconds,
                "data_quality_score": result.data_quality_score,
                "start_time": result.start_time.isoformat(),
                "end_time": result.end_time.isoformat(),
                "error_message": result.error_message,
                "data_file_path": result.data_file_path
            })

        results_df = pd.DataFrame(results_data)
        results_file = output_path / f"scraping_results_{timestamp}.csv"
        results_df.to_csv(results_file, index=False)

        logger.info(f"Results exported to {results_file}")


def main():
    """Main function for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Parallel Alabama County Scraper")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers")
    parser.add_argument("--max-pages", type=int, default=100, help="Max pages per county")
    parser.add_argument("--counties", nargs="+", help="Specific county codes to scrape")
    parser.add_argument("--resume", type=str, help="Resume from checkpoint file")
    parser.add_argument("--rate-limit", type=float, default=3.0, help="Rate limit delay in seconds")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create and run scraper
    scraper = ParallelCountyScraper(
        max_workers=args.workers,
        max_pages_per_county=args.max_pages,
        rate_limit_delay=args.rate_limit
    )

    try:
        summary = scraper.run_parallel_scraping(
            counties=args.counties,
            resume_from_checkpoint=args.resume
        )

        # Print summary
        print("\n" + "="*60)
        print("SCRAPING SUMMARY")
        print("="*60)
        print(f"Total Counties: {summary['overall_statistics']['total_counties_processed']}")
        print(f"Success Rate: {summary['overall_statistics']['success_rate_percentage']:.1f}%")
        print(f"Total Records: {summary['overall_statistics']['total_records_scraped']:,}")
        print(f"Duration: {summary['session_info']['total_duration_formatted']}")
        print(f"Records/Second: {summary['performance_metrics']['records_per_second']:.1f}")

        # Export results
        scraper.export_results()

    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
    except Exception as e:
        print(f"Scraping failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())