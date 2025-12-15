#!/usr/bin/env python3
"""
Data Freshness Monitoring and Alerting System for Alabama Auction Watcher

This script monitors data freshness, tracks scraping status, and provides
alerting capabilities for when data becomes stale or scraping issues occur.
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import sys

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataFreshnessMonitor:
    """Monitor data freshness and provide alerting capabilities."""

    def __init__(self, db_path: str = "alabama_auction_watcher.db"):
        self.db_path = db_path
        self.alerts = []
        self.metrics = {}

    def analyze_data_freshness(self) -> Dict[str, Any]:
        """
        Analyze the freshness of data across all counties and data sources.

        Returns:
            Dictionary with freshness analysis and recommendations
        """
        logger.info("Starting data freshness analysis...")

        try:
            # Check database freshness
            db_analysis = self._analyze_database_freshness()

            # Check raw file freshness
            file_analysis = self._analyze_raw_file_freshness()

            # Check scraping activity
            scraping_analysis = self._analyze_scraping_activity()

            # Generate alerts and recommendations
            alerts = self._generate_freshness_alerts(db_analysis, file_analysis, scraping_analysis)

            # Calculate overall freshness score
            freshness_score = self._calculate_freshness_score(db_analysis, file_analysis)

            analysis = {
                'timestamp': datetime.now().isoformat(),
                'overall_freshness_score': freshness_score,
                'database_analysis': db_analysis,
                'raw_files_analysis': file_analysis,
                'scraping_analysis': scraping_analysis,
                'alerts': alerts,
                'recommendations': self._generate_recommendations(freshness_score, alerts)
            }

            logger.info(f"Data freshness analysis complete. Score: {freshness_score:.1f}/100")

            return analysis

        except Exception as e:
            logger.error(f"Data freshness analysis failed: {e}")
            return {'error': str(e)}

    def _analyze_database_freshness(self) -> Dict[str, Any]:
        """Analyze freshness of data in the main database."""
        try:
            conn = sqlite3.connect(self.db_path)

            # Get basic statistics
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM properties")
            total_properties = cursor.fetchone()[0]

            # Get county coverage
            cursor.execute("SELECT COUNT(DISTINCT county) FROM properties")
            counties_with_data = cursor.fetchone()[0]

            # Get data recency (if created_at exists)
            try:
                cursor.execute("""
                    SELECT
                        MIN(created_at) as oldest_record,
                        MAX(created_at) as newest_record,
                        COUNT(*) as total_count
                    FROM properties
                    WHERE created_at IS NOT NULL
                """)
                result = cursor.fetchone()
                oldest_record, newest_record, records_with_timestamps = result

                # Calculate age of newest data
                if newest_record:
                    newest_datetime = datetime.fromisoformat(newest_record.replace('Z', '+00:00').replace('+00:00', ''))
                    hours_since_update = (datetime.now() - newest_datetime).total_seconds() / 3600
                else:
                    hours_since_update = None

            except Exception:
                oldest_record = None
                newest_record = None
                records_with_timestamps = 0
                hours_since_update = None

            # Get county-level freshness
            cursor.execute("""
                SELECT
                    county,
                    COUNT(*) as property_count,
                    MAX(created_at) as last_updated
                FROM properties
                GROUP BY county
                ORDER BY property_count DESC
            """)
            county_data = cursor.fetchall()

            conn.close()

            return {
                'total_properties': total_properties,
                'counties_with_data': counties_with_data,
                'oldest_record': oldest_record,
                'newest_record': newest_record,
                'records_with_timestamps': records_with_timestamps,
                'hours_since_last_update': hours_since_update,
                'county_breakdown': [
                    {
                        'county': row[0],
                        'property_count': row[1],
                        'last_updated': row[2]
                    }
                    for row in county_data
                ]
            }

        except Exception as e:
            logger.error(f"Database freshness analysis failed: {e}")
            return {'error': str(e)}

    def _analyze_raw_file_freshness(self) -> Dict[str, Any]:
        """Analyze freshness of raw CSV files."""
        try:
            raw_data_dir = Path("data/raw")

            if not raw_data_dir.exists():
                return {'error': 'Raw data directory not found'}

            csv_files = list(raw_data_dir.glob("scraped_*_county_*.csv"))

            file_analysis = {
                'total_files': len(csv_files),
                'file_details': [],
                'freshness_distribution': {},
                'oldest_file_hours': 0,
                'newest_file_hours': 0
            }

            now = datetime.now()

            for csv_file in csv_files:
                stat = csv_file.stat()
                modified_time = datetime.fromtimestamp(stat.st_mtime)
                hours_old = (now - modified_time).total_seconds() / 3600

                # Extract county from filename
                parts = csv_file.stem.split('_')
                county = parts[1] if len(parts) > 1 else 'unknown'

                file_info = {
                    'filename': csv_file.name,
                    'county': county,
                    'size_kb': round(stat.st_size / 1024, 2),
                    'modified_time': modified_time.isoformat(),
                    'hours_old': round(hours_old, 2)
                }

                file_analysis['file_details'].append(file_info)

            if csv_files:
                hours_list = [f['hours_old'] for f in file_analysis['file_details']]
                file_analysis['oldest_file_hours'] = max(hours_list)
                file_analysis['newest_file_hours'] = min(hours_list)

                # Categorize freshness
                fresh_files = sum(1 for h in hours_list if h < 24)
                stale_files = sum(1 for h in hours_list if 24 <= h < 168)  # 1-7 days
                very_stale_files = sum(1 for h in hours_list if h >= 168)  # >7 days

                file_analysis['freshness_distribution'] = {
                    'fresh_files_24h': fresh_files,
                    'stale_files_1_7d': stale_files,
                    'very_stale_files_7d_plus': very_stale_files
                }

            return file_analysis

        except Exception as e:
            logger.error(f"Raw file freshness analysis failed: {e}")
            return {'error': str(e)}

    def _analyze_scraping_activity(self) -> Dict[str, Any]:
        """Analyze recent scraping activity and status."""
        try:
            # Check for recent scraping checkpoint files
            checkpoint_dir = Path("data/checkpoints")
            scraping_analysis = {
                'active_scraping_sessions': 0,
                'recent_checkpoints': [],
                'scraping_progress': {}
            }

            if checkpoint_dir.exists():
                checkpoint_files = list(checkpoint_dir.glob("scrape_*_checkpoint.json"))

                for checkpoint_file in checkpoint_files[-5:]:  # Last 5 checkpoints
                    try:
                        with open(checkpoint_file, 'r') as f:
                            checkpoint_data = json.load(f)

                        scraping_analysis['recent_checkpoints'].append({
                            'filename': checkpoint_file.name,
                            'session_id': checkpoint_data.get('session_id', 'unknown'),
                            'total_counties': checkpoint_data.get('total_counties', 0),
                            'completed_counties': checkpoint_data.get('completed_counties', 0),
                            'timestamp': checkpoint_data.get('timestamp', 'unknown')
                        })

                    except Exception as e:
                        logger.warning(f"Failed to read checkpoint {checkpoint_file}: {e}")

            # Check for active scraping processes (simplified)
            # In a real implementation, you might check process lists or pid files

            return scraping_analysis

        except Exception as e:
            logger.error(f"Scraping activity analysis failed: {e}")
            return {'error': str(e)}

    def _generate_freshness_alerts(self, db_analysis: Dict, file_analysis: Dict, scraping_analysis: Dict) -> List[Dict[str, str]]:
        """Generate alerts based on freshness analysis."""
        alerts = []

        # Database alerts
        if 'hours_since_last_update' in db_analysis and db_analysis['hours_since_last_update']:
            hours = db_analysis['hours_since_last_update']

            if hours > 168:  # 7 days
                alerts.append({
                    'type': 'critical',
                    'category': 'database_freshness',
                    'message': f'Database not updated in {hours:.1f} hours (>{hours/24:.1f} days)',
                    'recommendation': 'Run data scraping immediately'
                })
            elif hours > 48:  # 2 days
                alerts.append({
                    'type': 'warning',
                    'category': 'database_freshness',
                    'message': f'Database last updated {hours:.1f} hours ago',
                    'recommendation': 'Consider running fresh data scraping'
                })

        # County coverage alerts
        if 'counties_with_data' in db_analysis:
            county_count = db_analysis['counties_with_data']
            if county_count < 20:
                alerts.append({
                    'type': 'warning',
                    'category': 'coverage',
                    'message': f'Only {county_count} counties have data (low coverage)',
                    'recommendation': 'Expand scraping to more Alabama counties'
                })

        # File freshness alerts
        if 'freshness_distribution' in file_analysis:
            dist = file_analysis['freshness_distribution']
            very_stale = dist.get('very_stale_files_7d_plus', 0)

            if very_stale > 10:
                alerts.append({
                    'type': 'warning',
                    'category': 'file_freshness',
                    'message': f'{very_stale} raw files are over 7 days old',
                    'recommendation': 'Clean up old files or refresh data'
                })

        # Data volume alerts
        if 'total_properties' in db_analysis:
            prop_count = db_analysis['total_properties']
            if prop_count < 1000:
                alerts.append({
                    'type': 'info',
                    'category': 'data_volume',
                    'message': f'Low property count ({prop_count:,} properties)',
                    'recommendation': 'Scale up data collection for better coverage'
                })

        return alerts

    def _calculate_freshness_score(self, db_analysis: Dict, file_analysis: Dict) -> float:
        """Calculate overall freshness score (0-100)."""
        score = 100.0

        # Penalize for database staleness
        if 'hours_since_last_update' in db_analysis and db_analysis['hours_since_last_update']:
            hours = db_analysis['hours_since_last_update']
            if hours > 24:
                score -= min(30, (hours - 24) / 24 * 10)  # Max 30 point penalty

        # Penalize for low county coverage
        if 'counties_with_data' in db_analysis:
            county_count = db_analysis['counties_with_data']
            expected_counties = 67  # Alabama has 67 counties
            coverage_ratio = county_count / expected_counties
            score -= (1 - coverage_ratio) * 40  # Max 40 point penalty

        # Penalize for stale files
        if 'freshness_distribution' in file_analysis:
            dist = file_analysis['freshness_distribution']
            total_files = file_analysis.get('total_files', 1)
            stale_ratio = dist.get('very_stale_files_7d_plus', 0) / total_files
            score -= stale_ratio * 20  # Max 20 point penalty

        return max(0, round(score, 1))

    def _generate_recommendations(self, freshness_score: float, alerts: List[Dict]) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []

        if freshness_score < 50:
            recommendations.append("URGENT: Data freshness is critically low - immediate action required")
        elif freshness_score < 70:
            recommendations.append("Data freshness is below optimal - schedule data refresh soon")

        # Categorize recommendations by alert type
        critical_alerts = [a for a in alerts if a['type'] == 'critical']
        warning_alerts = [a for a in alerts if a['type'] == 'warning']

        if critical_alerts:
            recommendations.append("Address critical alerts immediately")

        if warning_alerts:
            recommendations.append("Review and address warning alerts within 24 hours")

        # General recommendations
        recommendations.extend([
            "Set up automated daily data freshness checks",
            "Implement automated alerting for stale data",
            "Consider real-time data refresh for high-priority counties",
            "Monitor scraping success rates and error patterns"
        ])

        return recommendations

def generate_freshness_report() -> Dict[str, Any]:
    """Generate a comprehensive data freshness report."""
    monitor = DataFreshnessMonitor()
    return monitor.analyze_data_freshness()

def check_and_alert() -> bool:
    """Check data freshness and return True if alerts should be sent."""
    report = generate_freshness_report()

    if 'error' in report:
        logger.error(f"Freshness check failed: {report['error']}")
        return False

    alerts = report.get('alerts', [])
    critical_alerts = [a for a in alerts if a['type'] == 'critical']

    if critical_alerts:
        logger.warning(f"CRITICAL: {len(critical_alerts)} critical data freshness alerts!")
        for alert in critical_alerts:
            logger.warning(f"  - {alert['message']}")
        return True

    freshness_score = report.get('overall_freshness_score', 0)
    if freshness_score < 60:
        logger.warning(f"Data freshness score is low: {freshness_score}/100")
        return True

    logger.info(f"Data freshness check passed. Score: {freshness_score}/100")
    return False

def main():
    """Main monitoring routine."""
    print("Alabama Auction Watcher - Data Freshness Monitor")
    print("=" * 60)
    print("Analyzing data freshness across all data sources...")
    print()

    # Generate report
    report = generate_freshness_report()

    if 'error' in report:
        print(f"Error: {report['error']}")
        return False

    # Save detailed report
    report_file = f"data_freshness_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    # Print summary
    print(f"Data Freshness Report:")
    print(f"  Overall Score: {report['overall_freshness_score']:.1f}/100")

    db_analysis = report.get('database_analysis', {})
    print(f"  Total Properties: {db_analysis.get('total_properties', 0):,}")
    print(f"  Counties with Data: {db_analysis.get('counties_with_data', 0)}")

    if 'hours_since_last_update' in db_analysis and db_analysis['hours_since_last_update']:
        hours = db_analysis['hours_since_last_update']
        print(f"  Last Update: {hours:.1f} hours ago")

    file_analysis = report.get('raw_files_analysis', {})
    print(f"  Raw Files: {file_analysis.get('total_files', 0)}")

    alerts = report.get('alerts', [])
    print(f"  Alerts: {len(alerts)} total")

    # Show alerts by type
    critical_alerts = [a for a in alerts if a['type'] == 'critical']
    warning_alerts = [a for a in alerts if a['type'] == 'warning']
    info_alerts = [a for a in alerts if a['type'] == 'info']

    if critical_alerts:
        print(f"\nCRITICAL ALERTS ({len(critical_alerts)}):")
        for alert in critical_alerts:
            print(f"  - {alert['message']}")

    if warning_alerts:
        print(f"\nWARNING ALERTS ({len(warning_alerts)}):")
        for alert in warning_alerts:
            print(f"  - {alert['message']}")

    if info_alerts:
        print(f"\nINFO ALERTS ({len(info_alerts)}):")
        for alert in info_alerts:
            print(f"  - {alert['message']}")

    print(f"\nDetailed report saved to: {report_file}")

    # Recommendations
    recommendations = report.get('recommendations', [])
    if recommendations:
        print(f"\nRecommendations:")
        for i, rec in enumerate(recommendations[:5], 1):  # Top 5 recommendations
            print(f"  {i}. {rec}")

    return report['overall_freshness_score'] >= 70

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)